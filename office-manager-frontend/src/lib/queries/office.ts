import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth-store";

// Types - Match actual API schema
export interface Customer {
  id: string;
  company_name: string;
  contact_name?: string;
  email?: string;
  phone?: string;
  customer_type: string;
  address?: string;
  industry?: string;
  source?: string;
  notes?: string;
  customer_number?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface Employee {
  id: string;
  user_id?: string;
  employee_id: string;
  department_id?: string;
  department?: Department;
  user?: {
    id: string;
    email: string;
    full_name?: string;
  };
  job_title?: string;
  phone?: string;
  hire_date?: string;
  is_active: boolean;
  created_at: string;
}

export interface Department {
  id: string;
  name: string;
  description?: string;
  manager_id?: string;
  parent_id?: string;
  created_at: string;
}

export interface Location {
  id: string;
  name: string;
  address: string;
  city?: string;
  state?: string;
  country?: string;
  timezone?: string;
  is_active: boolean;
}

export interface Room {
  id: string;
  name: string;
  location_id: string;
  capacity: number;
  amenities?: string[];
  is_active: boolean;
}

export interface Appointment {
  id: string;
  title: string;
  description?: string;
  customer_id?: string;
  customer?: Customer;
  employee_id?: string;
  assigned_to_id?: string;
  start_time: string;
  end_time: string;
  status: "scheduled" | "confirmed" | "completed" | "cancelled";
  location?: string;
  appointment_type?: string;
  outcome?: string;
  next_steps?: string;
  notes?: string;
}

export interface TimeEntry {
  id: string;
  employee_id: string;
  project_id?: string;
  task_id?: string;
  description?: string;
  start_time: string;
  end_time?: string;
  duration_minutes?: number;
  billable: boolean;
}

export interface DashboardStats {
  total_customers: number;
  total_employees: number;
  active_appointments: number;
  room_bookings_today: number;
}

export interface User {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  role: string;
}

interface PaginatedResponse<T> {
  data: T[];
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

// Dashboard
export function useDashboardStats() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: ["office", "dashboard", "stats"],
    queryFn: async () => {
      const response = await apiClient.get<DashboardStats>("/office/dashboard/stats");
      return response.data;
    },
    enabled: isAuthenticated,
    staleTime: 60 * 1000,
    retry: false,
  });
}

// Users (for employee assignment)
export function useUsers() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: ["admin", "users"],
    queryFn: async () => {
      const response = await apiClient.get<User[]>("/admin/users");
      return response.data;
    },
    enabled: isAuthenticated,
  });
}

// Customers
interface CustomersResponse {
  customers: Customer[];
}

export function useCustomers(params: { skip?: number; limit?: number; search?: string } = {}) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: ["office", "customers", params],
    queryFn: async () => {
      const response = await apiClient.get<CustomersResponse>("/office/customers", { params });
      // Transform to match expected format
      return {
        data: response.data.customers || [],
        total: response.data.customers?.length || 0,
        skip: params.skip || 0,
        limit: params.limit || 100,
        has_more: false,
      };
    },
    enabled: isAuthenticated,
  });
}

