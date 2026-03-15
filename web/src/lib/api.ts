/**
 * API client helpers — equivalent to sports-data-admin's web/src/lib/api.ts.
 *
 * All API calls go through the Next.js proxy (/api/*) which forwards
 * to the FastAPI backend with the X-API-Key header.
 */

const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "dev-key-do-not-use-in-production";

interface FetchOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

/**
 * Fetch from the API with authentication and error handling.
 */
export async function fetchAPI<T = unknown>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { params, ...init } = options;

  // Build URL with query params
  let url = `/api${endpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) {
        searchParams.set(key, String(value));
      }
    }
    const qs = searchParams.toString();
    if (qs) url += `?${qs}`;
  }

  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
      ...init.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API error ${response.status}: ${error}`);
  }

  return response.json();
}

// ── Typed API functions ────────────────────────────────────────────────────

export interface Asset {
  id: number;
  asset_class_code: string | null;
  ticker: string;
  name: string;
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  exchange: string | null;
  is_active: boolean;
  last_price_at: string | null;
}

export interface MarketSession {
  id: number;
  asset_id: number;
  session_date: string;
  open_price: number | null;
  high_price: number | null;
  low_price: number | null;
  close_price: number | null;
  volume: number | null;
  change_pct: number | null;
  status: string;
}

export interface AlphaSignal {
  id: number;
  asset_id: number;
  signal_type: string;
  direction: string;
  strength: number;
  confidence_tier: string;
  ev_estimate: number | null;
  trigger_price: number | null;
  target_price: number | null;
  stop_loss: number | null;
  risk_reward_ratio: number | null;
  detected_at: string;
  expires_at: string | null;
  outcome: string | null;
  disabled_reason: string | null;
  derivation: Record<string, unknown> | null;
}

export interface ArbitrageOpportunity {
  asset_id: number;
  pair_key: string;
  exchange: string;
  price: number;
  bid: number | null;
  ask: number | null;
  spread_vs_reference: number | null;
  arb_pct: number | null;
  reference_exchange: string | null;
  observed_at: string;
}

export interface SentimentSnapshot {
  id: number;
  asset_id: number | null;
  fear_greed_index: number | null;
  social_volume: number | null;
  bullish_pct: number | null;
  bearish_pct: number | null;
  weighted_sentiment: number | null;
  observed_at: string;
}

export interface MarketAnalysis {
  id: number;
  asset_id: number;
  analysis_date: string;
  summary: string | null;
  key_moments_json: Record<string, unknown> | null;
  narrative_blocks_json: Record<string, unknown> | null;
  generated_by: string | null;
  generated_at: string | null;
}

export interface ScrapeRun {
  id: number;
  scraper_type: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  assets_processed: number | null;
  records_created: number | null;
  error_details: string | null;
}

export interface TaskRegistryEntry {
  name: string;
  description: string;
  params: string[];
  asset_classes: string[];
}

export interface JobRun {
  id: number;
  phase: string;
  asset_classes: string[] | null;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  error_summary: string | null;
  summary_data: Record<string, unknown> | null;
  created_at: string | null;
}

export interface JobRunFilters {
  phase?: string;
  status?: string;
  limit?: number;
}

export interface TriggerTaskResponse {
  job_id: string;
  task_name: string;
  status: string;
}

export interface DataConflict {
  id: number;
  conflict_type: string;
  source: string | null;
  description: string | null;
  resolved_at: string | null;
}

export interface EconomicIndicator {
  id: number;
  series_id: string;
  series_name: string;
  category: string;
  value: number;
  observation_date: string;
  source: string;
  created_at: string | null;
}

export interface LatestIndicator {
  series_id: string;
  series_name: string;
  category: string;
  value: number;
  observation_date: string;
  source: string;
}

export interface Candle {
  id: number;
  asset_id: number;
  timestamp: string;
  interval: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  vwap: number | null;
}

export interface PipelineRunResult {
  job_run_id: number;
  asset_id: number;
  session_date: string;
  status: string;
  stages_run: number;
  duration_seconds: number;
  stage_results: PipelineStageResult[];
}

export interface PipelineStageResult {
  stage: string;
  success: boolean;
  duration_ms: number;
  error: string | null;
}

export interface NarrativeBlock {
  role: string;
  narrative: string;
  word_count: number;
}

export interface SessionEvent {
  timestamp: string;
  event_type: string;
  role: string;
  description: string;
  price: number | null;
  volume: number | null;
}

