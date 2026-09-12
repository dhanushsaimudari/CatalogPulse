'use client';

import React, { useState, useEffect } from 'react';
import { ReviewItem } from '../../types/review';
import { fetchReviewItems, approveReviewItem, rejectReviewItem, autofixReviewItem, editReviewItem, bulkFixReviews } from '../../lib/api/reviews';
import { ReviewQueueTable } from '../../components/review/ReviewQueueTable';
import { ReviewDetailPanel } from '../../components/review/ReviewDetailPanel';
import { KeyboardShortcutsHelp } from '../../components/review/KeyboardShortcutsHelp';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { CheckCircle2, ShieldAlert, AlertCircle } from 'lucide-react';

export default function ReviewPage() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [selectedReviewIds, setSelectedReviewIds] = useState<Set<string>>(new Set());
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [bulkProcessing, setBulkProcessing] = useState(false);
  const [notification, setNotification] = useState<{
    type: 'success' | 'error' | 'info';
    message: string;
  } | null>(null);

  useEffect(() => {
    loadItems();

    const handleUpdate = () => loadItems();
    window.addEventListener('session-changed', handleUpdate);
    window.addEventListener('catalog-updated', handleUpdate);

    return () => {
      window.removeEventListener('session-changed', handleUpdate);
      window.removeEventListener('catalog-updated', handleUpdate);
    };
  }, []);

  const loadItems = async () => {
    setLoading(true);
    const data = await fetchReviewItems();
    setItems(data);
    setSelectedIndex((prev) => Math.min(Math.max(0, data.length - 1), prev));
    setLoading(false);
  };

  const selectedItem = items[selectedIndex] || null;

  const handleToggleSelect = (reviewId: string) => {
    setSelectedReviewIds((prev) => {
      const next = new Set(prev);
      if (next.has(reviewId)) {
        next.delete(reviewId);
      } else {
        next.add(reviewId);
      }
      return next;
    });
  };

  const handleToggleSelectAll = () => {
    if (selectedReviewIds.size === items.length) {
      setSelectedReviewIds(new Set());
    } else {
      setSelectedReviewIds(new Set(items.map((i) => i.review_id)));
    }
  };

  const handleSelectAll = () => {
    setSelectedReviewIds(new Set(items.map((i) => i.review_id)));
  };

  const handleClearSelection = () => {
    setSelectedReviewIds(new Set());
  };

  const handleFixSelected = async () => {
    if (selectedReviewIds.size === 0) return;
    setBulkProcessing(true);
    setNotification(null);
    try {
      const ids = Array.from(selectedReviewIds);
      const res = await bulkFixReviews(ids, false);
      setSelectedReviewIds(new Set());
      await loadItems();
      window.dispatchEvent(new CustomEvent('catalog-updated'));

      if (res) {
        if (res.applied_count > 0 && res.failed_count === 0) {
          setNotification({
            type: 'success',
            message: `Successfully fixed ${res.applied_count} selected exception${res.applied_count > 1 ? 's' : ''} across ${res.affected_products_count} product${res.affected_products_count > 1 ? 's' : ''}.`
          });
        } else if (res.applied_count > 0 && res.failed_count > 0) {
          setNotification({
            type: 'info',
            message: `Fixed ${res.applied_count} item${res.applied_count > 1 ? 's' : ''}, but ${res.failed_count} item${res.failed_count > 1 ? 's' : ''} could not be auto-fixed.`
          });
        } else {
          setNotification({
            type: 'error',
            message: `Could not auto-fix selected items (${res.failed_count} failed). Please review suggestions or edit manually.`
          });
        }
      } else {
        setNotification({
          type: 'error',
          message: 'Bulk fix failed. Unable to communicate with session service.'
        });
      }
    } catch (err: any) {
      setNotification({
        type: 'error',
        message: `Bulk fix error: ${err.message || 'Unknown error occurred.'}`
      });
    } finally {
      setBulkProcessing(false);
    }
  };

  const handleFixAll = async () => {
    setBulkProcessing(true);
    setNotification(null);
    try {
      const res = await bulkFixReviews(undefined, true);
      setSelectedReviewIds(new Set());
      await loadItems();
      window.dispatchEvent(new CustomEvent('catalog-updated'));

      if (res) {
        if (res.applied_count > 0 && res.failed_count === 0) {
          setNotification({
            type: 'success',
            message: `Successfully auto-fixed all ${res.applied_count} eligible review exception${res.applied_count > 1 ? 's' : ''} across ${res.affected_products_count} product${res.affected_products_count > 1 ? 's' : ''}.`
          });
        } else if (res.applied_count > 0 && res.failed_count > 0) {
          setNotification({
            type: 'info',
            message: `Auto-fixed ${res.applied_count} eligible item${res.applied_count > 1 ? 's' : ''}. ${res.failed_count} item${res.failed_count > 1 ? 's' : ''} remain unfixable or require manual review.`
          });
        } else if (res.eligible_count === 0) {
          setNotification({
            type: 'info',
            message: 'No eligible auto-fixable items found in pending queue.'
          });
        } else {
          setNotification({
            type: 'error',
            message: `Auto-fix completed with 0 applied fixes (${res.failed_count} failed).`
          });
        }
      } else {
        setNotification({
          type: 'error',
          message: 'Bulk fix all failed. Unable to communicate with session service.'
        });
      }
    } catch (err: any) {
      setNotification({
        type: 'error',
        message: `Bulk fix error: ${err.message || 'Unknown error occurred.'}`
      });
    } finally {
      setBulkProcessing(false);
    }
  };

  const handleApprove = async (item: ReviewItem) => {
    await approveReviewItem(item.review_id);
    setItems((prev) => prev.filter((i) => i.review_id !== item.review_id));
    window.dispatchEvent(new CustomEvent('catalog-updated'));
  };

  const handleReject = async (item: ReviewItem) => {
    await rejectReviewItem(item.review_id);
    setItems((prev) => prev.filter((i) => i.review_id !== item.review_id));
    window.dispatchEvent(new CustomEvent('catalog-updated'));
  };

  const handleAutoFix = async (item: ReviewItem) => {
    await autofixReviewItem(item.review_id);
    setItems((prev) => prev.filter((i) => i.review_id !== item.review_id));
    window.dispatchEvent(new CustomEvent('catalog-updated'));
  };

  const handleEdit = async (item: ReviewItem, customValue: string) => {
    await editReviewItem(item.review_id, customValue);
    setItems((prev) => prev.filter((i) => i.review_id !== item.review_id));
    setIsEditing(false);
    window.dispatchEvent(new CustomEvent('catalog-updated'));
  };

  // Keyboard Shortcuts Handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore when typing inside input elements
      const target = e.target as HTMLElement;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) {
        if (e.key === 'Escape') {
          setIsEditing(false);
        }
        return;
      }

      if (!selectedItem) return;

      const key = e.key.toUpperCase();

      if (key === 'A') {
        e.preventDefault();
        handleApprove(selectedItem);
      } else if (key === 'R') {
        e.preventDefault();
        handleReject(selectedItem);
      } else if (key === 'F') {
        e.preventDefault();
        handleAutoFix(selectedItem);
      } else if (key === 'E') {
        e.preventDefault();
        setIsEditing(true);
      } else if (key === 'ESCAPE') {
        e.preventDefault();
        setIsEditing(false);
      } else if (key === 'N') {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(items.length - 1, prev + 1));
      } else if (key === 'P') {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(0, prev - 1));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedItem, items]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800 font-mono">
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            Human Review Queue Workbench <ShieldAlert className="w-5 h-5 text-amber-600 dark:text-amber-400" />
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-sans mt-0.5">Flagged exception queue for ambiguous brands, rule failures, and low-confidence items</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge status="REVIEW">{items.length} Pending Exceptions</Badge>
        </div>
      </div>

      {/* Keyboard Shortcuts Toolbar */}
      <KeyboardShortcutsHelp />

      {/* Supervisor Bulk Action Bar */}
      {!loading && items.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-mono shadow-sm">
          <div className="flex items-center gap-2">
            <span className="text-slate-600 dark:text-slate-400 font-semibold">
              Supervisor Bulk Review:
            </span>
            <span className="text-blue-600 dark:text-blue-400 font-bold">
              {selectedReviewIds.size} of {items.length} selected
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" variant="outline" onClick={handleSelectAll} disabled={bulkProcessing}>
              Select All
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleClearSelection}
              disabled={bulkProcessing || selectedReviewIds.size === 0}
            >
              Clear Selection
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={handleFixSelected}
              disabled={bulkProcessing || selectedReviewIds.size === 0}
              className="bg-amber-100 hover:bg-amber-200 dark:bg-amber-950/60 dark:hover:bg-amber-900 text-amber-900 dark:text-amber-200 border-amber-300 dark:border-amber-800"
            >
              {bulkProcessing ? 'Processing...' : `Fix Selected (${selectedReviewIds.size})`}
            </Button>
            <Button
              size="sm"
              variant="primary"
              onClick={handleFixAll}
              disabled={bulkProcessing}
              className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold"
            >
              {bulkProcessing ? 'Processing...' : 'Fix All Eligible'}
            </Button>
          </div>
        </div>
      )}

      {/* Bulk Action Result Notification */}
      {notification && (
        <div
          className={`p-3 rounded-lg text-xs font-mono flex items-center justify-between gap-2 border ${
            notification.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
              : notification.type === 'info'
              ? 'bg-blue-50 dark:bg-blue-950/40 border-blue-300 dark:border-blue-800 text-blue-800 dark:text-blue-300'
              : 'bg-rose-50 dark:bg-rose-950/40 border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-300'
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 dark:text-rose-400" />
            )}
            <span>{notification.message}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs font-bold px-1"
            title="Dismiss notification"
          >
            ×
          </button>
        </div>
      )}

      {/* Queue View & Inspection Split */}
      {loading ? (
        <div className="p-12 text-center font-mono text-slate-500 dark:text-slate-400 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-sm">
          Loading review queue items...
        </div>
      ) : items.length === 0 ? (
        <div className="p-12 text-center font-mono text-emerald-700 dark:text-emerald-400 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg space-y-2 shadow-sm">
          <CheckCircle2 className="w-8 h-8 text-emerald-600 dark:text-emerald-400 mx-auto" />
          <h3 className="text-sm font-bold">Review Queue Clean</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">All catalog records are validated and approved for export.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <ReviewQueueTable
              items={items}
              selectedIndex={selectedIndex}
              selectedReviewIds={selectedReviewIds}
              onToggleSelect={handleToggleSelect}
              onToggleSelectAll={handleToggleSelectAll}
              onSelectItem={setSelectedIndex}
              onApprove={handleApprove}
              onReject={handleReject}
              onAutoFix={handleAutoFix}
            />
          </div>

          <div className="lg:col-span-1">
            <ReviewDetailPanel
              item={selectedItem}
              onApprove={handleApprove}
              onReject={handleReject}
              onAutoFix={handleAutoFix}
              onEdit={handleEdit}
              isEditing={isEditing}
              onStartEdit={() => setIsEditing(true)}
              onCancelEdit={() => setIsEditing(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
