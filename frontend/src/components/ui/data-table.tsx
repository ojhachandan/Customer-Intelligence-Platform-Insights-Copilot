import { Skeleton } from "./skeleton";

interface Column<T> {
  key: string;
  header: string;
  align?: "left" | "right" | "center";
  render: (row: T) => React.ReactNode;
}

export function DataTable<T>({
  columns,
  data,
  rowKey,
  onRowClick,
  emptyMessage = "No data available",
}: {
  columns: Column<T>[];
  data: T[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
}) {
  if (data.length === 0) {
    return <p className="py-12 text-center text-sm text-[var(--text-muted)]">{emptyMessage}</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm text-[var(--text-primary)]">
        <thead className="border-b border-[var(--border-subtle)] text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={`pb-3 pr-4 font-semibold ${col.align === "right" ? "text-right" : ""}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border-subtle)]">
          {data.map((row) => (
            <tr
              key={rowKey(row)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={`transition-colors duration-150 ${
                onRowClick ? "cursor-pointer hover:bg-[var(--bg-subtle)]" : "hover:bg-[var(--bg-subtle)]/50"
              }`}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={`py-3.5 pr-4 ${col.align === "right" ? "text-right font-medium" : ""}`}
                >
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DataTableSkeleton({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="space-y-4">
      <div className="flex gap-6 border-b border-[var(--border-subtle)] pb-3">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-3 w-24" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-6 py-2.5">
          {Array.from({ length: columns }).map((_, j) => (
            <Skeleton key={j} className="h-4 w-24" />
          ))}
        </div>
      ))}
    </div>
  );
}
