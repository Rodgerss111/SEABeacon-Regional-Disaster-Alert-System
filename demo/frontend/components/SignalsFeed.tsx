"use client";

import { SignalPayload } from "../lib/api";

const CLASS_COLOR: Record<string, string> = {
  distress: "text-red-400",
  observation: "text-sky-300",
  noise: "text-neutral-400",
};

function formatTime(iso: string) {
  return new Date(iso).toISOString().slice(5, 16).replace("T", " ");
}

type Props = {
  signals: SignalPayload[];
  hideHeader?: boolean;
};

export default function SignalsFeed({ signals, hideHeader }: Props) {
  return (
    <div className="flex flex-col h-full">
      {!hideHeader && (
        <div className="px-4 py-3 border-b border-seabeacon-border flex items-baseline justify-between">
          <h2 className="font-semibold text-sm uppercase tracking-wider">Signals</h2>
          <span className="text-xs text-seabeacon-dim">{signals.length}</span>
        </div>
      )}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {signals.length === 0 ? (
          <div className="px-4 py-6 text-sm text-seabeacon-dim">No signals yet.</div>
        ) : (
          signals.slice().reverse().map((s) => (
            <div
              key={s.id}
              className="mx-3 my-2 px-3 py-2 rounded bg-seabeacon-panelLight border border-seabeacon-border"
            >
              <div className="flex items-baseline justify-between gap-2 mb-1 flex-wrap">
                <span className={`text-[11px] uppercase tracking-wider ${CLASS_COLOR[s.classification]}`}>
                  {s.classification} · {s.language} · {s.source_type}
                </span>
                <span className="text-[11px] text-seabeacon-dim">{formatTime(s.timestamp)}</span>
              </div>
              <div className="text-sm leading-snug break-words">{s.text}</div>
              <div className="mt-1 text-[11px] text-seabeacon-dim">
                conf {(s.confidence * 100).toFixed(0)}%
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
