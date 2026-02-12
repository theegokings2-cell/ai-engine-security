"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layouts/header";
import { portalApiClient } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { CheckSquare, Plus, Clock, Calendar, ChevronLeft, ChevronRight, Edit, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { format, addMonths, subMonths, startOfMonth, endOfMonth, isSameMonth, parseISO, isAfter } from "date-fns";

interface PortalUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  permissions: string[];
}

interface Task {
  id: string;
  title: string;
  description?: string;
  status: "pending" | "in_progress" | "completed" | "cancelled";
  priority: "low" | "medium" | "high" | "urgent";
  due_date?: string;
  created_at: string;
}

const statusColors: Record<Task["status"], string> = {
  pending: "bg-gray-100 text-gray-800",
  in_progress: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
};

const priorityColors: Record<Task["priority"], string> = {
  low: "bg-gray-100 text-gray-600",
  medium: "bg-blue-100 text-blue-600",
  high: "bg-orange-100 text-orange-600",
  urgent: "bg-red-100 text-red-600",
};

export default function EmployeeTasksPage() {
  const router = useRouter();
  const [user, setUser] = useState<PortalUser | null>(null);
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [formData, setFormData] = useState({
    status: "pending" as Task["status"],
  });
  const [newTaskData, setNewTaskData] = useState({
    title: "",
    description: "",
    priority: "medium" as Task["priority"],
    due_date: "",
  });

  useEffect(() => {
    const token = localStorage.getItem("portal_access_token");
    if (!token) {
      router.push("/portal/employee-login");
      return;
    }

    portalApiClient.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    fetchUser();
  }, [router]);

  const fetchUser = async () => {
    try {
      const response = await portalApiClient.get("/portal/auth/employee-me");
      setUser(response.data);
    } catch (error) {
      console.error("Failed to fetch user:", error);
      localStorage.removeItem("portal_access_token");
      router.push("/portal/employee-login");
    }
  };

  const fetchTasks = async () => {
    if (!user) return;

    try {
      setIsLoading(true);
      const monthStart = startOfMonth(currentMonth);
      const monthEnd = endOfMonth(currentMonth);

      const response = await portalApiClient.get("/portal/tasks", {
        params: {
          skip: 0,
          limit: 100,
          status: statusFilter,
        },
      });

      let taskList = response.data.tasks || [];

      // Filter to show only active tasks + completed this month
      taskList = taskList.filter((task: Task) => {
        const isActive = task.status !== "completed" && task.status !== "cancelled";
        const isThisMonth = task.due_date ? isSameMonth(parseISO(task.due_date), currentMonth) : false;
        return isActive || isThisMonth;
      });

      // Sort: overdue first, then by due date
      const now = new Date();
      taskList.sort((a: Task, b: Task) => {
        const aOverdue = a.due_date && isAfter(parseISO(a.due_date), now) === false && a.status !== "completed";
        const bOverdue = b.due_date && isAfter(parseISO(b.due_date), now) === false && b.status !== "completed";
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
  }, [user, currentMonth, statusFilter]);

  const openEditDialog = (task: Task) => {
    setSelectedTask(task);
    setFormData({ status: task.status });
    setIsDialogOpen(true);
  };

  const openCreateDialog = () => {
    setNewTaskData({
      title: "",
      description: "",
      priority: "medium",
      due_date: "",
    });
    setIsCreateDialogOpen(true);
  };

  const handleUpdateStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask) return;

    try {
      await portalApiClient.put(`/portal/tasks/${selectedTask.id}/status`, {
        status: formData.status,
      });
      setIsDialogOpen(false);
      setSelectedTask(null);
      fetchTasks();
    } catch (error) {
      console.error("Failed to update task:", error);
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskData.title) return;

    try {
      await portalApiClient.post("/portal/tasks", {
        title: newTaskData.title,
        description: newTaskData.description,
        priority: newTaskData.priority,
        due_date: newTaskData.due_date || undefined,
      });
      setIsCreateDialogOpen(false);
      fetchTasks();
    } catch (error) {
      console.error("Failed to create task:", error);
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    if (!confirm("Are you sure you want to delete this task?")) return;

    try {
      await portalApiClient.delete(`/portal/tasks/${taskId}`);
      fetchTasks();
    } catch (error) {
      console.error("Failed to delete task:", error);
    }
  };

  const formatDate = (dateStr: string) => {
    return format(parseISO(dateStr), "MMM d, yyyy");
  };

  const formatDateTime = (dateStr: string) => {
    return format(parseISO(dateStr), "MMM d, h:mm a");
  };

  const activeCount = tasks.filter(t => t.status !== "completed" && t.status !== "cancelled").length;
  const overdueCount = tasks.filter(t => {
    if (!t.due_date) return false;
    const now = new Date();
    const isPast = isAfter(now, parseISO(t.due_date));
    return isPast && t.status !== "completed" && t.status !== "cancelled";
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
            <div className="flex items-center gap-4">
              <Button variant="outline" size="icon" onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <h2 className="text-xl font-semibold">{format(currentMonth, "MMMM yyyy")}</h2>
              <Button variant="outline" size="icon" onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={() => setCurrentMonth(new Date())}>Today</Button>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-sm">
                {overdueCount > 0 && (
                  <span className="text-red-600 font-medium mr-4">
                    ⚠️ {overdueCount} overdue
                  </span>
                )}
                <span className="text-muted-foreground">
                  {activeCount} active
                </span>
              </div>
              <Select value={statusFilter || "all"} onValueChange={(value) => setStatusFilter(value === "all" ? undefined : value)}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="All Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
              <Button onClick={openCreateDialog}>
                <Plus className="h-4 w-4 mr-2" />
                Add Task
              </Button>
            </div>
          </div>

          {/* Stats */}
          <div className="grid gap-4 md:grid-cols-4 mb-6">
            <Card className={cn("bg-blue-50 border-blue-200")}>
              <CardContent className="p-4">
                <p className="text-sm text-blue-600">Pending</p>
                <p className="text-2xl font-bold text-blue-700">
                  {tasks.filter(t => t.status === "pending").length}
                </p>
              </CardContent>
            </Card>
            <Card className={cn("bg-blue-50 border-blue-200")}>
              <CardContent className="p-4">
                <p className="text-sm text-blue-600">In Progress</p>
                <p className="text-2xl font-bold text-blue-700">
                  {tasks.filter(t => t.status === "in_progress").length}
                </p>
              </CardContent>
            </Card>
            <Card className={cn("bg-green-50 border-green-200")}>
              <CardContent className="p-4">
                <p className="text-sm text-green-600">Completed</p>
                <p className="text-2xl font-bold text-green-700">
                  {tasks.filter(t => t.status === "completed").length}
                </p>
              </CardContent>
            </Card>
            <Card className={cn("bg-red-50 border-red-200")}>
              <CardContent className="p-4">
                <p className="text-sm text-red-600">Overdue</p>
                <p className="text-2xl font-bold text-red-700">
                  {overdueCount}
                </p>
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
                <p className="text-muted-foreground mb-4">No tasks for {format(currentMonth, "MMMM yyyy")}</p>
                <Button onClick={openCreateDialog}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Your First Task
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {tasks.map((task) => {
                const isOverdue = task.due_date && isAfter(new Date(), parseISO(task.due_date)) && task.status !== "completed" && task.status !== "cancelled";
                
                return (
                  <Card key={task.id} className={cn("transition-colors", isOverdue && "border-red-300 bg-red-50")}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className={cn("font-medium", task.status === "completed" && "line-through text-muted-foreground")}>
                              {task.title}
                            </h3>
                            {isOverdue && (
                              <span className="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded-full">
                                Overdue
                              </span>
                            )}
                          </div>
                          {task.description && (
                            <p className="text-sm text-muted-foreground mb-2">{task.description}</p>
                          )}
                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            {task.due_date && (
                              <div className="flex items-center gap-1">
                                <Calendar className="h-4 w-4" />
                                <span className={cn(isOverdue && "text-red-600 font-medium")}>
                                  Due: {formatDate(task.due_date)}
                                </span>
                              </div>
                            )}
                            <div className="flex items-center gap-1">
                              <Clock className="h-4 w-4" />
                              <span>Created: {formatDate(task.created_at)}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={cn("px-2 py-1 rounded-full text-xs font-medium", statusColors[task.status])}>
                            {task.status.replace("_", " ")}
                          </span>
                          <span className={cn("px-2 py-1 rounded-full text-xs font-medium", priorityColors[task.priority])}>
                            {task.priority}
                          </span>
                          {task.status !== "completed" && task.status !== "cancelled" && (
                            <Button variant="ghost" size="icon" onClick={() => openEditDialog(task)}>
                              <Edit className="h-4 w-4" />
                            </Button>
                          )}
                          <Button variant="ghost" size="icon" onClick={() => handleDeleteTask(task.id)}>
                            <Trash2 className="h-4 w-4 text-red-500" />
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

      {/* Edit Task Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Update Task Status</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleUpdateStatus} className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Task</Label>
              <p className="text-sm font-medium">{selectedTask?.title}</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <Select value={formData.status} onValueChange={(value) => setFormData({ status: value as Task["status"] })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
              <Button type="submit">Update</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Create Task Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create New Task</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateTask} className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="title">Task Title *</Label>
              <Input
                id="title"
                placeholder="Enter task title"
                value={newTaskData.title}
                onChange={(e) => setNewTaskData({ ...newTaskData, title: e.target.value })}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Enter task description"
                value={newTaskData.description}
                onChange={(e) => setNewTaskData({ ...newTaskData, description: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="priority">Priority</Label>
              <Select value={newTaskData.priority} onValueChange={(value) => setNewTaskData({ ...newTaskData, priority: value as Task["priority"] })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select priority" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="urgent">Urgent</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="due_date">Due Date</Label>
              <Input
                id="due_date"
                type="datetime-local"
                value={newTaskData.due_date}
                onChange={(e) => setNewTaskData({ ...newTaskData, due_date: e.target.value })}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsCreateDialogOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={!newTaskData.title}>Create Task</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
