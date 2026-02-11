"use client";

import Link from "next/link";
import { Header } from "@/components/layouts/header";
import { useTaskStatistics, useTasks } from "@/lib/queries/tasks";
import { useDashboardStats, useUpcomingAppointments, Appointment } from "@/lib/queries/office";
import { useTodayEvents, CalendarEvent } from "@/lib/queries/calendar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  CheckSquare,
  Clock,
  AlertTriangle,
  CheckCircle,
  Users,
  UserCircle,
  CalendarCheck,
  DoorOpen,
  FileText,
  Settings,
  CalendarDays,
  ArrowRight,
  StickyNote,
} from "lucide-react";
import { Task } from "@/types";
import { format } from "date-fns";

const priorityColors: Record<string, string> = {
  urgent: "text-red-600 bg-red-50",
  high: "text-orange-600 bg-orange-50",
  medium: "text-yellow-600 bg-yellow-50",
  low: "text-slate-600 bg-slate-50",
};

const statusColors: Record<string, string> = {
  pending: "text-slate-500",
  in_progress: "text-blue-500",
  completed: "text-green-500",
  cancelled: "text-gray-400",
};

export default function DashboardPage() {
  const { data: taskStats, isLoading: loadingTasks, isError: taskError } = useTaskStatistics();
  const { data: officeStats, isLoading: loadingOffice, isError: officeError } = useDashboardStats();
  const { data: recentTasksData } = useTasks({ limit: 5 });
  const { data: todayEvents } = useTodayEvents();
  const { data: upcomingAppointments } = useUpcomingAppointments(5);

  const recentTasks: Task[] = recentTasksData?.data ?? recentTasksData?.items ?? [];
  const appointments: Appointment[] = upcomingAppointments ?? [];

  // /calendar/today returns { events_by_hour: { "16": [...], "17": [...] }, total_count }
  // Flatten the nested structure into a sorted array
  const rawEvents = todayEvents as any;
  const calendarEvents: CalendarEvent[] = (() => {
    if (!rawEvents) return [];
    if (Array.isArray(rawEvents)) return rawEvents;
    if (rawEvents.events_by_hour) {
      const flattened: CalendarEvent[] = [];
      for (const events of Object.values(rawEvents.events_by_hour)) {
        if (Array.isArray(events)) flattened.push(...(events as CalendarEvent[]));
      }
      return flattened.sort((a, b) =>
        new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
      );
    }
    return rawEvents?.data ?? rawEvents?.items ?? [];
  })();

  const officeStatCards = [
    {
      title: "Total Customers",
      value: officeStats?.total_customers ?? 0,
      icon: Users,
      color: "text-indigo-500",
      bg: "bg-indigo-50",
      href: "/customers",
      description: "View all customers",
    },
    {
      title: "Employees",
      value: officeStats?.total_employees ?? 0,
      icon: UserCircle,
      color: "text-purple-500",
      bg: "bg-purple-50",
      href: "/employees",
      description: "Manage your team",
    },
    {
      title: "Active Appointments",
      value: officeStats?.active_appointments ?? 0,
      icon: CalendarCheck,
      color: "text-teal-500",
      bg: "bg-teal-50",
      href: "/appointments",
      description: "View appointments",
    },
    {
      title: "Room Bookings Today",
      value: officeStats?.room_bookings_today ?? 0,
      icon: DoorOpen,
      color: "text-emerald-500",
      bg: "bg-emerald-50",
      href: "/settings",
      description: "Manage rooms",
    },
  ];

  const taskStatCards = [
    {
      title: "Total Tasks",
      value: taskStats?.total ?? 0,
      icon: CheckSquare,
      color: "text-blue-500",
      bg: "bg-blue-50",
      href: "/tasks",
      description: "View all tasks",
    },
    {
      title: "In Progress",
      value: taskStats?.in_progress ?? 0,
      icon: Clock,
      color: "text-yellow-500",
      bg: "bg-yellow-50",
      href: "/tasks",
      description: "Currently active",
    },
    {
      title: "Completed",
      value: taskStats?.completed ?? 0,
      icon: CheckCircle,
      color: "text-green-500",
      bg: "bg-green-50",
      href: "/tasks",
      description: "Finished tasks",
    },
    {
      title: "Overdue",
      value: taskStats?.overdue ?? 0,
      icon: AlertTriangle,
      color: "text-red-500",
      bg: "bg-red-50",
      href: "/tasks",
      description: "Needs attention",
    },
  ];

  const quickLinks = [
    { title: "Calendar", icon: CalendarDays, href: "/calendar", color: "text-blue-500", bg: "bg-blue-50", description: "Schedule & events" },
    { title: "Notes", icon: StickyNote, href: "/notes", color: "text-amber-500", bg: "bg-amber-50", description: "Your notes" },
    { title: "Appointments", icon: Clock, href: "/appointments", color: "text-teal-500", bg: "bg-teal-50", description: "Book & manage" },
    { title: "Settings", icon: Settings, href: "/settings", color: "text-slate-500", bg: "bg-slate-50", description: "Configuration" },
  ];

  return (
    <>
      <Header title="Dashboard" />
      <div className="flex-1 p-6 space-y-8">
        {/* Office Overview */}
        <section>
          <h2 className="text-lg font-semibold mb-4">Office Overview</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {officeStatCards.map((stat) => (
              <Link key={stat.title} href={stat.href} className="block group">
                <Card className="cursor-pointer transition-all hover:shadow-md hover:border-primary/30 h-full">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">
                      {stat.title}
                    </CardTitle>
                    <div className={`p-2 rounded-lg ${stat.bg}`}>
                      <stat.icon className={`h-4 w-4 ${stat.color}`} />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {loadingOffice ? "-" : officeError ? "N/A" : stat.value}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                      {stat.description}
                      <ArrowRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </section>

        {/* Task Statistics */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Task Statistics</h2>
            <Link href="/tasks" className="text-sm text-primary hover:underline flex items-center gap-1">
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {taskStatCards.map((stat) => (
              <Link key={stat.title} href={stat.href} className="block group">
                <Card className="cursor-pointer transition-all hover:shadow-md hover:border-primary/30 h-full">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">
                      {stat.title}
                    </CardTitle>
                    <div className={`p-2 rounded-lg ${stat.bg}`}>
                      <stat.icon className={`h-4 w-4 ${stat.color}`} />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {loadingTasks ? "-" : taskError ? "N/A" : stat.value}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                      {stat.description}
                      <ArrowRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </section>

        {/* Quick Links */}
        <section>
          <h2 className="text-lg font-semibold mb-4">Quick Links</h2>
          <div className="grid gap-4 md:grid-cols-4">
            {quickLinks.map((link) => (
              <Link key={link.title} href={link.href} className="block group">
                <Card className="cursor-pointer transition-all hover:shadow-md hover:border-primary/30 h-full">
                  <CardContent className="flex items-center gap-4 p-4">
                    <div className={`p-3 rounded-lg ${link.bg}`}>
                      <link.icon className={`h-5 w-5 ${link.color}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{link.title}</p>
                      <p className="text-xs text-muted-foreground">{link.description}</p>
                    </div>
                    <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </section>

        {/* Today's Schedule & Recent Tasks */}
        <div className="grid gap-4 md:grid-cols-2">
          <Link href="/calendar" className="block group">
            <Card className="cursor-pointer transition-all hover:shadow-md hover:border-primary/30 h-full">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <CalendarDays className="h-5 w-5 text-teal-500" />
                  Today&apos;s Schedule
                </CardTitle>
                <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </CardHeader>
              <CardContent>
                {calendarEvents.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No events today. Click to view your calendar.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {calendarEvents.slice(0, 5).map((event) => (
                      <div key={event.id} className="flex items-center gap-3">
                        <div className={`w-1 h-8 rounded-full shrink-0 ${
                          event.event_type === "meeting" ? "bg-blue-400" :
                          event.event_type === "call" ? "bg-green-400" :
                          event.event_type === "reminder" ? "bg-yellow-400" :
                          "bg-red-400"
                        }`} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{event.title}</p>
                          <p className="text-xs text-muted-foreground">
                            {event.all_day === true || event.all_day === "Y" as any
                              ? "All day"
                              : `${format(new Date(event.start_time), "h:mm a")} - ${format(new Date(event.end_time), "h:mm a")}`}
                          </p>
                        </div>
                        {event.location && (
                          <span className="text-xs text-muted-foreground shrink-0">{event.location}</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </Link>

          <Link href="/tasks" className="block group">
            <Card className="cursor-pointer transition-all hover:shadow-md hover:border-primary/30 h-full">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <CheckSquare className="h-5 w-5 text-blue-500" />
                  Recent Tasks
                </CardTitle>
                <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </CardHeader>
              <CardContent>
                {recentTasks.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No tasks yet. Click to create your first task.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {recentTasks.slice(0, 5).map((task) => (
                      <div key={task.id} className="flex items-center justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{task.title}</p>
                          <p className="text-xs text-muted-foreground">
                            {task.due_date
                              ? `Due ${format(new Date(task.due_date), "MMM d")}`
                              : "No due date"}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className={`text-xs px-2 py-0.5 rounded-full ${priorityColors[task.priority] ?? ""}`}>
                            {task.priority}
                          </span>
                          <span className={`text-xs ${statusColors[task.status] ?? ""}`}>
                            {task.status.replace("_", " ")}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </Link>
        </div>

        {/* Upcoming Appointments */}
        {appointments.length > 0 && (
          <Link href="/appointments" className="block group">
            <Card className="cursor-pointer transition-all hover:shadow-md hover:border-primary/30">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <CalendarCheck className="h-5 w-5 text-teal-500" />
                  Upcoming Appointments
                </CardTitle>
                <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                  {appointments.slice(0, 6).map((apt) => (
                    <div key={apt.id} className="flex items-center gap-3 p-2 rounded-lg bg-muted/50">
                      <div className="w-1 h-8 rounded-full bg-teal-400 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{apt.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {format(new Date(apt.start_time), "MMM d, h:mm a")}
                        </p>
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${
                        apt.status === "confirmed" ? "bg-green-100 text-green-800" :
                        apt.status === "scheduled" ? "bg-blue-100 text-blue-800" :
                        "bg-gray-100 text-gray-800"
                      }`}>
                        {apt.status}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </Link>
        )}
      </div>
    </>
  );
}
