import { useState } from "react";
import { AnimatePresence, LayoutGroup, motion } from "framer-motion";
import { NavSidebar } from "./components/ui/NavSidebar";
import type { Page } from "./components/ui/NavSidebar";
import { ExecutivePosture } from "./pages/ExecutivePosture";
import { ControlRegistry } from "./pages/ControlRegistry";
import { ActionCenter } from "./pages/ActionCenter";
import { ObservabilityEngine } from "./pages/ObservabilityEngine";
import { SystemLogs } from "./pages/SystemLogs";
import { simulateDrift } from "./lib/api";
import { FleetRefreshProvider, useFleetRefresh } from "./hooks/FleetRefreshContext";

function CountdownIndicator() {
  const { secondsRemaining } = useFleetRefresh();
  
  return (
    <div style={{ position: "fixed", top: 20, right: 30, display: "flex", alignItems: "center", gap: 10, background: "rgba(24, 24, 27, 0.6)", padding: "8px 16px", borderRadius: 20, backdropFilter: "blur(12px)", border: "1px solid rgba(255,255,255,0.1)", zIndex: 50 }}>
      <div style={{ position: "relative", width: 20, height: 20 }}>
        <svg width="20" height="20" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="3" />
          <circle 
            cx="12" cy="12" r="10" fill="none" stroke="var(--cyan)" strokeWidth="3"
            strokeDasharray="62.8"
            strokeDashoffset={62.8 * (1 - secondsRemaining / 30)}
            strokeLinecap="round"
            transform="rotate(-90 12 12)"
            style={{ transition: "stroke-dashoffset 1s linear" }}
          />
        </svg>
      </div>
      <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-secondary)", fontVariantNumeric: "tabular-nums" }}>
        Refresh in {secondsRemaining}s
      </span>
    </div>
  );
}

function App() {
  const [page, setPage] = useState<Page>("Monitoring Dashboard");
  const [driftLoading, setDriftLoading] = useState(false);
  const [toast, setToast] = useState<{
    message: string;
    type: "success" | "error";
  } | null>(null);

  const showToast = (message: string, type: "success" | "error") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  async function handleSimulateDrift() {
    setDriftLoading(true);
    try {
      const result = await simulateDrift();
      showToast(`Drift simulated for ${result.device_id} on ${result.parameter}`, "success");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Drift simulation failed", "error");
    } finally {
      setDriftLoading(false);
    }
  }

  const pages: Record<Page, React.ReactNode> = {
    "Executive View": <ExecutivePosture />,
    "Rules Registry": <ControlRegistry onToast={showToast} />,
    "Monitoring Dashboard": <ActionCenter />,
    "Observability Engine": <ObservabilityEngine />,
    "System Logs": <SystemLogs />,
  };

  return (
    <FleetRefreshProvider>
      <LayoutGroup>
        <div className="app-layout">
          <CountdownIndicator />
          <NavSidebar
            activePage={page}
            onNavigate={setPage}
            onSimulateDrift={handleSimulateDrift}
            driftLoading={driftLoading}
          />

          <main className="main-content">
            <AnimatePresence mode="wait">
              <motion.div
                key={page}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.25 }}
              >
                {pages[page]}
              </motion.div>
            </AnimatePresence>
          </main>

          {/* Toast notification */}
          <AnimatePresence>
            {toast && (
              <motion.div
                initial={{ opacity: 0, y: 40, x: "-50%" }}
                animate={{ opacity: 1, y: 0, x: "-50%" }}
                exit={{ opacity: 0, y: 40, x: "-50%" }}
                transition={{ type: "spring", stiffness: 350, damping: 30 }}
                style={{
                  position: "fixed",
                  bottom: 28,
                  left: "50%",
                  padding: "12px 24px",
                  borderRadius: "var(--radius-md)",
                  fontSize: "0.85rem",
                  fontWeight: 500,
                  zIndex: 100,
                  backdropFilter: "blur(16px)",
                  border: `1px solid ${
                    toast.type === "success"
                      ? "rgba(52, 211, 153, 0.3)"
                      : "rgba(244, 63, 94, 0.3)"
                  }`,
                  background:
                    toast.type === "success"
                      ? "rgba(52, 211, 153, 0.12)"
                      : "rgba(244, 63, 94, 0.12)",
                  color:
                    toast.type === "success"
                      ? "var(--emerald)"
                      : "var(--crimson)",
                  boxShadow:
                    toast.type === "success"
                      ? "0 8px 32px rgba(52, 211, 153, 0.1)"
                      : "0 8px 32px rgba(244, 63, 94, 0.1)",
                }}
              >
                {toast.message}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </LayoutGroup>
    </FleetRefreshProvider>
  );
}

export default App;