export function useCustomer(id: string) {
  return useQuery({
    queryKey: ["office", "customers", id],
    queryFn: async () => {
      const response = await apiClient.get<Customer>(`/office/customers/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateCustomer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<Customer>) => {
      // Filter out empty strings and undefined values
      const cleanParams: Record<string, string> = {};
      for (const [key, value] of Object.entries(data)) {
        if (value !== undefined && value !== null && value !== "") {
          cleanParams[key] = String(value);
        }
      }

      // API expects query parameters, not JSON body
      const response = await apiClient.post<{ customer: Customer; message: string }>(
        "/office/customers",
        null,
        { params: cleanParams }
      );
      return response.data.customer;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["office", "customers"] });
    },
  });
}

export function useUpdateCustomer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<Customer> }) => {
      const cleanParams: Record<string, string> = {};
      for (const [key, value] of Object.entries(data)) {
        if (value !== undefined && value !== null && value !== "") {
          cleanParams[key] = String(value);
        }
      }
      const response = await apiClient.put<{ customer: Customer; message: string }>(
        `/office/customers/${id}`,
        null,
        { params: cleanParams }
      );
      return response.data.customer;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["office", "customers"] });
    },
  });
}

export function useDeleteCustomer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/office/customers/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["office", "customers"] });
    },
  });
}

// Employees
interface EmployeesResponse {
  employees: Employee[];
}

export function useEmployees(params: { skip?: number; limit?: number; department_id?: string } = {}) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: ["office", "employees", params],
    queryFn: async () => {
      const response = await apiClient.get<EmployeesResponse>("/office/employees", { params });
      return {
        data: response.data.employees || [],
        total: response.data.employees?.length || 0,
        skip: params.skip || 0,
        limit: params.limit || 100,
        has_more: false,
      };
    },
    enabled: isAuthenticated,
  });
}

export function useCreateEmployee() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Record<string, string>) => {
      const form = new URLSearchParams();
      for (const [key, value] of Object.entries(data)) {
        if (value) form.append(key, value);
      }
      const response = await apiClient.post<{ employee: Employee; message: string }>(
        "/office/employees/with-user",
        form,
      );
      return response.data.employee;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["office", "employees"] });
    },
  });
}

export function useDeleteEmployee() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/office/employees/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["office", "employees"] });
    },
  });
}

// Departments
interface DepartmentsResponse {
  departments: Department[];
}

export function useDepartments() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: ["office", "departments"],
    queryFn: async () => {
      const response = await apiClient.get<DepartmentsResponse>("/office/departments/enterprise");
      return {
        data: response.data.departments || [],
        total: response.data.departments?.length || 0,
        skip: 0,
        limit: 500,
        has_more: false,
      };
    },
    enabled: isAuthenticated,
  });
}

export function useCreateDepartment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<Department>) => {
      const response = await apiClient.post<{ department: Department; message: string }>(
        "/office/departments",
        null,
        { params: data }
      );
      return response.data.department;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["office", "departments"] });
    },
  });
}

// Locations
interface LocationsResponse {
  locations: Location[];
}

export function useLocations() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: ["office", "locations"],
    queryFn: async () => {
      const response = await apiClient.get<LocationsResponse>("/office/locations");
      return {
        data: response.data.locations || [],
        total: response.data.locations?.length || 0,
        skip: 0,
        limit: 100,
        has_more: false,
      };
    },
    enabled: isAuthenticated,
  });
}

// Rooms
interface RoomsResponse {
  rooms: Room[];
}

export function useRooms(params: { location_id?: string } = {}) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: ["office", "rooms", params],
    queryFn: async () => {
      const response = await apiClient.get<RoomsResponse>("/office/rooms", { params });
      return {
        data: response.data.rooms || [],
        total: response.data.rooms?.length || 0,
        skip: 0,
        limit: 100,
        has_more: false,
      };
    },
    enabled: isAuthenticated,
  });
}

export function useAvailableRooms(params: { start_time: string; end_time: string; capacity?: number }) {
  return useQuery({
    queryKey: ["office", "rooms", "available", params],
    queryFn: async () => {
      const response = await apiClient.get<RoomsResponse>("/office/rooms/available", { params });
      return response.data.rooms || [];
    },
    enabled: !!params.start_time && !!params.end_time,
  });
}

// Appointments
interface AppointmentsResponse {
  appointments: Appointment[];
}

export function useAppointments(params: {
  skip?: number;
  limit?: number;
  status?: string;
  start_date?: string;
  end_date?: string;
} = {}) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: ["office", "appointments", params],
    queryFn: async () => {
      // Fetch from both office appointments AND calendar events (meetings/calls)
      const [aptResponse, calResponse] = await Promise.all([
        apiClient.get<AppointmentsResponse>("/office/appointments", { params }).catch(() => ({ data: { appointments: [] } })),
        apiClient.get<any[]>("/calendar", {
          params: {
            start_date: params.start_date,
            end_date: params.end_date,
          },
        }).catch(() => ({ data: [] })),
      ]);

      const officeAppointments = aptResponse.data.appointments || [];

      // Convert calendar meetings/calls to appointment format
      const calEvents = (Array.isArray(calResponse.data) ? calResponse.data : [])
        .filter((e: any) => e.event_type === "meeting" || e.event_type === "call");

      // Build a set of existing appointment keys (title+start) to deduplicate
      const existingKeys = new Set(
        officeAppointments.map((a: Appointment) => `${a.title}|${new Date(a.start_time).getTime()}`)
      );

      const calAsAppointments: Appointment[] = calEvents
        .filter((e: any) => !existingKeys.has(`${e.title}|${new Date(e.start_time).getTime()}`))
        .map((e: any) => ({
          id: e.id,
          tenant_id: e.tenant_id,
          title: e.title,
          description: e.description || "",
          location: e.location || "",
          start_time: e.start_time,
          end_time: e.end_time,
          status: "scheduled" as const,
          appointment_type: e.event_type,
          customer_id: "",
          assigned_to_id: e.created_by_id || "",
        }));

      const merged = [...officeAppointments, ...calAsAppointments]
        .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());

      return {
        data: merged,
        total: merged.length,
        skip: params.skip || 0,
        limit: params.limit || 100,
        has_more: false,
      };
    },
    enabled: isAuthenticated,
  });
}

export function useCreateAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<Appointment>) => {
      // Backend expects Form(...) parameters — send as URLSearchParams
      const form = new URLSearchParams();
      if (data.title) form.append("title", data.title);
      if (data.start_time) form.append("start_time", new Date(data.start_time).toISOString());
      if (data.end_time) form.append("end_time", new Date(data.end_time).toISOString());
      if (data.customer_id) form.append("customer_id", data.customer_id);
      if (data.description) form.append("description", data.description);
      if (data.location) form.append("location", data.location);

      const response = await apiClient.post<{ appointment: Appointment; message: string }>(
        "/office/appointments",
        form,
      );

      // Also create a calendar event so it shows on the calendar
      try {
        await apiClient.post("/calendar", {
          title: data.title,
          description: data.description || "",
          event_type: "meeting",
          start_time: new Date(data.start_time!).toISOString(),
          end_time: new Date(data.end_time!).toISOString(),
          location: data.location || "",
          attendees: [],
        });
      } catch {
        // Calendar event creation is best-effort; appointment is the primary record
      }

      return response.data.appointment;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["office", "appointments"] });
      queryClient.invalidateQueries({ queryKey: ["calendar"] });
    },
  });
}

export function useUpdateAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<Appointment> }) => {
      const form = new URLSearchParams();
      if (data.title) form.append("title", data.title);
      if (data.start_time) form.append("start_time", new Date(data.start_time).toISOString());
      if (data.end_time) form.append("end_time", new Date(data.end_time).toISOString());
      if (data.customer_id) form.append("customer_id", data.customer_id);
      if (data.description !== undefined) form.append("description", data.description);
      if (data.location !== undefined) form.append("location", data.location);
      if (data.status) form.append("status", data.status);
      if (data.appointment_type) form.append("appointment_type", data.appointment_type);

      const response = await apiClient.put<{ appointment: Appointment }>(
        `/office/appointments/${id}`,
        form,
        { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
      );
      return response.data.appointment;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["office", "appointments"] });
    },
  });
}

export function useDeleteAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/office/appointments/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["office", "appointments"] });
    },
  });
}

export function useUpcomingAppointments(limit: number = 5) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: ["office", "appointments", "upcoming", limit],
    queryFn: async () => {
      const today = new Date();
      const endDate = new Date(today.getFullYear() + 1, today.getMonth(), today.getDate());

      // Fetch from both sources
      const [aptResponse, calResponse] = await Promise.all([
        apiClient.get<AppointmentsResponse>("/office/appointments", {
          params: { skip: 0, limit: 100 },
        }).catch(() => ({ data: { appointments: [] } })),
        apiClient.get<any[]>("/calendar", {
          params: {
            start_date: today.toISOString(),
            end_date: endDate.toISOString(),
          },
        }).catch(() => ({ data: [] })),
      ]);

      const officeAppointments = (aptResponse.data.appointments || [])
        .filter((apt: Appointment) => {
          const aptDate = new Date(apt.start_time);
          return aptDate >= today && ["scheduled", "confirmed"].includes(apt.status);
        });

      // Calendar meetings/calls not already in appointments
      const existingKeys = new Set(
        officeAppointments.map((a: Appointment) => `${a.title}|${new Date(a.start_time).getTime()}`)
      );

      const calEvents = (Array.isArray(calResponse.data) ? calResponse.data : [])
        .filter((e: any) => (e.event_type === "meeting" || e.event_type === "call")
          && new Date(e.start_time) >= today
          && !existingKeys.has(`${e.title}|${new Date(e.start_time).getTime()}`))
        .map((e: any) => ({
          id: e.id,
          tenant_id: e.tenant_id,
          title: e.title,
          description: e.description || "",
          location: e.location || "",
          start_time: e.start_time,
          end_time: e.end_time,
          status: "scheduled" as const,
          appointment_type: e.event_type,
          customer_id: "",
          assigned_to_id: e.created_by_id || "",
        }));

      return [...officeAppointments, ...calEvents]
        .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())
        .slice(0, limit);
    },
    enabled: isAuthenticated,
  });
}

// Time Entries
interface TimeEntriesResponse {
  time_entries: TimeEntry[];
}

export function useTimeEntries(params: { employee_id?: string; start_date?: string; end_date?: string } = {}) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: ["office", "time-entries", params],
    queryFn: async () => {
      const response = await apiClient.get<TimeEntriesResponse>("/office/time-entries", { params });
      return {
        data: response.data.time_entries || [],
        total: response.data.time_entries?.length || 0,
        skip: 0,
        limit: 100,
        has_more: false,
      };
    },
    enabled: isAuthenticated,
  });
}

export function useCreateTimeEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<TimeEntry>) => {
      const response = await apiClient.post<TimeEntry>("/office/time-entries", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["office", "time-entries"] });
    },
  });
}

// Notes
export interface Note {
  id: string;
  title: string;
  content: string;
  is_pinned: boolean;
  updated_at: string;
}

interface NotesResponse {
  notes: Note[];
}

export function useNotes(search?: string) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: ["office", "notes", search],
    queryFn: async () => {
      const response = await apiClient.get<NotesResponse>("/office/notes", { params: { search } });
      return response.data.notes || [];
    },
    enabled: isAuthenticated,
  });
}

export function useCreateNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { title: string; content: string; is_pinned?: boolean }) => {
      const formBody = new URLSearchParams();
      formBody.append("title", data.title);
      formBody.append("content", data.content);
      if (data.is_pinned !== undefined) formBody.append("is_pinned", String(data.is_pinned));
      const response = await apiClient.post<{ note: Note }>("/office/notes", formBody.toString(), {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      return response.data.note;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["office", "notes"] });
    },
  });
}

export function useUpdateNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<{ title: string; content: string; is_pinned: boolean }> }) => {
      const formBody = new URLSearchParams();
      if (data.title !== undefined) formBody.append("title", data.title);
      if (data.content !== undefined) formBody.append("content", data.content);
      if (data.is_pinned !== undefined) formBody.append("is_pinned", String(data.is_pinned));
      const response = await apiClient.put<{ note: Note }>(`/office/notes/${id}`, formBody.toString(), {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      return response.data.note;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["office", "notes"] });
    },
  });
}

export function useDeleteNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/office/notes/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["office", "notes"] });
    },
  });
}
