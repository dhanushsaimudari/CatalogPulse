'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Download, FileSpreadsheet, CheckCircle2, AlertTriangle, ArrowRight, Table2, Layers } from 'lucide-react';
import { exportCleanIntelligenceCsv, exportSessionCsv } from '../../lib/api/export';
import { fetchProducts } from '../../lib/api/products';
import { getActiveSessionId } from '../../lib/session';

export default function ExportCenterPage() {
  const [totalProducts, setTotalProducts] = useState<number>(0);
  const [pendingReviews, setPendingReviews] = useState<number>(0);
  const [validatedCount, setValidatedCount] = useState<number>(0);
  const [exportingClean, setExportingClean] = useState(false);
  const [exportingLegacy, setExportingLegacy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    loadCatalogStats();

    const handleUpdate = () => loadCatalogStats();
    window.addEventListener('session-changed', handleUpdate);
    window.addEventListener('catalog-updated', handleUpdate);

    return () => {
      window.removeEventListener('session-changed', handleUpdate);
      window.removeEventListener('catalog-updated', handleUpdate);
    };
  }, []);

  const loadCatalogStats = async () => {
    setLoading(true);
    try {
      const sessionId = getActiveSessionId();
      const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || '/api/v1';

      const prodRes = await fetchProducts({ limit: 100 });
      setTotalProducts(prodRes.total || 0);

      const validProds = (prodRes.items || []).filter((p: any) => !p.requires_review).length;
      setValidatedCount(validProds);

      const revRes = await fetch(`${apiBase}/sessions/${sessionId}/reviews?status=PENDING`);
      if (revRes.ok) {
        const revData = await revRes.json();
        setPendingReviews(Array.isArray(revData) ? revData.length : 0);
      }
    } catch (e) {
      console.error('Failed to load catalog stats:', e);
    }
    setLoading(false);
  };

  const handleDownloadClean = async () => {
    setExportingClean(true);
    setNotification(null);
    try {
      const res = await exportCleanIntelligenceCsv();
      if (res.success) {
        setNotification({ type: 'success', message: 'Clean Dynamic Intelligence CSV generated and downloaded successfully.' });
      } else {
        setNotification({ type: 'error', message: res.message || 'Clean CSV export failed.' });
      }
    } catch (e: any) {
      setNotification({ type: 'error', message: e.message || 'Network error during export.' });
    } finally {
      setExportingClean(false);
    }
  };

  const handleDownloadLegacy = async () => {
    setExportingLegacy(true);
    setNotification(null);
    try {
      const res = await exportSessionCsv();
      if (res.success) {
        setNotification({ type: 'success', message: 'Legacy 252-Column Unilog Delivery CSV generated and downloaded successfully.' });
      } else {
        setNotification({ type: 'error', message: res.message || 'Legacy CSV export failed.' });
      }
    } catch (e: any) {
      setNotification({ type: 'error', message: e.message || 'Network error during export.' });
    } finally {
      setExportingLegacy(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto font-mono">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            Export Center <Download className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-sans mt-0.5">
            Export verified industrial product intelligence into clean modern feeds or partner schemas
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
            {totalProducts} Products Ready
          </span>
          {pendingReviews > 0 ? (
            <Badge status="REVIEW">{pendingReviews} Pending Reviews</Badge>
          ) : (
            <Badge status="VALID">All Validated</Badge>
          )}
        </div>
      </div>

      {notification && (
        <div className={`p-4 rounded-lg text-xs font-mono border flex items-center gap-2 ${
          notification.type === 'success'
            ? 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
            : 'bg-rose-50 dark:bg-rose-950/60 border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-300'
        }`}>
          {notification.type === 'success' ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertTriangle className="w-4 h-4 shrink-0" />}
          <span>{notification.message}</span>
        </div>
      )}

      {totalProducts === 0 ? (
        <Card className="p-12 text-center space-y-4 max-w-2xl mx-auto my-8">
          <div className="w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-950 border border-blue-300 dark:border-blue-800 text-blue-600 dark:text-blue-400 flex items-center justify-center mx-auto">
            <FileSpreadsheet className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h2 className="text-lg font-bold text-slate-800 dark:text-slate-200">No Products in Active Session</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-sans">
              Upload product datasheets or spreadsheets to enrich items and generate export files.
            </p>
          </div>
          <Link href="/upload">
            <Button size="md" variant="primary" className="mx-auto">
              Upload Catalog Data
            </Button>
          </Link>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Status summary banner */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="p-4 space-y-1">
              <span className="text-[10px] text-slate-500 uppercase">Total Catalog SKUs</span>
              <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">{totalProducts}</div>
              <span className="text-[11px] text-slate-500 font-sans">Extracted and structured in memory</span>
            </Card>

            <Card className="p-4 space-y-1">
              <span className="text-[10px] text-slate-500 uppercase">Validation Pass Rate</span>
              <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                {totalProducts > 0 ? `${((validatedCount / totalProducts) * 100).toFixed(0)}%` : '0%'}
              </div>
              <span className="text-[11px] text-slate-500 font-sans">{validatedCount} items passed deterministic rules</span>
            </Card>

            <Card className="p-4 space-y-1">
              <span className="text-[10px] text-slate-500 uppercase">Pending Review Items</span>
              <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">{pendingReviews}</div>
              <span className="text-[11px] text-slate-500 font-sans">Exceptions flagged for human oversight</span>
            </Card>
          </div>

          {/* Export Options Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* 1. PRIMARY: CLEAN DYNAMIC INTELLIGENCE CSV */}
            <Card className="p-6 space-y-4 border-2 border-blue-500/40 dark:border-blue-500/30 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-800">
                    Recommended Primary Format
                  </span>
                  <Table2 className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                </div>

                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                    Clean Dynamic Intelligence CSV
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 font-sans mt-1 leading-relaxed">
                    Compact, normalized product record containing core identifiers, taxonomy, and dynamically discovered technical specifications as individual named columns.
                  </p>
                </div>

                <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-slate-800 text-xs">
                  <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                    <span>Dynamic attribute columns with normalized UOM units</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                    <span>Grounded product descriptions without promotional fluff</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                    <span>Zero filler empty columns — clean for ERP & modern eCommerce</span>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-2">
                <Button
                  size="md"
                  variant="primary"
                  className="w-full justify-center bg-blue-600 hover:bg-blue-700 text-white"
                  onClick={handleDownloadClean}
                  disabled={exportingClean}
                >
                  <Download className="w-4 h-4 mr-2" />
                  {exportingClean ? 'Generating Clean CSV...' : 'Download Clean Catalog CSV'}
                </Button>
                <span className="text-[10px] text-slate-400 block text-center font-sans">
                  Standard format for modern inventory management and B2B platforms
                </span>
              </div>
            </Card>

            {/* 2. LEGACY PARTNER: 252-COLUMN UNILOG DELIVERY CSV */}
            <Card className="p-6 space-y-4 border border-slate-200 dark:border-slate-800 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700">
                    Legacy Partner Export
                  </span>
                  <Layers className="w-5 h-5 text-slate-400" />
                </div>

                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                    Legacy 252-Column Unilog Delivery CSV
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 font-sans mt-1 leading-relaxed">
                    Full delivery projection mapping attributes into fixed 252-column schema slots (MFR URL, ATTRIBUTE_LABEL_1..N, ITEM_FEATURE_1..N) for legacy distributor feeds.
                  </p>
                </div>

                <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-slate-800 text-xs">
                  <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                    <span>Exact 252-column count preserved for partner ingestion</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                    <span>Fixed schema column slotting with attribute sequence ordering</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                    <span>Preserved for backward compatibility with existing workflows</span>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-2">
                <Button
                  size="md"
                  variant="outline"
                  className="w-full justify-center"
                  onClick={handleDownloadLegacy}
                  disabled={exportingLegacy}
                >
                  <Download className="w-4 h-4 mr-2" />
                  {exportingLegacy ? 'Generating 252-Col CSV...' : 'Download Legacy 252-Col CSV'}
                </Button>
                <span className="text-[10px] text-slate-400 block text-center font-sans">
                  Use when integrating with legacy Unilog-compatible delivery pipelines
                </span>
              </div>
            </Card>

          </div>
        </div>
      )}
    </div>
  );
}

