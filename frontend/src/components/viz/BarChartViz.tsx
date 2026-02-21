import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { DisplayData } from "../../lib/types";

interface BarChartVizProps {
  display: DisplayData;
  compact?: boolean;
}

export function BarChartViz({ display, compact }: BarChartVizProps) {
  const { data, x_axis, y_axis, title } = display;
  if (!x_axis || !y_axis || data.length === 0) return null;

  const height = compact ? 200 : 400;

  return (
    <div className="flex flex-col gap-2">
      {title && (
        <h4 className="text-xs font-medium text-gray-600 dark:text-gray-300">
          {title}
        </h4>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data as Record<string, string | number>[]} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
          <XAxis
            dataKey={x_axis}
            tick={{ fontSize: compact ? 10 : 12 }}
            className="fill-gray-600 dark:fill-gray-400"
          />
          <YAxis
            tick={{ fontSize: compact ? 10 : 12 }}
            className="fill-gray-600 dark:fill-gray-400"
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--tooltip-bg, #fff)",
              borderColor: "var(--tooltip-border, #e5e7eb)",
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <Bar dataKey={y_axis} fill="#3b82f6" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
