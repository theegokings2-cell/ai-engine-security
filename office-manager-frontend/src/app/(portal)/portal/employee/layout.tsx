"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Calendar, CheckSquare, Users, FileText, Clock, LogOut, LayoutDashboard, User } from "lucide-react";
import { portalApiClient } from "@/lib/api/client";

interface PortalUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  permissions: string[];
}

const navigation = [
  { name: "Dashboard", href: "/portal/employee", icon: LayoutDashboard },
  { name: "Calendar", href: "/portal/employee/calendar", icon: Calendar },
  { name: "Appointments", href: "/portal/employee/appointments", icon: Clock },
  { name: "Tasks", href: "/portal/employee/tasks", icon: CheckSquare },
  { name: "Notes", href: "/portal/employee/notes", icon: FileText },
  { name: "Customers", href: "/portal/employee/customers", icon: Users },
];

export default function EmployeePortalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<PortalUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("portal_access_token");
    if (!token) {
      router.push("/portal/employee-login");
      return;
    }

    portalApiClient.defaults.headers.common["Authorization"] = `Bearer ${token}`;

    // Check if this is an employee login
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      if (payload.portal_type !== "employee") {
        router.push("/portal/dashboard");
        return;
      }
    } catch {
      localStorage.removeItem("portal_access_token");
      localStorage.removeItem("portal_refresh_token");
      router.push("/portal/employee-login");
      return;
    }

    fetchUser();
  }, [router]);

  const fetchUser = async () => {
    try {
      const response = await portalApiClient.get("/portal/auth/employee-me");
      setUser(response.data);
    } catch (error: any) {
      // Auth failed - clear tokens and redirect
      localStorage.removeItem("portal_access_token");
      localStorage.removeItem("portal_refresh_token");
      router.push("/portal/employee-login");
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("portal_access_token");
    localStorage.removeItem("portal_refresh_token");
    router.push("/portal/employee-login");
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Top Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link href="/portal/employee" className="text-xl font-bold text-primary">
                Employee Portal
              </Link>
              <span className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded-full">
                {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
              </span>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <User className="h-5 w-5 text-muted-foreground" />
                <span className="text-sm font-medium">{user.full_name}</span>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
              >
                <LogOut className="h-4 w-4" />
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-64 bg-white shadow-sm min-h-[calc(100vh-4rem)]">
          <nav className="p-4 space-y-1">
            {navigation.map((item) => {
              const isActive = pathname === item.href || 
                (item.href !== "/portal/employee" && pathname.startsWith(item.href));
              
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-gray-100 hover:text-foreground"
                  }`}
                >
                  <item.icon className="h-5 w-5" />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
