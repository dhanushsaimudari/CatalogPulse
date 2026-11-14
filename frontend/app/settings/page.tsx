'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Settings, Cpu, ShieldCheck, RefreshCw, Trash2, PlusCircle, ExternalLink, Activity, Sparkles } from 'lucide-react';
import { getActiveSessionId, createNewSession, clearCurrentSession } from '../../lib/session';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || '/api/v1';

export default function SettingsPage() {
  const [sessionId, setSessionId] = useState('');
  const [healthData, setHealthData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [extending, setExtending] = useState(false);

  useEffect(() => {
    setSessionId(getActiveSessionId());
    loadHealth();
  }, []);

  const loadHealth = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        setHealthData(await res.json());
      }
    } catch (e) {
      console.error('Failed to load health:', e);
    }
    setLoading(false);
  };

  const handleExtend = async () => {
    setExtending(true);
    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}/extend`, { method: 'POST' });
      if (res.ok) {
        alert('Session extended successfully by +120 minutes.');
      }
    } catch (e) {
      alert('Failed to extend session.');
    } finally {
      setExtending(false);
    }
  };

  const handleNew = async () => {
    const newId = await createNewSession(false);
    setSessionId(newId);
    window.location.reload();
  };

  const handleClear = async () => {
    if (confirm('Are you sure you want to clear all products and data from the active session?')) {
      await clearCurrentSession();
      window.location.reload();
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto font-mono text-xs">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            System Settings & Engine Status <Settings className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-sans mt-0.5">
            CatalogPulse AI runtime configuration, AI provider statuses, and session controls
          </p>
        </div>
        <Button size="sm" variant="outline" onClick={loadHealth}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh Status
        </Button>
      </div>

      {/* AI ENGINE ARCHITECTURE */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider">
              AI Provider Hierarchy
            </h2>
          </div>
          <span className="text-[10px] text-slate-400 uppercase">Multi-tier Fallback Engine</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* PRIMARY: GOOGLE GEMINI */}
          <div className="p-4 rounded-lg border border-blue-300 dark:border-blue-900 bg-blue-50/50 dark:bg-blue-950/30 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-blue-900 dark:text-blue-200">Google Gemini (Primary)</span>
              <Badge status={healthData?.gemini === 'available' ? 'VALID' : 'BLOCKED'}>
                {healthData?.gemini === 'available' ? 'AVAILABLE' : 'STANDBY'}
              </Badge>
            </div>
            <p className="text-[11px] text-slate-600 dark:text-slate-400 font-sans">
              Multimodal document understanding, open-world noun discovery, and technical attribute extraction.
            </p>
            <div className="text-[10px] text-slate-500 pt-1 border-t border-blue-200 dark:border-blue-900/60 font-mono">
              Model: {healthData?.providers?.gemini?.message ? healthData.providers.gemini.message : 'gemini-2.5-flash'}
            </div>
          </div>

          {/* SECONDARY: IBM WATSONX */}
          <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-800 dark:text-slate-200">IBM watsonx.ai (Fallback)</span>
              <Badge status={healthData?.watsonx === 'available' ? 'VALID' : 'BLOCKED'}>
                {healthData?.watsonx === 'available' ? 'AVAILABLE' : 'STANDBY'}
              </Badge>
            </div>
            <p className="text-[11px] text-slate-600 dark:text-slate-400 font-sans">
              Secondary cloud LLM fallback running meta-llama/llama-3-3-70b-instruct.
            </p>
            <div className="text-[10px] text-slate-500 pt-1 border-t border-slate-200 dark:border-slate-800 font-mono">
              Model: meta-llama/llama-3-3-70b-instruct
            </div>
          </div>

          {/* TERTIARY: LOCAL DETERMINISTIC CORE */}
          <div className="p-4 rounded-lg border border-emerald-300 dark:border-emerald-900 bg-emerald-50/40 dark:bg-emerald-950/20 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-emerald-900 dark:text-emerald-200">Local Deterministic Core</span>
              <Badge status="VALID">ALWAYS ACTIVE</Badge>
            </div>
            <p className="text-[11px] text-slate-600 dark:text-slate-400 font-sans">
              Local scikit-learn taxonomy classifier, deterministic regex parsers, and LOV dictionary rules.
            </p>
            <div className="text-[10px] text-slate-500 pt-1 border-t border-emerald-200 dark:border-emerald-900/60 font-mono">
              Status: {healthData?.local_ml?.status || 'AVAILABLE'}
            </div>
          </div>
        </div>
      </Card>

      {/* SESSION MANAGEMENT */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider">
              Active Processing Session
            </h2>
          </div>
          <span className="text-[10px] font-mono text-slate-500">ID: {sessionId}</span>
        </div>

        <p className="text-xs text-slate-600 dark:text-slate-400 font-sans leading-relaxed">
          CatalogPulse AI runs on a stateless, in-memory session architecture. Catalog products, audit events, and validation matrices are isolated per session with an automatic 120-minute sliding window expiration.
        </p>

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <Button size="sm" variant="primary" onClick={handleExtend} disabled={extending}>
            Extend Session (+120m)
          </Button>

          <Button size="sm" variant="outline" onClick={handleNew}>
            <PlusCircle className="w-3.5 h-3.5 mr-1" /> New Clean Session
          </Button>

          <Button size="sm" variant="danger" onClick={handleClear}>
            <Trash2 className="w-3.5 h-3.5 mr-1" /> Clear Session Data
          </Button>
        </div>
      </Card>

      {/* API & PLATFORM DOCUMENTATION */}
      <Card className="p-6 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider">
              Backend Endpoints & API Documentation
            </h2>
          </div>
          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold">FastAPI Operational</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <a
            href="/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="p-3 rounded border border-slate-200 dark:border-slate-800 hover:border-blue-400 dark:hover:border-blue-600 flex items-center justify-between transition-colors"
          >
            <div>
              <span className="font-bold text-slate-900 dark:text-slate-100 block">Swagger Interactive API Docs</span>
              <span className="text-[11px] text-slate-500 font-mono">/docs</span>
            </div>
            <ExternalLink className="w-4 h-4 text-slate-400" />
          </a>

          <a
            href="/redoc"
            target="_blank"
            rel="noopener noreferrer"
            className="p-3 rounded border border-slate-200 dark:border-slate-800 hover:border-blue-400 dark:hover:border-blue-600 flex items-center justify-between transition-colors"
          >
            <div>
              <span className="font-bold text-slate-900 dark:text-slate-100 block">ReDoc Technical Specifications</span>
              <span className="text-[11px] text-slate-500 font-mono">/redoc</span>
            </div>
            <ExternalLink className="w-4 h-4 text-slate-400" />
          </a>
        </div>
      </Card>
    </div>
  );
}
