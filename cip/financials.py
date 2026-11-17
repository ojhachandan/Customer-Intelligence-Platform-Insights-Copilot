"""Decimal-safe financial reconciliation and audited revenue definitions in GBP."""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from cip.datasets import get_active_dataset_id
from cip.models import OrderLine

logger = logging.getLogger(__name__)


def calculate_financial_reconciliation(
    session: Session,
    dataset_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, Any]:
    """Calculate audited, ledger-reconciled financial metrics for the chosen dataset context.
    
    Financial Measures (in GBP):
    - Gross Merchandise Sales: sum(quantity * unit_price) for SALE lines.
    - Returns: sum(quantity * unit_price) for RETURN lines (signed negative).
    - Cancellations: sum(quantity * unit_price) for CANCELLATION lines (signed negative).
    - Other Adjustments: sum(quantity * unit_price) for NON_PRODUCT_CHARGE and PRICE_ADJUSTMENT lines.
    - Net Merchandise Revenue: Gross Sales + Returns + Cancellations.
    - Total Net Ledger: Gross Sales + Returns + Cancellations + Other Adjustments.
    - Eligible Sales Invoices: count(distinct order_id) for SALE lines.
    - Cancellation Invoices: count(distinct order_id) for CANCELLATION lines.
    - Identified Customers: count(distinct customer_id) where customer_id != 'UNASSIGNED'.
    - Gross AOV: Gross Sales / Eligible Invoices.
    - Net AOV: Net Merchandise Revenue / Eligible Invoices.
    - Repeat Customer Rate: count(customers with >1 sale invoice) / count(customers with >=1 sale invoice).
    """
    ds_id = dataset_id or get_active_dataset_id(session)
    line_total = OrderLine.quantity * OrderLine.unit_price

    filters = [OrderLine.dataset_id == ds_id]
    if start_date:
        filters.append(OrderLine.ordered_at >= start_date)
    if end_date:
        filters.append(OrderLine.ordered_at < end_date)

    # 1. Core Financial Aggregation by Transaction Type
    stmt = (
        select(
            func.coalesce(func.sum(case((OrderLine.transaction_type == "SALE", line_total), else_=0.0)), 0.0).label("gross_sales"),
            func.coalesce(func.sum(case((OrderLine.transaction_type == "RETURN", line_total), else_=0.0)), 0.0).label("returns_amount"),
            func.coalesce(func.sum(case((OrderLine.transaction_type == "CANCELLATION", line_total), else_=0.0)), 0.0).label("cancellations_amount"),
            func.coalesce(func.sum(case((OrderLine.transaction_type.in_(["NON_PRODUCT_CHARGE", "PRICE_ADJUSTMENT"]), line_total), else_=0.0)), 0.0).label("adjustments_amount"),
            func.count(func.distinct(case((OrderLine.transaction_type == "SALE", OrderLine.order_id), else_=None))).label("sales_invoices"),
            func.count(func.distinct(case((OrderLine.transaction_type == "CANCELLATION", OrderLine.order_id), else_=None))).label("cancellation_invoices"),
            func.count(func.distinct(case((OrderLine.customer_id != "UNASSIGNED", OrderLine.customer_id), else_=None))).label("unique_customers"),
            func.coalesce(func.sum(case((OrderLine.transaction_type == "SALE", OrderLine.quantity), else_=0)), 0).label("gross_units"),
            func.coalesce(func.sum(case((OrderLine.transaction_type.in_(["RETURN", "CANCELLATION"]), OrderLine.quantity), else_=0)), 0).label("returned_units"),
            func.coalesce(func.sum(OrderLine.quantity), 0).label("net_units"),
        )
        .where(*filters)
    )

    row = session.execute(stmt).one()
    (
        gross_sales,
        returns_amount,
        cancellations_amount,
        adjustments_amount,
        sales_invoices,
        cancellation_invoices,
        unique_customers,
        gross_units,
        returned_units,
        net_units,
    ) = row

    gross_sales_dec = Decimal(str(round(float(gross_sales), 2)))
    returns_dec = Decimal(str(round(float(returns_amount), 2)))
    cancels_dec = Decimal(str(round(float(cancellations_amount), 2)))
    adjusts_dec = Decimal(str(round(float(adjustments_amount), 2)))

    # Net merchandise revenue: Gross + Returns + Cancellations (returns/cancels are signed negative)
    net_merch_revenue = gross_sales_dec + returns_dec + cancels_dec
    total_net_ledger = net_merch_revenue + adjusts_dec

    sales_inv_count = int(sales_invoices)
    gross_aov = round(float(gross_sales_dec) / sales_inv_count, 2) if sales_inv_count > 0 else 0.0
    net_aov = round(float(net_merch_revenue) / sales_inv_count, 2) if sales_inv_count > 0 else 0.0

    # Repeat customer rate on eligible sales invoices
    repeat_subq = (
        select(OrderLine.customer_id)
        .where(
            OrderLine.dataset_id == ds_id,
            OrderLine.customer_id != "UNASSIGNED",
            OrderLine.transaction_type == "SALE",
        )
        .group_by(OrderLine.customer_id)
        .having(func.count(func.distinct(OrderLine.order_id)) > 1)
        .subquery()
    )
    repeat_count = session.scalar(select(func.count()).select_from(repeat_subq)) or 0

    all_purchasers_subq = (
        select(OrderLine.customer_id)
        .where(
            OrderLine.dataset_id == ds_id,
            OrderLine.customer_id != "UNASSIGNED",
            OrderLine.transaction_type == "SALE",
        )
        .group_by(OrderLine.customer_id)
        .subquery()
    )
    all_purchasers_count = session.scalar(select(func.count()).select_from(all_purchasers_subq)) or 0

    repeat_rate = round(repeat_count / all_purchasers_count, 4) if all_purchasers_count > 0 else 0.0

    return {
        "dataset_id": ds_id,
        "currency": "GBP" if ds_id == "uci_online_retail_ii_v1" else "USD",
        "gross_merchandise_sales": float(gross_sales_dec),
        "returns_and_refunds": float(returns_dec),
        "cancellation_adjustments": float(cancels_dec),
        "other_adjustments": float(adjusts_dec),
        "net_merchandise_revenue": float(net_merch_revenue),
        "total_net_ledger": float(total_net_ledger),
        "eligible_sales_invoices": sales_inv_count,
        "cancellation_invoices": int(cancellation_invoices),
        "unique_identified_customers": int(unique_customers),
        "active_purchasing_customers": all_purchasers_count,
        "repeat_purchasing_customers": repeat_count,
        "repeat_customer_rate": repeat_rate,
        "gross_average_order_value": gross_aov,
        "net_average_order_value": net_aov,
        "gross_units_sold": int(gross_units),
        "returned_units": int(returned_units),
        "net_units": int(net_units),
    }

