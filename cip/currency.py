"""Currency utilities for backend display string generation.
Source data is in USD and is converted to INR for display at USD_TO_INR.
"""
from __future__ import annotations

import math

from cip.settings import get_settings


def get_usd_to_inr_rate() -> float:
    settings = get_settings()
    rate = settings.usd_to_inr
    if not math.isfinite(rate) or rate <= 0:
        raise ValueError(f"Invalid USD_TO_INR rate: {rate}")
    return rate


def convert_usd_to_inr(amount: float) -> float:
    return round(amount * get_usd_to_inr_rate(), 2)


def to_inr(amount: float, notation: str = "indian") -> str:
    """Format USD amount into INR display string (e.g. ₹4,110 or ₹1,23,456)."""
    inr_val = round(amount * get_usd_to_inr_rate())
    is_neg = inr_val < 0
    inr_val = abs(inr_val)
    val_str = str(inr_val)

    if notation == "indian" and len(val_str) > 3:
        last3 = val_str[-3:]
        rest = val_str[:-3]
        groups = []
        while len(rest) > 2:
            groups.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.append(rest)
        groups.reverse()
        formatted = ",".join(groups) + "," + last3
    else:
        formatted = f"{inr_val:,}"

    prefix = "-₹" if is_neg else "₹"
    return f"{prefix}{formatted}"

