import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GlassCard } from "../components/ui/GlassCard";
import { Badge } from "../components/ui/Badge";
import { Dropzone } from "../components/ui/Dropzone";
import { usePolling } from "../hooks/usePolling";
import { fetchRules } from "../lib/api";
import { Search, ChevronDown, FileText } from "lucide-react";

interface ControlRegistryProps {
  onToast: (message: string, type: "success" | "error") => void;
}

export function ControlRegistry({ onToast }: ControlRegistryProps) {
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const fetchRulesCb = useCallback(() => fetchRules(200), []);
  const { data: rules, loading, refresh } = usePolling(fetchRulesCb, 30000);

  const filtered = (rules || []).filter((r) => {
    if (!search) return true;
    const term = search.toLowerCase();
    return (
      (r.suggested_id || "").toLowerCase().includes(term) ||
      (r.category || "").toLowerCase().includes(term) ||
      (r.technical_parameter || "").toLowerCase().includes(term)
    );
  });

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
          Rules Registry
        </h1>
        <span
          style={{
            fontSize: "0.8rem",
            color: "var(--text-muted)",
            fontWeight: 500,
          }}
        >
          {filtered.length} rules
        </span>
      </div>

      <Dropzone onUploadComplete={refresh} onToast={onToast} />

      {/* Search */}
      <div style={{ position: "relative", marginBottom: 24 }}>
        <Search
          size={16}
          style={{
            position: "absolute",
            left: 12,
            top: "50%",
            transform: "translateY(-50%)",
            color: "var(--text-muted)",
          }}
        />
        <input
          className="search-input"
          placeholder="Search rules by ID, category, or parameter..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {loading && !rules ? (
        <div
          style={{ textAlign: "center", padding: 60, color: "var(--text-muted)" }}
        >
          Loading rules...
        </div>
      ) : filtered.length === 0 ? (
        <GlassCard hover={false}>
          <div
            style={{
              textAlign: "center",
              padding: "40px 0",
              color: "var(--text-muted)",
            }}
          >
            {rules && rules.length === 0
              ? "No rules in the registry. Ingest a policy PDF first."
              : "No rules match your search."}
          </div>
        </GlassCard>
      ) : (
        <div className="rules-grid">
          {filtered.map((rule, idx) => {
            const id = rule.suggested_id || `rule-${idx}`;
            const isOpen = expanded === id;

            return (
              <motion.div
                key={id}
                className="glass-card"
                style={{
                  padding: 0,
                  overflow: "hidden",
                  cursor: "pointer",
                }}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: Math.min(idx * 0.03, 0.5) }}
                whileHover={{ y: -2, transition: { duration: 0.2 } }}
                onClick={() => setExpanded(isOpen ? null : id)}
              >
                <div style={{ padding: "20px 20px 16px" }}>
                  {/* Header */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      justifyContent: "space-between",
                      marginBottom: 12,
                    }}
                  >
                    <div>
                      <div
                        style={{
                          fontSize: "0.9rem",
                          fontWeight: 600,
                          marginBottom: 4,
                        }}
                      >
                        {rule.suggested_id || "N/A"}
                      </div>
                      <div
                        style={{
                          fontSize: "0.75rem",
                          color: "var(--text-muted)",
                        }}
                      >
                        {rule.category || "Uncategorized"}
                      </div>
                    </div>
                    <Badge severity={rule.severity || "MEDIUM"} />
                  </div>

                  {/* Parameter & Expected */}
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: 6,
                      fontSize: "0.8rem",
                    }}
                  >
                    <div>
                      <span style={{ color: "var(--text-muted)" }}>
                        Parameter:{" "}
                      </span>
                      <code
                        style={{
                          color: "var(--cyan)",
                          background: "rgba(34,211,238,0.08)",
                          padding: "2px 6px",
                          borderRadius: 4,
                          fontSize: "0.78rem",
                        }}
                      >
                        {rule.technical_parameter}
                      </code>
                    </div>
                    <div>
                      <span style={{ color: "var(--text-muted)" }}>
                        Expected:{" "}
                      </span>
                      <code
                        style={{
                          color: "var(--emerald)",
                          background: "rgba(52,211,153,0.08)",
                          padding: "2px 6px",
                          borderRadius: 4,
                          fontSize: "0.78rem",
                        }}
                      >
                        {rule.expected_value}
                      </code>
                      <span
                        style={{
                          color: "var(--text-muted)",
                          marginLeft: 6,
                          fontSize: "0.72rem",
                        }}
                      >
                        ({rule.logic})
                      </span>
                    </div>
                  </div>

                  {/* Expand toggle */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                      marginTop: 12,
                      fontSize: "0.72rem",
                      color: "var(--text-muted)",
                    }}
                  >
                    <FileText size={12} />
                    View Source
                    <motion.span
                      animate={{ rotate: isOpen ? 180 : 0 }}
                      transition={{ duration: 0.2 }}
                      style={{ display: "inline-flex", marginLeft: "auto" }}
                    >
                      <ChevronDown size={14} />
                    </motion.span>
                  </div>
                </div>

                {/* Expandable source */}
                <AnimatePresence>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{
                        height: { type: "spring", stiffness: 300, damping: 30 },
                        opacity: { duration: 0.2 },
                      }}
                      style={{ overflow: "hidden" }}
                    >
                      <div
                        style={{
                          padding: "0 20px 20px",
                          borderTop: "1px solid var(--border-subtle)",
                          paddingTop: 16,
                        }}
                      >
                        <div
                          style={{
                            fontSize: "0.78rem",
                            color: "var(--text-muted)",
                            marginBottom: 8,
                          }}
                        >
                          <strong style={{ color: "var(--text-secondary)" }}>
                            Source:{" "}
                          </strong>
                          {rule.source_document || "Unknown"}
                        </div>
                        <div
                          className="terminal-viewport"
                          style={{
                            maxHeight: 120,
                            fontSize: "0.72rem",
                          }}
                        >
                          <span className="terminal-line">
                            {rule.chunk_reference || "No chunk provided"}
                          </span>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}
