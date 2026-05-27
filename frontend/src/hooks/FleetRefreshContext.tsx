import React, { createContext, useContext, useState, useEffect } from "react";

interface FleetRefreshContextType {
  secondsRemaining: number;
  tick: number;
}

const FleetRefreshContext = createContext<FleetRefreshContextType | undefined>(undefined);

export function FleetRefreshProvider({ children }: { children: React.ReactNode }) {
  const [secondsRemaining, setSecondsRemaining] = useState(30);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          setTick((t) => t + 1);
          return 30;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <FleetRefreshContext.Provider value={{ secondsRemaining, tick }}>
      {children}
    </FleetRefreshContext.Provider>
  );
}

export function useFleetRefresh() {
  const context = useContext(FleetRefreshContext);
  if (context === undefined) {
    throw new Error("useFleetRefresh must be used within a FleetRefreshProvider");
  }
  return context;
}
