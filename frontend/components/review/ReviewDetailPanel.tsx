'use client';

import React from 'react';
import { ReviewItem } from '../../types/review';
import { Card, CardHeader } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Check, X, Wand2, Edit3 } from 'lucide-react';

interface ReviewDetailPanelProps {
  item: ReviewItem | null;
  onApprove: (item: ReviewItem) => void;
  onReject: (item: ReviewItem) => void;
  onAutoFix: (item: ReviewItem) => void;
  onEdit: (item: ReviewItem, customValue: string) => void;
  isEditing?: boolean;
  onStartEdit?: () => void;
  onCancelEdit?: () => void;
}

export const ReviewDetailPanel: React.FC<ReviewDetailPanelProps> = ({
  item,
  onApprove,
  onReject,
  onAutoFix,
  onEdit,
  isEditing = false,
  onStartEdit,
  onCancelEdit,
}) => {
  const [internalEditing, setInternalEditing] = React.useState(false);
  const [customVal, setCustomVal] = React.useState('');
  const inputRef = React.useRef<HTMLInputElement>(null);

  const activeEditing = isEditing || internalEditing;

  React.useEffect(() => {
    if (item) {
      setCustomVal(item.suggested_value || item.current_value || '');
      setInternalEditing(false);
    }
  }, [item]);

  React.useEffect(() => {
    if (activeEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [activeEditing]);

  const handleStartEdit = () => {
    if (onStartEdit) {
      onStartEdit();
    } else {
      setInternalEditing(true);
    }
  };

  const handleCancel = () => {
    if (onCancelEdit) {
      onCancelEdit();
    }
    setInternalEditing(false);
    if (item) {
      setCustomVal(item.suggested_value || item.current_value || '');
    }
  };

  const handleSubmitEdit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!item || !customVal.trim()) return;
    onEdit(item, customVal.trim());
    handleCancel();
  };

  if (!item) {
    return (
      <Card className="flex flex-col items-center justify-center p-8 text-center text-slate-500">
        <p className="text-xs font-mono">Select an item from the review queue to inspect details</p>
      </Card>
    );
  }

  return (
    <Card className="space-y-4">
      <CardHeader title="Review Item Inspection" subtitle={`Product MPN: ${item.mfg_part_num}`} />

      <div className="space-y-3 text-xs font-mono">
        <div className="flex justify-between items-center bg-slate-50 dark:bg-slate-950 p-3 rounded border border-slate-200 dark:border-slate-800">
          <div>
            <span className="text-[10px] text-slate-500 uppercase block">Issue Type</span>
            <span className="font-bold text-slate-800 dark:text-slate-200">{item.issue_type}</span>
          </div>
          <Badge status={item.severity}>{item.severity}</Badge>
        </div>

        <div className="bg-slate-50 dark:bg-slate-950 p-3 rounded border border-slate-200 dark:border-slate-800">
          <span className="text-[10px] text-slate-500 uppercase block mb-1">Target Field & Reason</span>
          <p className="text-slate-700 dark:text-slate-300 text-[11px] leading-relaxed">
            <strong className="text-blue-600 dark:text-blue-400 uppercase">{item.field}:</strong> {item.reason}
          </p>
        </div>

        {/* Diff Comparison */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-slate-50 dark:bg-slate-950 p-3 rounded border border-slate-200 dark:border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block mb-1">Current Unvalidated Value</span>
            <span className="text-amber-700 dark:text-amber-300 font-bold block break-all">{item.current_value}</span>
          </div>

          <div className="bg-slate-50 dark:bg-slate-950 p-3 rounded border border-slate-200 dark:border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block mb-1">Suggested Canonical Value</span>
            <span className="text-emerald-700 dark:text-emerald-400 font-bold block break-all">{item.suggested_value}</span>
          </div>
        </div>

        {/* Custom Edit Form Drawer */}
        {activeEditing && (
          <form onSubmit={handleSubmitEdit} className="p-3 bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 rounded space-y-2.5 animate-in fade-in duration-150">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-blue-800 dark:text-blue-300 uppercase flex items-center gap-1.5">
                <Edit3 className="w-3.5 h-3.5" /> Enter Custom Value for {item.field}
              </span>
              <span className="text-[10px] text-slate-400">Press Enter to save</span>
            </div>
            <input
              ref={inputRef}
              type="text"
              value={customVal}
              onChange={(e) => setCustomVal(e.target.value)}
              className="w-full px-3 py-1.5 text-xs font-mono bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded focus:outline-hidden focus:ring-1 focus:ring-blue-500 text-slate-900 dark:text-slate-100"
              placeholder={`Enter override value for ${item.field}...`}
            />
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" size="sm" onClick={handleCancel}>
                Cancel (Esc)
              </Button>
              <Button type="submit" variant="primary" size="sm" className="bg-blue-600 hover:bg-blue-500">
                Apply Custom Override
              </Button>
            </div>
          </form>
        )}

        {/* Action Buttons */}
        <div className="pt-2 grid grid-cols-2 gap-2">
          <Button variant="primary" size="sm" onClick={() => onApprove(item)} className="bg-emerald-600 hover:bg-emerald-500">
            <Check className="w-3.5 h-3.5" /> Approve (A)
          </Button>

          <Button variant="secondary" size="sm" onClick={() => onAutoFix(item)} className="border-amber-400 dark:border-amber-700 text-amber-800 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900/40">
            <Wand2 className="w-3.5 h-3.5" /> Auto-Fix (F)
          </Button>

          <Button variant="outline" size="sm" onClick={() => onReject(item)} className="border-rose-300 dark:border-rose-800 text-rose-700 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950">
            <X className="w-3.5 h-3.5" /> Reject (R)
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleStartEdit}
            className={activeEditing ? 'bg-blue-50 dark:bg-blue-950 text-blue-600 border-blue-300 dark:border-blue-700' : ''}
          >
            <Edit3 className="w-3.5 h-3.5" /> Edit (E)
          </Button>
        </div>
      </div>
    </Card>
  );
};
