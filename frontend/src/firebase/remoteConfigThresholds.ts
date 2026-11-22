import {
  fetchAndActivate,
  getBoolean,
  getNumber,
  getRemoteConfig,
  type RemoteConfig,
} from "firebase/remote-config";
import type { FirebaseApp } from "firebase/app";

export interface HybridRuntimeThresholds {
  shortPromptThresholdChars: number;
  longPdfThresholdChars: number;
  chunkSizeChars: number;
  forceCloudForSummaries: boolean;
}

export const DEFAULT_HYBRID_THRESHOLDS: HybridRuntimeThresholds = {
  shortPromptThresholdChars: 2500,
  longPdfThresholdChars: 60000,
  chunkSizeChars: 25000,
  forceCloudForSummaries: true,
};

function clampNumber(value: number, min: number, max: number, fallback: number): number {
  if (!Number.isFinite(value)) return fallback;
  return Math.min(max, Math.max(min, Math.round(value)));
}

export function readHybridThresholds(remoteConfig: RemoteConfig): HybridRuntimeThresholds {
  const shortPromptThresholdChars = clampNumber(
    getNumber(remoteConfig, "short_prompt_threshold_chars"),
    200,
    12000,
    DEFAULT_HYBRID_THRESHOLDS.shortPromptThresholdChars
  );

  const longPdfThresholdChars = clampNumber(
    getNumber(remoteConfig, "long_pdf_threshold_chars"),
    10000,
    300000,
    DEFAULT_HYBRID_THRESHOLDS.longPdfThresholdChars
  );

  const chunkSizeChars = clampNumber(
    getNumber(remoteConfig, "chunk_size_chars"),
    5000,
    80000,
    DEFAULT_HYBRID_THRESHOLDS.chunkSizeChars
  );

  const forceCloudForSummaries = getBoolean(remoteConfig, "force_cloud_for_summaries");

  return {
    shortPromptThresholdChars,
    longPdfThresholdChars,
    chunkSizeChars,
    forceCloudForSummaries,
  };
}

export async function loadRemoteHybridThresholds(
  firebaseApp: FirebaseApp,
  minimumFetchIntervalMillis = 60_000 // Use a short interval during hackathon testing; e.g. 3_600_000 in prod
): Promise<HybridRuntimeThresholds> {
  const rc = getRemoteConfig(firebaseApp);
  rc.settings.minimumFetchIntervalMillis = minimumFetchIntervalMillis;

  rc.defaultConfig = {
    short_prompt_threshold_chars: DEFAULT_HYBRID_THRESHOLDS.shortPromptThresholdChars,
    long_pdf_threshold_chars: DEFAULT_HYBRID_THRESHOLDS.longPdfThresholdChars,
    chunk_size_chars: DEFAULT_HYBRID_THRESHOLDS.chunkSizeChars,
    force_cloud_for_summaries: DEFAULT_HYBRID_THRESHOLDS.forceCloudForSummaries,
  };

  try {
    await fetchAndActivate(rc);
  } catch {
    // Fall back gracefully to defaultConfig / last activated cache when offline or throttled.
  }

  return readHybridThresholds(rc);
}
