"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layouts/header";
import { portalApiClient } from "@/lib/api/client";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CheckSquare, Calendar, Clock, Eye } from "lucide-react";
import { format, parseISO, isAfter } from "date-fns";
import { cn } from "@/lib/utils";

interface PortalUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface Task {
  id: string;
  title: string;
  description?: string;
  status: "todo" | "in_progress" | "done" | "cancelled";
  priority: "low" | "medium" | "high" | "urgent";
  due_date?: string;
}

const statusColors: Record<Task["status"], string> = {
  todo: "bg-gray-100 text-gray-800",
  in_progress: "bg-blue-100 text-blue-800",
  done: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
};

const priorityColors: Record<Task["priority"], string> = {
  low: "bg-gray-100 text-gray-600",
  medium: "bg-blue-100 text-blue-600",
  high: "bg-orange-100 text-orange-600",
  urgent: "bg-red-100 text-red-600",
};

export default function CustomerTasksPage() {
  const router = useRouter();
  const [user, setUser] = useState<PortalUser | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("portal_access_token");
    if (!token) {
      router.push("/portal/login");
      return;
    }

    portalApiClient.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    fetchUser();
  }, [router]);

  const fetchUser = async () => {
    try {
      const response = await portalApiClient.get("/portal/auth/me");
      setUser(response.data);
    } catch (error) {
      console.error("Failed to fetch user:", error);
      localStorage.removeItem("portal_access_token");
      router.push("/portal/login");
    }
  };

  const fetchTasks = async () => {
    if (!user) return;

    try {
      setIsLoading(true);
      const response = await portalApiClient.get("/portal/tasks", {
        params: { limit: 100 },
      });

      let taskList = response.data.tasks || [];

      // Sort: overdue first, then by due date
      const now = new Date();
      taskList.sort((a: Task, b: Task) => {
        const aOverdue = a.due_date && isAfter(now, parseISO(a.due_date)) && a.status !== "done";
        const bOverdue = b.due_date && isAfter(now, parseISO(b.due_date)) && b.status !== "done";
        if (aOverdue && !bOverdue) return -1;
        if (!aOverdue && bOverdue) return 1;
        if (a.due_date && b.due_date) return parseISO(a.due_date).getTime() - parseISO(b.due_date).getTime();
        return 0;
      });

      setTasks(taskList);
    } catch (error) {
      console.error("Failed to fetch tasks:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchTasks();
    }
  }, [user]);

  const formatDate = (dateStr: string) => {
    return format(parseISO(dateStr), "MMM d, yyyy");
  };

  // Group by status
  const todoTasks = tasks.filter(t => t.status === "todo");
  const inProgressTasks = tasks.filter(t => t.status === "in_progress");
  const doneTasks = tasks.filter(t => t.status === "done");

  const overdueCount = tasks.filter(t => {
    if (!t.due_date) return false;
    const now = new Date();
    return isAfter(now, parseISO(t.due_date)) && t.status !== "done" && t.status !== "cancelled";
  }).length;

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <>
      <Header title="My Tasks" />
      <div className="flex-1 p-6">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">My Tasks</h2>
            {overdueCount > 0 && (
              <span className="text-sm text-red-600 font-medium">
                ⚠️ {overdueCount} overdue
              </span>
            )}
          </div>

          {/* Stats */}
          <div className="grid gap-4 md:grid-cols-3 mb-6">
            <Card className="bg-gray-50">
              <CardContent className="p-4">
                <p className="text-sm text-gray-600">To Do</p>
                <p className="text-2xl font-bold">{todoTasks.length}</p>
              </CardContent>
            </Card>
            <Card className="bg-blue-50">
              <CardContent className="p-4">
                <p className="text-sm text-blue-600">In Progress</p>
                <p className="text-2xl font-bold">{inProgressTasks.length}</p>
              </CardContent>
            </Card>
            <Card className="bg-green-50">
              <CardContent className="p-4">
                <p className="text-sm text-green-600">Done</p>
                <p className="text-2xl font-bold">{doneTasks.length}</p>
              </CardContent>
            </Card>
          </div>

          {/* Tasks List */}
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : tasks.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <CheckSquare className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No tasks assigned</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {tasks.map((task) => {
                const isOverdue = task.due_date && isAfter(new Date(), parseISO(task.due_date)) && task.status !== "done" && task.status !== "cancelled";

                return (
                  <Card key={task.id} className={cn("hover:bg-accent/50 transition-colors", isOverdue && "border-red-300 bg-red-50")}>
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4 flex-1">
                          <div>
                            <h4 className={cn("font-medium", task.status === "done" && "line-through text-muted-foreground")}>
                              {task.title}
                            </h4>
                            {task.due_date && (
                              <div className="flex items-center gap-1 text-sm text-muted-foreground mt-1">
                                <Calendar className="h-3 w-3" />
                                <span className={cn(isOverdue && "text-red-600 font-medium")}>
                                  Due: {formatDate(task.due_date)}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={cn("px-2 py-1 rounded-full text-xs font-medium", statusColors[task.status])}>
                            {task.status.replace("_", " ")}
                          </span>
                          <span className={cn("px-2 py-1 rounded-full text-xs font-medium", priorityColors[task.priority])}>
                            {task.priority}
                          </span>
                          <Button variant="ghost" size="sm" onClick={() => setSelectedTask(task)}>
                            <Eye className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* View Task Dialog */}
      {selectedTask && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setSelectedTask(null)}>
          <Card className="w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <CheckSquare className="h-6 w-6 text-primary" />
                <h2 className="text-xl font-semibold">{selectedTask.title}</h2>
              </div>

              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <span className={cn("px-2 py-1 rounded-full text-xs font-medium", statusColors[selectedTask.status])}>
                    {selectedTask.status.replace("_", " ")}
                  </span>
                  <span className={cn("px-2 py-1 rounded-full text-xs font-medium", priorityColors[selectedTask.priority])}>
                    {selectedTask.priority}
                  </span>
                </div>

                {selectedTask.due_date && (
                  <div className="flex items-center gap-2 text-sm">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span className={cn(isAfter(new Date(), parseISO(selectedTask.due_date)) && selectedTask.status !== "done" && "text-red-600 font-medium")}>
                      Due: {formatDate(selectedTask.due_date)}
                    </span>
                  </div>
                )}

                {selectedTask.description && (
                  <div className="text-sm">
                    <span className="text-muted-foreground">Description:</span>
                    <p className="mt-1">{selectedTask.description}</p>
                  </div>
                )}
              </div>

              <div className="mt-6 flex justify-end">
                <Button variant="outline" onClick={() => setSelectedTask(null)}>Close</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}
