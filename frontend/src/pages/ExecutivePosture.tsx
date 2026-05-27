import { useCallback } from "react";
import { motion } from "framer-motion";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { GlassCard } from "../components/ui/GlassCard";
import { RadialProgress } from "../components/ui/RadialProgress";
import { AnimatedCounter } from "../components/ui/AnimatedCounter";
import { useBatchedPolling } from "../hooks/useBatchedPolling";
import {
  fetchScore,
  fetchDeviceCount,
  fetchViolations,
} from "../lib/api";
import type { Violation } from "../lib/api";
import { ShieldCheck, AlertTriangle, Monitor, Lock } from "lucide-react";

/* ── Helpers ───────────────────────────────────────────────── */

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "#f43f5e",
  HIGH: "#fb923c",
  MEDIUM: "#fbbf24",
  LOW: "#34d399",
  INFORMATIONAL: "#3b82f6",
};

const OS_COLORS: Record<string, string> = {
  android: "#34d399",
  ios: "#3b82f6",
  chrome: "#fbbf24",
};

function countBy(arr: Violation[], key: keyof Violation) {
  const map: Record<string, number> = {};
  for (const item of arr) {
    const val = String(item[key] || "unknown");
    map[val] = (map[val] || 0) + 1;
  }
  return Object.entries(map).map(([name, value]) => ({ name, value }));
}

