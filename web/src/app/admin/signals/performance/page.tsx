"use client";

import { useEffect, useState, useMemo } from "react";
import { api, type AlphaSignal } from "@/lib/api";

export default function SignalPerformancePage() {
  const [signals, setSignals] = useState<AlphaSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.listSignals({ limit: 500 });
        setSignals(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const stats = useMemo(() => {
    const resolved = signals.filter((s) => s.outcome && s.outcome !== "PENDING");
    const hits = resolved.filter((s) => s.outcome === "HIT");
    const misses = resolved.filter((s) => s.outcome === "MISS");
    const expired = resolved.filter((s) => s.outcome === "EXPIRED");
    const pending = signals.filter((s) => !s.outcome || s.outcome === "PENDING");

    const byType: Record<string, { total: number; hits: number; misses: number }> = {};
    for (const s of resolved) {
      if (!byType[s.signal_type]) byType[s.signal_type] = { total: 0, hits: 0, misses: 0 };
      byType[s.signal_type].total++;
      if (s.outcome === "HIT") byType[s.signal_type].hits++;
      if (s.outcome === "MISS") byType[s.signal_type].misses++;
    }

    const byTier: Record<string, { total: number; hits: number }> = {};
    for (const s of resolved) {
      if (!byTier[s.confidence_tier]) byTier[s.confidence_tier] = { total: 0, hits: 0 };
      byTier[s.confidence_tier].total++;
      if (s.outcome === "HIT") byTier[s.confidence_tier].hits++;
    }

    return {
      total: signals.length,
      resolved: resolved.length,
      hits: hits.length,
      misses: misses.length,
      expired: expired.length,
      pending: pending.length,
      hitRate: resolved.length > 0 ? (hits.length / resolved.length * 100) : 0,
      byType,
      byTier,
    };
  }, [signals]);

  return (
    <div>
      <h1 style={{ fontSize: "24px", marginBottom: "20px" }}>Signal Performance</h1>

      {error && (
        <div style={{ padding: "12px", backgroundColor: "#fef2f2", color: "#b91c1c", borderRadius: "6px", marginBottom: "16px", fontSize: "13px" }}>
          {error}
        </div>
      )}
      {loading && <div style={{ color: "#999" }}>Loading...</div>}

      {/* Overall Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: "12px", marginBottom: "20px" }}>
        <KpiCard label="Total Signals" value={stats.total} />
        <KpiCard label="Resolved" value={stats.resolved} />
        <KpiCard label="Hits" value={stats.hits} color="#27ae60" />
        <KpiCard label="Misses" value={stats.misses} color="#e74c3c" />
        <KpiCard label="Expired" value={stats.expired} color="#f39c12" />
        <KpiCard label="Hit Rate" value={`${stats.hitRate.toFixed(1)}%`} color={stats.hitRate >= 50 ? "#27ae60" : "#e74c3c"} />
      </div>

      {/* By Signal Type */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
        <div style={{ backgroundColor: "#fff", borderRadius: "8px", padding: "20px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
          <h2 style={{ fontSize: "16px", marginBottom: "12px", color: "#333" }}>Performance by Signal Type</h2>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #eee" }}>
                <th style={{ textAlign: "left", padding: "8px", fontSize: "11px", color: "#666", textTransform: "uppercase" }}>Type</th>
                <th style={{ textAlign: "right", padding: "8px", fontSize: "11px", color: "#666", textTransform: "uppercase" }}>Total</th>
                <th style={{ textAlign: "right", padding: "8px", fontSize: "11px", color: "#666", textTransform: "uppercase" }}>Hits</th>
                <th style={{ textAlign: "right", padding: "8px", fontSize: "11px", color: "#666", textTransform: "uppercase" }}>Rate</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(stats.byType).map(([type, data]) => (
                <tr key={type} style={{ borderBottom: "1px solid #f0f0f0" }}>
                  <td style={{ padding: "8px" }}>{type}</td>
                  <td style={{ padding: "8px", textAlign: "right" }}>{data.total}</td>
                  <td style={{ padding: "8px", textAlign: "right", color: "#27ae60" }}>{data.hits}</td>
                  <td style={{ padding: "8px", textAlign: "right", fontWeight: "bold" }}>
                    {data.total > 0 ? `${(data.hits / data.total * 100).toFixed(0)}%` : "—"}
                  </td>
                </tr>
              ))}
              {Object.keys(stats.byType).length === 0 && (
                <tr><td colSpan={4} style={{ padding: "16px", textAlign: "center", color: "#999" }}>No resolved signals yet</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div style={{ backgroundColor: "#fff", borderRadius: "8px", padding: "20px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
          <h2 style={{ fontSize: "16px", marginBottom: "12px", color: "#333" }}>Performance by Confidence Tier</h2>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #eee" }}>
                <th style={{ textAlign: "left", padding: "8px", fontSize: "11px", color: "#666", textTransform: "uppercase" }}>Tier</th>
                <th style={{ textAlign: "right", padding: "8px", fontSize: "11px", color: "#666", textTransform: "uppercase" }}>Total</th>
                <th style={{ textAlign: "right", padding: "8px", fontSize: "11px", color: "#666", textTransform: "uppercase" }}>Hits</th>
                <th style={{ textAlign: "right", padding: "8px", fontSize: "11px", color: "#666", textTransform: "uppercase" }}>Rate</th>
              </tr>
            </thead>
            <tbody>
              {["HIGH", "MEDIUM", "LOW"].map((tier) => {
                const data = stats.byTier[tier];
                if (!data) return null;
                return (
                  <tr key={tier} style={{ borderBottom: "1px solid #f0f0f0" }}>
                    <td style={{ padding: "8px" }}>
                      <span style={{
                        padding: "2px 8px", borderRadius: "3px", fontSize: "12px", fontWeight: "bold",
                        backgroundColor: tier === "HIGH" ? "#dcfce7" : tier === "MEDIUM" ? "#fef9c3" : "#f5f5f5",
                        color: tier === "HIGH" ? "#15803d" : tier === "MEDIUM" ? "#a16207" : "#666",
                      }}>
                        {tier}
                      </span>
                    </td>
                    <td style={{ padding: "8px", textAlign: "right" }}>{data.total}</td>
                    <td style={{ padding: "8px", textAlign: "right", color: "#27ae60" }}>{data.hits}</td>
                    <td style={{ padding: "8px", textAlign: "right", fontWeight: "bold" }}>
                      {data.total > 0 ? `${(data.hits / data.total * 100).toFixed(0)}%` : "—"}
                    </td>
                  </tr>
                );
              })}
              {Object.keys(stats.byTier).length === 0 && (
                <tr><td colSpan={4} style={{ padding: "16px", textAlign: "center", color: "#999" }}>No resolved signals yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function KpiCard({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div style={{ backgroundColor: "#fff", borderRadius: "8px", padding: "16px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)", textAlign: "center" }}>
      <div style={{ fontSize: "28px", fontWeight: "bold", color: color || "#333" }}>{value}</div>
      <div style={{ fontSize: "11px", color: "#888", marginTop: "4px" }}>{label}</div>
    </div>
  );
}
