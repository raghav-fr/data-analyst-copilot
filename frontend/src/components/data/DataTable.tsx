"use client";

interface DataTableProps {
  columns: string[];
  data: Record<string, unknown>[];
  maxRows?: number;
}

export default function DataTable({ columns, data, maxRows = 100 }: DataTableProps) {
  const rows = data.slice(0, maxRows);

  return (
    <div className="overflow-auto" style={{ maxHeight: "300px" }}>
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col} title={col}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map((col) => (
                <td key={col} title={String(row[col] ?? "")}>
                  {row[col] === null || row[col] === undefined || row[col] === ""
                    ? <span style={{ color: "var(--text-muted)", fontStyle: "italic" }}>null</span>
                    : String(row[col])
                  }
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length > maxRows && (
        <div className="py-2 text-center text-xs" style={{ color: "var(--text-muted)" }}>
          Showing {maxRows} of {data.length.toLocaleString()} rows
        </div>
      )}
    </div>
  );
}
