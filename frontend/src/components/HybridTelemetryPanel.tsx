import React from "react";
import type { TelemetryEvent } from "../ai/hybridInference";

interface HybridTelemetryPanelProps {
  events: TelemetryEvent[];
  onClear?: () => void;
}

export const HybridTelemetryBadge: React.FC<{ latest?: TelemetryEvent }> = ({ latest }) => {
  if (!latest) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
        <span className="h-2 w-2 rounded-full bg-slate-400" />
        Hybrid AI: Ready
      </span>
    );
  }

  const isOnDevice = latest.actualSource === "ON_DEVICE";
  const badgeClasses = isOnDevice
    ? "bg-emerald-100 text-emerald-800 border-emerald-200"
    : "bg-sky-100 text-sky-800 border-sky-200";
  const dotClasses = isOnDevice ? "bg-emerald-500" : "bg-sky-500";

  return (
    <div className="inline-flex flex-wrap items-center gap-2">
      <span
        className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${badgeClasses}`}
      >
        <span className={`h-2 w-2 rounded-full ${dotClasses}`} />
        {isOnDevice ? "On-Device (Local)" : "Cloud (Gemini)"}
      </span>

      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-700">
        {latest.latencyMs} ms
      </span>

      {latest.fallbackOccurred && (
        <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800">
          Fell back to cloud
        </span>
      )}
    </div>
  );
};

export const HybridTelemetryPanel: React.FC<HybridTelemetryPanelProps> = ({ events, onClear }) => {
  const latest = events[events.length - 1];
  const onDeviceCount = events.filter((e) => e.actualSource === "ON_DEVICE").length;
  const cloudCount = events.filter((e) => e.actualSource === "IN_CLOUD").length;

  return (
    <section
      aria-label="Hybrid AI Telemetry"
      className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2.5">
          <h3 className="text-sm font-semibold text-slate-900">Hybrid Inference Telemetry</h3>
          <HybridTelemetryBadge latest={latest} />
        </div>

        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span>Local: {onDeviceCount}</span>
          <span>Cloud: {cloudCount}</span>
          {onClear && events.length > 0 && (
            <button
              type="button"
              onClick={onClear}
              className="rounded border border-slate-200 px-2 py-0.5 text-slate-600 hover:bg-slate-50"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {events.length === 0 ? (
        <p className="mt-3 text-xs text-slate-500">
          No inference calls logged yet. Ask a quick study question or summarize a PDF to see live
          on-device vs. cloud execution.
        </p>
      ) : (
        <ul className="mt-3 max-h-60 space-y-2 overflow-y-auto pr-1">
          {[...events].reverse().map((ev) => (
            <li
              key={ev.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`rounded px-1.5 py-0.5 font-semibold ${
                    ev.actualSource === "ON_DEVICE"
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-sky-100 text-sky-800"
                  }`}
                >
                  {ev.actualSource}
                </span>
                <span className="font-medium text-slate-800">{ev.taskType}</span>
                {ev.fallbackOccurred && (
                  <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[11px] text-amber-800">
                    fallback
                  </span>
                )}
              </div>

              <div className="flex items-center gap-3 text-slate-600">
                <span>
                  {ev.inputChars.toLocaleString()} → {ev.outputChars.toLocaleString()} chars
                </span>
                <span className="font-mono font-medium text-slate-800">{ev.latencyMs} ms</span>
                <span className="font-mono text-[11px] text-slate-400">
                  {new Date(ev.timestamp).toLocaleTimeString()}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};
