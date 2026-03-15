/**
 * Admin navigation sidebar — categorized sections like sports-data-admin.
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavItem {
  href: string;
  label: string;
  exact?: boolean;
}

const navSections: { title: string; items: NavItem[] }[] = [
  {
    title: "General",
    items: [
      { href: "/admin", label: "Dashboard", exact: true },
    ],
  },
  {
    title: "Markets",
    items: [
      { href: "/admin/markets/browser", label: "Market Browser" },
      { href: "/admin/markets/assets", label: "Assets" },
      { href: "/admin/economic", label: "Economic" },
    ],
  },
  {
    title: "Signals",
    items: [
      { href: "/admin/signals", label: "Alpha Signals", exact: true },
      { href: "/admin/signals/performance", label: "Performance" },
      { href: "/admin/social", label: "Social Feed" },
    ],
  },
  {
    title: "Analytics",
    items: [
      { href: "/admin/pipeline", label: "Pipeline Runs" },
      { href: "/admin/portfolio", label: "Portfolio" },
    ],
  },
  {
    title: "System",
    items: [
      { href: "/admin/control-panel", label: "Control Panel" },
      { href: "/admin/logs", label: "Logs" },
      { href: "/admin/diagnostics", label: "Diagnostics" },
    ],
  },
];

export function AdminNav() {
  const pathname = usePathname();

  const isActive = (href: string, exact?: boolean) =>
    exact ? pathname === href : pathname.startsWith(href);

  return (
    <nav
      style={{
        width: "220px",
        backgroundColor: "#1a1a2e",
        color: "white",
        display: "flex",
        flexDirection: "column",
        height: "100%",
      }}
    >
      {/* Logo */}
      <div
        style={{
          padding: "16px",
          borderBottom: "1px solid #333",
        }}
      >
        <div style={{ fontSize: "18px", fontWeight: 700, letterSpacing: "-0.02em" }}>
          Fin Data
        </div>
        <div style={{ fontSize: "11px", color: "#888", marginTop: "2px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Admin Console
        </div>
      </div>

      {/* Nav sections */}
      <div style={{ flex: 1, overflowY: "auto", padding: "8px 0" }}>
        {navSections.map((section) => (
          <div key={section.title} style={{ marginBottom: "16px" }}>
            <div
              style={{
                fontSize: "10px",
                fontWeight: 600,
                color: "#666",
                textTransform: "uppercase",
                letterSpacing: "0.1em",
                padding: "0 16px",
                marginBottom: "4px",
              }}
            >
              {section.title}
            </div>
            {section.items.map((item) => {
              const active = isActive(item.href, item.exact);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  style={{
                    display: "block",
                    padding: "8px 16px",
                    color: active ? "#fff" : "#aaa",
                    backgroundColor: active ? "#16213e" : "transparent",
                    textDecoration: "none",
                    fontSize: "13px",
                    fontWeight: active ? 600 : 400,
                    borderLeft: active ? "3px solid #e94560" : "3px solid transparent",
                    transition: "background 0.15s, color 0.15s",
                  }}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div
        style={{
          padding: "12px 16px",
          borderTop: "1px solid #333",
          fontSize: "11px",
          color: "#555",
        }}
      >
        Fin Data Admin v0.2.0
      </div>
    </nav>
  );
}
