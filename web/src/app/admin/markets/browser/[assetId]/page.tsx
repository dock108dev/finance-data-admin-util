/**
 * Asset detail page — price history, sessions, signals, fundamentals.
 * Equivalent to sports-data-admin's game detail page.
 */

"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, type Asset, type MarketSession, type AlphaSignal } from "@/lib/api";

export default function AssetDetail() {
  const params = useParams();
  const assetId = Number(params.assetId);

  const [asset, setAsset] = useState<Asset | null>(null);
  const [sessions, setSessions] = useState<MarketSession[]>([]);
  const [signals, setSignals] = useState<AlphaSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [a, sess, sigs] = await Promise.all([
          api.getAsset(assetId),
          api.listAssetSessions(assetId, { limit: 20 }),
          api.listSignals({ limit: 10 }),
        ]);
        setAsset(a);
        setSessions(sess);
        // Filter signals for this asset client-side (API may not support asset_id filter directly)
        setSignals(sigs.filter((s) => s.asset_id === assetId));
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [assetId]);

  if (loading) return <p style={{ color: "#999" }}>Loading asset detail...</p>;
  if (error) return <div style={{ padding: "12px", backgroundColor: "#fef2f2", color: "#b91c1c", borderRadius: "6px" }}>{error}</div>;
  if (!asset) return <p>Asset not found.</p>;

  const latestSession = sessions[0] ?? null;

  return (
    <div>
      <Link href="/admin/markets/browser" style={{ color: "#666", fontSize: "13px", textDecoration: "none" }}>
        &larr; Back to Browser
      </Link>

      <div style={{ display: "flex", alignItems: "baseline", gap: "12px", margin: "12px 0 24px" }}>
        <h1 style={{ fontSize: "28px" }}>{asset.ticker}</h1>
        <span style={{ fontSize: "16px", color: "#666" }}>{asset.name}</span>
        {asset.asset_class_code && (
          <span style={{
            fontSize: "11px",
            padding: "2px 8px",
            borderRadius: "3px",
            backgroundColor: asset.asset_class_code === "STOCKS" ? "#e8f5e9" : "#fff3e0",
            color: asset.asset_class_code === "STOCKS" ? "#2e7d32" : "#e65100",
          }}>
            {asset.asset_class_code}
          </span>
        )}
      </div>

      {/* Summary row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px", marginBottom: "24px" }}>
        <InfoCard label="Last Price" value={latestSession?.close_price != null ? `$${latestSession.close_price.toLocaleString()}` : "--"} />
        <InfoCard label="Change %" value={latestSession?.change_pct != null ? `${latestSession.change_pct >= 0 ? "+" : ""}${latestSession.change_pct.toFixed(2)}%` : "--"} color={latestSession?.change_pct != null ? (latestSession.change_pct >= 0 ? "#27ae60" : "#e74c3c") : undefined} />
        <InfoCard label="Volume" value={latestSession?.volume != null ? latestSession.volume.toLocaleString() : "--"} />
        <InfoCard label="Exchange" value={asset.exchange ?? "--"} />
        <InfoCard label="Sector" value={asset.sector ?? "--"} />
        <InfoCard label="Market Cap" value={asset.market_cap != null ? `$${(asset.market_cap / 1e9).toFixed(1)}B` : "--"} />
      </div>

      {/* Latest Session OHLCV */}
      {latestSession && (
        <Section title={`Latest Session — ${latestSession.session_date}`}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: "12px" }}>
            <InfoCard label="Open" value={`$${latestSession.open_price?.toLocaleString() ?? "--"}`} />
            <InfoCard label="High" value={`$${latestSession.high_price?.toLocaleString() ?? "--"}`} />
            <InfoCard label="Low" value={`$${latestSession.low_price?.toLocaleString() ?? "--"}`} />
            <InfoCard label="Close" value={`$${latestSession.close_price?.toLocaleString() ?? "--"}`} />
          </div>
        </Section>
      )}

      {/* Price History */}
      <Section title="Recent Sessions">
        {sessions.length === 0 ? (
          <p style={{ color: "#999", fontSize: "13px" }}>No session data yet.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #eee" }}>
                <th style={th}>Date</th>
                <th style={{ ...th, textAlign: "right" }}>Open</th>
                <th style={{ ...th, textAlign: "right" }}>High</th>
                <th style={{ ...th, textAlign: "right" }}>Low</th>
                <th style={{ ...th, textAlign: "right" }}>Close</th>
                <th style={{ ...th, textAlign: "right" }}>Volume</th>
                <th style={{ ...th, textAlign: "right" }}>Change</th>
                <th style={th}>Status</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.id} style={{ borderBottom: "1px solid #f5f5f5" }}>
                  <td style={td}>{s.session_date}</td>
                  <td style={{ ...td, textAlign: "right" }}>{s.open_price?.toLocaleString() ?? "-"}</td>
                  <td style={{ ...td, textAlign: "right" }}>{s.high_price?.toLocaleString() ?? "-"}</td>
                  <td style={{ ...td, textAlign: "right" }}>{s.low_price?.toLocaleString() ?? "-"}</td>
                  <td style={{ ...td, textAlign: "right" }}>{s.close_price?.toLocaleString() ?? "-"}</td>
                  <td style={{ ...td, textAlign: "right" }}>{s.volume?.toLocaleString() ?? "-"}</td>
                  <td style={{ ...td, textAlign: "right" }}>
                    {s.change_pct != null ? (
                      <span style={{ color: s.change_pct >= 0 ? "#27ae60" : "#e74c3c" }}>
                        {s.change_pct >= 0 ? "+" : ""}{s.change_pct.toFixed(2)}%
                      </span>
                    ) : "-"}
                  </td>
                  <td style={td}>{s.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      {/* Active Signals */}
      <Section title="Active Signals">
        {signals.length === 0 ? (
          <p style={{ color: "#999", fontSize: "13px" }}>No signals detected for this asset.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #eee" }}>
                <th style={th}>Type</th>
                <th style={th}>Direction</th>
                <th style={th}>Confidence</th>
                <th style={{ ...th, textAlign: "right" }}>Strength</th>
                <th style={{ ...th, textAlign: "right" }}>Entry</th>
                <th style={{ ...th, textAlign: "right" }}>Target</th>
                <th style={th}>Detected</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((sig) => (
                <tr key={sig.id} style={{ borderBottom: "1px solid #f5f5f5" }}>
                  <td style={td}>{sig.signal_type}</td>
                  <td style={td}>
                    <span style={{ color: sig.direction === "LONG" ? "#27ae60" : sig.direction === "SHORT" ? "#e74c3c" : "#999" }}>
                      {sig.direction}
                    </span>
                  </td>
                  <td style={td}>
                    <span style={{
                      fontSize: "11px",
                      padding: "2px 6px",
                      borderRadius: "3px",
                      backgroundColor: sig.confidence_tier === "HIGH" ? "#dcfce7" : sig.confidence_tier === "MEDIUM" ? "#fef9c3" : "#f3f4f6",
                      color: sig.confidence_tier === "HIGH" ? "#166534" : sig.confidence_tier === "MEDIUM" ? "#854d0e" : "#6b7280",
                    }}>
                      {sig.confidence_tier}
                    </span>
                  </td>
                  <td style={{ ...td, textAlign: "right" }}>{(sig.strength * 100).toFixed(0)}%</td>
                  <td style={{ ...td, textAlign: "right" }}>{sig.trigger_price?.toLocaleString() ?? "-"}</td>
                  <td style={{ ...td, textAlign: "right" }}>{sig.target_price?.toLocaleString() ?? "-"}</td>
                  <td style={td}>{new Date(sig.detected_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ backgroundColor: "white", borderRadius: "8px", padding: "20px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)", marginBottom: "16px" }}>
      <h2 style={{ fontSize: "16px", marginBottom: "12px" }}>{title}</h2>
      {children}
    </div>
  );
}

function InfoCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ backgroundColor: "white", borderRadius: "8px", padding: "12px 16px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
      <div style={{ fontSize: "11px", color: "#999", marginBottom: "2px", textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: "18px", fontWeight: "bold", color: color ?? "#333" }}>{value}</div>
    </div>
  );
}

const th: React.CSSProperties = { padding: "8px 10px", textAlign: "left", fontSize: "11px", color: "#999", textTransform: "uppercase", fontWeight: 600 };
const td: React.CSSProperties = { padding: "8px 10px" };
