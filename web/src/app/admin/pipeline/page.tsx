"use client";

import { useEffect, useState } from "react";
import { api, type JobRun } from "@/lib/api";

export default function PipelinePage() {
  const [jobs, setJobs] = useState<JobRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("");

  useEffect(() => {
    async function load() {
      try {
        const data = await api.listJobRuns({
          phase: filter || undefined,
          limit: 100,
        });
        setJobs(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [filter]);

  return (
    <div>
      <h1 style={{ fontSize: "24px", marginBottom: "20px" }}>Pipeline Runs</h1>

      {error && (
        <div style={{ padding: "12px", backgroundColor: "#fef2f2", color: "#b91c1c", borderRadius: "6px", marginBottom: "16px", fontSize: "13px" }}>
          {error}
        </div>
      )}

      {/* Filter */}
      <div style={{ marginBottom: "16px", display: "flex", gap: "12px", alignItems: "center" }}>
        <label style={{ fontSize: "13px", color: "#666" }}>Filter by phase:</label>
        <select
          value={filter}
          onChange={(e) => { setFilter(e.target.value); setLoading(true); }}
          style={{ padding: "6px 12px", border: "1px solid #ddd", borderRadius: "4px", fontSize: "13px" }}
        >
          <option value="">All phases</option>
          <option value="analysis_pipeline">Analysis Pipeline</option>
          <option value="ingest_daily_prices">Daily Prices</option>
          <option value="signal_pipeline">Signal Pipeline</option>
        </select>
      </div>

      {loading && <div style={{ color: "#999" }}>Loading...</div>}

      {/* Jobs Table */}
      <div style={{ backgroundColor: "#fff", borderRadius: "8px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #eee", backgroundColor: "#fafafa" }}>
              <th style={{ textAlign: "left", padding: "10px 12px", color: "#666", fontSize: "11px", textTransform: "uppercase" }}>ID</th>
              <th style={{ textAlign: "left", padding: "10px 12px", color: "#666", fontSize: "11px", textTransform: "uppercase" }}>Phase</th>
              <th style={{ textAlign: "left", padding: "10px 12px", color: "#666", fontSize: "11px", textTransform: "uppercase" }}>Status</th>
              <th style={{ textAlign: "left", padding: "10px 12px", color: "#666", fontSize: "11px", textTransform: "uppercase" }}>Started</th>
              <th style={{ textAlign: "right", padding: "10px 12px", color: "#666", fontSize: "11px", textTransform: "uppercase" }}>Duration</th>
              <th style={{ textAlign: "left", padding: "10px 12px", color: "#666", fontSize: "11px", textTransform: "uppercase" }}>Details</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id} style={{ borderBottom: "1px solid #f0f0f0" }}>
                <td style={{ padding: "10px 12px", fontFamily: "monospace" }}>{job.id}</td>
                <td style={{ padding: "10px 12px" }}>
                  <span style={{ padding: "2px 8px", backgroundColor: "#f0f4ff", borderRadius: "3px", fontSize: "12px" }}>
                    {job.phase}
                  </span>
                </td>
                <td style={{ padding: "10px 12px" }}>
                  <StatusBadge status={job.status} />
                </td>
                <td style={{ padding: "10px 12px", fontSize: "12px", color: "#666" }}>
                  {job.started_at ? new Date(job.started_at).toLocaleString() : "—"}
                </td>
                <td style={{ padding: "10px 12px", textAlign: "right", fontFamily: "monospace" }}>
                  {job.duration_seconds != null ? `${job.duration_seconds.toFixed(1)}s` : "—"}
                </td>
                <td style={{ padding: "10px 12px", fontSize: "12px" }}>
                  {job.error_summary && (
                    <span style={{ color: "#e74c3c" }}>{job.error_summary}</span>
                  )}
                  {job.summary_data && !job.error_summary && (
                    <span style={{ color: "#666" }}>
                      {JSON.stringify(job.summary_data).slice(0, 60)}...
                    </span>
                  )}
                </td>
              </tr>
            ))}
            {jobs.length === 0 && !loading && (
              <tr>
                <td colSpan={6} style={{ padding: "24px", textAlign: "center", color: "#999" }}>
                  No pipeline runs found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    completed: { bg: "#dcfce7", text: "#15803d" },
    running: { bg: "#dbeafe", text: "#1d4ed8" },
    failed: { bg: "#fef2f2", text: "#b91c1c" },
    pending: { bg: "#f5f5f5", text: "#666" },
  };
  const c = colors[status] || colors.pending;
  return (
    <span style={{ padding: "2px 8px", backgroundColor: c.bg, color: c.text, borderRadius: "3px", fontSize: "12px", fontWeight: "bold" }}>
      {status}
    </span>
  );
}
