"use client";

type Props = {
  running: boolean;
  speed: number;
  onSpeedChange: (s: number) => void;
  onRun: () => void;
  onStop: () => void;
  onReset: () => void;
};

const SPEEDS = [30, 60, 120, 300];

export default function ScenarioControls({
  running,
  speed,
  onSpeedChange,
  onRun,
  onStop,
  onReset,
}: Props) {
  return (
    <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
      {!running ? (
        <button
          onClick={onRun}
          className="px-3 sm:px-4 py-1.5 rounded bg-red-600 hover:bg-red-500 text-xs sm:text-sm font-medium transition-colors"
        >
          <span className="sm:hidden">Run scenario</span>
          <span className="hidden sm:inline">Run Kammuri 2019</span>
        </button>
      ) : (
        <button
          onClick={onStop}
          className="px-3 sm:px-4 py-1.5 rounded bg-amber-600 hover:bg-amber-500 text-xs sm:text-sm font-medium transition-colors"
        >
          Pause
        </button>
      )}

      <button
        onClick={onReset}
        className="px-2.5 sm:px-3 py-1.5 rounded border border-seabeacon-border hover:bg-seabeacon-panelLight text-xs sm:text-sm transition-colors"
      >
        Reset
      </button>

      <div className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm">
        <span className="text-seabeacon-dim text-[11px] sm:text-xs">Speed</span>
        <select
          value={speed}
          onChange={(e) => onSpeedChange(Number(e.target.value))}
          className="bg-seabeacon-panelLight border border-seabeacon-border rounded px-1.5 sm:px-2 py-1 text-xs sm:text-sm"
        >
          {SPEEDS.map((s) => (
            <option key={s} value={s}>
              {s}×
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
