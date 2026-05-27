import { motion } from "framer-motion";
import {
  Shield,
  BookOpen,
  Zap,
  Activity,
  AlertTriangle,
} from "lucide-react";
import type { ReactNode } from "react";

export type Page =
  | "Executive View"
  | "Rules Registry"
  | "Monitoring Dashboard"
  | "Observability Engine"
  | "System Logs";

interface NavItem {
  label: Page;
  icon: ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Monitoring Dashboard", icon: <Zap size={18} /> },
  { label: "Rules Registry", icon: <BookOpen size={18} /> },
  { label: "Executive View", icon: <Shield size={18} /> },
  { label: "Observability Engine", icon: <Activity size={18} /> },
  { label: "System Logs", icon: <Activity size={18} /> },
];

interface NavSidebarProps {
  activePage: Page;
  onNavigate: (page: Page) => void;
  onSimulateDrift: () => void;
  driftLoading: boolean;
}

export function NavSidebar({
  activePage,
  onNavigate,
  onSimulateDrift,
  driftLoading,
}: NavSidebarProps) {
  return (
    <nav className="sidebar">
      {/* Brand */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 8,
        }}
      >
        <div
          style={{
            width: 34,
            height: 34,
            borderRadius: 10,
            background:
              "linear-gradient(135deg, rgba(59,130,246,0.3), rgba(139,92,246,0.3))",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            border: "1px solid rgba(59,130,246,0.2)",
          }}
        >
          <Shield size={18} style={{ color: "#93c5fd" }} />
        </div>
        <div>
          <div
            style={{
              fontSize: "1.05rem",
              fontWeight: 700,
              letterSpacing: "-0.02em",
            }}
          >
            Swif Compliance
          </div>
          <div
            style={{
              fontSize: "0.65rem",
              color: "var(--text-muted)",
              fontWeight: 500,
              letterSpacing: "0.04em",
              textTransform: "uppercase",
            }}
          >
            Control Plane
          </div>
        </div>
      </div>

      <div
        style={{
          height: 1,
          background: "var(--border-subtle)",
          margin: "16px 0",
        }}
      />

      {/* Navigation */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 4,
          flex: 1,
        }}
      >
        <div
          style={{
            fontSize: "0.65rem",
            fontWeight: 600,
            color: "var(--text-muted)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            padding: "0 12px",
            marginBottom: 4,
          }}
        >
          Dashboard
        </div>
        {NAV_ITEMS.map((item) => {
          const isActive = activePage === item.label;
          return (
            <button
              key={item.label}
              onClick={() => onNavigate(item.label)}
              style={{
                position: "relative",
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "10px 12px",
                borderRadius: 8,
                border: "none",
                background: isActive
                  ? "rgba(59, 130, 246, 0.1)"
                  : "transparent",
                color: isActive
                  ? "var(--text-primary)"
                  : "var(--text-secondary)",
                cursor: "pointer",
                fontSize: "0.85rem",
                fontWeight: isActive ? 500 : 400,
                fontFamily: "inherit",
                textAlign: "left",
                transition: "all 0.2s ease",
              }}
              onMouseEnter={(e) => {
                if (!isActive)
                  e.currentTarget.style.background =
                    "rgba(255, 255, 255, 0.04)";
              }}
              onMouseLeave={(e) => {
                if (!isActive) e.currentTarget.style.background = "transparent";
              }}
            >
              {isActive && (
                <motion.div
                  layoutId="nav-indicator"
                  style={{
                    position: "absolute",
                    left: 0,
                    top: "50%",
                    transform: "translateY(-50%)",
                    width: 3,
                    height: 20,
                    borderRadius: 3,
                    background:
                      "linear-gradient(180deg, #3b82f6, #8b5cf6)",
                  }}
                  transition={{
                    type: "spring",
                    stiffness: 350,
                    damping: 30,
                  }}
                />
              )}
              {item.icon}
              {item.label}
            </button>
          );
        })}
      </div>


    </nav>
  );
}
