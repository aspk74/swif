import { useCallback } from "react";
import { motion } from "framer-motion";
import { GlassCard } from "../components/ui/GlassCard";
import { AnimatedCounter } from "../components/ui/AnimatedCounter";
import { usePolling } from "../hooks/usePolling";
import { fetchRules } from "../lib/api";
import {
  Sparkles,
  DollarSign,
} from "lucide-react";

export function ObservabilityEngine() {
  const fetchRulesCb = useCallback(() => fetchRules(200), []);
  const { data: rules } = usePolling(fetchRulesCb, 30000);

  // AI Pipeline estimates
  const totalRules = rules?.length ?? 0;
  const estimatedTokens = totalRules * 1200;
  const estimatedCost = (estimatedTokens / 1_000_000) * 0.15;

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
        Observability Engine
      </h1>

      {/* AI Pipeline Estimates */}
      <div
        style={{
          fontSize: "0.72rem",
          fontWeight: 600,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          marginBottom: 12,
        }}
      >
        AI Pipeline Estimates
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 20,
        }}
      >
        <GlassCard delay={0.4}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 16,
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
              Estimated Tokens Used
            </div>
            <Sparkles
              size={16}
              style={{ color: "var(--text-muted)", opacity: 0.5 }}
            />
          </div>
          <div
            style={{
              fontSize: "2.4rem",
              fontWeight: 700,
              letterSpacing: "-0.03em",
              lineHeight: 1,
              color: "#c084fc",
            }}
          >
            <AnimatedCounter value={estimatedTokens} />
          </div>
          <div
            style={{
              fontSize: "0.72rem",
              color: "var(--text-muted)",
              marginTop: 6,
            }}
          >
            ~{totalRules} rules × 1,200 tokens
          </div>
        </GlassCard>

        <GlassCard delay={0.5}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 16,
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
              Estimated LLM Cost
            </div>
            <DollarSign
              size={16}
              style={{ color: "var(--text-muted)", opacity: 0.5 }}
            />
          </div>
          <div
            style={{
              fontSize: "2.4rem",
              fontWeight: 700,
              letterSpacing: "-0.03em",
              lineHeight: 1,
              color: "var(--emerald)",
            }}
          >
            <AnimatedCounter
              value={estimatedCost}
              prefix="$"
              decimals={4}
            />
          </div>
          <div
            style={{
              fontSize: "0.72rem",
              color: "var(--text-muted)",
              marginTop: 6,
            }}
          >
            gemini-2.5-flash pricing
          </div>
        </GlassCard>
      </div>
    </motion.div>
  );
}
