import { Component, type ReactNode, useMemo } from "react";
import type { DisplayData } from "../../lib/types";
import { repairDisplay } from "../../lib/displayRepair";
import { TextAnswer } from "./TextAnswer";
import { DataTable } from "./DataTable";
import { BarChartViz } from "./BarChartViz";
import { LineChartViz } from "./LineChartViz";
import { PieChartViz } from "./PieChartViz";
import { ScatterPlotViz } from "./ScatterPlotViz";

class VizErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    console.warn("VizRenderer: render error", error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <p className="text-xs text-gray-400 italic">
          Unable to render visualization
        </p>
      );
    }
    return this.props.children;
  }
}

interface VizRendererProps {
  display: DisplayData;
  compact?: boolean;
}

export function VizRenderer({ display, compact }: VizRendererProps) {
  const repaired = useMemo(() => repairDisplay(display), [display]);

  return (
    <VizErrorBoundary>
      <VizRendererInner display={repaired} compact={compact} />
    </VizErrorBoundary>
  );
}

const VIZ_ERROR = (
  <p className="text-xs text-gray-400 italic">
    Unable to render visualization
  </p>
);

function VizRendererInner({ display, compact }: VizRendererProps) {
  if (!display.data || display.data.length === 0) return VIZ_ERROR;

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
      return VIZ_ERROR;
  }
}
