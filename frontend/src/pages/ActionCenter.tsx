import { useState, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import { useBatchedPolling } from "../hooks/useBatchedPolling";
import { fetchViolations, executeRemediation } from "../lib/api";
import type { Violation } from "../lib/api";
import { Wrench, Lock, ShieldCheck, Clock } from "lucide-react";

export function ActionCenter() {
  const fetchViolationsCb = useCallback(() => fetchViolations(1000), []);
  const { data: violations, refresh } = useBatchedPolling(fetchViolationsCb);
  const [fixingIds, setFixingIds] = useState<Set<string>>(new Set());

  // We need a fast ticking local state to update the grace period countdowns smoothly
  const [, setNow] = useState(Date.now());
  useEffect(() => {
    const int = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(int);
  }, []);

  const REALISTIC_NAMES = [
    "Anushka's MacBook Pro", "Rishi's Google Pad", "John's ThinkPad",
    "Sarah's iPhone 14", "Mike's Dell XPS", "Emily's iPad Air",
    "David's Galaxy S23", "Chloe's MacBook Air", "James's Surface Pro",
    "Lisa's Pixel 8", "Tom's Chromebook", "Anna's Galaxy Tab",
    "Robert's Mac Studio", "Maria's iPhone 15 Pro", "William's XPS 15",
    "Sophie's iPad Pro", "Richard's ThinkPad T14", "Emma's Pixel 7a",
    "Joseph's ROG Zephyrus", "Olivia's MacBook Pro 16", "Charles's Surface Laptop",
    "Grace's Galaxy Z Fold", "Daniel's Alienware m16", "Lily's iPhone 13",
    "Matthew's ThinkPad X1"
  ];

  // Map all 25 devices in the fleet to their current state based on active violations
  const fleetDevices = Array.from({ length: 25 }, (_, idx) => {
    const devNum = idx + 1;
    const deviceId = `LAPTOP-CORP-${String(devNum).padStart(3, "0")}`;
    const deviceName = REALISTIC_NAMES[idx];

    const deviceViolations =
      violations?.filter(
        (v) =>
          v.device_id === deviceId && v.action_taken !== "AUTOMATED_FIX"
      ) || [];

    // Determine worst state
    let state: "HEALTHY" | "GRACE_PERIOD" | "NON_COMPLIANT" | "QUARANTINED" = "HEALTHY";
    if (deviceViolations.some((v) => v.action_taken === "QUARANTINED")) {
      state = "QUARANTINED";
    } else if (deviceViolations.some((v) => v.action_taken === "LOGGED_FOR_REVIEW")) {
      state = "NON_COMPLIANT";
    } else if (deviceViolations.some((v) => v.action_taken === "GRACE_PERIOD")) {
      state = "GRACE_PERIOD";
    }

    return {
      deviceId,
      deviceName,
      deviceViolations,
      state,
      idx
    };
  });

  // Count active alerts in the fleet
  const activeAlertsCount = fleetDevices.filter((d) => d.state !== "HEALTHY").length;

  async function handleFix(deviceId: string, deviceViolations: Violation[]) {
    // Collect all violations for this device that need fixing
    const toFix = deviceViolations.filter(
      (v) =>
        v.action_taken === "LOGGED_FOR_REVIEW" ||
        v.action_taken === "GRACE_PERIOD"
    );

    if (toFix.length === 0) return;

    setFixingIds((prev) => new Set(prev).add(deviceId));
    try {
      // Execute fixes concurrently
      await Promise.all(toFix.map((v) => executeRemediation(v._id)));
      // Note: we let the global batched polling (or next tick) refresh the state, 
      // but we can also manually refresh here
      refresh();
    } catch (err) {
      console.error("Failed to fix some violations:", err);
    } finally {
      setFixingIds((prev) => {
        const next = new Set(prev);
        next.delete(deviceId);
        return next;
      });
    }
  }

  function formatCountdown(expiresAtStr: string) {
    const expiresAt = new Date(expiresAtStr).getTime();
    const diff = expiresAt - Date.now();
    if (diff <= 0) return "Expired";
    
    const h = Math.floor(diff / (1000 * 60 * 60));
    const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const s = Math.floor((diff % (1000 * 60)) / 1000);
    
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m ${s}s`;
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 28,
        }}
      >
        <h1
          style={{
            fontSize: "1.6rem",
            fontWeight: 700,
            letterSpacing: "-0.02em",
          }}
        >
          Monitoring Dashboard
        </h1>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
        <h2
          style={{
            fontSize: "1.2rem",
            fontWeight: 600,
            letterSpacing: "-0.01em",
            color: "var(--text-primary)",
          }}
        >
          Device Fleet Alerts
        </h2>
        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", background: "rgba(255,255,255,0.05)", padding: "2px 8px", borderRadius: 12 }}>
          {activeAlertsCount} Active Alerts / {fleetDevices.length} Total Devices
        </span>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
          gap: 16,
        }}
      >
        {fleetDevices.map(({ deviceId, deviceName, deviceViolations, state, idx }) => {
            const isFixing = fixingIds.has(deviceId);

            // Get styling based on state
            let borderColor = "rgba(52, 211, 153, 0.25)";
            let bgGrad = "linear-gradient(135deg, rgba(52, 211, 153, 0.08), rgba(52, 211, 153, 0.02))";
            let shadow = "0 4px 20px rgba(52, 211, 153, 0.02)";
            let textColor = "var(--emerald)";
            let dotColor = "emerald";

            if (state === "QUARANTINED") {
              borderColor = "rgba(192, 132, 252, 0.35)";
              bgGrad = "linear-gradient(135deg, rgba(192, 132, 252, 0.12), rgba(192, 132, 252, 0.03))";
              shadow = "0 4px 20px rgba(192, 132, 252, 0.05)";
              textColor = "var(--purple)";
              dotColor = "purple";
            } else if (state === "NON_COMPLIANT") {
              borderColor = "rgba(244, 63, 94, 0.35)";
              bgGrad = "linear-gradient(135deg, rgba(244, 63, 94, 0.12), rgba(244, 63, 94, 0.03))";
              shadow = "0 4px 20px rgba(244, 63, 94, 0.05)";
              textColor = "var(--crimson)";
              dotColor = "crimson";
            } else if (state === "GRACE_PERIOD") {
              borderColor = "rgba(251, 191, 36, 0.35)";
              bgGrad = "linear-gradient(135deg, rgba(251, 191, 36, 0.12), rgba(251, 191, 36, 0.03))";
              shadow = "0 4px 20px rgba(251, 191, 36, 0.05)";
              textColor = "var(--amber)";
              dotColor = "amber";
            }

            // Find the earliest grace period to show on the tile
            const gracePeriods = deviceViolations
              .filter((v) => v.action_taken === "GRACE_PERIOD" && v.grace_period_expires_at)
              .map((v) => v.grace_period_expires_at!);
            
            let earliestGraceExpiry: string | null = null;
            if (gracePeriods.length > 0) {
              earliestGraceExpiry = gracePeriods.reduce((a, b) => 
                new Date(a).getTime() < new Date(b).getTime() ? a : b
              );
            }

            return (
              <motion.div
                key={deviceId}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3, delay: Math.min(idx * 0.02, 0.4) }}
                style={{
                  padding: "16px 20px",
                  borderRadius: "var(--radius-md)",
                  border: `1px solid ${borderColor}`,
                  background: bgGrad,
                  boxShadow: shadow,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  minHeight: 140,
                  position: "relative",
                  overflow: "hidden",
                  backdropFilter: "blur(12px)",
                  WebkitBackdropFilter: "blur(12px)",
                  transition: "border-color 0.3s ease, box-shadow 0.3s ease",
                }}
              >
                {/* Glowing status dots */}
                <div style={{ position: "absolute", top: 12, right: 12 }}>
                  <div className={`pulse-dot pulse-dot-${dotColor}`} />
                </div>

                <div>
                  <div
                    style={{
                      fontSize: "0.88rem",
                      fontWeight: 700,
                      color: textColor,
                      marginBottom: 4,
                      letterSpacing: "-0.01em",
                    }}
                  >
                    {deviceName}
                  </div>
                  <code style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                    {deviceId}
                  </code>

                  {state !== "HEALTHY" && (
                    <ul
                      style={{
                        marginTop: 12,
                        paddingLeft: 14,
                        fontSize: "0.76rem",
                        color: "var(--text-secondary)",
                        display: "flex",
                        flexDirection: "column",
                        gap: 4,
                      }}
                    >
                      {deviceViolations.map((v, vIdx) => {
                        const shortName = v.technical_parameter
                          .replace(/_/g, " ")
                          .replace(/\b\w/g, (c) => c.toUpperCase());
                        return (
                          <li key={vIdx} style={{ listStyleType: "disc" }}>
                            {shortName}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>

                {/* Status Footer */}
                <div style={{ marginTop: 16 }}>
                  {state === "HEALTHY" && (
                    <div
                      style={{
                        fontSize: "0.72rem",
                        color: "rgba(52, 211, 153, 0.7)",
                        fontWeight: 500,
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                      }}
                    >
                      <ShieldCheck size={14} />
                      All checks passing
                    </div>
                  )}

                  {state === "QUARANTINED" && (
                    <div
                      style={{
                        fontSize: "0.72rem",
                        color: textColor,
                        fontWeight: 600,
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                      }}
                    >
                      <Lock size={14} />
                      Device Quarantined
                    </div>
                  )}

                  {(state === "NON_COMPLIANT" || state === "GRACE_PERIOD") && (
                    <div style={{ display: "flex", alignItems: "center", justifyContext: "space-between", justifyContent: "space-between" }}>
                      {/* Fix Button */}
                      <button
                        onClick={() => handleFix(deviceId, deviceViolations)}
                        disabled={isFixing}
                        style={{
                          background: "rgba(255,255,255,0.05)",
                          border: `1px solid ${borderColor}`,
                          color: "var(--text-primary)",
                          padding: "4px 10px",
                          borderRadius: 6,
                          fontSize: "0.72rem",
                          fontWeight: 500,
                          cursor: isFixing ? "not-allowed" : "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                          opacity: isFixing ? 0.6 : 1,
                        }}
                      >
                        <Wrench size={12} />
                        {isFixing ? "Fixing..." : "Execute Fix"}
                      </button>

                      {/* Timer Badge for Grace Period */}
                      {state === "GRACE_PERIOD" && earliestGraceExpiry && (
                        <div 
                          style={{
                            fontSize: "0.68rem",
                            color: "var(--amber)",
                            background: "rgba(251, 191, 36, 0.1)",
                            padding: "2px 6px",
                            borderRadius: 4,
                            display: "flex",
                            alignItems: "center",
                            gap: 4
                          }}
                        >
                          <Clock size={10} />
                          {formatCountdown(earliestGraceExpiry)}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
    </motion.div>
  );
}
