import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { DisplayData } from "../../lib/types";

interface PieChartVizProps {
  display: DisplayData;
  compact?: boolean;
}

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4", "#f97316"];

export function PieChartViz({ display, compact }: PieChartVizProps) {
  const { data, label_key, value_key, title } = display;
  if (!label_key || !value_key || data.length === 0) return null;

  const height = compact ? 200 : 400;

  return (
    <div className="flex flex-col gap-2">
      {title && (
        <h4 className="text-xs font-medium text-gray-600 dark:text-gray-300">
          {title}
        </h4>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={data as Record<string, string | number>[]}
            dataKey={value_key}
            nameKey={label_key}
            cx="50%"
            cy="50%"
            outerRadius={compact ? 60 : 140}
            innerRadius={compact ? 30 : 70}
            paddingAngle={2}
            label={!compact}
          >
            {data.map((_, index) => (
              <Cell key={index} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--tooltip-bg, #fff)",
              borderColor: "var(--tooltip-border, #e5e7eb)",
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          {!compact && <Legend />}
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
