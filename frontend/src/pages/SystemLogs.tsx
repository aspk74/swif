import { useCallback, useMemo } from "react";
import { motion } from "framer-motion";
import { useBatchedPolling } from "../hooks/useBatchedPolling";
import { fetchViolations } from "../lib/api";
import { TerminalLog } from "../components/ui/TerminalLog";
import { GlassCard } from "../components/ui/GlassCard";
import { Terminal } from "lucide-react";

export function SystemLogs() {
  const fetchViolationsCb = useCallback(() => fetchViolations(1000), []);
  const { data: violations } = useBatchedPolling(fetchViolationsCb);

  const logLines = useMemo(() => {
    if (!violations) return [];
    
    // Reverse so chronologically older events are at the top and newer at the bottom
    const sorted = [...violations].reverse();
    
    let lines: string[] = [];
    for (const v of sorted) {
      if (v.remediation_logs) {
        const time = new Date(v.violated_at || v.remediation_timestamp || Date.now()).toLocaleTimeString();
        lines.push(`--- [${time}] EVENT ON DEVICE: ${v.device_id} ---`);
        const blockLines = v.remediation_logs.split('\n');
        lines = lines.concat(blockLines);
        lines.push('');
      }
    }
    
    // Return only the last 200 lines for performance with animation
    return lines.slice(-200);
  }, [violations]);

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
          gap: 12,
          marginBottom: 28,
        }}
      >
        <Terminal size={28} style={{ color: "var(--cyan)" }} />
        <h1
          style={{
            fontSize: "1.6rem",
            fontWeight: 700,
            letterSpacing: "-0.02em",
          }}
        >
          System Logs
        </h1>
      </div>

      <GlassCard delay={0.1}>
        <div style={{ height: "calc(100vh - 150px)", overflowY: "auto" }}>
          <div style={{ padding: "10px 0" }}>
            {logLines.length > 0 ? (
              <TerminalLog lines={logLines} />
            ) : (
              <div style={{ padding: 20, color: "var(--text-muted)", fontFamily: "monospace" }}>
                {">"} Waiting for system events...
              </div>
            )}
          </div>
        </div>
      </GlassCard>
    </motion.div>
  );
}
