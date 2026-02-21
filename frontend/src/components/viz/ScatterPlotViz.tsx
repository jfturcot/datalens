import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { DisplayData } from "../../lib/types";

interface ScatterPlotVizProps {
  display: DisplayData;
  compact?: boolean;
}

export function ScatterPlotViz({ display, compact }: ScatterPlotVizProps) {
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
        <ScatterChart margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
          <XAxis
            dataKey={x_axis}
            name={x_axis}
            tick={{ fontSize: compact ? 10 : 12 }}
            className="fill-gray-600 dark:fill-gray-400"
          />
          <YAxis
            dataKey={y_axis}
            name={y_axis}
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
            cursor={{ strokeDasharray: "3 3" }}
          />
          <Scatter data={data as Record<string, string | number>[]} fill="#3b82f6" />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
