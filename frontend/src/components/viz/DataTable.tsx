import type { DisplayData } from "../../lib/types";

interface DataTableProps {
  display: DisplayData;
  compact?: boolean;
}

export function DataTable({ display, compact }: DataTableProps) {
  const rows = display.data;
  const firstRow = rows[0];
  if (!firstRow) return null;

  const columns = Object.keys(firstRow);
  const visibleRows = compact ? rows.slice(0, 5) : rows;

  return (
    <div className="overflow-auto rounded-lg border border-gray-200 dark:border-gray-700">
      <table className="min-w-full text-left text-xs">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800">
            {columns.map((col) => (
              <th
                key={col}
                className="whitespace-nowrap px-3 py-2 font-medium text-gray-600 dark:text-gray-300"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visibleRows.map((row, i) => (
            <tr
              key={i}
              className="border-b border-gray-100 last:border-0 dark:border-gray-800"
            >
              {columns.map((col) => (
                <td
                  key={col}
                  className="whitespace-nowrap px-3 py-1.5 text-gray-800 dark:text-gray-200"
                >
                  {String(row[col] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {compact && rows.length > 5 && (
        <div className="border-t border-gray-200 px-3 py-1.5 text-center text-xs text-gray-400 dark:border-gray-700 dark:text-gray-500">
          {rows.length - 5} more rows...
        </div>
      )}
    </div>
  );
}
