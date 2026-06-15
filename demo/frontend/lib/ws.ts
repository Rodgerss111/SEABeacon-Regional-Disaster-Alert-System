"use client";

import { API_BASE } from "./api";

export type SseHandlers = {
  onState?: (data: any) => void;
  onTick?: (data: any) => void;
  onAlert?: (data: any) => void;
  onSignal?: (data: any) => void;
  onDone?: (data: any) => void;
  onError?: (err: Event) => void;
};

export function openScenarioStream(slug: string, handlers: SseHandlers): EventSource {
  const url = `${API_BASE}/events/${slug}`;
  const es = new EventSource(url);

  const dispatch = (name: string, cb?: (d: any) => void) =>
    es.addEventListener(name, (ev: MessageEvent) => {
      if (!cb) return;
      try {
        cb(JSON.parse(ev.data));
      } catch {
        cb(ev.data);
      }
    });

  dispatch("state", handlers.onState);
  dispatch("tick", handlers.onTick);
  dispatch("alert", handlers.onAlert);
  dispatch("signal", handlers.onSignal);
  dispatch("done", handlers.onDone);

  if (handlers.onError) {
    es.onerror = handlers.onError;
  }
  return es;
}
