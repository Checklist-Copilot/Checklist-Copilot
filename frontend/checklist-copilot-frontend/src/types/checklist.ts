// Denormalized completion stats — the backend recomputes these on every save
// so the dashboard can show progress without loading the JSON column.
export interface ChecklistStats {
  total_items: number;
  edited_items: number;
  completed_items: number;
}

export interface ChecklistSummary extends ChecklistStats {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface Checklist extends ChecklistStats {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  checklist: Record<string, unknown>;
  checklist_prev: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ChecklistListResponse {
  checklists: ChecklistSummary[];
}
