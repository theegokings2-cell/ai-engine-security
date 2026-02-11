"use client";

import { useState } from "react";
import { Header } from "@/components/layouts/header";
import { useTasks, useCreateTask, useUpdateTask, useDeleteTask } from "@/lib/queries/tasks";
import { Task, TaskFilters } from "@/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, Trash2, Edit, Search } from "lucide-react";
import { cn } from "@/lib/utils";

const statusColors: Record<Task["status"], string> = {
  pending: "bg-gray-100 text-gray-800",
  in_progress: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
};

const priorityColors: Record<Task["priority"], string> = {
  low: "bg-gray-100 text-gray-800",
  medium: "bg-yellow-100 text-yellow-800",
  high: "bg-orange-100 text-orange-800",
  urgent: "bg-red-100 text-red-800",
};

export default function TasksPage() {
  const [filters, setFilters] = useState<TaskFilters>({ page: 1, limit: 20 });
  const [searchQuery, setSearchQuery] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState("");

  const { data, isLoading } = useTasks(filters);
  const createTask = useCreateTask();
  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setFilters((f) => ({ ...f, search: searchQuery, page: 1 }));
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;

    await createTask.mutateAsync({
      title: newTaskTitle,
      status: "pending",
      priority: "medium",
    });
    setNewTaskTitle("");
    setIsCreateOpen(false);
  };

  const handleStatusChange = async (task: Task, newStatus: Task["status"]) => {
    await updateTask.mutateAsync({
      id: task.id,
      data: { status: newStatus },
    });
  };

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this task?")) {
      await deleteTask.mutateAsync(id);
    }
  };

  return (
    <>
      <Header title="Tasks" />
      <div className="flex-1 p-6">
        <div className="flex items-center justify-between mb-6">
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search tasks..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 w-64"
              />
            </div>
            <Button type="submit" variant="secondary">
              Search
            </Button>
          </form>
          <Button onClick={() => setIsCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Task
          </Button>
        </div>

        {isCreateOpen && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="text-lg">Create New Task</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreateTask} className="flex gap-2">
                <Input
                  placeholder="Task title..."
                  value={newTaskTitle}
                  onChange={(e) => setNewTaskTitle(e.target.value)}
                  className="flex-1"
                  autoFocus
                />
                <Button type="submit" disabled={createTask.isPending}>
                  {createTask.isPending ? "Creating..." : "Create"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsCreateOpen(false)}
                >
                  Cancel
                </Button>
              </form>
            </CardContent>
          </Card>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : (data?.data ?? data?.items ?? []).length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No tasks found.</p>
            <Button
              variant="link"
              className="mt-2"
              onClick={() => setIsCreateOpen(true)}
            >
              Create your first task
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {(data?.data ?? data?.items ?? []).map((task) => (
              <Card key={task.id}>
                <CardContent className="flex items-center justify-between p-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <h3 className="font-medium">{task.title}</h3>
                      <span
                        className={cn(
                          "px-2 py-1 rounded-full text-xs font-medium",
                          statusColors[task.status]
                        )}
                      >
                        {task.status.replace("_", " ")}
                      </span>
                      <span
                        className={cn(
                          "px-2 py-1 rounded-full text-xs font-medium",
                          priorityColors[task.priority]
                        )}
                      >
                        {task.priority}
                      </span>
                    </div>
                    {task.description && (
                      <p className="text-sm text-muted-foreground mt-1">
                        {task.description}
                      </p>
                    )}
                    {task.due_date && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Due: {new Date(task.due_date).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <select
                      value={task.status}
                      onChange={(e) =>
                        handleStatusChange(task, e.target.value as Task["status"])
                      }
                      className="text-sm border rounded px-2 py-1 bg-background"
                    >
                      <option value="pending">Pending</option>
                      <option value="in_progress">In Progress</option>
                      <option value="completed">Completed</option>
                      <option value="cancelled">Cancelled</option>
                    </select>
                    <Button variant="ghost" size="icon">
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(task.id)}
                      disabled={deleteTask.isPending}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {data && data.has_more && (
          <div className="flex justify-center gap-2 mt-6">
            <Button
              variant="outline"
              disabled={!filters.page || filters.page <= 1}
              onClick={() => setFilters((f) => ({ ...f, page: (f.page || 1) - 1 }))}
            >
              Previous
            </Button>
            <span className="flex items-center px-4 text-sm">
              Showing {(data.data ?? data.items ?? []).length} of {data.total}
            </span>
            <Button
              variant="outline"
              disabled={!data.has_more}
              onClick={() => setFilters((f) => ({ ...f, page: (f.page || 1) + 1 }))}
            >
              Next
            </Button>
          </div>
        )}
      </div>
    </>
  );
}
