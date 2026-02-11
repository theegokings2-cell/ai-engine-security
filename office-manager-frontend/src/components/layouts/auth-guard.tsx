"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useCurrentUser } from "@/lib/queries/auth";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading, accessToken } = useAuthStore();
  const { isLoading: isUserLoading } = useCurrentUser();

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !accessToken) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, accessToken, router]);

  if (isLoading || isUserLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!isAuthenticated && !accessToken) {
    return null;
  }

  return <>{children}</>;
}
