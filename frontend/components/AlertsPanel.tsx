"use client";

import { AlertPayload } from "../lib/api";

const SEVERITY_LABEL: Record<string, string> = {
  urgent: "URGENT",
  warning: "WARNING",
  advisory: "ADVISORY",
};

const SEVERITY_BORDER: Record<string, string> = {
  urgent: "border-red-500",
  warning: "border-amber-500",
  advisory: "border-yellow-300",
};

function formatTime(iso: string) {
  const d = new Date(iso);
  return d.toISOString().slice(5, 16).replace("T", " ");
}

type Props = {
  alerts: AlertPayload[];
  hideHeader?: boolean;
};

export default function AlertsPanel({ alerts, hideHeader }: Props) {
  // Show only English alerts in the panel — judges read English.
  const filtered = alerts.filter((a) => a.language === "en");

  return (
    <div className="flex flex-col h-full">
      {!hideHeader && (
        <div className="px-4 py-3 border-b border-seabeacon-border flex items-baseline justify-between">
          <h2 className="font-semibold text-sm uppercase tracking-wider">Alerts</h2>
          <span className="text-xs text-seabeacon-dim">{filtered.length}</span>
        </div>
      )}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {filtered.length === 0 ? (
          <div className="px-4 py-6 text-sm text-seabeacon-dim">
            No alerts yet. Start the scenario to begin replay.
          </div>
        ) : (
          filtered.map((a) => (
            <div
              key={a.id}
              className={`mx-3 my-2 px-3 py-2.5 rounded border-l-4 ${SEVERITY_BORDER[a.severity]} bg-seabeacon-panelLight`}
            >
              <div className="flex items-baseline justify-between gap-2 mb-1 flex-wrap">
                <span className={`text-[11px] font-semibold severity-${a.severity}`}>
                  {SEVERITY_LABEL[a.severity]} · {a.country_code}
                </span>
                <span className="text-[11px] text-seabeacon-dim">{formatTime(a.issued_at)} UTC</span>
              </div>
              <div className="text-sm font-medium leading-snug mb-1 break-words">{a.title}</div>
              <div className="text-xs text-seabeacon-dim leading-relaxed break-words">{a.body}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
