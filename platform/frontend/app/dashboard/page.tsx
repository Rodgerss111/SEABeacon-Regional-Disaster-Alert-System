"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertPayload,
  ImpactZone,
  ScenarioDetail,
  SeekResponse,
  SignalPayload,
  TrackPoint,
  getScenario,
  seekScenario,
  startScenario,
  stopScenario,
} from "../../lib/api";
import { openScenarioStream } from "../../lib/ws";
import AlertsPanel from "../../components/AlertsPanel";
import SignalsFeed from "../../components/SignalsFeed";
import ScenarioTimeline from "../../components/Timeline/ScenarioTimeline";
import ScenarioControls from "../../components/ScenarioControls";

const AseanMap = dynamic(() => import("../../components/Map/AseanMap"), { ssr: false });

const SCENARIO_SLUG = "kammuri-2019";

type FeedTab = "alerts" | "signals";

export default function Dashboard() {
  const [scenario, setScenario] = useState<ScenarioDetail | null>(null);
  const [trackSoFar, setTrackSoFar] = useState<TrackPoint[]>([]);
  const [currentPoint, setCurrentPoint] = useState<TrackPoint | null>(null);
  const [scenarioTime, setScenarioTime] = useState<Date | null>(null);
  const [impactZones, setImpactZones] = useState<ImpactZone[]>([]);
  const [alerts, setAlerts] = useState<AlertPayload[]>([]);
  const [signals, setSignals] = useState<SignalPayload[]>([]);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(60);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<FeedTab>("alerts");

  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    getScenario(SCENARIO_SLUG)
      .then(setScenario)
      .catch((e) => setError(String(e)));
  }, []);

  const handleState = useCallback((data: any) => {
    if (data.track_so_far) setTrackSoFar(data.track_so_far);
    if (data.impact_zones) setImpactZones(data.impact_zones);
    if (data.alerts) setAlerts(data.alerts);
    if (data.signals) setSignals(data.signals);
    if (data.scenario_time) setScenarioTime(new Date(data.scenario_time));
    if (typeof data.running === "boolean") setRunning(data.running);
  }, []);

  const handleTick = useCallback((data: any) => {
    if (data.scenario_time) setScenarioTime(new Date(data.scenario_time));
    if (data.current_point) {
      const tp = data.current_point as TrackPoint;
      setCurrentPoint(tp);
      setTrackSoFar((prev) => [...prev, tp]);
    }
  }, []);

  const handleAlert = useCallback((data: any) => {
    const a = data as AlertPayload & {
      lat?: number;
      lon?: number;
      municipality_name?: string;
      eta_hours?: number;
      confidence?: number;
    };
    setAlerts((prev) => [a, ...prev]);
    if (a.lat != null && a.lon != null && a.municipality_id != null) {
      setImpactZones((prev) => {
        const key = `${a.municipality_id}:${a.severity}`;
        const exists = prev.some((z) => `${z.municipality_id}:${z.severity}` === key);
        if (exists) return prev;
        return [
          ...prev,
          {
            municipality_id: a.municipality_id!,
            municipality_name: a.municipality_name ?? "",
            country_code: a.country_code,
            lat: a.lat!,
            lon: a.lon!,
            severity: a.severity,
            eta_hours: a.eta_hours ?? 0,
            confidence: a.confidence ?? 0,
          },
        ];
      });
    }
  }, []);

  const handleSignal = useCallback((data: any) => {
    setSignals((prev) => [...prev, data as SignalPayload]);
  }, []);

  const handleDone = useCallback(() => {
    setRunning(false);
  }, []);

  const connectStream = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    const es = openScenarioStream(SCENARIO_SLUG, {
      onState: handleState,
      onTick: handleTick,
      onAlert: handleAlert,
      onSignal: handleSignal,
      onDone: handleDone,
      onError: () => {},
    });
    esRef.current = es;
  }, [handleAlert, handleDone, handleSignal, handleState, handleTick]);

  const onRun = async () => {
    setError(null);
    setTrackSoFar([]);
    setCurrentPoint(null);
    setImpactZones([]);
    setAlerts([]);
    setSignals([]);
    try {
      await startScenario(SCENARIO_SLUG, speed);
      setRunning(true);
      setTimeout(connectStream, 250);
    } catch (e: any) {
      setError(String(e?.message ?? e));
    }
  };

  const onStop = async () => {
    try {
      await stopScenario(SCENARIO_SLUG);
    } catch {}
    setRunning(false);
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  };

  const onReset = async () => {
    await onStop();
    setTrackSoFar([]);
    setCurrentPoint(null);
    setImpactZones([]);
    setAlerts([]);
    setSignals([]);
    setScenarioTime(scenario ? new Date(scenario.start_time) : null);
  };

  const applySeekSnapshot = useCallback((snap: SeekResponse) => {
    setTrackSoFar(snap.track_so_far ?? []);
    setCurrentPoint(snap.current_point ?? null);
    setImpactZones(snap.impact_zones ?? []);
    setAlerts(snap.alerts ?? []);
    setSignals(snap.signals ?? []);
    setScenarioTime(snap.scenario_time ? new Date(snap.scenario_time) : null);
  }, []);

  const onSeek = async (target: Date) => {
    if (!scenario) return;
    const isoNaive = target.toISOString().replace(/\.\d+Z$/, "").replace(/Z$/, "");
    const wasRunning = running;

    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }

    try {
      const snap = await seekScenario(scenario.slug, isoNaive, {
        resume: wasRunning,
        speed,
      });
      applySeekSnapshot(snap);
      setRunning(snap.running);
      if (snap.running) {
        setTimeout(connectStream, 200);
      }
    } catch (e: any) {
      setError(String(e?.message ?? e));
    }
  };

  useEffect(() => {
    return () => {
      esRef.current?.close();
    };
  }, []);

  const scenarioStart = useMemo(
    () => (scenario ? new Date(scenario.start_time) : null),
    [scenario]
  );
  const scenarioEnd = useMemo(
    () => (scenario ? new Date(scenario.end_time) : null),
    [scenario]
  );

  const visibleAlertsCount = alerts.filter((a) => a.language === "en").length;

  return (
    <main className="min-h-[100dvh] flex flex-col bg-[#0a0e14] text-seabeacon-text">
      <header className="flex flex-wrap items-center justify-between gap-3 px-4 sm:px-5 py-3 border-b border-seabeacon-border">
        <div className="flex items-baseline gap-3 flex-wrap min-w-0">
          <span className="text-base sm:text-lg font-semibold tracking-tight">SEABeacon</span>
          <span className="text-[11px] sm:text-xs text-seabeacon-dim truncate max-w-[60vw] sm:max-w-none">
            {scenario?.name ?? "loading…"}
          </span>
        </div>
        <ScenarioControls
          running={running}
          speed={speed}
          onSpeedChange={setSpeed}
          onRun={onRun}
          onStop={onStop}
          onReset={onReset}
        />
      </header>

      {error && (
        <div className="bg-red-900/40 text-red-200 text-sm px-4 sm:px-5 py-2 border-b border-red-800">
          {error}
        </div>
      )}

      {/* Main area: stacked on mobile, side-by-side on lg+. */}
      <div className="flex-1 flex flex-col lg:flex-row min-h-0">
        {/* Map */}
        <div className="relative w-full h-[55vh] sm:h-[60vh] lg:h-auto lg:flex-1 min-h-0">
          <AseanMap
            trackSoFar={trackSoFar}
            currentPoint={currentPoint}
            impactZones={impactZones}
            alerts={alerts}
            signals={signals}
          />
        </div>

        {/* Side / bottom panel */}
        <aside className="w-full lg:w-[380px] xl:w-[420px] border-t lg:border-t-0 lg:border-l border-seabeacon-border flex flex-col min-h-0 flex-1 lg:flex-none">
          {/* Mobile/tablet: tab switcher. Desktop (lg+): both panels stacked. */}
          <div className="flex border-b border-seabeacon-border lg:hidden" role="tablist">
            <button
              role="tab"
              aria-selected={activeTab === "alerts"}
              onClick={() => setActiveTab("alerts")}
              className={`flex-1 px-4 py-2 text-xs uppercase tracking-wider font-semibold border-b-2 transition-colors ${
                activeTab === "alerts"
                  ? "border-red-500 text-seabeacon-text"
                  : "border-transparent text-seabeacon-dim hover:text-seabeacon-text"
              }`}
            >
              Alerts ({visibleAlertsCount})
            </button>
            <button
              role="tab"
              aria-selected={activeTab === "signals"}
              onClick={() => setActiveTab("signals")}
              className={`flex-1 px-4 py-2 text-xs uppercase tracking-wider font-semibold border-b-2 transition-colors ${
                activeTab === "signals"
                  ? "border-sky-400 text-seabeacon-text"
                  : "border-transparent text-seabeacon-dim hover:text-seabeacon-text"
              }`}
            >
              Signals ({signals.length})
            </button>
          </div>

          {/* Mobile/tablet single-pane content. */}
          <div className="lg:hidden flex-1 min-h-0">
            {activeTab === "alerts" ? (
              <AlertsPanel alerts={alerts} hideHeader />
            ) : (
              <SignalsFeed signals={signals} hideHeader />
            )}
          </div>

          {/* Desktop split: alerts top, signals bottom. */}
          <div className="hidden lg:flex flex-col flex-1 min-h-0">
            <div className="flex-1 min-h-0 border-b border-seabeacon-border">
              <AlertsPanel alerts={alerts} />
            </div>
            <div className="flex-1 min-h-0">
              <SignalsFeed signals={signals} />
            </div>
          </div>
        </aside>
      </div>

      <footer className="px-4 sm:px-5 py-3 border-t border-seabeacon-border">
        <ScenarioTimeline
          scenarioStart={scenarioStart}
          scenarioEnd={scenarioEnd}
          scenarioTime={scenarioTime}
          onSeek={onSeek}
          disabled={!scenario}
        />
      </footer>
    </main>
  );
}