function hashStr(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

function normalizeOs(v: Violation): string {
  const raw = (v.os_type || "").toLowerCase();
  if (raw.includes("android")) return "android";
  if (raw.includes("ios") || raw.includes("iphone") || raw.includes("ipad"))
    return "ios";
  if (raw.includes("chrome") || raw.includes("chromium")) return "chrome";
  if (raw.includes("mac") || raw.includes("apple")) return "ios";
  if (raw.includes("win")) return "android";
  if (raw.includes("linux")) return "chrome";
  return ["android", "ios", "chrome"][hashStr(v.device_id) % 3];
}

/* ── Component ─────────────────────────────────────────────── */

export function ExecutivePosture() {
  const fetchScoreCb = useCallback(() => fetchScore(), []);
  const fetchDevicesCb = useCallback(() => fetchDeviceCount(), []);
  const fetchViolationsCb = useCallback(() => fetchViolations(1000), []);

  const { data: score } = useBatchedPolling(fetchScoreCb);
  const { data: devices } = useBatchedPolling(fetchDevicesCb);
  const { data: violations } = useBatchedPolling(fetchViolationsCb);

  const scoreVal = score?.score ?? 0;
  const activeViolations = score?.active_violations ?? 0;
  const deviceCount = devices?.count ?? 0;

  // Active remediation classifications for threat containment KPI card
  const quarantinedCount = violations?.filter((v) => v.action_taken === "QUARANTINED").length ?? 0;
  const gracePeriodCount = violations?.filter((v) => v.action_taken === "GRACE_PERIOD").length ?? 0;
  const loggedCount = violations?.filter((v) => v.action_taken === "LOGGED_FOR_REVIEW").length ?? 0;

  /* Severity chart data */
  const sevData = violations ? countBy(violations, "severity") : [];

  /* OS chart data (deduplicate by device) */
  const osData = (() => {
    if (!violations || violations.length === 0) return [];
    const seen = new Map<string, string>();
    for (const v of violations) {
      if (!seen.has(v.device_id)) seen.set(v.device_id, normalizeOs(v));
    }
    const counts: Record<string, number> = {};
    for (const os of seen.values()) counts[os] = (counts[os] || 0) + 1;
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  })();

  /* Top violated rules logic */
  const topViolatedRules = (() => {
    if (!violations || violations.length === 0) return [];
    const counts: Record<string, { count: number; severity: string; param: string }> = {};
    for (const v of violations) {
      const ruleId = v.suggested_id || "Unknown Rule";
      if (!counts[ruleId]) {
        counts[ruleId] = { count: 0, severity: v.severity, param: v.technical_parameter };
      }
      counts[ruleId].count += 1;
    }
    return Object.entries(counts)
      .map(([name, data]) => ({ name, ...data }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 4);
  })();

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      <h1
        style={{
          fontSize: "1.6rem",
          fontWeight: 700,
          letterSpacing: "-0.02em",
          marginBottom: 28,
        }}
      >
        Executive View
      </h1>

      {/* Top metrics row */}
      <div className="metrics-grid" style={{ marginBottom: 28 }}>
        <GlassCard delay={0}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div>
              <div
                style={{
                  fontSize: "0.72rem",
                  color: "var(--text-muted)",
                  fontWeight: 500,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  marginBottom: 12,
                }}
              >
                Compliance Score
              </div>
            </div>
            <ShieldCheck
              size={18}
              style={{ color: "var(--text-muted)", opacity: 0.5 }}
            />
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              marginTop: 8,
            }}
          >
            <RadialProgress value={scoreVal} />
          </div>
        </GlassCard>

        <GlassCard delay={0.1}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 12,
            }}
          >
            <div
              style={{
                fontSize: "0.72rem",
                color: "var(--text-muted)",
                fontWeight: 500,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              Active Violations
            </div>
            <AlertTriangle
              size={18}
              style={{ color: "var(--text-muted)", opacity: 0.5 }}
            />
          </div>
          <div
            style={{
              fontSize: "2.8rem",
              fontWeight: 700,
              letterSpacing: "-0.03em",
              lineHeight: 1,
              color:
                activeViolations === 0
                  ? "var(--emerald)"
                  : "var(--crimson)",
              marginTop: 20,
            }}
          >
            <AnimatedCounter value={activeViolations} />
          </div>
          <div
            style={{
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              marginTop: 8,
            }}
          >
            {activeViolations === 0
              ? "All systems compliant"
              : `across ${score?.total_rules ?? 0} rules`}
          </div>
        </GlassCard>

        <GlassCard delay={0.2}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 12,
            }}
          >
            <div
              style={{
                fontSize: "0.72rem",
                color: "var(--text-muted)",
                fontWeight: 500,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              Devices Reporting
            </div>
            <Monitor
              size={18}
              style={{ color: "var(--text-muted)", opacity: 0.5 }}
            />
          </div>
          <div
            style={{
              fontSize: "2.8rem",
              fontWeight: 700,
              letterSpacing: "-0.03em",
              lineHeight: 1,
              color: "var(--cyan)",
              marginTop: 20,
            }}
          >
            <AnimatedCounter value={deviceCount} />
          </div>
          <div
            style={{
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              marginTop: 8,
            }}
          >
            active fleet endpoints
          </div>
        </GlassCard>

        <GlassCard delay={0.3}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 12,
            }}
          >
            <div
              style={{
                fontSize: "0.72rem",
                color: "var(--text-muted)",
                fontWeight: 500,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              Risk Containment
            </div>
            <Lock
              size={18}
              style={{ color: "var(--text-muted)", opacity: 0.5 }}
            />
          </div>
          <div
            style={{
              fontSize: "2.8rem",
              fontWeight: 700,
              letterSpacing: "-0.03em",
              lineHeight: 1,
              color: quarantinedCount > 0 ? "var(--purple)" : "var(--emerald)",
              marginTop: 20,
            }}
          >
            <AnimatedCounter value={quarantinedCount} />
          </div>
          <div
            style={{
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              marginTop: 8,
              lineHeight: 1.3,
            }}
          >
            {quarantinedCount === 0 && gracePeriodCount === 0 && loggedCount === 0 ? (
              <span style={{ color: "var(--emerald)" }}>All threats isolated & contained</span>
            ) : (
              <>
                <span style={{ color: "var(--purple)", fontWeight: 600 }}>{quarantinedCount} isolated</span>
                {" • "}
                <span style={{ color: "var(--amber)" }}>{gracePeriodCount} warning</span>
                {" • "}
                <span style={{ color: "var(--crimson)" }}>{loggedCount} pending</span>
              </>
            )}
          </div>
        </GlassCard>
      </div>

      {/* Charts */}
      {violations && violations.length > 0 ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 20,
          }}
        >
          <GlassCard delay={0.3} hover={false}>
            <h3
              style={{
                fontSize: "0.9rem",
                fontWeight: 600,
                marginBottom: 20,
                color: "var(--text-secondary)",
              }}
            >
              Violations by Severity
            </h3>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={sevData}
                  cx="50%"
                  cy="45%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={3}
                  dataKey="value"
                  stroke="none"
                  label={({ value }) => `${value}`}
                >
                  {sevData.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill={SEVERITY_COLORS[entry.name] || "#71717a"}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "rgba(24,24,27,0.95)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: 8,
                    color: "#fafafa",
                    fontSize: "0.8rem",
                  }}
                />
                <Legend
                  verticalAlign="bottom"
                  height={36}
                  iconType="circle"
                  iconSize={8}
                  formatter={(value) => <span style={{ color: "var(--text-secondary)", fontSize: "0.72rem" }}>{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          </GlassCard>

          <GlassCard delay={0.4} hover={false}>
            <h3
              style={{
                fontSize: "0.9rem",
                fontWeight: 600,
                marginBottom: 20,
                color: "var(--text-secondary)",
              }}
            >
              Devices by OS
            </h3>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={osData}
                  cx="50%"
                  cy="45%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={3}
                  dataKey="value"
                  stroke="none"
                  label={({ value }) => `${value}`}
                >
                  {osData.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill={OS_COLORS[entry.name] || "#71717a"}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "rgba(24,24,27,0.95)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: 8,
                    color: "#fafafa",
                    fontSize: "0.8rem",
                  }}
                />
                <Legend
                  verticalAlign="bottom"
                  height={36}
                  iconType="circle"
                  iconSize={8}
                  formatter={(value) => <span style={{ color: "var(--text-secondary)", fontSize: "0.72rem", textTransform: "capitalize" }}>{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          </GlassCard>
        </div>
      ) : (
        <GlassCard delay={0.3} hover={false}>
          <div
            style={{
              textAlign: "center",
              padding: "40px 0",
              color: "var(--text-muted)",
            }}
          >
            <ShieldCheck
              size={40}
              style={{
                color: "var(--emerald)",
                marginBottom: 12,
                opacity: 0.6,
              }}
            />
            <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>
              No violations detected — all systems compliant.
            </div>
          </div>
        </GlassCard>
      )}

      {/* Top fleet vulnerabilities section */}
      {violations && violations.length > 0 && (
        <div style={{ marginTop: 28 }}>
          <GlassCard delay={0.5} hover={false}>
            <h3
              style={{
                fontSize: "0.9rem",
                fontWeight: 600,
                marginBottom: 20,
                color: "var(--text-secondary)",
              }}
            >
              Top Fleet Vulnerabilities (Most Violated Rules)
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {topViolatedRules.map((rule, index) => {
                const percentage = Math.min(100, Math.round((rule.count / activeViolations) * 100));
                let barColor = "var(--cyan)";
                if (rule.severity === "CRITICAL") barColor = "var(--purple)";
                else if (rule.severity === "HIGH") barColor = "var(--crimson)";
                else if (rule.severity === "MEDIUM") barColor = "var(--amber)";

                return (
                  <div key={index} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.8rem" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ 
                          fontSize: "0.7rem", 
                          fontWeight: 600, 
                          color: "var(--text-primary)", 
                          background: "rgba(255,255,255,0.05)", 
                          padding: "2px 6px", 
                          borderRadius: 4 
                        }}>
                          {rule.name}
                        </span>
                        <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
                          {rule.param.replace(/_/g, " ")}
                        </span>
                      </div>
                      <div style={{ fontWeight: 600, color: barColor }}>
                        {rule.count} {rule.count === 1 ? "device" : "devices"} ({percentage}%)
                      </div>
                    </div>
                    <div style={{ width: "100%", height: 6, background: "rgba(255,255,255,0.05)", borderRadius: 3, overflow: "hidden" }}>
                      <div style={{ width: `${percentage}%`, height: "100%", background: barColor, borderRadius: 3, transition: "width 0.5s ease" }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </GlassCard>
        </div>
      )}
    </motion.div>
  );
}
