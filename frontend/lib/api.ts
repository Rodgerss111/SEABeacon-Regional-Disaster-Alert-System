export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
export const MAP_STYLE_URL =
  process.env.NEXT_PUBLIC_MAP_STYLE_URL ?? "https://tiles.openfreemap.org/styles/liberty";

export type Severity = "advisory" | "warning" | "urgent";

export interface TrackPoint {
  timestamp: string;
  lat: number;
  lon: number;
  max_wind_kt: number;
  pressure_mb: number;
  category: number;
}

export interface ImpactZone {
  municipality_id: number;
  municipality_name: string;
  country_code: string;
  lat: number;
  lon: number;
  severity: Severity;
  eta_hours: number;
  confidence: number;
}

export interface AlertPayload {
  id: number;
  scenario_id: number;
  country_code: string;
  municipality_id: number | null;
  severity: Severity;
  issued_at: string;
  title: string;
  body: string;
  language: string;
  lat?: number;
  lon?: number;
  municipality_name?: string;
  eta_hours?: number;
  confidence?: number;
}

export interface SignalPayload {
  id: number;
  timestamp: string;
  lat: number;
  lon: number;
  language: string;
  source_type: string;
  text: string;
  classification: "distress" | "observation" | "noise";
  confidence: number;
}

export interface ScenarioDetail {
  id: number;
  slug: string;
  name: string;
  hazard_type: string;
  start_time: string;
  end_time: string;
  description: string;
  track_points: TrackPoint[];
}

export async function getScenario(slug: string): Promise<ScenarioDetail> {
  const res = await fetch(`${API_BASE}/scenarios/${slug}`);
  if (!res.ok) throw new Error(`failed to fetch scenario: ${res.status}`);
  return res.json();
}

export async function startScenario(slug: string, speed = 60): Promise<void> {
  const res = await fetch(`${API_BASE}/scenarios/${slug}/run`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ speed }),
  });
  if (!res.ok) throw new Error(`failed to start scenario: ${res.status}`);
}

export async function stopScenario(slug: string): Promise<void> {
  const res = await fetch(`${API_BASE}/scenarios/${slug}/stop`, { method: "POST" });
  if (!res.ok) throw new Error(`failed to stop scenario: ${res.status}`);
}

export interface SeekResponse {
  scenario_slug: string;
  scenario_time: string | null;
  running: boolean;
  speed: number;
  track_so_far: TrackPoint[];
  impact_zones: ImpactZone[];
  alerts: AlertPayload[];
  signals: SignalPayload[];
  current_point: TrackPoint | null;
}

export async function seekScenario(
  slug: string,
  scenarioTime: string,
  opts: { resume?: boolean; speed?: number } = {}
): Promise<SeekResponse> {
  const res = await fetch(`${API_BASE}/scenarios/${slug}/seek`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      scenario_time: scenarioTime,
      resume: opts.resume ?? false,
      speed: opts.speed ?? 60,
    }),
  });
  if (!res.ok) throw new Error(`failed to seek: ${res.status}`);
  return res.json();
}
