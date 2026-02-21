import type { DisplayData } from "../../lib/types";
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
  switch (display.type) {
    case "text":
      return <TextAnswer display={display} />;
    case "table":
      return <DataTable display={display} compact={compact} />;
    case "bar_chart":
      return <BarChartViz display={display} compact={compact} />;
    case "line_chart":
      return <LineChartViz display={display} compact={compact} />;
    case "pie_chart":
      return <PieChartViz display={display} compact={compact} />;
    case "scatter_plot":
      return <ScatterPlotViz display={display} compact={compact} />;
    default:
      return null;
  }
}
