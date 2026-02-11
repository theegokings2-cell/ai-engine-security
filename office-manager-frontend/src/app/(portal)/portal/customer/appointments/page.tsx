"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layouts/header";
import { portalApiClient } from "@/lib/api/client";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Calendar, Clock, MapPin, Eye } from "lucide-react";
import { format, addMonths, subMonths, startOfMonth, endOfMonth, parseISO } from "date-fns";
import { cn } from "@/lib/utils";

interface PortalUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface Appointment {
  id: string;
  title: string;
  description?: string;
  customer_id?: string;
  start_time: string;
  end_time: string;
  status: "scheduled" | "confirmed" | "completed" | "cancelled";
  location?: string;
  notes?: string;
}

const statusColors: Record<Appointment["status"], string> = {
  scheduled: "bg-blue-100 text-blue-800",
  confirmed: "bg-green-100 text-green-800",
  completed: "bg-gray-100 text-gray-800",
  cancelled: "bg-red-100 text-red-800",
};

export default function CustomerAppointmentsPage() {
  const router = useRouter();
  const [user, setUser] = useState<PortalUser | null>(null);
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedAppointment, setSelectedAppointment] = useState<Appointment | null>(null);

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

  const fetchAppointments = async () => {
    if (!user) return;

    try {
      setIsLoading(true);
      const monthStart = startOfMonth(currentMonth);
      const monthEnd = endOfMonth(currentMonth);

      const response = await portalApiClient.get("/portal/appointments", {
        params: {
          skip: 0,
          limit: 100,
          start_date: monthStart.toISOString(),
          end_date: monthEnd.toISOString(),
        },
      });

      // Filter for current month and sort by date
      let apts = response.data.appointments || [];
      apts = apts
        .filter((apt: Appointment) => {
          const aptDate = parseISO(apt.start_time);
          return aptDate >= monthStart && aptDate <= monthEnd;
        })
        .sort((a: Appointment, b: Appointment) => 
          new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
        );

      setAppointments(apts);
    } catch (error) {
      console.error("Failed to fetch appointments:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchAppointments();
    }
  }, [user, currentMonth]);

  const formatTime = (dateStr: string) => {
    return format(parseISO(dateStr), "h:mm a");
  };

  const formatDate = (dateStr: string) => {
    return format(parseISO(dateStr), "EEE, MMM d");
  };

  // Group appointments by date
  const appointmentsByDate = appointments.reduce((acc, apt) => {
    const date = format(parseISO(apt.start_time), "yyyy-MM-dd");
    if (!acc[date]) acc[date] = [];
    acc[date].push(apt);
    return acc;
  }, {} as Record<string, Appointment[]>);

  const sortedDates = Object.keys(appointmentsByDate).sort();

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <>
      <Header title="My Appointments" />
      <div className="flex-1 p-6">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <Button variant="outline" size="icon" onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}>
                <Calendar className="h-4 w-4" />
              </Button>
              <h2 className="text-xl font-semibold">{format(currentMonth, "MMMM yyyy")}</h2>
              <Button variant="outline" size="icon" onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}>
                <Calendar className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={() => setCurrentMonth(new Date())}>Today</Button>
            </div>
          </div>

          {/* Appointments List */}
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : sortedDates.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Calendar className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No appointments for {format(currentMonth, "MMMM yyyy")}</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-6">
              {sortedDates.map((date) => (
                <div key={date}>
                  <h3 className="text-sm font-medium text-muted-foreground mb-3">
                    {format(parseISO(date), "EEEE, MMMM d")}
                  </h3>
                  <div className="space-y-3">
                    {appointmentsByDate[date].map((apt) => (
                      <Card key={apt.id} className="hover:bg-accent/50 transition-colors">
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                              <div className="text-center">
                                <p className="text-lg font-semibold">{formatTime(apt.start_time)}</p>
                                <p className="text-xs text-muted-foreground">to {formatTime(apt.end_time)}</p>
                              </div>
                              <div>
                                <div className="flex items-center gap-2 mb-1">
                                  <h4 className="font-medium">{apt.title}</h4>
                                  <span className={cn("px-2 py-0.5 rounded-full text-xs font-medium", statusColors[apt.status])}>
                                    {apt.status}
                                  </span>
                                </div>
                                {apt.location && (
                                  <div className="flex items-center gap-1 text-sm text-muted-foreground">
                                    <MapPin className="h-3 w-3" />
                                    <span>{apt.location}</span>
                                  </div>
                                )}
                              </div>
                            </div>
                            <Button variant="ghost" size="sm" onClick={() => setSelectedAppointment(apt)}>
                              <Eye className="h-4 w-4" />
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* View Appointment Dialog */}
      {selectedAppointment && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setSelectedAppointment(null)}>
          <Card className="w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <Calendar className="h-6 w-6 text-primary" />
                <h2 className="text-xl font-semibold">{selectedAppointment.title}</h2>
              </div>

              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <span className={cn("px-2 py-1 rounded-full text-xs font-medium", statusColors[selectedAppointment.status])}>
                    {selectedAppointment.status}
                  </span>
                </div>

                <div className="flex items-center gap-2 text-sm">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span>
                    {formatDate(selectedAppointment.start_time)} {formatTime(selectedAppointment.start_time)} - {formatTime(selectedAppointment.end_time)}
                  </span>
                </div>

                {selectedAppointment.location && (
                  <div className="flex items-center gap-2 text-sm">
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                    <span>{selectedAppointment.location}</span>
                  </div>
                )}

                {selectedAppointment.description && (
                  <div className="text-sm">
                    <span className="text-muted-foreground">Description:</span>
                    <p className="mt-1">{selectedAppointment.description}</p>
                  </div>
                )}

                {selectedAppointment.notes && (
                  <div className="text-sm">
                    <span className="text-muted-foreground">Notes:</span>
                    <p className="mt-1 p-2 bg-muted rounded">{selectedAppointment.notes}</p>
                  </div>
                )}
              </div>

              <div className="mt-6 flex justify-end">
                <Button variant="outline" onClick={() => setSelectedAppointment(null)}>Close</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}
