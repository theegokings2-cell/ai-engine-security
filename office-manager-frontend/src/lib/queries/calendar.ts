import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api/client";

export interface CalendarEvent {
  id: string;
  tenant_id: string;
  title: string;
  description?: string;
  event_type: "meeting" | "call" | "reminder" | "blocked";
  start_time: string;
  end_time: string;
  all_day: boolean;
  location?: string;
  meeting_link?: string;
  attendees: string[];
  reminder_minutes?: number[];
  created_by_id: string;
  created_at: string;
}

export interface CreateEventData {
  title: string;
  description?: string;
  event_type?: "meeting" | "call" | "reminder" | "blocked";
  start_time: string;
  end_time: string;
  all_day?: boolean;
  timezone?: string;
  location?: string;
  attendees?: string[];
  reminder_minutes?: number[];
}

export interface EventFilters {
  start_date?: string;
  end_date?: string;
  event_type?: string;
}

export function useEvents(filters: EventFilters = {}) {
  return useQuery({
    queryKey: ["calendar", "events", filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.start_date) params.append("start_date", filters.start_date);
      if (filters.end_date) params.append("end_date", filters.end_date);
      if (filters.event_type) params.append("event_type", filters.event_type);

      const response = await apiClient.get<CalendarEvent[]>(`/calendar?${params.toString()}`);
      return response.data;
    },
  });
}

export function useTodayEvents() {
  return useQuery({
    queryKey: ["calendar", "today"],
    queryFn: async () => {
      const response = await apiClient.get<CalendarEvent[]>("/calendar/today");
      return response.data;
    },
  });
}

export function useCreateEvent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateEventData) => {
      const response = await apiClient.post<CalendarEvent>("/calendar", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calendar"] });
    },
  });
}

export function useUpdateEvent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<CreateEventData> }) => {
      const response = await apiClient.put<CalendarEvent>(`/calendar/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calendar"] });
    },
  });
}

export function useDeleteEvent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/calendar/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calendar"] });
    },
  });
}
