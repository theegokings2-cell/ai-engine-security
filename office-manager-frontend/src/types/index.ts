export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "manager" | "staff" | "viewer";
  tenant_id: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: "pending" | "in_progress" | "completed" | "cancelled";
  priority: "low" | "medium" | "high" | "urgent";
  assignee_id?: string;
  assignee?: User;
  due_date?: string;
  created_at: string;
  updated_at: string;
  tenant_id: string;
}

export interface CalendarEvent {
  id: string;
  title: string;
  description?: string;
  start_time: string;
  end_time: string;
  all_day: boolean;
  location?: string;
  attendee_ids?: string[];
  attendees?: User[];
  created_at: string;
  updated_at: string;
  tenant_id: string;
}

export interface Note {
  id: string;
  title: string;
  content: string;
  tags?: string[];
  folder?: string;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
  tenant_id: string;
  owner_id: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  items?: T[];  // fallback
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

export interface TaskFilters {
  status?: Task["status"];
  priority?: Task["priority"];
  assignee_id?: string;
  search?: string;
  skip?: number;
  limit?: number;
  page?: number;  // convenience - converted to skip
}

export interface CalendarFilters {
  start_date: string;
  end_date: string;
}

export interface NoteFilters {
  search?: string;
  folder?: string;
  tags?: string[];
  page?: number;
  size?: number;
}
