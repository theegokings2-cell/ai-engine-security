"use client";

import { useState, useCallback } from "react";
import { Header } from "@/components/layouts/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ChevronLeft, ChevronRight, Plus, Loader2, Globe } from "lucide-react";
import { format, addMonths, subMonths, startOfWeek, endOfWeek, parseISO, startOfDay, endOfDay } from "date-fns";
import { enUS } from "date-fns/locale";
import { Calendar, dateFnsLocalizer, Views } from "react-big-calendar";
import withDragAndDrop from "react-big-calendar/lib/addons/dragAndDrop";
import "react-big-calendar/lib/css/react-big-calendar.css";
import "react-big-calendar/lib/addons/dragAndDrop/styles.css";
import { useEvents, useCreateEvent, useUpdateEvent, useDeleteEvent, CalendarEvent } from "@/lib/queries/calendar";
import { useAuthStore } from "@/lib/stores/auth-store";
import { formatTimeInTimezone, getTimezoneOffset } from "@/lib/timezone";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

const locales = {
  "en-US": enUS,
};

const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales,
});

function parse(dateStr: string, str: string) {
  return new Date(dateStr);
}

function getDay(date: Date) {
  return date.getDay();
}

const DnDCalendar = withDragAndDrop<CalendarEvent & { start: Date; end: Date }>(Calendar as any);

