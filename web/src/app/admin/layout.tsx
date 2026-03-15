/**
 * Admin layout — navigation sidebar + main content area + runs drawer.
 * Equivalent to sports-data-admin's admin layout.
 */

import { AdminNav } from "@/components/admin/AdminNav";
import { RunsDrawer } from "@/components/admin/RunsDrawer";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <AdminNav />
      <main
        style={{
          flex: 1,
          padding: "24px",
          paddingBottom: "48px",
          backgroundColor: "#f8f9fa",
          overflow: "auto",
        }}
      >
        {children}
      </main>
      <RunsDrawer />
    </div>
  );
}
