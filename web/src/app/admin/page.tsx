/**
 * Admin dashboard home — quick stats and overview.
 * Equivalent to sports-data-admin's /admin page.
 */

"use client";

import { useEffect, useState } from "react";
import { api, type AlphaSignal, type ScrapeRun } from "@/lib/api";

export default function AdminDashboard() {
  const [assetCount, setAssetCount] = useState<number | null>(null);
  const [signalCount, setSignalCount] = useState<number | null>(null);
  const [arbCount, setArbCount] = useState<number | null>(null);
  const [lastSync, setLastSync] = useState<string | null>(null);
  const [recentSignals, setRecentSignals] = useState<AlphaSignal[]>([]);
  const [recentRuns, setRecentRuns] = useState<ScrapeRun[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [assets, signals, arbs, runs] = await Promise.all([
          api.listAssets(),
          api.listSignals({ outcome: "PENDING", limit: 100 }),
          api.listArbitrage(),
          api.listRuns({ limit: 5 }),
        ]);
        setAssetCount(assets.length);
        setSignalCount(signals.length);
        setArbCount(arbs.length);
        setRecentSignals(signals.slice(0, 5));
        setRecentRuns(runs);

        // Last sync time from most recent exchange_sync run
        const syncRuns = await api.listRuns({ scraper_type: "exchange_sync", limit: 1 });
        if (syncRuns.length > 0 && syncRuns[0].finished_at) {
          setLastSync(new Date(syncRuns[0].finished_at).toLocaleString());
        } else {
          setLastSync("Never");
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    }
    load();
  }, []);

  return (
    <div>
      <h1 style={{ fontSize: "24px", marginBottom: "24px" }}>
        Fin Data Admin Dashboard
      </h1>

      {error && (
        <div style={{ padding: "12px", backgroundColor: "#fef2f2", color: "#b91c1c", borderRadius: "6px", marginBottom: "16px", fontSize: "13px" }}>
          {error}
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
          gap: "16px",
          marginBottom: "32px",
        }}
      >
        <StatCard title="Tracked Assets" value={assetCount !== null ? String(assetCount) : "--"} subtitle="Stocks + Crypto" />
        <StatCard title="Active Signals" value={signalCount !== null ? String(signalCount) : "--"} subtitle="Alpha opportunities" />
        <StatCard title="Arb Opportunities" value={arbCount !== null ? String(arbCount) : "--"} subtitle="Cross-exchange" />
        <StatCard title="Last Sync" value={lastSync ?? "--"} subtitle="Exchange prices" small />
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))",
          gap: "16px",
        }}
      >
        <Card title="Recent Signals">
          {recentSignals.length === 0 ? (
            <p style={{ color: "#666" }}>
              No signals yet. Configure data sources and run the signal pipeline.
            </p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #eee" }}>
                  <th style={miniTh}>Type</th>
                  <th style={miniTh}>Direction</th>
                  <th style={miniTh}>Confidence</th>
                  <th style={{ ...miniTh, textAlign: "right" }}>Strength</th>
                  <th style={miniTh}>Detected</th>
                </tr>
              </thead>
              <tbody>
                {recentSignals.map((s) => (
                  <tr key={s.id} style={{ borderBottom: "1px solid #f5f5f5" }}>
                    <td style={miniTd}>{s.signal_type}</td>
                    <td style={miniTd}>
                      <span style={{ color: s.direction === "LONG" ? "#27ae60" : s.direction === "SHORT" ? "#e74c3c" : "#999" }}>
                        {s.direction}
                      </span>
                    </td>
                    <td style={miniTd}><ConfidenceBadge tier={s.confidence_tier} /></td>
                    <td style={{ ...miniTd, textAlign: "right" }}>{(s.strength * 100).toFixed(0)}%</td>
                    <td style={miniTd}>{new Date(s.detected_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
        <Card title="Recent Runs">
          {recentRuns.length === 0 ? (
            <p style={{ color: "#666" }}>
              No scraper runs yet. Start the Celery worker and beat scheduler.
            </p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #eee" }}>
                  <th style={miniTh}>Scraper</th>
                  <th style={miniTh}>Status</th>
                  <th style={{ ...miniTh, textAlign: "right" }}>Records</th>
                  <th style={miniTh}>Started</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((r) => (
                  <tr key={r.id} style={{ borderBottom: "1px solid #f5f5f5" }}>
                    <td style={miniTd}>{r.scraper_type}</td>
                    <td style={miniTd}><StatusBadge status={r.status} /></td>
                    <td style={{ ...miniTd, textAlign: "right" }}>{r.records_created ?? "-"}</td>
                    <td style={miniTd}>{r.started_at ? new Date(r.started_at).toLocaleString() : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </div>
  );
}

function StatCard({ title, value, subtitle, small }: { title: string; value: string; subtitle: string; small?: boolean }) {
  return (
    <div style={{ backgroundColor: "white", borderRadius: "8px", padding: "20px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
      <div style={{ fontSize: "14px", color: "#666", marginBottom: "4px" }}>{title}</div>
      <div style={{ fontSize: small ? "18px" : "32px", fontWeight: "bold", marginBottom: "4px" }}>{value}</div>
      <div style={{ fontSize: "12px", color: "#999" }}>{subtitle}</div>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ backgroundColor: "white", borderRadius: "8px", padding: "20px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
      <h2 style={{ fontSize: "18px", marginBottom: "12px" }}>{title}</h2>
      {children}
    </div>
  );
}

function ConfidenceBadge({ tier }: { tier: string }) {
  const colors: Record<string, { bg: string; fg: string }> = {
    HIGH: { bg: "#dcfce7", fg: "#166534" },
    MEDIUM: { bg: "#fef9c3", fg: "#854d0e" },
    LOW: { bg: "#f3f4f6", fg: "#6b7280" },
  };
  const c = colors[tier] ?? colors.LOW;
  return (
    <span style={{ fontSize: "11px", padding: "2px 6px", borderRadius: "3px", backgroundColor: c.bg, color: c.fg }}>
      {tier}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, { bg: string; fg: string }> = {
    success: { bg: "#dcfce7", fg: "#166534" },
    running: { bg: "#dbeafe", fg: "#1e40af" },
    error: { bg: "#fef2f2", fg: "#991b1b" },
    queued: { bg: "#f3f4f6", fg: "#6b7280" },
  };
  const c = colors[status] ?? colors.queued;
  return (
    <span style={{ fontSize: "11px", padding: "2px 6px", borderRadius: "3px", backgroundColor: c.bg, color: c.fg }}>
      {status}
    </span>
  );
}

const miniTh: React.CSSProperties = { padding: "6px 8px", textAlign: "left", fontSize: "11px", color: "#999", textTransform: "uppercase", fontWeight: 600 };
const miniTd: React.CSSProperties = { padding: "6px 8px" };