export interface DiagnosticsInfo {
  db_pool: Record<string, unknown> | string;
  realtime: {
    boot_epoch: number;
    total_connections: number;
    total_channels: number;
    channels: Record<string, number>;
    publish_count: number;
    error_count: number;
  };
  poller: {
    poll_count: Record<string, number>;
    last_poll_duration_ms: Record<string, number>;
    last_poll_at: Record<string, string | null>;
  };
}

export interface HealthStatus {
  status: string;
  app: string;
  db: string;
  redis: string;
  celery: string;
}

export interface DockerLogsResponse {
  container: string;
  lines: number;
  logs: string;
}

// ── API Calls ──────────────────────────────────────────────────────────────

export const api = {
  // Markets
  listAssets: (params?: { asset_class?: string; sector?: string }) =>
    fetchAPI<Asset[]>("/markets/assets", { params }),

  getAsset: (id: number) => fetchAPI<Asset>(`/markets/assets/${id}`),

  listSessions: (params?: { asset_id?: number; asset_class?: string; limit?: number }) =>
    fetchAPI<MarketSession[]>("/markets/sessions", { params }),

  listAssetSessions: (assetId: number, params?: { start_date?: string; end_date?: string; limit?: number }) =>
    fetchAPI<MarketSession[]>(`/markets/assets/${assetId}/sessions`, { params }),

  // Signals
  listSignals: (params?: {
    signal_type?: string;
    confidence_tier?: string;
    direction?: string;
    outcome?: string;
    min_strength?: number;
    limit?: number;
  }) => fetchAPI<AlphaSignal[]>("/signals/alpha", { params }),

  listArbitrage: (params?: { asset_id?: number; min_arb_pct?: number }) =>
    fetchAPI<ArbitrageOpportunity[]>("/signals/arbitrage", { params }),

  listSentiment: (params?: { asset_id?: number; asset_class_id?: number; limit?: number }) =>
    fetchAPI<SentimentSnapshot[]>("/signals/sentiment", { params }),

  getAnalysis: (sessionId: number) =>
    fetchAPI<MarketAnalysis>(`/signals/analysis/${sessionId}`),

  // Admin
  getTaskRegistry: () => fetchAPI<TaskRegistryEntry[]>("/admin/tasks/registry"),

  triggerTask: (taskName: string, params?: Record<string, unknown>) =>
    fetchAPI<TriggerTaskResponse>("/admin/tasks/trigger", {
      method: "POST",
      body: JSON.stringify({ task_name: taskName, params }),
    }),

  listRuns: (params?: { scraper_type?: string; status?: string; limit?: number }) =>
    fetchAPI<ScrapeRun[]>("/admin/tasks/runs", { params }),

  listJobRuns: (filters: JobRunFilters = {}) =>
    fetchAPI<JobRun[]>("/admin/pipeline/jobs", {
      params: {
        phase: filters.phase,
        status: filters.status,
        limit: filters.limit,
      },
    }),

  listConflicts: (params?: { conflict_type?: string; unresolved_only?: boolean }) =>
    fetchAPI<DataConflict[]>("/admin/data/conflicts", { params }),

  syncExchange: (assetClass?: string) =>
    fetchAPI("/admin/exchange/sync", {
      method: "POST",
      params: { asset_class: assetClass },
    }),

  runPipeline: (assetId: number, sessionDate?: string) =>
    fetchAPI(`/admin/pipeline/${assetId}/run`, {
      method: "POST",
      params: { session_date: sessionDate },
    }),

  // Economic
  listEconomicIndicators: (params?: { series_id?: string; category?: string; start_date?: string; end_date?: string }) =>
    fetchAPI<EconomicIndicator[]>("/economic/indicators", { params }),

  getLatestIndicators: () =>
    fetchAPI<LatestIndicator[]>("/economic/latest"),

  // Candles
  getCandles: (assetId: number, params?: { interval?: string; start_date?: string; end_date?: string; limit?: number }) =>
    fetchAPI<Candle[]>(`/markets/candles/${assetId}`, { params }),

  // Pipeline
  runPipelineSync: (assetId: number, sessionDate?: string) =>
    fetchAPI<PipelineRunResult>(`/admin/pipeline/${assetId}/run`, {
      method: "POST",
      params: { session_date: sessionDate, sync: true },
    }),

  // Diagnostics
  getDiagnostics: () =>
    fetchAPI<DiagnosticsInfo>("/diagnostics"),

  getHealth: () =>
    fetch("/healthz").then(r => r.json()) as Promise<HealthStatus>,

  // Docker Logs
  fetchDockerLogs: (container: string, lines: number = 1000) =>
    fetchAPI<DockerLogsResponse>("/admin/logs", { params: { container, lines } }),
};
