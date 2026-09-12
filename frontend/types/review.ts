export interface ReviewItem {
  review_id: string;
  product_id: string;
  mfg_part_num: string;
  product_name: string;
  field_name: string;
  field?: string;
  issue_type: string;
  severity: 'WARNING' | 'ERROR' | 'CRITICAL';
  current_value: string;
  suggested_value: string;
  reason: string;
  quality_score: number;
  status: 'OPEN' | 'APPROVED' | 'REJECTED' | 'FIXED';
  assigned_to?: string;
  reviewed_at?: string;
  is_demo_data?: boolean;
}

export interface BulkFixResponse {
  status: string;
  selected_count: number;
  eligible_count: number;
  applied_count: number;
  failed_count: number;
  remaining_pending: number;
  affected_products_count: number;
}
