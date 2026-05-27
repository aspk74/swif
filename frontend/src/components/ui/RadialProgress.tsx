import { motion } from "framer-motion";

interface RadialProgressProps {
  value: number; // 0-100
  size?: number;
  strokeWidth?: number;
  color?: string;
  trackColor?: string;
}

export function RadialProgress({
  value,
  size = 140,
  strokeWidth = 10,
  color = "var(--emerald)",
  trackColor = "rgba(255,255,255,0.06)",
}: RadialProgressProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const center = size / 2;

  // Choose color dynamically based on score
  let activeColor = color;
  if (value < 50) activeColor = "var(--crimson)";
  else if (value < 75) activeColor = "var(--amber)";
  else activeColor = "var(--emerald)";

  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        {/* Track */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={trackColor}
          strokeWidth={strokeWidth}
        />
        {/* Progress arc */}
        <motion.circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={activeColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{
            strokeDashoffset:
              circumference - (circumference * Math.min(value, 100)) / 100,
          }}
          transition={{ duration: 1.5, ease: [0.25, 0.46, 0.45, 0.94] }}
          style={{
            filter: `drop-shadow(0 0 6px ${activeColor})`,
          }}
        />
      </svg>
      {/* Center label */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <span
          style={{
            fontSize: "2rem",
            fontWeight: 700,
            color: activeColor,
            fontVariantNumeric: "tabular-nums",
            lineHeight: 1,
          }}
        >
          {Math.round(value)}
        </span>
        <span
          style={{
            fontSize: "0.7rem",
            color: "var(--text-muted)",
            fontWeight: 500,
            letterSpacing: "0.05em",
            textTransform: "uppercase",
            marginTop: 4,
          }}
        >
          Score
        </span>
      </div>
    </div>
  );
}
