"use client";

import { useEffect, useRef, useState } from "react";

type Props = {
  scenarioStart: Date | null;
  scenarioEnd: Date | null;
  scenarioTime: Date | null;
  onSeek?: (target: Date) => void; // committed value (drag end / click)
  onSeekPreview?: (target: Date) => void; // throttled preview while dragging
  disabled?: boolean;
};

function fmtFull(d: Date | null) {
  if (!d) return "—";
  return d.toISOString().slice(0, 16).replace("T", " ") + " UTC";
}

function fmtShort(d: Date | null) {
  if (!d) return "—";
  return d.toISOString().slice(5, 16).replace("T", " ");
}

export default function ScenarioTimeline({
  scenarioStart,
  scenarioEnd,
  scenarioTime,
  onSeek,
  onSeekPreview,
  disabled,
}: Props) {
  const [dragValueMs, setDragValueMs] = useState<number | null>(null);
  const previewTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastPreview = useRef<number>(0);

  // Reset local drag state when external scenarioTime changes (e.g. tick from SSE).
  useEffect(() => {
    if (dragValueMs === null) return;
    // If user finishes dragging and external time matches, clear.
    if (scenarioTime && Math.abs(scenarioTime.getTime() - dragValueMs) < 60_000) {
      setDragValueMs(null);
    }
  }, [scenarioTime, dragValueMs]);

  if (!scenarioStart || !scenarioEnd) {
    return (
      <div className="h-2 bg-seabeacon-panelLight rounded-full overflow-hidden">
        <div className="h-full bg-red-500" style={{ width: "0%" }} />
      </div>
    );
  }

  const startMs = scenarioStart.getTime();
  const endMs = scenarioEnd.getTime();
  const totalMs = Math.max(1, endMs - startMs);

  const liveMs = scenarioTime ? scenarioTime.getTime() : startMs;
  const valueMs = dragValueMs ?? liveMs;
  const progress = Math.max(0, Math.min(1, (valueMs - startMs) / totalMs));

  const displayTime = new Date(valueMs);

  const stepMs = 30 * 60 * 1000; // 30-min ticks

  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = Number(e.target.value);
    setDragValueMs(v);

    if (onSeekPreview) {
      // Throttle preview to ~6/s.
      const now = Date.now();
      if (now - lastPreview.current > 160) {
        lastPreview.current = now;
        onSeekPreview(new Date(v));
      } else if (previewTimer.current === null) {
        previewTimer.current = setTimeout(() => {
          previewTimer.current = null;
          onSeekPreview(new Date(v));
        }, 160);
      }
    }
  };

  const commitSeek = () => {
    if (dragValueMs === null) return;
    if (previewTimer.current !== null) {
      clearTimeout(previewTimer.current);
      previewTimer.current = null;
    }
    onSeek?.(new Date(dragValueMs));
  };

  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 w-full">
      <span className="hidden sm:block text-xs text-seabeacon-dim w-44 shrink-0">
        {fmtFull(scenarioStart)}
      </span>

      <div className="relative flex-1 h-6 flex items-center">
        <div className="absolute inset-x-0 h-2 bg-seabeacon-panelLight rounded-full overflow-hidden">
          <div
            className="h-full bg-red-500 transition-[width] duration-150"
            style={{ width: `${(progress * 100).toFixed(2)}%` }}
          />
        </div>
        <input
          type="range"
          min={startMs}
          max={endMs}
          step={stepMs}
          value={valueMs}
          disabled={disabled}
          onChange={onChange}
          onMouseUp={commitSeek}
          onTouchEnd={commitSeek}
          onKeyUp={commitSeek}
          aria-label="Scrub scenario timeline"
          className="seabeacon-slider absolute inset-0 w-full h-6 appearance-none bg-transparent cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
        />
      </div>

      <span className="hidden sm:block text-xs text-seabeacon-dim w-44 shrink-0 text-right">
        {fmtFull(scenarioEnd)}
      </span>

      <span className="text-xs font-medium sm:ml-2 sm:w-44 sm:text-right">
        <span className="sm:hidden text-seabeacon-dim">Now: </span>
        <span className="hidden sm:inline">{fmtFull(displayTime)}</span>
        <span className="sm:hidden">{fmtShort(displayTime)}</span>
      </span>
    </div>
  );
}
