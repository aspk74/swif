import { useEffect, useRef, useState } from "react";
import { motion, useSpring, useTransform } from "framer-motion";

interface AnimatedCounterProps {
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  duration?: number;
}

export function AnimatedCounter({
  value,
  prefix = "",
  suffix = "",
  decimals = 0,
  duration = 1.2,
}: AnimatedCounterProps) {
  const spring = useSpring(0, {
    stiffness: 60,
    damping: 20,
    duration: duration,
  });
  const display = useTransform(spring, (v) => {
    if (decimals > 0) return v.toFixed(decimals);
    return Math.round(v).toLocaleString();
  });
  const [displayValue, setDisplayValue] = useState("0");
  const prevValue = useRef(0);

  useEffect(() => {
    spring.set(value);
    prevValue.current = value;
  }, [value, spring]);

  useEffect(() => {
    const unsub = display.on("change", (v) => setDisplayValue(v));
    return unsub;
  }, [display]);

  return (
    <motion.span
      key={value}
      style={{ fontVariantNumeric: "tabular-nums" }}
    >
      {prefix}
      {displayValue}
      {suffix}
    </motion.span>
  );
}
