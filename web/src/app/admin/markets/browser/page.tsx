/**
 * Market Browser — browse all assets with session data.
 * Equivalent to sports-data-admin's Game Browser (/admin/sports/browser).
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Asset, type MarketSession } from "@/lib/api";

type AssetClass = "ALL" | "STOCKS" | "CRYPTO";

interface AssetRow {
  id: number;
  ticker: string;
  name: string;
  assetClass: string;
  sector: string;
  lastPrice: string;
  changePct: string;
  volume: string;
  hasCandles: boolean;
  hasSignals: boolean;
  hasSocial: boolean;
  hasAnalysis: boolean;
}

export default function MarketBrowser() {
  const [filter, setFilter] = useState<AssetClass>("ALL");
  const [assets, setAssets] = useState<AssetRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const params = filter === "ALL" ? undefined : { asset_class: filter };
        const rawAssets = await api.listAssets(params);

        // Fetch latest session for each asset to get price data
        const rows: AssetRow[] = await Promise.all(
          rawAssets.map(async (asset) => {
            let session: MarketSession | null = null;
            try {
              const sessions = await api.listAssetSessions(asset.id, { limit: 1 });
              session = sessions[0] ?? null;
            } catch {
              // No sessions yet
            }

            const now = Date.now();
            const hasRecentPrice = asset.last_price_at
              ? now - new Date(asset.last_price_at).getTime() < 48 * 60 * 60 * 1000
              : false;

            return {
              id: asset.id,
              ticker: asset.ticker,
              name: asset.name,
              assetClass: asset.asset_class_code ?? "",
              sector: asset.sector ?? "-",
              lastPrice: session?.close_price != null ? `$${session.close_price.toLocaleString()}` : "--",
              changePct: session?.change_pct != null ? `${session.change_pct >= 0 ? "+" : ""}${session.change_pct.toFixed(2)}%` : "--",
              volume: session?.volume != null ? formatVolume(session.volume) : "--",
              hasCandles: hasRecentPrice,
              hasSignals: hasRecentPrice,
              hasSocial: false,
              hasAnalysis: false,
            };
          })
        );

        setAssets(rows);
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
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "20px",
        }}
      >
        <h1 style={{ fontSize: "24px" }}>Market Browser</h1>
        <div style={{ display: "flex", gap: "8px" }}>
          {(["ALL", "STOCKS", "CRYPTO"] as const).map((cls) => (
            <button
              key={cls}
              onClick={() => setFilter(cls)}
              style={{
                padding: "6px 16px",
                borderRadius: "4px",
                border: "1px solid #ddd",
                backgroundColor: filter === cls ? "#1a1a2e" : "white",
                color: filter === cls ? "white" : "#333",
                cursor: "pointer",
                fontSize: "13px",
              }}
            >
              {cls}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div style={{ padding: "12px", backgroundColor: "#fef2f2", color: "#b91c1c", borderRadius: "6px", marginBottom: "16px", fontSize: "13px" }}>
          {error}
        </div>
      )}

      <div
        style={{
          backgroundColor: "white",
          borderRadius: "8px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          overflow: "hidden",
        }}
      >
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: "13px",
          }}
        >
          <thead>
            <tr
              style={{
                backgroundColor: "#f5f5f5",
                borderBottom: "2px solid #eee",
              }}
            >
              <th style={thStyle}>Ticker</th>
              <th style={thStyle}>Name</th>
              <th style={thStyle}>Class</th>
              <th style={thStyle}>Sector</th>
              <th style={{ ...thStyle, textAlign: "right" }}>Last Price</th>
              <th style={{ ...thStyle, textAlign: "right" }}>Change %</th>
              <th style={{ ...thStyle, textAlign: "right" }}>Volume</th>
              <th style={{ ...thStyle, textAlign: "center" }}>Candles</th>
              <th style={{ ...thStyle, textAlign: "center" }}>Signals</th>
              <th style={{ ...thStyle, textAlign: "center" }}>Social</th>
              <th style={{ ...thStyle, textAlign: "center" }}>Analysis</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={11} style={{ padding: "40px", textAlign: "center", color: "#999" }}>
                  Loading assets...
                </td>
              </tr>
            ) : assets.length === 0 ? (
              <tr>
                <td
                  colSpan={11}
                  style={{ padding: "40px", textAlign: "center", color: "#999" }}
                >
                  No assets loaded. Configure data sources and run daily ingestion.
                </td>
              </tr>
            ) : (
              assets.map((asset) => (
                <Link
                  key={asset.id}
                  href={`/admin/markets/browser/${asset.id}`}
                  style={{ display: "contents", textDecoration: "none", color: "inherit" }}
                >
                  <tr
                    style={{
                      borderBottom: "1px solid #eee",
                      cursor: "pointer",
                    }}
                  >
                    <td style={tdStyle}>
                      <strong>{asset.ticker}</strong>
                    </td>
                    <td style={tdStyle}>{asset.name}</td>
                    <td style={tdStyle}>{asset.assetClass}</td>
                    <td style={tdStyle}>{asset.sector}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      {asset.lastPrice}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      <span
                        style={{
                          color: asset.changePct.startsWith("-") ? "#e74c3c" : "#27ae60",
                        }}
                      >
                        {asset.changePct}
                      </span>
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      {asset.volume}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "center" }}>
                      <StatusDot ok={asset.hasCandles} />
                    </td>
                    <td style={{ ...tdStyle, textAlign: "center" }}>
                      <StatusDot ok={asset.hasSignals} />
                    </td>
                    <td style={{ ...tdStyle, textAlign: "center" }}>
                      <StatusDot ok={asset.hasSocial} />
                    </td>
                    <td style={{ ...tdStyle, textAlign: "center" }}>
                      <StatusDot ok={asset.hasAnalysis} />
                    </td>
                  </tr>
                </Link>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: "10px",
        height: "10px",
        borderRadius: "50%",
        backgroundColor: ok ? "#27ae60" : "#e74c3c",
      }}
    />
  );
}

function formatVolume(v: number): string {
  if (v >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(1)}B`;
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v.toFixed(0);
}

const thStyle: React.CSSProperties = {
  padding: "10px 12px",
  textAlign: "left",
  fontWeight: 600,
  fontSize: "12px",
  textTransform: "uppercase",
  color: "#666",
};

const tdStyle: React.CSSProperties = {
  padding: "10px 12px",
};
