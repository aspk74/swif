import { motion, AnimatePresence } from "framer-motion";

interface TerminalLogProps {
  lines: string[];
  isError?: boolean;
}

export function TerminalLog({ lines, isError = false }: TerminalLogProps) {
  return (
    <div className="terminal-viewport">
      <AnimatePresence>
        {lines.map((line, i) => (
          <motion.div
            key={`${i}-${line.slice(0, 20)}`}
            className={isError ? "terminal-line-error" : "terminal-line"}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: i * 0.08 }}
          >
            <span style={{ color: "var(--text-muted)", marginRight: 8 }}>
              {">"}
            </span>
            {line}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
