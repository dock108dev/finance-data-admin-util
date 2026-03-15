/**
 * Asset List — manage tracked assets (add, edit, deactivate).
 * Equivalent to sports-data-admin's Team List (/admin/sports/teams).
 */

"use client";

import { useEffect, useState } from "react";
import { api, type Asset } from "@/lib/api";

export default function AssetList() {
  const [assetClass, setAssetClass] = useState<"ALL" | "STOCKS" | "CRYPTO">("ALL");
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const params = assetClass === "ALL" ? undefined : { asset_class: assetClass };
        const data = await api.listAssets(params);
        setAssets(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [assetClass]);

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
        <h1 style={{ fontSize: "24px" }}>Tracked Assets</h1>
        <div style={{ display: "flex", gap: "8px" }}>
          <select
            value={assetClass}
            onChange={(e) => setAssetClass(e.target.value as typeof assetClass)}
            style={{
              padding: "6px 12px",
              borderRadius: "4px",
              border: "1px solid #ddd",
              fontSize: "13px",
            }}
          >
            <option value="ALL">All Classes</option>
            <option value="STOCKS">Stocks</option>
            <option value="CRYPTO">Crypto</option>
          </select>
          <button
            style={{
              padding: "6px 16px",
              borderRadius: "4px",
              border: "none",
              backgroundColor: "#1a1a2e",
              color: "white",
              cursor: "pointer",
              fontSize: "13px",
            }}
          >
            + Add Asset
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: "12px", backgroundColor: "#fef2f2", color: "#b91c1c", borderRadius: "6px", marginBottom: "16px", fontSize: "13px" }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ backgroundColor: "white", borderRadius: "8px", padding: "40px", textAlign: "center", color: "#999", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
          Loading assets...
        </div>
      ) : assets.length === 0 ? (
        <div
          style={{
            backgroundColor: "white",
            borderRadius: "8px",
            padding: "40px",
            textAlign: "center",
            color: "#999",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          }}
        >
          <p>No assets configured yet.</p>
          <p style={{ fontSize: "13px" }}>
            Add stock tickers (AAPL, MSFT, GOOGL) or crypto tokens (BTC, ETH, SOL)
            to start tracking.
          </p>
        </div>
      ) : (
        <div style={{ backgroundColor: "white", borderRadius: "8px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)", overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
            <thead>
              <tr style={{ backgroundColor: "#f5f5f5", borderBottom: "2px solid #eee" }}>
                <th style={thStyle}>Ticker</th>
                <th style={thStyle}>Name</th>
                <th style={thStyle}>Class</th>
                <th style={thStyle}>Sector</th>
                <th style={thStyle}>Exchange</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Market Cap</th>
                <th style={thStyle}>Active</th>
                <th style={thStyle}>Last Price At</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((asset) => {
                const freshness = getFreshness(asset.last_price_at);
                return (
                  <tr key={asset.id} style={{ borderBottom: "1px solid #eee" }}>
                    <td style={tdStyle}><strong>{asset.ticker}</strong></td>
                    <td style={tdStyle}>{asset.name}</td>
                    <td style={tdStyle}>
                      <span style={{
                        fontSize: "11px",
                        padding: "2px 6px",
                        borderRadius: "3px",
                        backgroundColor: asset.asset_class_code === "STOCKS" ? "#e8f5e9" : "#fff3e0",
                        color: asset.asset_class_code === "STOCKS" ? "#2e7d32" : "#e65100",
                      }}>
                        {asset.asset_class_code}
                      </span>
                    </td>
                    <td style={tdStyle}>{asset.sector ?? "-"}</td>
                    <td style={tdStyle}>{asset.exchange ?? "-"}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      {asset.market_cap != null ? `$${(asset.market_cap / 1e9).toFixed(1)}B` : "-"}
                    </td>
                    <td style={tdStyle}>
                      <span style={{
                        display: "inline-block",
                        width: "8px",
                        height: "8px",
                        borderRadius: "50%",
                        backgroundColor: asset.is_active ? "#27ae60" : "#999",
                      }} />
                    </td>
                    <td style={tdStyle}>
                      {asset.last_price_at ? (
                        <span style={{ color: freshness.color }}>
                          {new Date(asset.last_price_at).toLocaleString()}
                        </span>
                      ) : (
                        <span style={{ color: "#999" }}>Never</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function getFreshness(lastPriceAt: string | null): { color: string } {
  if (!lastPriceAt) return { color: "#e74c3c" };
  const hoursAgo = (Date.now() - new Date(lastPriceAt).getTime()) / (1000 * 60 * 60);
  if (hoursAgo < 24) return { color: "#27ae60" };
  if (hoursAgo < 48) return { color: "#f39c12" };
  return { color: "#e74c3c" };
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
