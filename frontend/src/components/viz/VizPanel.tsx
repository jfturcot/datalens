import { useCallback, useEffect, useRef, useState } from "react";
import type { DisplayData } from "../../lib/types";
import { SQLBlock } from "../chat/SQLBlock";
import { VizRenderer } from "./VizRenderer";

interface VizPanelProps {
  display: DisplayData;
  sql?: string | null;
  onClose: () => void;
}

const MIN_WIDTH = 360;
const MAX_WIDTH_RATIO = 0.85;

export function VizPanel({ display, sql, onClose }: VizPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState<number | null>(null);
  const dragging = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(0);

  // Default to 2/3 of the parent container (the area right of sidebar)
  useEffect(() => {
    if (width !== null) return;
    const parent = panelRef.current?.parentElement;
    if (parent) {
      const available = parent.getBoundingClientRect().width;
      setWidth(Math.max(MIN_WIDTH, Math.round(available * (2 / 3))));
    } else {
      setWidth(Math.round(window.innerWidth * 0.55));
    }
  }, [width]);

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      e.preventDefault();
      dragging.current = true;
      startX.current = e.clientX;
      startWidth.current = width ?? 640;

      const onPointerMove = (ev: PointerEvent) => {
        if (!dragging.current) return;
        const delta = startX.current - ev.clientX;
        const maxWidth = window.innerWidth * MAX_WIDTH_RATIO;
        setWidth(Math.min(maxWidth, Math.max(MIN_WIDTH, startWidth.current + delta)));
      };

      const onPointerUp = () => {
        dragging.current = false;
        document.removeEventListener("pointermove", onPointerMove);
        document.removeEventListener("pointerup", onPointerUp);
      };

      document.addEventListener("pointermove", onPointerMove);
      document.addEventListener("pointerup", onPointerUp);
    },
    [width],
  );

  return (
    <div
      ref={panelRef}
      className="relative flex h-full shrink-0 flex-col border-l border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900"
      style={{ width: width ?? "66%" }}
    >
      {/* Drag handle */}
      <div
        onPointerDown={onPointerDown}
        className="absolute left-0 top-0 z-10 h-full w-1.5 cursor-col-resize hover:bg-blue-400/40 active:bg-blue-500/50"
      />

      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700">
        <h3 className="text-sm font-medium text-gray-800 dark:text-gray-200">
          {display.title ?? "Visualization"}
        </h3>
        <button
          onClick={onClose}
          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-300"
          aria-label="Close panel"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-5 w-5"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      </div>
      <div className="flex-1 overflow-auto p-4">
        <VizRenderer display={display} />
        {sql && <SQLBlock sql={sql} />}
      </div>
    </div>
  );
}
