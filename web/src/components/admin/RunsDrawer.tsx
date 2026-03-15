"use client";

import { useCallback, useEffect, useState } from "react";
import styles from "./RunsDrawer.module.css";
import { api, type JobRun } from "@/lib/api";

type DrawerSize = "collapsed" | "half" | "full";

const PHASE_OPTIONS = [
  { value: "", label: "All phases" },
  { value: "ingest_daily_prices", label: "Daily Prices" },
  { value: "ingest_intraday_prices", label: "Intraday Prices" },
  { value: "sync_exchange_prices", label: "Exchange Sync" },
  { value: "collect_social_sentiment", label: "Social Sentiment" },
  { value: "run_signal_pipeline", label: "Signal Pipeline" },
  { value: "generate_market_analysis", label: "Market Analysis" },
  { value: "run_daily_sweep", label: "Daily Sweep" },
  { value: "sync_onchain_data", label: "On-chain Sync" },
  { value: "ingest_fundamentals", label: "Fundamentals" },
];

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "success", label: "Success" },
  { value: "running", label: "Running" },
  { value: "error", label: "Error" },
];

const AUTO_REFRESH_MS = 30_000;

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "-";
  if (seconds < 1) return "<1s";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

const SIZE_CLASS: Record<DrawerSize, string> = {
  collapsed: styles.drawerCollapsed,
  half: styles.drawerHalf,
  full: styles.drawerFull,
};

export function RunsDrawer() {
  const [size, setSize] = useState<DrawerSize>("collapsed");
  const [runs, setRuns] = useState<JobRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [phase, setPhase] = useState("");
  const [status, setStatus] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const fetchRuns = useCallback(async () => {
    try {
      setError(null);
      const data = await api.listJobRuns({
        phase: phase || undefined,
        status: status || undefined,
        limit: 100,
      });
      setRuns(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [phase, status]);

  // Fetch when opened or filters change
  useEffect(() => {
    if (size !== "collapsed") {
      setLoading(true);
      fetchRuns();
    }
  }, [fetchRuns, size]);

  // Auto-refresh when open
  useEffect(() => {
    if (size === "collapsed") return;
    const interval = setInterval(fetchRuns, AUTO_REFRESH_MS);
    return () => clearInterval(interval);
  }, [fetchRuns, size]);

  const toggleSize = () => {
    setSize((prev) => (prev === "collapsed" ? "half" : "collapsed"));
  };

  const getStatusClass = (s: string) => {
    switch (s) {
      case "success":
        return styles.statusSuccess;
      case "running":
        return styles.statusRunning;
      case "error":
        return styles.statusError;
      default:
        return "";
    }
  };

  return (
    <div className={`${styles.drawer} ${SIZE_CLASS[size]}`}>
      {/* Tab bar — always visible */}
      <div className={styles.tabBar} onClick={toggleSize}>
        <span className={styles.tabLabel}>
          Runs {size === "collapsed" ? "\u25B2" : "\u25BC"}
        </span>
        <div
          className={styles.tabControls}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            className={`${styles.tabBtn} ${size === "half" ? styles.tabBtnActive : ""}`}
            onClick={() => setSize("half")}
            title="Half height"
          >
            &#x2B12;
          </button>
          <button
            className={`${styles.tabBtn} ${size === "full" ? styles.tabBtnActive : ""}`}
            onClick={() => setSize("full")}
            title="Full height"
          >
            &#x2610;
          </button>
          <button
            className={styles.tabBtn}
            onClick={() => setSize("collapsed")}
            title="Collapse"
          >
            &#x2715;
          </button>
        </div>
      </div>

      {/* Body — only rendered when open */}
      {size !== "collapsed" && (
        <>
          <div className={styles.toolbar}>
            <select value={phase} onChange={(e) => setPhase(e.target.value)}>
              {PHASE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <button
              className={styles.refreshBtn}
              onClick={fetchRuns}
              disabled={loading}
            >
              {loading ? "Loading..." : "Refresh"}
            </button>
            <span className={styles.autoRefreshLabel}>Auto-refresh: 30s</span>
          </div>

          <div className={styles.body}>
            {error && <div className={styles.error}>{error}</div>}

            {!loading && runs.length === 0 && !error && (
              <div className={styles.empty}>No task runs found.</div>
            )}

            {runs.length > 0 && (
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Phase</th>
                    <th>Asset Classes</th>
                    <th>Status</th>
                    <th>Started</th>
                    <th>Duration</th>
                    <th>Summary</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <>
                      <tr
                        key={run.id}
                        className={
                          run.summary_data ? styles.expandable : undefined
                        }
                        onClick={() => {
                          if (run.summary_data) {
                            setExpandedId(
                              expandedId === run.id ? null : run.id
                            );
                          }
                        }}
                      >
                        <td>
                          <span className={styles.phaseBadge}>
                            {run.phase}
                          </span>
                        </td>
                        <td>
                          {(run.asset_classes ?? []).map((ac) => (
                            <span key={ac} className={styles.assetClassBadge}>
                              {ac}
                            </span>
                          ))}
                        </td>
                        <td>
                          <span
                            className={`${styles.statusPill} ${getStatusClass(run.status)}`}
                          >
                            {run.status}
                          </span>
                        </td>
                        <td>
                          {run.started_at
                            ? `${formatDate(run.started_at)} ${formatTime(run.started_at)}`
                            : "-"}
                        </td>
                        <td className={styles.durationCell}>
                          {formatDuration(run.duration_seconds)}
                        </td>
                        <td>
                          {run.error_summary
                            ? run.error_summary.slice(0, 60)
                            : run.summary_data
                              ? "Click to expand"
                              : "-"}
                        </td>
                      </tr>
                      {expandedId === run.id && run.summary_data && (
                        <tr
                          key={`${run.id}-detail`}
                          className={styles.summaryRow}
                        >
                          <td colSpan={6}>
                            <pre className={styles.summaryPre}>
                              {JSON.stringify(run.summary_data, null, 2)}
                            </pre>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
