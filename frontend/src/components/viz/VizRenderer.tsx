import { useMemo } from "react";
import type { DisplayData } from "../../lib/types";
import { repairDisplay } from "../../lib/displayRepair";
import { TextAnswer } from "./TextAnswer";
import { DataTable } from "./DataTable";
import { BarChartViz } from "./BarChartViz";
import { LineChartViz } from "./LineChartViz";
import { PieChartViz } from "./PieChartViz";
import { ScatterPlotViz } from "./ScatterPlotViz";

interface VizRendererProps {
  display: DisplayData;
  compact?: boolean;
}

export function VizRenderer({ display, compact }: VizRendererProps) {
  const repaired = useMemo(() => repairDisplay(display), [display]);

  switch (repaired.type) {
    case "text":
      return <TextAnswer display={repaired} />;
    case "table":
      return <DataTable display={repaired} compact={compact} />;
    case "bar_chart":
      return <BarChartViz display={repaired} compact={compact} />;
    case "line_chart":
      return <LineChartViz display={repaired} compact={compact} />;
    case "pie_chart":
      return <PieChartViz display={repaired} compact={compact} />;
    case "scatter_plot":
      return <ScatterPlotViz display={repaired} compact={compact} />;
    default:
      return null;
  }
}
