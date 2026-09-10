'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useConnectivity } from '../../lib/connectivity-context';
import { RefreshCw, Server, Globe, Cpu, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';

export const ConnectivityIndicator: React.FC = () => {
  const { status, latencyMs, healthData, isChecking, checkConnectivity } = useConnectivity();
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getStatusColor = () => {
    switch (status) {
      case 'connected':
        return 'bg-emerald-500';
      case 'waking':
        return 'bg-amber-500 animate-pulse';
      case 'disconnected':
        return 'bg-rose-500';
      default:
        return 'bg-slate-400';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'connected':
        return latencyMs ? `Connected (${latencyMs}ms)` : 'Connected';
      case 'waking':
        return 'Waking up...';
      case 'disconnected':
        return 'Disconnected';
      default:
        return 'Checking...';
    }
  };

  const watsonxStatus = healthData?.watsonx || healthData?.providers?.watsonx?.status || 'unknown';
  const geminiStatus = healthData?.gemini || healthData?.providers?.gemini?.status || 'unknown';

  return (
    <div className="relative font-mono" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-2.5 py-1 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors text-xs"
        title="View live system connectivity status"
        aria-label="System status indicator"
      >
        <span className={`w-2 h-2 rounded-full ${getStatusColor()}`} />
        <span className="text-[11px] text-slate-700 dark:text-slate-300 font-medium">
          {getStatusText()}
        </span>
      </button>

      {/* Popover Dropdown */}
      {open && (
        <div className="absolute right-0 mt-2 w-80 p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-xl z-50 space-y-3.5 text-xs text-slate-700 dark:text-slate-300 animate-in fade-in slide-in-from-top-1 duration-150">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
            <span className="font-bold uppercase tracking-wider text-[11px] text-slate-800 dark:text-slate-200">
              System Infrastructure
            </span>
            <button
              onClick={() => checkConnectivity()}
              disabled={isChecking}
              className="flex items-center gap-1 text-[10px] text-blue-600 dark:text-blue-400 hover:underline disabled:opacity-50"
            >
              <RefreshCw className={`w-3 h-3 ${isChecking ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          <div className="space-y-2.5">
            {/* Frontend */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Globe className="w-3.5 h-3.5 text-slate-500" />
                <span>Frontend:</span>
              </div>
              <span className="font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1 text-[11px]">
                <CheckCircle2 className="w-3 h-3" /> Vercel (Online)
              </span>
            </div>

            {/* Backend */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Server className="w-3.5 h-3.5 text-slate-500" />
                <span>Backend:</span>
              </div>
              <span className="font-semibold text-[11px] flex items-center gap-1">
                {status === 'connected' ? (
                  <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Render ({latencyMs}ms)
                  </span>
                ) : status === 'waking' ? (
                  <span className="text-amber-600 dark:text-amber-400 flex items-center gap-1">
                    <RefreshCw className="w-3 h-3 animate-spin" /> Render Waking Up
                  </span>
                ) : (
                  <span className="text-rose-600 dark:text-rose-400 flex items-center gap-1">
                    <XCircle className="w-3 h-3" /> Render (Offline)
                  </span>
                )}
              </span>
            </div>

            {/* Primary AI */}
            <div className="border-t border-slate-100 dark:border-slate-800/80 pt-2 space-y-1">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Cpu className="w-3.5 h-3.5 text-blue-500" />
                  <span className="font-medium text-[11px]">Primary AI:</span>
                </div>
                <span className="font-bold text-[10px] text-blue-600 dark:text-blue-400">
                  {watsonxStatus.toUpperCase()}
                </span>
              </div>
              <p className="text-[10px] text-slate-500 dark:text-slate-400 pl-5">
                IBM watsonx.ai (meta-llama/llama-3-3-70b-instruct)
              </p>
            </div>

            {/* Fallback AI */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Cpu className="w-3.5 h-3.5 text-amber-500" />
                  <span className="font-medium text-[11px]">Fallback AI:</span>
                </div>
                <span className="font-bold text-[10px] text-amber-600 dark:text-amber-400">
                  {geminiStatus.toUpperCase()}
                </span>
              </div>
              <p className="text-[10px] text-slate-500 dark:text-slate-400 pl-5">
                Google Gemini (gemini-2.5-flash)
              </p>
            </div>
          </div>

          {status === 'waking' && (
            <div className="mt-2 p-2 bg-amber-50 dark:bg-amber-950/50 border border-amber-300 dark:border-amber-800 rounded text-[10px] text-amber-800 dark:text-amber-300 leading-snug flex items-start gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>Render free-tier instance is spinning up. First request takes ~30 seconds.</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export const ColdStartBanner: React.FC = () => {
  const { status, checkConnectivity } = useConnectivity();

  if (status !== 'waking') return null;

  return (
    <div className="bg-amber-500/10 border-b border-amber-500/30 px-4 py-2 font-mono text-xs text-amber-800 dark:text-amber-300 flex items-center justify-between animate-in fade-in duration-200">
      <div className="flex items-center gap-2">
        <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-600 dark:text-amber-400 shrink-0" />
        <span>
          <strong>Backend Service Waking Up:</strong> Render free-tier instances spin down after inactivity. Cold start takes ~30 seconds. Thank you for your patience!
        </span>
      </div>
      <button
        onClick={() => checkConnectivity()}
        className="px-2 py-0.5 bg-amber-600 hover:bg-amber-700 text-white text-[10px] font-bold rounded shrink-0"
      >
        Check Status
      </button>
    </div>
  );
};
