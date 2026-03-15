/**
 * Signal Viewer — alpha signals and arbitrage opportunities.
 * Equivalent to sports-data-admin's FairBet Odds Viewer (/admin/fairbet/odds).
 */

"use client";

import { useEffect, useState } from "react";
import { api, type AlphaSignal } from "@/lib/api";

type SignalFilter = "ALL" | "CROSS_EXCHANGE_ARB" | "TECHNICAL_BREAKOUT" | "SENTIMENT_DIVERGENCE" | "WHALE_ACCUMULATION";
type ConfidenceFilter = "ALL" | "HIGH" | "MEDIUM" | "LOW";

export default function SignalViewer() {
  const [signalType, setSignalType] = useState<SignalFilter>("ALL");
  const [confidence, setConfidence] = useState<ConfidenceFilter>("ALL");
  const [signals, setSignals] = useState<AlphaSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const params: Record<string, string | number> = {};
        if (signalType !== "ALL") params.signal_type = signalType;
        if (confidence !== "ALL") params.confidence_tier = confidence;
        const data = await api.listSignals(params);
        setSignals(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [signalType, confidence]);

  return (
    <div>
      <h1 style={{ fontSize: "24px", marginBottom: "20px" }}>
        Alpha Signals
      </h1>

      {/* Filters */}
      <div
        style={{
          display: "flex",
          gap: "12px",
          marginBottom: "20px",
          flexWrap: "wrap",
        }}
      >
        <FilterSelect
          label="Signal Type"
          value={signalType}
          onChange={(v) => setSignalType(v as SignalFilter)}
          options={[
            { value: "ALL", label: "All Types" },
            { value: "CROSS_EXCHANGE_ARB", label: "Cross-Exchange Arb" },
            { value: "TECHNICAL_BREAKOUT", label: "Technical Breakout" },
            { value: "SENTIMENT_DIVERGENCE", label: "Sentiment Divergence" },
            { value: "WHALE_ACCUMULATION", label: "Whale Accumulation" },
          ]}
        />
        <FilterSelect
          label="Confidence"
          value={confidence}
          onChange={(v) => setConfidence(v as ConfidenceFilter)}
          options={[
            { value: "ALL", label: "All Tiers" },
            { value: "HIGH", label: "HIGH" },
            { value: "MEDIUM", label: "MEDIUM" },
            { value: "LOW", label: "LOW" },
          ]}
        />
      </div>

      {error && (
        <div style={{ padding: "12px", backgroundColor: "#fef2f2", color: "#b91c1c", borderRadius: "6px", marginBottom: "16px", fontSize: "13px" }}>
          {error}
        </div>
      )}

      {/* Signal Table */}
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
            <tr style={{ backgroundColor: "#f5f5f5", borderBottom: "2px solid #eee" }}>
              <th style={thStyle}>Asset</th>
              <th style={thStyle}>Type</th>
              <th style={thStyle}>Direction</th>
              <th style={{ ...thStyle, textAlign: "right" }}>Strength</th>
              <th style={thStyle}>Confidence</th>
              <th style={{ ...thStyle, textAlign: "right" }}>EV %</th>
              <th style={{ ...thStyle, textAlign: "right" }}>Entry</th>
              <th style={{ ...thStyle, textAlign: "right" }}>Target</th>
              <th style={{ ...thStyle, textAlign: "right" }}>R:R</th>
              <th style={thStyle}>Detected</th>
              <th style={thStyle}>Outcome</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={11} style={{ padding: "40px", textAlign: "center", color: "#999" }}>
                  Loading signals...
                </td>
              </tr>
            ) : signals.length === 0 ? (
              <tr>
                <td
                  colSpan={11}
                  style={{ padding: "40px", textAlign: "center", color: "#999" }}
                >
                  No signals detected yet. Run the signal pipeline to scan for opportunities.
                </td>
              </tr>
            ) : (
              signals.map((s) => (
                <>
                  <tr
                    key={s.id}
                    style={{ borderBottom: "1px solid #eee", cursor: s.derivation ? "pointer" : "default" }}
                    onClick={() => s.derivation && setExpandedId(expandedId === s.id ? null : s.id)}
                  >
                    <td style={tdStyle}>{s.asset_id}</td>
                    <td style={tdStyle}>{s.signal_type}</td>
                    <td style={tdStyle}>
                      <span style={{
                        color: s.direction === "LONG" ? "#27ae60" : s.direction === "SHORT" ? "#e74c3c" : "#999",
                        fontWeight: 600,
                      }}>
                        {s.direction}
                      </span>
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "6px" }}>
                        <div style={{ width: "60px", height: "6px", backgroundColor: "#eee", borderRadius: "3px", overflow: "hidden" }}>
                          <div style={{ width: `${s.strength * 100}%`, height: "100%", backgroundColor: s.strength > 0.7 ? "#27ae60" : s.strength > 0.4 ? "#f39c12" : "#e74c3c", borderRadius: "3px" }} />
                        </div>
                        <span>{(s.strength * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td style={tdStyle}>
                      <ConfidenceBadge tier={s.confidence_tier} />
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      {s.ev_estimate != null ? `${(s.ev_estimate * 100).toFixed(1)}%` : "-"}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      {s.trigger_price?.toLocaleString() ?? "-"}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      {s.target_price?.toLocaleString() ?? "-"}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      {s.risk_reward_ratio != null ? s.risk_reward_ratio.toFixed(1) : "-"}
                    </td>
                    <td style={tdStyle}>{new Date(s.detected_at).toLocaleString()}</td>
                    <td style={tdStyle}>
                      {s.outcome ? (
                        <span style={{
                          fontSize: "11px",
                          padding: "2px 6px",
                          borderRadius: "3px",
                          backgroundColor: s.outcome === "HIT" ? "#dcfce7" : s.outcome === "MISS" ? "#fef2f2" : "#f3f4f6",
                          color: s.outcome === "HIT" ? "#166534" : s.outcome === "MISS" ? "#991b1b" : "#6b7280",
                        }}>
                          {s.outcome}
                        </span>
                      ) : (
                        <span style={{ color: "#999" }}>PENDING</span>
                      )}
                    </td>
                  </tr>
                  {expandedId === s.id && s.derivation && (
                    <tr key={`${s.id}-detail`}>
                      <td colSpan={11} style={{ padding: "12px 16px", backgroundColor: "#fafafa" }}>
                        <pre style={{ fontSize: "11px", whiteSpace: "pre-wrap", margin: 0 }}>
                          {JSON.stringify(s.derivation, null, 2)}
                        </pre>
                      </td>
                    </tr>
                  )}
                </>
              ))
            )}
          </tbody>
        </table>
      </div>
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

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div>
      <label
        style={{
          display: "block",
          fontSize: "11px",
          color: "#666",
          marginBottom: "4px",
          textTransform: "uppercase",
        }}
      >
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          padding: "6px 12px",
          borderRadius: "4px",
          border: "1px solid #ddd",
          fontSize: "13px",
          minWidth: "160px",
        }}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
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
