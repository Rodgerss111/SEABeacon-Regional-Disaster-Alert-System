"use client";

import { useEffect, useRef } from "react";
import maplibregl, { Map as MlMap } from "maplibre-gl";
import { MAP_STYLE_URL, ImpactZone, TrackPoint, AlertPayload, SignalPayload } from "../../lib/api";

type Props = {
  trackSoFar: TrackPoint[];
  currentPoint: TrackPoint | null;
  impactZones: ImpactZone[];
  alerts: AlertPayload[];
  signals: SignalPayload[];
};

const SEVERITY_COLOR: Record<string, string> = {
  urgent: "#dc2626",
  warning: "#f59e0b",
  advisory: "#facc15",
};
const SEVERITY_OPACITY: Record<string, number> = {
  urgent: 0.30,
  warning: 0.25,
  advisory: 0.20,
};
const SEVERITY_RADIUS_KM: Record<string, number> = {
  urgent: 90,
  warning: 160,
  advisory: 240,
};

function metersToPixelsAtMaxZoom(meters: number, latitude: number) {
  return meters / 0.075 / Math.cos((latitude * Math.PI) / 180);
}

export default function AseanMap({
  trackSoFar,
  currentPoint,
  impactZones,
  alerts,
  signals,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MlMap | null>(null);
  const loadedRef = useRef(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE_URL,
      center: [118.0, 14.0],
      zoom: 4.2,
      attributionControl: { compact: true },
    });
    mapRef.current = map;

    map.on("load", () => {
      loadedRef.current = true;

      map.addSource("track", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "track-line",
        type: "line",
        source: "track",
        paint: {
          "line-color": "#60a5fa",
          "line-width": 3,
          "line-opacity": 0.85,
        },
      });

      map.addSource("storm", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "storm-eye",
        type: "circle",
        source: "storm",
        paint: {
          "circle-radius": 9,
          "circle-color": "#ef4444",
          "circle-stroke-color": "#fff",
          "circle-stroke-width": 2,
        },
      });

      map.addSource("impact", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "impact-fill",
        type: "circle",
        source: "impact",
        paint: {
          "circle-radius": ["get", "px_radius"],
          "circle-color": ["get", "color"],
          "circle-opacity": ["get", "opacity"],
          "circle-stroke-color": ["get", "color"],
          "circle-stroke-width": 1,
          "circle-stroke-opacity": 0.7,
        },
      });

      map.addSource("muni-points", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "muni-dots",
        type: "circle",
        source: "muni-points",
        paint: {
          "circle-radius": 4,
          "circle-color": ["get", "color"],
          "circle-stroke-color": "#fff",
          "circle-stroke-width": 1,
        },
      });

      map.addSource("signals", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "signals-dots",
        type: "circle",
        source: "signals",
        paint: {
          "circle-radius": 5,
          "circle-color": [
            "match",
            ["get", "classification"],
            "distress", "#f43f5e",
            "observation", "#38bdf8",
            "noise", "#a3a3a3",
            "#94a3b8",
          ],
          "circle-stroke-color": "#0a0e14",
          "circle-stroke-width": 1.5,
        },
      });

      map.on("click", "signals-dots", (e: any) => {
        const f = e.features?.[0];
        if (!f) return;
        new maplibregl.Popup({ offset: 12 })
          .setLngLat(f.geometry.coordinates)
          .setHTML(
            `<div style="color:#0a0e14;font-size:12px;max-width:240px;">
              <div style="font-weight:600;margin-bottom:4px;">${f.properties.language} · ${f.properties.classification}</div>
              <div>${f.properties.text}</div>
              <div style="margin-top:4px;color:#475569;">conf ${(f.properties.confidence * 100).toFixed(0)}%</div>
            </div>`
          )
          .addTo(map);
      });

      map.on("click", "muni-dots", (e: any) => {
        const f = e.features?.[0];
        if (!f) return;
        new maplibregl.Popup({ offset: 10 })
          .setLngLat(f.geometry.coordinates)
          .setHTML(
            `<div style="color:#0a0e14;font-size:12px;">
              <div style="font-weight:600;">${f.properties.name}</div>
              <div>${f.properties.severity.toUpperCase()} · ETA ${f.properties.eta_hours}h</div>
            </div>`
          )
          .addTo(map);
      });
    });

    return () => {
      map.remove();
      mapRef.current = null;
      loadedRef.current = false;
    };
  }, []);

  // Track polyline
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    const src = map.getSource("track") as maplibregl.GeoJSONSource | undefined;
    if (!src) return;
    src.setData({
      type: "FeatureCollection",
      features: trackSoFar.length >= 2
        ? [{
            type: "Feature",
            geometry: {
              type: "LineString",
              coordinates: trackSoFar.map((p) => [p.lon, p.lat]),
            },
            properties: {},
          }]
        : [],
    } as any);
  }, [trackSoFar]);

  // Storm eye
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    const src = map.getSource("storm") as maplibregl.GeoJSONSource | undefined;
    if (!src) return;
    src.setData({
      type: "FeatureCollection",
      features: currentPoint
        ? [{
            type: "Feature",
            geometry: { type: "Point", coordinates: [currentPoint.lon, currentPoint.lat] },
            properties: { wind: currentPoint.max_wind_kt, cat: currentPoint.category },
          }]
        : [],
    } as any);
  }, [currentPoint]);

  // Impact zones (rendered as circles sized in pixels per severity)
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    const src = map.getSource("impact") as maplibregl.GeoJSONSource | undefined;
    const muniSrc = map.getSource("muni-points") as maplibregl.GeoJSONSource | undefined;
    if (!src || !muniSrc) return;

    const features = impactZones.map((z) => {
      const radiusKm = SEVERITY_RADIUS_KM[z.severity] ?? 100;
      const pxRadius = Math.max(15, metersToPixelsAtMaxZoom(radiusKm * 1000, z.lat) * Math.pow(2, map.getZoom() - 22));
      return {
        type: "Feature" as const,
        geometry: { type: "Point" as const, coordinates: [z.lon, z.lat] },
        properties: {
          color: SEVERITY_COLOR[z.severity],
          opacity: SEVERITY_OPACITY[z.severity],
          severity: z.severity,
          px_radius: pxRadius,
          name: z.municipality_name,
        },
      };
    });
    src.setData({ type: "FeatureCollection", features } as any);

    const muniFeatures = impactZones.map((z) => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [z.lon, z.lat] },
      properties: {
        name: z.municipality_name,
        severity: z.severity,
        eta_hours: z.eta_hours,
        color: SEVERITY_COLOR[z.severity],
      },
    }));
    muniSrc.setData({ type: "FeatureCollection", features: muniFeatures } as any);
  }, [impactZones]);

  // Signals
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    const src = map.getSource("signals") as maplibregl.GeoJSONSource | undefined;
    if (!src) return;
    src.setData({
      type: "FeatureCollection",
      features: signals.map((s) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [s.lon, s.lat] },
        properties: {
          text: s.text,
          language: s.language,
          classification: s.classification,
          confidence: s.confidence,
        },
      })),
    } as any);
  }, [signals]);

  return <div ref={containerRef} className="absolute inset-0" />;
}
