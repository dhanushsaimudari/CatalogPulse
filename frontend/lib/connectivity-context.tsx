'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

export type ConnectivityStatus = 'connected' | 'waking' | 'disconnected' | 'checking';

export interface HealthData {
  backend?: string;
  status?: string;
  service?: string;
  watsonx?: string;
  gemini?: string;
  primary_provider?: string;
  secondary_provider?: string;
  ai_status?: string;
  ai_message?: string;
  providers?: Record<string, any>;
  [key: string]: any;
}

interface ConnectivityContextType {
  status: ConnectivityStatus;
  latencyMs: number | null;
  healthData: HealthData | null;
  isChecking: boolean;
  lastChecked: Date | null;
  checkConnectivity: () => Promise<void>;
}

const ConnectivityContext = createContext<ConnectivityContextType>({
  status: 'checking',
  latencyMs: null,
  healthData: null,
  isChecking: false,
  lastChecked: null,
  checkConnectivity: async () => {},
});

export const ConnectivityProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<ConnectivityStatus>('checking');
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [healthData, setHealthData] = useState<HealthData | null>(null);
  const [isChecking, setIsChecking] = useState<boolean>(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const checkConnectivity = useCallback(async () => {
    setIsChecking(true);
    const startTime = Date.now();
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || '/api/v1';

    // Timer to detect Render cold start waking condition if request takes > 2.5 seconds
    const wakingTimer = setTimeout(() => {
      setStatus((current) => (current !== 'connected' ? 'waking' : current));
    }, 2500);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000); // 60s generous timeout

    try {
      const res = await fetch(`${apiBase}/health`, {
        signal: controller.signal,
        cache: 'no-store'
      });
      clearTimeout(wakingTimer);
      clearTimeout(timeoutId);

      const elapsed = Date.now() - startTime;
      if (res.ok) {
        const data = await res.json();
        setLatencyMs(elapsed);
        setHealthData(data);
        setStatus('connected');
        setLastChecked(new Date());
      } else {
        setStatus('disconnected');
      }
    } catch (e) {
      clearTimeout(wakingTimer);
      clearTimeout(timeoutId);
      setStatus('disconnected');
    } finally {
      setIsChecking(false);
    }
  }, []);

  useEffect(() => {
    checkConnectivity();
    const interval = setInterval(checkConnectivity, 30000);
    return () => clearInterval(interval);
  }, [checkConnectivity]);

  return (
    <ConnectivityContext.Provider
      value={{
        status,
        latencyMs,
        healthData,
        isChecking,
        lastChecked,
        checkConnectivity,
      }}
    >
      {children}
    </ConnectivityContext.Provider>
  );
};

export const useConnectivity = () => useContext(ConnectivityContext);
