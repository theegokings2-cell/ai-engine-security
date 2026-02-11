"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { portalApiClient } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";

export default function PasswordResetPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [isResetMode, setIsResetMode] = useState(!!searchParams.get("token"));
  const [formData, setFormData] = useState({
    email: "",
    new_password: "",
    confirmPassword: "",
    reset_token: searchParams.get("token") || "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    
    if (!isResetMode && !formData.email.trim()) {
      newErrors.email = "Email is required";
    } else if (!isResetMode && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "Invalid email format";
    }
    
    if (isResetMode) {
      if (!formData.reset_token.trim()) {
        newErrors.reset_token = "Reset token is required";
      }
      if (!formData.new_password) {
        newErrors.new_password = "New password is required";
      } else if (formData.new_password.length < 8) {
        newErrors.new_password = "Password must be at least 8 characters";
      }
      if (formData.new_password !== formData.confirmPassword) {
        newErrors.confirmPassword = "Passwords do not match";
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleRequestReset = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      const response = await portalApiClient.post("/portal/auth/password-reset/request", {
        email: formData.email,
      });

      toast({ 
        title: "Reset Email Sent", 
        description: response.data.message
      });
    } catch (error: any) {
      toast({
        title: "Request Failed",
        description: error.response?.data?.detail || "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmReset = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      const response = await portalApiClient.post("/portal/auth/password-reset/confirm", {
        token: formData.reset_token,
        new_password: formData.new_password,
      });

      toast({ 
        title: "Password Reset", 
        description: response.data.message
      });
      
      router.push("/portal/login");
    } catch (error: any) {
      toast({
        title: "Reset Failed",
        description: error.response?.data?.detail || "Invalid or expired reset token",
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
          <CardTitle className="text-2xl">
            {isResetMode ? "Set New Password" : "Reset Password"}
          </CardTitle>
          <CardDescription>
            {isResetMode 
              ? "Enter your new password below"
              : "Enter your email to receive a password reset link"
            }
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!isResetMode ? (
            <form onSubmit={handleRequestReset} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="your@email.com"
                  value={formData.email}
                  onChange={(e) => setFormData((f) => ({ ...f, email: e.target.value }))}
                  required
                />
                {errors.email && <p className="text-sm text-red-500">{errors.email}</p>}
              </div>
              
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? "Sending..." : "Send Reset Link"}
              </Button>
            </form>
          ) : (
            <form onSubmit={handleConfirmReset} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="reset_token">Reset Token</Label>
                <Input
                  id="reset_token"
                  type="text"
                  placeholder="Paste your reset token"
                  value={formData.reset_token}
                  onChange={(e) => setFormData((f) => ({ ...f, reset_token: e.target.value }))}
                  required
                />
                {errors.reset_token && <p className="text-sm text-red-500">{errors.reset_token}</p>}
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="new_password">New Password</Label>
                <Input
                  id="new_password"
                  type="password"
                  placeholder="••••••••"
                  value={formData.new_password}
                  onChange={(e) => setFormData((f) => ({ ...f, new_password: e.target.value }))}
                  required
                />
                {errors.new_password && <p className="text-sm text-red-500">{errors.new_password}</p>}
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="••••••••"
                  value={formData.confirmPassword}
                  onChange={(e) => setFormData((f) => ({ ...f, confirmPassword: e.target.value }))}
                  required
                />
                {errors.confirmPassword && <p className="text-sm text-red-500">{errors.confirmPassword}</p>}
              </div>
              
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? "Resetting..." : "Reset Password"}
              </Button>
            </form>
          )}
          
          <div className="mt-4 text-center text-sm">
            {!isResetMode ? (
              <>
                <span className="text-muted-foreground">Remember your password? </span>
                <Link href="/portal/login" className="text-primary hover:underline">
                  Sign in
                </Link>
              </>
            ) : (
              <>
                <span className="text-muted-foreground">Didn't receive a token? </span>
                <button 
                  type="button"
                  onClick={() => setIsResetMode(false)}
                  className="text-primary hover:underline"
                >
                  Request new reset
                </button>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
