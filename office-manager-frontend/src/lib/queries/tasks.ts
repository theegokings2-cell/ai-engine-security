import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth-store";
import { Task, TaskFilters, PaginatedResponse } from "@/types";

export function useTasks(filters: TaskFilters = {}) {
  // Convert page to skip/limit
  const { page, ...rest } = filters;
  const limit = filters.limit || 20;
  const skip = page ? (page - 1) * limit : (filters.skip || 0);

  return useQuery({
    queryKey: ["tasks", "list", filters],
    queryFn: async () => {
      const response = await apiClient.get<PaginatedResponse<Task>>("/tasks", {
        params: { ...rest, skip, limit },
      });
      return response.data;
    },
    staleTime: 2 * 60 * 1000,
  });
}

export function useTask(id: string) {
  return useQuery({
    queryKey: ["tasks", "detail", id],
    queryFn: async () => {
      const response = await apiClient.get<Task>(`/tasks/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<Task>) => {
      const response = await apiClient.post<Task>("/tasks", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

export function useUpdateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<Task> }) => {
      const response = await apiClient.put<Task>(`/tasks/${id}`, data);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({
        queryKey: ["tasks", "detail", variables.id],
      });
    },
  });
}

export function useDeleteTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/tasks/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

export function useParseTaskFromText() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (text: string) => {
      const response = await apiClient.post<Task>("/tasks/from-text", { text });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

export function useTaskStatistics() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: ["tasks", "statistics"],
    queryFn: async () => {
      const response = await apiClient.get<{
        total: number;
        pending: number;
        in_progress: number;
        completed: number;
        overdue: number;
      }>("/tasks/statistics");
      return response.data;
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
