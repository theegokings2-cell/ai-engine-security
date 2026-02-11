"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { portalApiClient } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";

export default function PortalLoginPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    username: "",
    password: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await portalApiClient.post("/portal/auth/login", new URLSearchParams({
        username: formData.username,
        password: formData.password,
      }), {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      // Store tokens
      localStorage.setItem("portal_access_token", response.data.access_token);
      if (response.data.refresh_token) {
        localStorage.setItem("portal_refresh_token", response.data.refresh_token);
      }

      toast({
        title: "Success",
        description: "Welcome to your customer portal!"
      });
      router.push("/portal/dashboard");
    } catch (error: any) {
      toast({
        title: "Login Failed",
        description: error.response?.data?.detail || "Invalid email or password",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Customer Portal</CardTitle>
          <CardDescription>Sign in to access your account</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="your@email.com"
                value={formData.username}
                onChange={(e) => setFormData((f) => ({ ...f, username: e.target.value }))}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={formData.password}
                onChange={(e) => setFormData((f) => ({ ...f, password: e.target.value }))}
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? "Signing in..." : "Sign In"}
            </Button>
          </form>
          <div className="mt-4 space-y-2 text-center text-sm">
            <div>
              <span className="text-muted-foreground">Are you an employee? </span>
              <Link href="/portal/employee-login" className="text-primary hover:underline font-medium">
                Employee login
              </Link>
            </div>
            <div>
              <span className="text-muted-foreground">Don&apos;t have an account? </span>
              <Link href="/portal/register" className="text-primary hover:underline font-medium">
                Contact us to get access
              </Link>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
