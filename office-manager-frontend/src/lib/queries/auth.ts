import { useMutation, useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { useAuthStore, User } from "@/lib/stores/auth-store";

interface LoginCredentials {
  username: string;
  password: string;
}

interface RegisterData {
  email: string;
  password: string;
  full_name: string;
  tenant_name?: string;
}

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in?: number;
}

interface RegisterResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export function useLogin() {
  const setTokens = useAuthStore((state) => state.setTokens);
  const setUser = useAuthStore((state) => state.setUser);
  const setLoading = useAuthStore((state) => state.setLoading);

  return useMutation({
    mutationFn: async (credentials: LoginCredentials) => {
      const formData = new URLSearchParams();
      formData.append("username", credentials.username);
      formData.append("password", credentials.password);

      const response = await apiClient.post<LoginResponse>(
        "/auth/login",
        formData,
        {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        }
      );
      return response.data;
    },
    onSuccess: async (data) => {
      // Set tokens first
      setTokens(data.access_token, data.refresh_token);

      // Then fetch user data
      try {
        const userResponse = await apiClient.get<User>("/auth/me", {
          headers: {
            Authorization: `Bearer ${data.access_token}`,
          },
        });
        setUser(userResponse.data);
        useAuthStore.setState({ isAuthenticated: true, isLoading: false });
      } catch {
        setLoading(false);
      }
    },
  });
}

export function useRegister() {
  const login = useAuthStore((state) => state.login);

  return useMutation({
    mutationFn: async (data: RegisterData) => {
      const response = await apiClient.post<RegisterResponse>(
        "/auth/register",
        data
      );
      return response.data;
    },
    onSuccess: (data) => {
      login(data.user, data.access_token, data.refresh_token);
    },
  });
}

export function useCurrentUser() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const setUser = useAuthStore((state) => state.setUser);
  const setLoading = useAuthStore((state) => state.setLoading);

  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      const response = await apiClient.get<User>("/auth/me");
      setUser(response.data);
      return response.data;
    },
    enabled: !!accessToken,
    retry: false,
    staleTime: 5 * 60 * 1000,
    meta: {
      onSettled: () => setLoading(false),
    },
  });
}

export function useLogout() {
  const logout = useAuthStore((state) => state.logout);

  return useMutation({
    mutationFn: async () => {
      try {
        await apiClient.post("/auth/logout");
      } catch {
        // Ignore logout errors
      }
    },
    onSettled: () => {
      logout();
    },
  });
}