export default function CalendarPage() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [view, setView] = useState<"month" | "week" | "day" | "agenda">("month");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [isViewOpen, setIsViewOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const { toast } = useToast();

  // Form state
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [eventType, setEventType] = useState<"meeting" | "call" | "reminder" | "blocked">("meeting");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [location, setLocation] = useState("");

  // Fetch events (12 month range for full year visibility)
  const { data: events = [], isLoading } = useEvents({
    start_date: startOfDay(currentDate).toISOString(),
    end_date: endOfDay(addMonths(currentDate, 12)).toISOString(),
  });

  const createEvent = useCreateEvent();
  const updateEvent = useUpdateEvent();
  const deleteEvent = useDeleteEvent();

  // Convert to react-big-calendar format
  const calendarEvents = events.map((event) => ({
    ...event,
    start: parseISO(event.start_time),
    end: parseISO(event.end_time),
    title: event.title,
  }));

  const eventStyleGetter = (event: CalendarEvent) => {
    const colors: Record<string, string> = {
      meeting: "#3b82f6",
      call: "#22c55e",
      reminder: "#eab308",
      blocked: "#ef4444",
    };
    return {
      style: {
        backgroundColor: colors[event.event_type] || "#3b82f6",
        borderRadius: "4px",
        opacity: 0.9,
        color: "white",
        border: "none",
        display: "block",
      },
    };
  };

  const handleSelectEvent = useCallback((event: CalendarEvent) => {
    setSelectedEvent(event);
    setIsViewOpen(true);
  }, []);

  const handleSelectSlot = useCallback(({ start }: { start: Date; end: Date }) => {
    // Default to 30 minute meetings
    const end = new Date(start.getTime() + 30 * 60 * 1000);
    setStartTime(format(start, "yyyy-MM-dd'T'HH:mm"));
    setEndTime(format(end, "yyyy-MM-dd'T'HH:mm"));
    setIsCreateOpen(true);
  }, []);

  const handleEventDrop = useCallback(async ({ event, start, end }: { event: any; start: any; end: any }) => {
    try {
      await updateEvent.mutateAsync({
        id: event.id,
        data: {
          start_time: start.toISOString(),
          end_time: end.toISOString(),
        },
      });
      toast({ title: "Success", description: "Event moved successfully" });
    } catch (error) {
      toast({ title: "Error", description: "Failed to move event", variant: "destructive" });
    }
  }, [updateEvent, toast]);

  const handleCreateEvent = async () => {
    if (!title || !startTime || !endTime) {
      toast({ title: "Error", description: "Please fill in all required fields", variant: "destructive" });
      return;
    }

    try {
      await createEvent.mutateAsync({
        title,
        description: description || undefined,
        event_type: eventType,
        start_time: new Date(startTime).toISOString(),
        end_time: new Date(endTime).toISOString(),
        location: location || undefined,
      });

      toast({ title: "Success", description: "Event created successfully" });
      setIsCreateOpen(false);
      resetForm();
    } catch (error) {
      toast({ title: "Error", description: "Failed to create event", variant: "destructive" });
    }
  };

  const handleUpdateEvent = async () => {
    if (!selectedEvent || !title || !startTime || !endTime) return;

    try {
      await updateEvent.mutateAsync({
        id: selectedEvent.id,
        data: {
          title,
          description: description || undefined,
          event_type: eventType,
          start_time: new Date(startTime).toISOString(),
          end_time: new Date(endTime).toISOString(),
          location: location || undefined,
        },
      });

      toast({ title: "Success", description: "Event updated successfully" });
      setIsEditOpen(false);
      setIsViewOpen(false);
    } catch (error) {
      toast({ title: "Error", description: "Failed to update event", variant: "destructive" });
    }
  };

  const handleDeleteEvent = async () => {
    if (!selectedEvent) return;

    try {
      await deleteEvent.mutateAsync(selectedEvent.id);
      toast({ title: "Success", description: "Event deleted successfully" });
      setIsDeleteOpen(false);
      setIsViewOpen(false);
      setSelectedEvent(null);
    } catch (error) {
      toast({ title: "Error", description: "Failed to delete event", variant: "destructive" });
    }
  };

  const openEditDialog = () => {
    if (!selectedEvent) return;
    setTitle(selectedEvent.title);
    setDescription(selectedEvent.description || "");
    setEventType(selectedEvent.event_type);
    setStartTime(format(parseISO(selectedEvent.start_time), "yyyy-MM-dd'T'HH:mm"));
    setEndTime(format(parseISO(selectedEvent.end_time), "yyyy-MM-dd'T'HH:mm"));
    setLocation(selectedEvent.location || "");
    setIsEditOpen(true);
    setIsViewOpen(false);
  };

  const resetForm = () => {
    setTitle("");
    setDescription("");
    setEventType("meeting");
    setStartTime("");
    setEndTime("");
    setLocation("");
  };

  return (
    <>
      <Header title="Calendar" />
      <div className="flex-1 p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Button variant="outline" size="icon" onClick={() => setCurrentDate(subMonths(currentDate, 1))}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <h2 className="text-xl font-semibold">{format(currentDate, "MMMM yyyy")}</h2>
            <Button variant="outline" size="icon" onClick={() => setCurrentDate(addMonths(currentDate, 1))}>
              <ChevronRight className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="sm" onClick={() => setCurrentDate(new Date())}>
              Today
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <Select value={view} onValueChange={(v: any) => setView(v)}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="month">Month</SelectItem>
                <SelectItem value="week">Week</SelectItem>
                <SelectItem value="day">Day</SelectItem>
                <SelectItem value="agenda">Agenda</SelectItem>
              </SelectContent>
            </Select>
            <Button
              onClick={() => {
                const now = new Date();
                const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), now.getHours(), 0, 0, 0);
                const end = new Date(start.getTime() + 30 * 60 * 1000);
                setStartTime(format(start, "yyyy-MM-dd'T'HH:mm"));
                setEndTime(format(end, "yyyy-MM-dd'T'HH:mm"));
                setIsCreateOpen(true);
              }}
            >
              <Plus className="h-4 w-4 mr-2" />
              New Event
            </Button>
          </div>
        </div>

        <Card>
          <CardContent className="p-4">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin" />
              </div>
            ) : (
              <div className="h-[600px]">
                <DnDCalendar
                  localizer={localizer}
                  events={calendarEvents}
                  defaultView={view}
                  view={view}
                  onView={setView as any}
                  date={currentDate}
                  onNavigate={setCurrentDate}
                  selectable
                  resizable
                  draggableAccessor={() => true}
                  onSelectEvent={handleSelectEvent as any}
                  onSelectSlot={handleSelectSlot as any}
                  onEventDrop={handleEventDrop as any}
                  eventPropGetter={eventStyleGetter as any}
                  step={30}
                  min={new Date(0, 0, 0, 6, 0, 0)}
                  max={new Date(0, 0, 0, 22, 0, 0)}
                  className="rbc-calendar"
                />
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Create Event Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={(open) => { setIsCreateOpen(open); if (!open) resetForm(); }}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Create New Event</DialogTitle>
            <DialogDescription>Add a new event to your calendar.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="title">Title *</Label>
              <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Event title" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="event-type">Event Type</Label>
              <Select value={eventType} onValueChange={(v: any) => setEventType(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="meeting">Meeting</SelectItem>
                  <SelectItem value="call">Call</SelectItem>
                  <SelectItem value="reminder">Reminder</SelectItem>
                  <SelectItem value="blocked">Blocked Time</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="start-time">Start Time *</Label>
                <Input id="start-time" type="datetime-local" value={startTime} onChange={(e) => setStartTime(e.target.value)} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="end-time">End Time *</Label>
                <Input id="end-time" type="datetime-local" value={endTime} onChange={(e) => setEndTime(e.target.value)} />
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="location">Location</Label>
              <Input id="location" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Meeting room or address" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="description">Description</Label>
              <Textarea id="description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Event details..." rows={3} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
            <Button onClick={handleCreateEvent} disabled={createEvent.isPending}>
              {createEvent.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Event
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Event Dialog */}
      <Dialog open={isViewOpen} onOpenChange={setIsViewOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>{selectedEvent?.title}</DialogTitle>
            <DialogDescription>Event details</DialogDescription>
          </DialogHeader>
          {selectedEvent && (
            <div className="grid gap-4 py-4">
              <div className="flex items-center gap-2">
                <span className={cn(
                  "px-2 py-1 rounded-full text-xs font-medium",
                  selectedEvent.event_type === "meeting" && "bg-blue-100 text-blue-800",
                  selectedEvent.event_type === "call" && "bg-green-100 text-green-800",
                  selectedEvent.event_type === "reminder" && "bg-yellow-100 text-yellow-800",
                  selectedEvent.event_type === "blocked" && "bg-red-100 text-red-800"
                )}>
                  {selectedEvent.event_type}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Start:</span>
                  <div className="font-medium">{format(parseISO(selectedEvent.start_time), "MMM d, yyyy h:mm a")}</div>
                </div>
                <div>
                  <span className="text-muted-foreground">End:</span>
                  <div className="font-medium">{format(parseISO(selectedEvent.end_time), "MMM d, yyyy h:mm a")}</div>
                </div>
              </div>
              {selectedEvent.location && (
                <div className="text-sm">
                  <span className="text-muted-foreground">Location:</span>
                  <div className="font-medium">{selectedEvent.location}</div>
                </div>
              )}
              {selectedEvent.description && (
                <div className="text-sm">
                  <span className="text-muted-foreground">Description:</span>
                  <div className="mt-1 p-2 bg-muted rounded">{selectedEvent.description}</div>
                </div>
              )}
              <div className="border-t pt-4 mt-2">
                <p className="text-sm font-medium mb-2">Add to Calendar:</p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => {
                    const start = parseISO(selectedEvent.start_time);
                    const end = parseISO(selectedEvent.end_time);
                    const formatDate = (d: Date) => d.toISOString().replace(/-|:|\.\d+/g, "");
                    const url = `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(selectedEvent.title)}&dates=${formatDate(start)}/${formatDate(end)}&details=${encodeURIComponent(selectedEvent.description || "")}&location=${encodeURIComponent(selectedEvent.location || "")}`;
                    window.open(url, "_blank");
                  }}>
                    📅 Google
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => {
                    const start = parseISO(selectedEvent.start_time);
                    const end = parseISO(selectedEvent.end_time);
                    const icsContent = `BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART:${start.toISOString().replace(/-|:|\.\d+/g, "").slice(0, -3)}Z
DTEND:${end.toISOString().replace(/-|:|\.\d+/g, "").slice(0, -3)}Z
SUMMARY:${selectedEvent.title}
DESCRIPTION:${selectedEvent.description || ""}
LOCATION:${selectedEvent.location || ""}
END:VEVENT
END:VCALENDAR`;
                    const blob = new Blob([icsContent], { type: "text/calendar" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = "event.ics";
                    a.click();
                  }}>
                    📎 Outlook/Apple
                  </Button>
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={openEditDialog}>Edit</Button>
            <Button variant="destructive" onClick={() => setIsDeleteOpen(true)}>Delete</Button>
            <Button variant="secondary" onClick={() => setIsViewOpen(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Event Dialog */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Edit Event</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="edit-title">Title *</Label>
              <Input id="edit-title" value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-event-type">Event Type</Label>
              <Select value={eventType} onValueChange={(v: any) => setEventType(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="meeting">Meeting</SelectItem>
                  <SelectItem value="call">Call</SelectItem>
                  <SelectItem value="reminder">Reminder</SelectItem>
                  <SelectItem value="blocked">Blocked Time</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="edit-start-time">Start Time *</Label>
                <Input id="edit-start-time" type="datetime-local" value={startTime} onChange={(e) => setStartTime(e.target.value)} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="edit-end-time">End Time *</Label>
                <Input id="edit-end-time" type="datetime-local" value={endTime} onChange={(e) => setEndTime(e.target.value)} />
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-location">Location</Label>
              <Input id="edit-location" value={location} onChange={(e) => setLocation(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-description">Description</Label>
              <Textarea id="edit-description" value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditOpen(false)}>Cancel</Button>
            <Button onClick={handleUpdateEvent} disabled={updateEvent.isPending}>
              {updateEvent.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete Event</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-muted-foreground">Are you sure you want to delete this event? This action cannot be undone.</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteOpen(false)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDeleteEvent} disabled={deleteEvent.isPending}>
              {deleteEvent.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
