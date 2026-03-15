/**
 * Control Panel — task dispatcher and run history.
 * Equivalent to sports-data-admin's Control Panel (/admin/control-panel).
 */

"use client";

import { useEffect, useState } from "react";
import { api, type TaskRegistryEntry, type ScrapeRun, type TriggerTaskResponse } from "@/lib/api";

export default function ControlPanel() {
  const [tasks, setTasks] = useState<TaskRegistryEntry[]>([]);
  const [recentRuns, setRecentRuns] = useState<ScrapeRun[]>([]);
  const [triggering, setTriggering] = useState<string | null>(null);
  const [taskParams, setTaskParams] = useState<Record<string, Record<string, string>>>({});
  const [lastResult, setLastResult] = useState<{ taskName: string; result: TriggerTaskResponse } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [registry, runs] = await Promise.all([
          api.getTaskRegistry(),
          api.listRuns({ limit: 20 }),
        ]);
        setTasks(registry);
        setRecentRuns(runs);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    }
    load();
  }, []);

  const handleTrigger = async (taskName: string) => {
    setTriggering(taskName);
    setError(null);
    try {
      const params = taskParams[taskName];
      // Filter out empty param values
      const cleanParams: Record<string, string> = {};
      if (params) {
        for (const [k, v] of Object.entries(params)) {
          if (v.trim()) cleanParams[k] = v.trim();
        }
      }
      const result = await api.triggerTask(taskName, Object.keys(cleanParams).length > 0 ? cleanParams : undefined);
      setLastResult({ taskName, result });
      // Refresh runs
      const runs = await api.listRuns({ limit: 20 });
      setRecentRuns(runs);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setTriggering(null);
    }
  };

  const updateParam = (taskName: string, paramName: string, value: string) => {
    setTaskParams((prev) => ({
      ...prev,
      [taskName]: { ...prev[taskName], [paramName]: value },
    }));
  };

  return (
    <div>
      <h1 style={{ fontSize: "24px", marginBottom: "20px" }}>Control Panel</h1>

      {error && (
        <div style={{ padding: "12px", backgroundColor: "#fef2f2", color: "#b91c1c", borderRadius: "6px", marginBottom: "16px", fontSize: "13px" }}>
          {error}
        </div>
      )}

      {lastResult && (
        <div style={{ padding: "12px", backgroundColor: "#f0fdf4", color: "#166534", borderRadius: "6px", marginBottom: "16px", fontSize: "13px" }}>
          Task <strong>{lastResult.taskName}</strong> dispatched. Job ID: <code>{lastResult.result.job_id}</code>
        </div>
      )}

      {/* Task Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(350px, 1fr))",
          gap: "12px",
          marginBottom: "32px",
        }}
      >
        {tasks.map((task) => (
          <div
            key={task.name}
            style={{
              backgroundColor: "white",
              borderRadius: "8px",
              padding: "16px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                marginBottom: "8px",
              }}
            >
              <code style={{ fontSize: "13px", fontWeight: "bold" }}>
                {task.name}
              </code>
              <div style={{ display: "flex", gap: "4px" }}>
                {task.asset_classes.map((cls) => (
                  <span
                    key={cls}
                    style={{
                      fontSize: "10px",
                      padding: "2px 6px",
                      borderRadius: "3px",
                      backgroundColor: cls === "STOCKS" ? "#e8f5e9" : "#fff3e0",
                      color: cls === "STOCKS" ? "#2e7d32" : "#e65100",
                    }}
                  >
                    {cls}
                  </span>
                ))}
              </div>
            </div>
            <p
              style={{
                fontSize: "12px",
                color: "#666",
                marginBottom: "12px",
              }}
            >
              {task.description}
            </p>
            {task.params.length > 0 && (
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "8px" }}>
                {task.params.map((p) => (
                  <input
                    key={p}
                    type="text"
                    placeholder={p}
                    value={taskParams[task.name]?.[p] ?? ""}
                    onChange={(e) => updateParam(task.name, p, e.target.value)}
                    style={{
                      padding: "4px 8px",
                      borderRadius: "4px",
                      border: "1px solid #ddd",
                      fontSize: "12px",
                      flex: "1",
                      minWidth: "100px",
                    }}
                  />
                ))}
              </div>
            )}
            <button
              onClick={() => handleTrigger(task.name)}
              disabled={triggering === task.name}
              style={{
                padding: "6px 16px",
                borderRadius: "4px",
                border: "none",
                backgroundColor:
                  triggering === task.name ? "#ccc" : "#e94560",
                color: "white",
                cursor:
                  triggering === task.name ? "not-allowed" : "pointer",
                fontSize: "12px",
                width: "100%",
              }}
            >
              {triggering === task.name ? "Triggering..." : "Run Now"}
            </button>
          </div>
        ))}
      </div>

      {/* Recent Runs */}
      <div
        style={{
          backgroundColor: "white",
          borderRadius: "8px",
          padding: "20px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
        }}
      >
        <h2 style={{ fontSize: "16px", marginBottom: "12px" }}>
          Recent Runs
        </h2>
        {recentRuns.length === 0 ? (
          <p style={{ color: "#999", fontSize: "13px" }}>
            No runs recorded yet. Trigger a task above or start the Celery beat
            scheduler.
          </p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #eee" }}>
                <th style={thStyle}>Scraper</th>
                <th style={thStyle}>Status</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Assets</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Records</th>
                <th style={thStyle}>Started</th>
                <th style={thStyle}>Finished</th>
                <th style={thStyle}>Error</th>
              </tr>
            </thead>
            <tbody>
              {recentRuns.map((run) => (
                <tr key={run.id} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={tdStyle}>{run.scraper_type}</td>
                  <td style={tdStyle}>
                    <span style={{
                      fontSize: "11px",
                      padding: "2px 6px",
                      borderRadius: "3px",
                      backgroundColor: run.status === "success" ? "#dcfce7" : run.status === "running" ? "#dbeafe" : run.status === "error" ? "#fef2f2" : "#f3f4f6",
                      color: run.status === "success" ? "#166534" : run.status === "running" ? "#1e40af" : run.status === "error" ? "#991b1b" : "#6b7280",
                    }}>
                      {run.status}
                    </span>
                  </td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>{run.assets_processed ?? "-"}</td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>{run.records_created ?? "-"}</td>
                  <td style={tdStyle}>{run.started_at ? new Date(run.started_at).toLocaleString() : "-"}</td>
                  <td style={tdStyle}>{run.finished_at ? new Date(run.finished_at).toLocaleString() : "-"}</td>
                  <td style={{ ...tdStyle, color: "#991b1b", maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {run.error_details ?? "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
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
