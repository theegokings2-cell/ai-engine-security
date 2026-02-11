"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layouts/header";
import { apiClient } from "@/lib/api/client";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Calendar, CheckSquare, FileText, Clock, User } from "lucide-react";
import { format, parseISO } from "date-fns";

interface PortalUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  permissions: string[];
}

interface DashboardStats {
  upcoming_appointments: number;
  active_tasks: number;
}

interface Appointment {
  id: string;
  title: string;
  start_time: string;
  status: string;
}

interface Task {
  id: string;
  title: string;
  status: string;
  priority: string;
  due_date?: string;
}

export default function CustomerDashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<PortalUser | null>(null);
  const [stats, setStats] = useState<DashboardStats>({ upcoming_appointments: 0, active_tasks: 0 });
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("portal_access_token");
    if (!token) {
      router.push("/portal/login");
      return;
    }

    apiClient.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    fetchUser();
  }, [router]);

  const fetchUser = async () => {
    try {
      const response = await apiClient.get("/portal/auth/me");
      setUser(response.data);
    } catch (error) {
      console.error("Failed to fetch user:", error);
      localStorage.removeItem("portal_access_token");
      router.push("/portal/login");
    }
  };

  const fetchDashboardData = async () => {
    if (!user) return;

    try {
      setIsLoading(true);
      
      // Fetch stats
      const statsRes = await apiClient.get("/portal/dashboard/stats");
      setStats(statsRes.data);
      
      // Fetch appointments
      try {
        const aptRes = await apiClient.get("/portal/appointments", { params: { limit: 5 } });
        setAppointments(aptRes.data.appointments || []);
      } catch (e) {
        setAppointments([]);
      }
      
      // Fetch tasks
      try {
        const taskRes = await apiClient.get("/portal/tasks", { params: { limit: 5 } });
        setTasks(taskRes.data.tasks || []);
      } catch (e) {
        setTasks([]);
      }
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchDashboardData();
    }
  }, [user]);

  const formatDate = (dateStr: string) => {
    return format(parseISO(dateStr), "MMM d, h:mm a");
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <>
      <Header title="My Dashboard" />
      <div className="flex-1 p-6">
        <div className="max-w-4xl mx-auto">
          {/* Welcome */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold">Welcome back, {user.full_name}!</h1>
            <p className="text-muted-foreground mt-1">Here's an overview of your account</p>
          </div>

          {/* Stats */}
          <div className="grid gap-4 md:grid-cols-2 mb-8">
            <Card>
              <CardContent className="flex items-center gap-4 p-6">
                <div className="p-3 bg-blue-100 rounded-lg">
                  <Calendar className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Upcoming Appointments</p>
                  <p className="text-2xl font-bold">{stats.upcoming_appointments}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex items-center gap-4 p-6">
                <div className="p-3 bg-green-100 rounded-lg">
                  <CheckSquare className="h-6 w-6 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Active Tasks</p>
                  <p className="text-2xl font-bold">{stats.active_tasks}</p>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            {/* Upcoming Appointments */}
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold flex items-center gap-2">
                    <Calendar className="h-5 w-5" />
                    Upcoming Appointments
                  </h2>
                  <Button variant="ghost" size="sm" onClick={() => router.push("/portal/customer/appointments")}>
                    View All
                  </Button>
                </div>
                {appointments.length === 0 ? (
                  <p className="text-muted-foreground text-center py-4">No upcoming appointments</p>
                ) : (
                  <div className="space-y-3">
                    {appointments.map((apt) => (
                      <div key={apt.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div>
                          <p className="font-medium">{apt.title}</p>
                          <p className="text-sm text-muted-foreground">{formatDate(apt.start_time)}</p>
                        </div>
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          apt.status === "confirmed" ? "bg-green-100 text-green-800" : "bg-blue-100 text-blue-800"
                        }`}>
                          {apt.status}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* My Tasks */}
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold flex items-center gap-2">
                    <CheckSquare className="h-5 w-5" />
                    My Tasks
                  </h2>
                  <Button variant="ghost" size="sm" onClick={() => router.push("/portal/customer/tasks")}>
                    View All
                  </Button>
                </div>
                {tasks.length === 0 ? (
                  <p className="text-muted-foreground text-center py-4">No active tasks</p>
                ) : (
                  <div className="space-y-3">
                    {tasks.slice(0, 5).map((task) => (
                      <div key={task.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div>
                          <p className="font-medium">{task.title}</p>
                          {task.due_date && (
                            <p className="text-sm text-muted-foreground">
                              Due: {format(parseISO(task.due_date), "MMM d")}
                            </p>
                          )}
                        </div>
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          task.priority === "high" ? "bg-red-100 text-red-800" :
                          task.priority === "medium" ? "bg-yellow-100 text-yellow-800" :
                          "bg-green-100 text-green-800"
                        }`}>
                          {task.priority}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Quick Links */}
          <Card className="mt-6">
            <CardContent className="p-6">
              <h2 className="text-lg font-semibold mb-4">Quick Links</h2>
              <div className="grid gap-4 md:grid-cols-3">
                <Button variant="outline" className="h-16 flex-col gap-2" onClick={() => router.push("/portal/customer/appointments")}>
                  <Calendar className="h-6 w-6" />
                  <span>My Appointments</span>
                </Button>
                <Button variant="outline" className="h-16 flex-col gap-2" onClick={() => router.push("/portal/customer/tasks")}>
                  <CheckSquare className="h-6 w-6" />
                  <span>My Tasks</span>
                </Button>
                <Button variant="outline" className="h-16 flex-col gap-2" onClick={() => router.push("/portal/customer/notes")}>
                  <FileText className="h-6 w-6" />
                  <span>My Notes</span>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
