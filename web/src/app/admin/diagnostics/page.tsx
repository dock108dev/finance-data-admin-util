"use client";

import { useEffect, useState } from "react";
import { api, type DiagnosticsInfo, type HealthStatus } from "@/lib/api";

export default function DiagnosticsPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [diag, setDiag] = useState<DiagnosticsInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [h, d] = await Promise.allSettled([
          api.getHealth(),
          api.getDiagnostics(),
        ]);
        if (h.status === "fulfilled") setHealth(h.value);
        if (d.status === "fulfilled") setDiag(d.value);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }
    load();
    // Auto-refresh every 10s
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h1 style={{ fontSize: "24px", marginBottom: "20px" }}>System Diagnostics</h1>

      {error && (
        <div style={{ padding: "12px", backgroundColor: "#fef2f2", color: "#b91c1c", borderRadius: "6px", marginBottom: "16px", fontSize: "13px" }}>
          {error}
        </div>
      )}
      {loading && !health && <div style={{ color: "#999" }}>Loading...</div>}

      {/* Health Status */}
      {health && (
        <div style={{ backgroundColor: "#fff", borderRadius: "8px", padding: "20px", marginBottom: "16px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
          <h2 style={{ fontSize: "16px", marginBottom: "16px", color: "#333" }}>Component Health</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px" }}>
            <HealthCard label="App" status={health.app} />
            <HealthCard label="Database" status={health.db} />
            <HealthCard label="Redis" status={health.redis} />
            <HealthCard label="Celery" status={health.celery} />
          </div>
        </div>
      )}

      {/* Realtime Status */}
      {diag?.realtime && (
        <div style={{ backgroundColor: "#fff", borderRadius: "8px", padding: "20px", marginBottom: "16px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
          <h2 style={{ fontSize: "16px", marginBottom: "16px", color: "#333" }}>Realtime Connections</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px" }}>
            <StatCard label="Connections" value={diag.realtime.total_connections} />
            <StatCard label="Channels" value={diag.realtime.total_channels} />
            <StatCard label="Events Published" value={diag.realtime.publish_count} />
            <StatCard label="Errors" value={diag.realtime.error_count} />
          </div>
          {Object.keys(diag.realtime.channels).length > 0 && (
            <div style={{ marginTop: "12px" }}>
              <div style={{ fontSize: "12px", color: "#888", marginBottom: "6px" }}>Active Channels:</div>
              {Object.entries(diag.realtime.channels).map(([ch, count]) => (
                <div key={ch} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", fontSize: "12px", borderBottom: "1px solid #f5f5f5" }}>
                  <code style={{ color: "#333" }}>{ch}</code>
                  <span style={{ color: "#666" }}>{count} subscriber{count !== 1 ? "s" : ""}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Poller Stats */}
      {diag?.poller && (
        <div style={{ backgroundColor: "#fff", borderRadius: "8px", padding: "20px", marginBottom: "16px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
          <h2 style={{ fontSize: "16px", marginBottom: "16px", color: "#333" }}>DB Poller Statistics</h2>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #eee" }}>
                <th style={{ textAlign: "left", padding: "8px", color: "#666", fontSize: "11px", textTransform: "uppercase" }}>Loop</th>
                <th style={{ textAlign: "right", padding: "8px", color: "#666", fontSize: "11px", textTransform: "uppercase" }}>Poll Count</th>
                <th style={{ textAlign: "right", padding: "8px", color: "#666", fontSize: "11px", textTransform: "uppercase" }}>Last Duration</th>
                <th style={{ textAlign: "left", padding: "8px", color: "#666", fontSize: "11px", textTransform: "uppercase" }}>Last Poll</th>
              </tr>
            </thead>
            <tbody>
              {["prices", "signals", "sessions"].map((loop) => (
                <tr key={loop} style={{ borderBottom: "1px solid #f0f0f0" }}>
                  <td style={{ padding: "8px", fontWeight: "bold" }}>{loop}</td>
                  <td style={{ padding: "8px", textAlign: "right", fontFamily: "monospace" }}>
                    {diag.poller.poll_count[loop] || 0}
                  </td>
                  <td style={{ padding: "8px", textAlign: "right", fontFamily: "monospace" }}>
                    {diag.poller.last_poll_duration_ms[loop] != null
                      ? `${diag.poller.last_poll_duration_ms[loop].toFixed(1)}ms`
                      : "—"}
                  </td>
                  <td style={{ padding: "8px", fontSize: "12px", color: "#666" }}>
                    {diag.poller.last_poll_at[loop]
                      ? new Date(diag.poller.last_poll_at[loop]!).toLocaleString()
                      : "Never"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* DB Pool */}
      {diag?.db_pool && typeof diag.db_pool === "object" && (
        <div style={{ backgroundColor: "#fff", borderRadius: "8px", padding: "20px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
          <h2 style={{ fontSize: "16px", marginBottom: "16px", color: "#333" }}>Database Pool</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px" }}>
            <StatCard label="Pool Size" value={(diag.db_pool as Record<string, number>).size ?? 0} />
            <StatCard label="Checked In" value={(diag.db_pool as Record<string, number>).checked_in ?? 0} />
            <StatCard label="Checked Out" value={(diag.db_pool as Record<string, number>).checked_out ?? 0} />
            <StatCard label="Overflow" value={(diag.db_pool as Record<string, number>).overflow ?? 0} />
          </div>
        </div>
      )}
    </div>
  );
}

function HealthCard({ label, status }: { label: string; status: string }) {
  const isOk = status === "ok" || status === "configured";
  return (
    <div style={{
      padding: "12px",
      borderRadius: "6px",
      backgroundColor: isOk ? "#dcfce7" : "#fef2f2",
      textAlign: "center",
    }}>
      <div style={{ fontSize: "20px" }}>{isOk ? "●" : "○"}</div>
      <div style={{ fontSize: "13px", fontWeight: "bold", color: isOk ? "#15803d" : "#b91c1c" }}>{label}</div>
      <div style={{ fontSize: "11px", color: isOk ? "#15803d" : "#b91c1c" }}>{status}</div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div style={{ padding: "12px", backgroundColor: "#f8f9fa", borderRadius: "6px", textAlign: "center" }}>
      <div style={{ fontSize: "24px", fontWeight: "bold", color: "#333" }}>{value}</div>
      <div style={{ fontSize: "11px", color: "#888" }}>{label}</div>
    </div>
  );
}
