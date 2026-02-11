"use client";

import { useRouter } from "next/navigation";
import { Header } from "@/components/layouts/header";
import { useDashboardStats } from "@/lib/queries/office";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, UserCircle, CalendarCheck } from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const { data: officeStats, isLoading: loadingOffice, isError: officeError } = useDashboardStats();

  return (
    <>
      <Header title="Dashboard" />
      <div className="flex-1 p-6 space-y-8">
        <section>
          <h2 className="text-lg font-semibold mb-4">Office Overview</h2>
          <div className="grid gap-4 md:grid-cols-3">
            <Link href="/customers" className="block">
              <Card className="cursor-pointer hover:bg-accent/50 transition-colors h-full">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Customers</CardTitle>
                  <Users className="h-4 w-4 text-indigo-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {loadingOffice ? "-" : officeError ? "N/A" : officeStats?.total_customers ?? 0}
                  </div>
                </CardContent>
              </Card>
            </Link>
            <Link href="/employees" className="block">
              <Card className="cursor-pointer hover:bg-accent/50 transition-colors h-full">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Employees</CardTitle>
                  <UserCircle className="h-4 w-4 text-purple-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {loadingOffice ? "-" : officeError ? "N/A" : officeStats?.total_employees ?? 0}
                  </div>
                </CardContent>
              </Card>
            </Link>
            <Link href="/appointments" className="block">
              <Card className="cursor-pointer hover:bg-accent/50 transition-colors h-full">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Appointments</CardTitle>
                  <CalendarCheck className="h-4 w-4 text-teal-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {loadingOffice ? "-" : officeError ? "N/A" : officeStats?.active_appointments ?? 0}
                  </div>
                </CardContent>
              </Card>
            </Link>
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
          <div className="grid gap-4 md:grid-cols-3">
            <Link href="/tasks" className="block">
              <Card className="cursor-pointer hover:bg-accent/50 transition-colors h-full">
                <CardHeader>
                  <CardTitle className="text-base">Manage Tasks</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">View and update your tasks</p>
                </CardContent>
              </Card>
            </Link>
            <Link href="/calendar" className="block">
              <Card className="cursor-pointer hover:bg-accent/50 transition-colors h-full">
                <CardHeader>
                  <CardTitle className="text-base">Calendar</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">Schedule and manage events</p>
                </CardContent>
              </Card>
            </Link>
            <Link href="/appointments" className="block">
              <Card className="cursor-pointer hover:bg-accent/50 transition-colors h-full">
                <CardHeader>
                  <CardTitle className="text-base">Appointments</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">View upcoming appointments</p>
                </CardContent>
              </Card>
            </Link>
          </div>
        </section>

        <div className="grid gap-4 md:grid-cols-2">
          <Link href="/customers" className="block">
            <Card className="cursor-pointer hover:bg-accent/50 transition-colors h-full">
              <CardHeader>
                <CardTitle>Customers</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">Manage your customer database</p>
              </CardContent>
            </Card>
          </Link>
          <Link href="/employees" className="block">
            <Card className="cursor-pointer hover:bg-accent/50 transition-colors h-full">
              <CardHeader>
                <CardTitle>Employees</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">Manage your team members</p>
              </CardContent>
            </Card>
          </Link>
        </div>
      </div>
    </>
  );
}
