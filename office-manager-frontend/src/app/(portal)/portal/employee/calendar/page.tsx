"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layouts/header";
import { portalApiClient } from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon, Clock, User, MapPin } from "lucide-react";
import { format, startOfMonth, endOfMonth, addMonths, subMonths, eachDayOfInterval, isSameMonth, isToday, parseISO, startOfWeek, endOfWeek, isSameDay } from "date-fns";

interface CalendarEvent {
  id: string;
  title: string;
  start_time: string;
  end_time: string;
  event_type: string;
  location?: string;
  description?: string;
  attendees?: string[];
  is_all_day: boolean;
  created_by_id: string;
  created_by_name?: string;
}

interface PortalUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  permissions: string[];
}

export default function EmployeeCalendarPage() {
  const router = useRouter();
  const [user, setUser] = useState<PortalUser | null>(null);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [isEventDialogOpen, setIsEventDialogOpen] = useState(false);

  // Check authentication
  useEffect(() => {
    const token = localStorage.getItem("portal_access_token");
    if (!token) {
      router.push("/portal/employee-login");
      return;
    }

    portalApiClient.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    fetchUser();
    fetchEvents();
  }, [router]);

  const fetchUser = async () => {
    try {
      const response = await portalApiClient.get("/portal/auth/employee-me");
      setUser(response.data);
    } catch (error) {
      console.error("Failed to fetch user:", error);
      localStorage.removeItem("portal_access_token");
      localStorage.removeItem("portal_refresh_token");
      router.push("/portal/employee-login");
    }
  };

  const fetchEvents = async () => {
    try {
      setIsLoading(true);
      const response = await portalApiClient.get("/calendar", {
        params: {
          start_date: startOfMonth(currentDate).toISOString(),
          end_date: endOfMonth(currentDate).toISOString(),
        },
      });
      setEvents(response.data || []);
    } catch (error) {
      console.error("Failed to fetch events:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchEvents();
    }
  }, [user, currentDate]);

  const getDaysInMonth = useCallback(() => {
    const monthStart = startOfMonth(currentDate);
    const monthEnd = endOfMonth(currentDate);
    const calendarStart = startOfWeek(monthStart);
    const calendarEnd = endOfWeek(monthEnd);
    return eachDayOfInterval({ start: calendarStart, end: calendarEnd });
  }, [currentDate]);

  const getEventsForDay = (day: Date) => {
    return events.filter((event) => {
      const eventDate = parseISO(event.start_time);
      return isSameDay(eventDate, day);
    });
  };

  const canViewEventDetails = (event: CalendarEvent) => {
    if (!user) return false;
    
    // Admins and managers can see all details
    if (user.role === "admin" || user.role === "manager") {
      return true;
    }
    
    // Check if user is the creator or attendee
    if (event.created_by_id === user.id) {
      return true;
    }
    
    if (event.attendees?.includes(user.id)) {
      return true;
    }
    
    return false;
  };

  const handleEventClick = (event: CalendarEvent) => {
    setSelectedEvent(event);
    setIsEventDialogOpen(true);
  };

  const formatEventTime = (start: string, end: string) => {
    const startDate = parseISO(start);
    const endDate = parseISO(end);
    return `${format(startDate, "h:mm a")} - ${format(endDate, "h:mm a")}`;
  };

  const getEventTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      meeting: "bg-blue-100 text-blue-800 border-blue-200",
      call: "bg-green-100 text-green-800 border-green-200",
      reminder: "bg-yellow-100 text-yellow-800 border-yellow-200",
      blocked: "bg-gray-100 text-gray-800 border-gray-200",
      appointment: "bg-purple-100 text-purple-800 border-purple-200",
    };
    return colors[type] || "bg-gray-100 text-gray-800 border-gray-200";
  };

  const days = getDaysInMonth();
  const weekDays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <>
      <Header title="My Calendar" />
      <div className="flex-1 p-6">
        <div className="max-w-7xl mx-auto">
          {/* Header Controls */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <Button variant="outline" size="icon" onClick={() => setCurrentDate(subMonths(currentDate, 1))}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <h2 className="text-2xl font-semibold">{format(currentDate, "MMMM yyyy")}</h2>
              <Button variant="outline" size="icon" onClick={() => setCurrentDate(addMonths(currentDate, 1))}>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={() => setCurrentDate(new Date())}>Today</Button>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="bg-blue-50">
                <CalendarIcon className="h-3 w-3 mr-1" />
                Meetings
              </Badge>
              <Badge variant="outline" className="bg-green-50">
                <Clock className="h-3 w-3 mr-1" />
                Calls
              </Badge>
              <Badge variant="outline" className="bg-gray-50">
                <User className="h-3 w-3 mr-1" />
                Private
              </Badge>
            </div>
          </div>

          {/* Calendar Grid */}
          <Card>
            <CardContent className="p-0">
              {/* Week Day Headers */}
              <div className="grid grid-cols-7 border-b">
                {weekDays.map((day) => (
                  <div key={day} className="p-3 text-center text-sm font-medium text-muted-foreground bg-gray-50">
                    {day}
                  </div>
                ))}
              </div>

              {/* Calendar Days */}
              <div className="grid grid-cols-7">
                {days.map((day, index) => {
                  const dayEvents = getEventsForDay(day);
                  const isCurrentMonth = isSameMonth(day, currentDate);
                  const isTodayDate = isToday(day);

                  return (
                    <div
                      key={index}
                      className={`min-h-[120px] border-b border-r p-2 ${
                        !isCurrentMonth ? "bg-gray-50" : ""
                      } ${isTodayDate ? "bg-blue-50/50" : ""}`}
                    >
                      <div className={`text-sm font-medium mb-2 ${
                        isTodayDate 
                          ? "bg-primary text-primary-foreground w-7 h-7 rounded-full flex items-center justify-center" 
                          : isCurrentMonth ? "text-foreground" : "text-muted-foreground"
                      }`}>
                        {format(day, "d")}
                      </div>
                      
                      <div className="space-y-1">
                        {dayEvents.slice(0, 3).map((event) => {
                          const showDetails = canViewEventDetails(event);
                          
                          return (
                            <button
                              key={event.id}
                              onClick={() => handleEventClick(event)}
                              className={`w-full text-left text-xs px-2 py-1 rounded border truncate ${
                                event.event_type === "meeting" 
                                  ? "bg-blue-50 border-blue-200 text-blue-800 hover:bg-blue-100"
                                  : event.event_type === "call"
                                  ? "bg-green-50 border-green-200 text-green-800 hover:bg-green-100"
                                  : event.event_type === "blocked"
                                  ? "bg-gray-100 border-gray-200 text-gray-600"
                                  : "bg-purple-50 border-purple-200 text-purple-800 hover:bg-purple-100"
                              }`}
                            >
                              {event.is_all_day ? (
                                <span className="flex items-center gap-1">
                                  <CalendarIcon className="h-3 w-3" />
                                  {showDetails ? event.title : "Busy"}
                                </span>
                              ) : (
                                <span className="flex items-center gap-1">
                                  <Clock className="h-3 w-3" />
                                  {format(parseISO(event.start_time), "h:mm")} {showDetails ? event.title : ""}
                                </span>
                              )}
                            </button>
                          );
                        })}
                        {dayEvents.length > 3 && (
                          <button
                            onClick={() => {
                              // Show all events for this day - could expand to modal
                            }}
                            className="text-xs text-muted-foreground hover:text-foreground w-full text-center"
                          >
                            +{dayEvents.length - 3} more
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Event Count */}
          <div className="mt-4 text-sm text-muted-foreground text-center">
            Showing {events.length} events for {format(currentDate, "MMMM yyyy")}
          </div>
        </div>
      </div>

      {/* Event Detail Dialog */}
      <Dialog open={isEventDialogOpen} onOpenChange={setIsEventDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CalendarIcon className="h-5 w-5" />
              {selectedEvent?.title || "Event Details"}
            </DialogTitle>
          </DialogHeader>
          {selectedEvent && (
            <div className="space-y-4 py-4">
              {/* Privacy Check */}
              {!canViewEventDetails(selectedEvent) && (
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-sm text-yellow-800">
                    <strong>Private Event</strong>
                    <br />
                    You don't have permission to view full details of this event.
                  </p>
                </div>
              )}

              {/* Event Type Badge */}
              <div className="flex items-center gap-2">
                <Badge className={getEventTypeColor(selectedEvent.event_type)}>
                  {selectedEvent.event_type.charAt(0).toUpperCase() + selectedEvent.event_type.slice(1)}
                </Badge>
                {selectedEvent.is_all_day && (
                  <Badge variant="outline">All Day</Badge>
                )}
              </div>

              {/* Time */}
              <div className="flex items-center gap-2 text-sm">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span>
                  {format(parseISO(selectedEvent.start_time), "EEEE, MMMM d, yyyy")}
                  <br />
                  {!selectedEvent.is_all_day && formatEventTime(selectedEvent.start_time, selectedEvent.end_time)}
                </span>
              </div>

              {/* Location */}
              {selectedEvent.location && canViewEventDetails(selectedEvent) && (
                <div className="flex items-center gap-2 text-sm">
                  <MapPin className="h-4 w-4 text-muted-foreground" />
                  <span>{selectedEvent.location}</span>
                </div>
              )}

              {/* Description */}
              {selectedEvent.description && canViewEventDetails(selectedEvent) && (
                <div className="text-sm">
                  <span className="text-muted-foreground">Description:</span>
                  <p className="mt-1">{selectedEvent.description}</p>
                </div>
              )}

              {/* Attendees */}
              {selectedEvent.attendees && selectedEvent.attendees.length > 0 && canViewEventDetails(selectedEvent) && (
                <div className="flex items-center gap-2 text-sm">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <span>{selectedEvent.attendees.length} attendee(s)</span>
                </div>
              )}

              {/* Created By */}
              {selectedEvent.created_by_name && (
                <div className="text-xs text-muted-foreground pt-2 border-t">
                  Created by: {selectedEvent.created_by_name}
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEventDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// Import Dialog components
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
