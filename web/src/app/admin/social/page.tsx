"use client";

import { useEffect, useState } from "react";
import { api, type SentimentSnapshot } from "@/lib/api";

export default function SocialPage() {
  const [snapshots, setSnapshots] = useState<SentimentSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.listSentiment({ limit: 50 });
        setSnapshots(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div>
      <h1 style={{ fontSize: "24px", marginBottom: "20px" }}>Social Sentiment Feed</h1>

      {error && (
        <div style={{ padding: "12px", backgroundColor: "#fef2f2", color: "#b91c1c", borderRadius: "6px", marginBottom: "16px", fontSize: "13px" }}>
          {error}
        </div>
      )}
      {loading && <div style={{ color: "#999" }}>Loading...</div>}

      {/* Sentiment Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "16px" }}>
        {snapshots.map((snap) => (
          <div
            key={snap.id}
            style={{
              backgroundColor: "#fff",
              borderRadius: "8px",
              padding: "16px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
              borderLeft: `4px solid ${sentimentColor(snap.weighted_sentiment)}`,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
              <span style={{ fontSize: "13px", fontWeight: "bold", color: "#333" }}>
                Asset #{snap.asset_id || "Global"}
              </span>
              <span style={{ fontSize: "11px", color: "#999" }}>
                {new Date(snap.observed_at).toLocaleString()}
              </span>
            </div>

            {/* Fear & Greed */}
            {snap.fear_greed_index != null && (
              <div style={{ marginBottom: "10px" }}>
                <div style={{ fontSize: "11px", color: "#888", marginBottom: "4px" }}>Fear & Greed Index</div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <div style={{ flex: 1, height: "8px", backgroundColor: "#eee", borderRadius: "4px", overflow: "hidden" }}>
                    <div style={{
                      width: `${snap.fear_greed_index}%`,
                      height: "100%",
                      backgroundColor: fgiColor(snap.fear_greed_index),
                      borderRadius: "4px",
                    }} />
                  </div>
                  <span style={{ fontSize: "14px", fontWeight: "bold", color: fgiColor(snap.fear_greed_index) }}>
                    {snap.fear_greed_index}
                  </span>
                </div>
                <div style={{ fontSize: "11px", color: "#888", marginTop: "2px" }}>
                  {fgiLabel(snap.fear_greed_index)}
                </div>
              </div>
            )}

            {/* Sentiment Breakdown */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px", fontSize: "12px" }}>
              <div>
                <div style={{ color: "#888", fontSize: "10px" }}>Bullish</div>
                <div style={{ color: "#27ae60", fontWeight: "bold" }}>
                  {snap.bullish_pct != null ? `${(snap.bullish_pct * 100).toFixed(0)}%` : "—"}
                </div>
              </div>
              <div>
                <div style={{ color: "#888", fontSize: "10px" }}>Bearish</div>
                <div style={{ color: "#e74c3c", fontWeight: "bold" }}>
                  {snap.bearish_pct != null ? `${(snap.bearish_pct * 100).toFixed(0)}%` : "—"}
                </div>
              </div>
              <div>
                <div style={{ color: "#888", fontSize: "10px" }}>Volume</div>
                <div style={{ fontWeight: "bold" }}>
                  {snap.social_volume != null ? snap.social_volume.toLocaleString() : "—"}
                </div>
              </div>
            </div>

            {/* Weighted Sentiment */}
            {snap.weighted_sentiment != null && (
              <div style={{ marginTop: "10px", fontSize: "12px" }}>
                <span style={{ color: "#888" }}>Weighted: </span>
                <span style={{ fontWeight: "bold", color: sentimentColor(snap.weighted_sentiment) }}>
                  {snap.weighted_sentiment.toFixed(3)}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>

      {snapshots.length === 0 && !loading && (
        <div style={{ textAlign: "center", color: "#999", marginTop: "40px" }}>
          No sentiment data available.
        </div>
      )}
    </div>
  );
}

function sentimentColor(score: number | null): string {
  if (score == null) return "#999";
  if (score > 0.3) return "#27ae60";
  if (score < -0.3) return "#e74c3c";
  return "#f39c12";
}

function fgiColor(index: number): string {
  if (index >= 75) return "#27ae60";
  if (index >= 50) return "#f39c12";
  if (index >= 25) return "#e67e22";
  return "#e74c3c";
}

function fgiLabel(index: number): string {
  if (index >= 75) return "Extreme Greed";
  if (index >= 55) return "Greed";
  if (index >= 45) return "Neutral";
  if (index >= 25) return "Fear";
  return "Extreme Fear";
}
