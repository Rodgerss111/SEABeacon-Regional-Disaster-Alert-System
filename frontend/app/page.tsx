import Link from "next/link";

export default function Landing() {
  return (
    <main className="min-h-[100dvh] flex items-center justify-center px-5 sm:px-8 py-10">
      <div className="max-w-2xl w-full">
        <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-4">SEABeacon</h1>
        <p className="text-sm sm:text-base text-seabeacon-dim mb-2 leading-relaxed">
          Cross-border disaster early-warning for ASEAN. SEABeacon ingests storm
          tracks, predicts impact zones, and pushes localized alerts to citizens
          in their language — across borders, before national systems often act.
        </p>
        <p className="text-sm sm:text-base text-seabeacon-dim mb-8 leading-relaxed">
          This is a hackathon demo. The current scenario replays Typhoon Kammuri
          (December 2019).
        </p>
        <div className="flex flex-col sm:flex-row gap-3">
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center px-5 py-2.5 rounded bg-red-600 hover:bg-red-500 text-white font-medium transition-colors"
          >
            Open dashboard
          </Link>
          <a
            href="https://t.me/"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center px-5 py-2.5 rounded border border-seabeacon-border hover:bg-seabeacon-panelLight text-sm transition-colors"
          >
            Subscribe via Telegram
          </a>
        </div>
      </div>
    </main>
  );
}
