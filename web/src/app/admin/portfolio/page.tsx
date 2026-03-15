/**
 * Portfolio Tracker — signal performance tracking.
 * New feature for financial context (no direct sports equivalent).
 */

"use client";

import { useEffect, useState } from "react";
import { api, type AlphaSignal } from "@/lib/api";

interface SignalStats {
  total: number;
  hit: number;
  miss: number;
  expired: number;
  pending: number;
  hitRate: number;
}

interface TypePerformance {
  signalType: string;
  total: number;
  hit: number;
  miss: number;
  hitRate: number;
}

export default function PortfolioTracker() {
  const [stats, setStats] = useState<SignalStats>({ total: 0, hit: 0, miss: 0, expired: 0, pending: 0, hitRate: 0 });
  const [typePerf, setTypePerf] = useState<TypePerformance[]>([]);
  const [resolvedSignals, setResolvedSignals] = useState<AlphaSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const allSignals = await api.listSignals({ limit: 200 });

        const hit = allSignals.filter((s) => s.outcome === "HIT").length;
        const miss = allSignals.filter((s) => s.outcome === "MISS").length;
        const expired = allSignals.filter((s) => s.outcome === "EXPIRED").length;
        const pending = allSignals.filter((s) => !s.outcome || s.outcome === "PENDING").length;
        const total = allSignals.length;
        const hitRate = hit + miss > 0 ? (hit / (hit + miss)) * 100 : 0;

        setStats({ total, hit, miss, expired, pending, hitRate });

        // Group by signal_type
        const byType: Record<string, { total: number; hit: number; miss: number }> = {};
        for (const s of allSignals) {
          if (!byType[s.signal_type]) byType[s.signal_type] = { total: 0, hit: 0, miss: 0 };
          byType[s.signal_type].total++;
          if (s.outcome === "HIT") byType[s.signal_type].hit++;
          if (s.outcome === "MISS") byType[s.signal_type].miss++;
        }
        setTypePerf(
          Object.entries(byType).map(([signalType, d]) => ({
            signalType,
            ...d,
            hitRate: d.hit + d.miss > 0 ? (d.hit / (d.hit + d.miss)) * 100 : 0,
          }))
        );

        // Show resolved signals as proxy for "positions"
        setResolvedSignals(allSignals.filter((s) => s.outcome === "HIT" || s.outcome === "MISS").slice(0, 20));
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <p style={{ color: "#999" }}>Loading portfolio data...</p>;

  return (
    <div>
      <h1 style={{ fontSize: "24px", marginBottom: "20px" }}>
        Portfolio Tracker
      </h1>

      {error && (
        <div style={{ padding: "12px", backgroundColor: "#fef2f2", color: "#b91c1c", borderRadius: "6px", marginBottom: "16px", fontSize: "13px" }}>
          {error}
        </div>
      )}

      {/* Summary Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "12px",
          marginBottom: "24px",
        }}
      >
        <SummaryCard label="Total Signals" value={String(stats.total)} />
        <SummaryCard label="Signal Hit Rate" value={stats.hitRate > 0 ? `${stats.hitRate.toFixed(1)}%` : "--%"} color={stats.hitRate >= 50 ? "#27ae60" : stats.hitRate > 0 ? "#e74c3c" : "#666"} />
        <SummaryCard label="Hits / Misses" value={`${stats.hit} / ${stats.miss}`} />
        <SummaryCard label="Pending" value={String(stats.pending)} />
      </div>

      {/* Signal Performance by Type */}
      <div
        style={{
          backgroundColor: "white",
          borderRadius: "8px",
          padding: "20px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          marginBottom: "16px",
        }}
      >
        <h2 style={{ fontSize: "16px", marginBottom: "12px" }}>
          Performance by Signal Type
        </h2>
        {typePerf.length === 0 ? (
          <p style={{ color: "#999", fontSize: "13px" }}>
            No signal data available yet.
          </p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #eee" }}>
                <th style={thStyle}>Signal Type</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Total</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Hits</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Misses</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Hit Rate</th>
              </tr>
            </thead>
            <tbody>
              {typePerf.map((tp) => (
                <tr key={tp.signalType} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={tdStyle}>{tp.signalType}</td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>{tp.total}</td>
                  <td style={{ ...tdStyle, textAlign: "right", color: "#27ae60" }}>{tp.hit}</td>
                  <td style={{ ...tdStyle, textAlign: "right", color: "#e74c3c" }}>{tp.miss}</td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>
                    <span style={{
                      fontWeight: 600,
                      color: tp.hitRate >= 50 ? "#27ae60" : tp.hitRate > 0 ? "#e74c3c" : "#999",
                    }}>
                      {tp.hit + tp.miss > 0 ? `${tp.hitRate.toFixed(1)}%` : "-"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Resolved Signals (proxy for Active Positions) */}
      <div
        style={{
          backgroundColor: "white",
          borderRadius: "8px",
          padding: "20px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
        }}
      >
        <h2 style={{ fontSize: "16px", marginBottom: "12px" }}>
          Resolved Signals
        </h2>
        {resolvedSignals.length === 0 ? (
          <p style={{ color: "#999", fontSize: "13px" }}>
            No resolved signals yet. Signals will appear here once they are marked HIT or MISS.
          </p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #eee" }}>
                <th style={thStyle}>Asset</th>
                <th style={thStyle}>Type</th>
                <th style={thStyle}>Direction</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Entry</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Target</th>
                <th style={thStyle}>Outcome</th>
                <th style={thStyle}>Detected</th>
              </tr>
            </thead>
            <tbody>
              {resolvedSignals.map((s) => (
                <tr key={s.id} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={tdStyle}>{s.asset_id}</td>
                  <td style={tdStyle}>{s.signal_type}</td>
                  <td style={tdStyle}>
                    <span style={{ color: s.direction === "LONG" ? "#27ae60" : s.direction === "SHORT" ? "#e74c3c" : "#999" }}>
                      {s.direction}
                    </span>
                  </td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>{s.trigger_price?.toLocaleString() ?? "-"}</td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>{s.target_price?.toLocaleString() ?? "-"}</td>
                  <td style={tdStyle}>
                    <span style={{
                      fontSize: "11px",
                      padding: "2px 6px",
                      borderRadius: "3px",
                      backgroundColor: s.outcome === "HIT" ? "#dcfce7" : "#fef2f2",
                      color: s.outcome === "HIT" ? "#166534" : "#991b1b",
                    }}>
                      {s.outcome}
                    </span>
                  </td>
                  <td style={tdStyle}>{new Date(s.detected_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function SummaryCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ backgroundColor: "white", borderRadius: "8px", padding: "16px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
      <div style={{ fontSize: "12px", color: "#999", marginBottom: "4px" }}>{label}</div>
      <div style={{ fontSize: "24px", fontWeight: "bold", color: color || "#333" }}>{value}</div>
    </div>
  );
}

const thStyle: React.CSSProperties = {
  padding: "8px 10px",
  textAlign: "left",
  fontWeight: 600,
  fontSize: "11px",
  textTransform: "uppercase",
  color: "#999",
};

const tdStyle: React.CSSProperties = {
  padding: "8px 10px",
};
