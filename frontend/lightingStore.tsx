import React, { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";

type BackendStatus = {
  restaurantId: number;
  state: "on" | "off";
  brightness: number;
  lastUpdated: string;
};

type BackendHistory = {
  id: number;
  restaurantId: number;
  action: string;
  timestamp: string;
};

type ScheduleRule = {
  days: string[];
  startTime: string;
  endTime: string;
  enabled: boolean;
};

type FullSchedule = {
  deviceId?: string;
  restaurantId?: string;
  rules: ScheduleRule[];
  createdAt?: string;
  updatedAt?: string;
};

type LightingContextType = {
  isOn: boolean;
  brightness: number;
  lastUpdated: string;
  history: BackendHistory[];
  loading: boolean;
  error: string | null;
  toggleLight: () => Promise<void>;
  refreshStatus: () => Promise<void>;
  refreshHistory: () => Promise<void>;
  saveSchedule: (scheduleOn: string, scheduleOff: string) => Promise<void>;
  // New methods for full schedule support
  saveFullSchedule: (rules: ScheduleRule[]) => Promise<FullSchedule>;
  loadFullSchedule: () => Promise<FullSchedule | null>;
  restaurantId: number;
};

const LightingContext = createContext<LightingContextType | undefined>(undefined);

const RESTAURANT_ID = 1;

export const LightingProvider = ({ children }: { children: ReactNode }) => {
  const baseUrl = useMemo(
    () => (process.env.EXPO_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, ""),
    []
  );

  const [status, setStatus] = useState<BackendStatus | null>(null);
  const [history, setHistory] = useState<BackendHistory[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshStatus = async () => {
    const response = await fetch(`${baseUrl}/lights/status?restaurantId=${RESTAURANT_ID}`);
    if (!response.ok) {
      throw new Error(`Status request failed (${response.status})`);
    }
    const body = (await response.json()) as BackendStatus;
    setStatus(body);
  };

  const refreshHistory = async () => {
    const response = await fetch(`${baseUrl}/lights/history?restaurantId=${RESTAURANT_ID}`);
    if (!response.ok) {
      throw new Error(`History request failed (${response.status})`);
    }
    const body = (await response.json()) as BackendHistory[];
    setHistory(body);
  };

  const toggleLight = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${baseUrl}/lights/toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          restaurantId: RESTAURANT_ID,
          action: "toggle",
        }),
      });
      if (!response.ok) {
        throw new Error(`Toggle request failed (${response.status})`);
      }
      const body = (await response.json()) as BackendStatus;
      setStatus(body);
      await refreshHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown toggle error");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const saveSchedule = async (scheduleOn: string, scheduleOff: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${baseUrl}/lights/schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          restaurantId: RESTAURANT_ID,
          scheduleOn,
          scheduleOff,
        }),
      });
      if (!response.ok) {
        throw new Error(`Schedule request failed (${response.status})`);
      }
      const body = (await response.json()) as BackendStatus;
      setStatus(body);
      await refreshHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown schedule error");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // New method: Save full day-specific schedule
  const saveFullSchedule = async (rules: ScheduleRule[]): Promise<FullSchedule> => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${baseUrl}/lights/schedule/full`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          restaurantId: RESTAURANT_ID,
          rules: rules,
        }),
      });
      if (!response.ok) {
        throw new Error(`Full schedule request failed (${response.status})`);
      }
      const body = (await response.json()) as FullSchedule;
      return body;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown full schedule error");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // New method: Load full day-specific schedule
  const loadFullSchedule = async (): Promise<FullSchedule | null> => {
    try {
      const response = await fetch(`${baseUrl}/lights/schedule/full?restaurantId=${RESTAURANT_ID}`);
      if (!response.ok) {
        if (response.status === 404) {
          return null; // No schedule found
        }
        throw new Error(`Load schedule request failed (${response.status})`);
      }
      return (await response.json()) as FullSchedule;
    } catch (err) {
      console.error("Failed to load schedule:", err);
      return null;
    }
  };

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        await Promise.all([refreshStatus(), refreshHistory()]);
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : "Failed to load lighting data");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };
    void load();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <LightingContext.Provider
      value={{
        isOn: status?.state === "on",
        brightness: status?.brightness ?? 0,
        lastUpdated: status?.lastUpdated ?? "",
        history,
        loading,
        error,
        toggleLight,
        refreshStatus,
        refreshHistory,
        saveSchedule,
        saveFullSchedule,
        loadFullSchedule,
        restaurantId: RESTAURANT_ID,
      }}
    >
      {children}
    </LightingContext.Provider>
  );
};

export const useLighting = () => {
  const ctx = useContext(LightingContext);
  if (!ctx) {
    throw new Error("useLighting must be used within LightingProvider");
  }
  return ctx;
};
