export interface ChecklistSummary {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface Checklist {
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
