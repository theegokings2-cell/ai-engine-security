"use client";

import { useState } from "react";
import { Header } from "@/components/layouts/header";
import {
  useAppointments,
  useCreateAppointment,
  useUpdateAppointment,
  useDeleteAppointment,
  useCustomers,
  Appointment,
} from "@/lib/queries/office";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { Plus, Clock, MapPin, User, Calendar, ChevronLeft, ChevronRight, Edit, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { format, addMonths, subMonths, startOfMonth, endOfMonth, isSameMonth } from "date-fns";

const statusColors: Record<Appointment["status"], string> = {
  scheduled: "bg-blue-100 text-blue-800",
  confirmed: "bg-green-100 text-green-800",
  completed: "bg-gray-100 text-gray-800",
  cancelled: "bg-red-100 text-red-800",
};

type AppointmentFormData = Partial<Appointment>;

export default function AppointmentsPage() {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedAppointment, setSelectedAppointment] = useState<Appointment | null>(null);
  const [isViewOpen, setIsViewOpen] = useState(false);
  const [formData, setFormData] = useState<AppointmentFormData>({
    status: "scheduled",
  });

  // Fetch appointments for current month view
  const monthStart = startOfMonth(currentMonth);
  const monthEnd = endOfMonth(currentMonth);

  const { data, isLoading, error } = useAppointments({
    skip: 0,
    limit: 100,
    status: statusFilter,
    start_date: monthStart.toISOString(),
    end_date: monthEnd.toISOString(),
  });

  const { data: customersData } = useCustomers({ limit: 100 });
  const createAppointment = useCreateAppointment();
  const updateAppointment = useUpdateAppointment();
  const deleteAppointment = useDeleteAppointment();

  const customers = customersData?.data ?? [];
  
  // Show all appointments for the selected month, but hide past scheduled/confirmed ones
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const appointments = (data?.data ?? []).filter((apt) => {
    const aptDate = new Date(apt.start_time);
    return isSameMonth(aptDate, currentMonth);
  }).filter((apt) => {
    // Hide past scheduled/confirmed appointments (they're outdated)
    const aptDate = new Date(apt.start_time);
    aptDate.setHours(0, 0, 0, 0);
    if (aptDate < today && ["scheduled", "confirmed"].includes(apt.status)) {
      return false;
    }
    return true;
  });

  const openCreateDialog = () => {
    setSelectedAppointment(null);
    setFormData({ status: "scheduled" });
    setIsDialogOpen(true);
  };

  const openEditDialog = (appointment: Appointment) => {
    setSelectedAppointment(appointment);
    setFormData({
      id: appointment.id,
      title: appointment.title,
      description: appointment.description,
      start_time: appointment.start_time,
      end_time: appointment.end_time,
      customer_id: appointment.customer_id,
      location: appointment.location,
      notes: appointment.notes,
      status: appointment.status,
      appointment_type: appointment.appointment_type,
    });
    setIsDialogOpen(true);
    setIsViewOpen(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title || !formData.start_time || !formData.end_time) return;

    if (selectedAppointment) {
      // Update existing appointment
      await updateAppointment.mutateAsync({ id: selectedAppointment.id, data: formData });
    } else {
      // Create new appointment
      await createAppointment.mutateAsync(formData);
    }
    setIsDialogOpen(false);
    setFormData({ status: "scheduled" });
    setSelectedAppointment(null);
  };

  const handleDelete = async () => {
    if (!selectedAppointment) return;
    if (confirm("Are you sure you want to delete this appointment?")) {
      await deleteAppointment.mutateAsync(selectedAppointment.id);
      setIsViewOpen(false);
      setSelectedAppointment(null);
    }
  };

  const formatTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString([], {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <>
      <Header title="Appointments" />
      <div className="flex-1 p-6">
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
          <div className="flex items-center gap-2">
            <Select value={statusFilter || "all"} onValueChange={(value) => setStatusFilter(value === "all" ? undefined : value)}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="All Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="scheduled">Scheduled</SelectItem>
                <SelectItem value="confirmed">Confirmed</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={openCreateDialog}>
              <Plus className="h-4 w-4 mr-2" />
              New Appointment
            </Button>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : appointments.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No appointments found for {format(currentMonth, "MMMM yyyy")}.</p>
            <Button variant="link" className="mt-2" onClick={openCreateDialog}>
              Schedule your first appointment
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {appointments.map((appointment) => (
              <Card key={appointment.id} className="cursor-pointer hover:bg-accent/50 transition-colors" onClick={() => { setSelectedAppointment(appointment); setIsViewOpen(true); }}>
                <CardContent className="flex items-center justify-between p-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <h3 className="font-medium">{appointment.title}</h3>
                      <span className={cn("px-2 py-1 rounded-full text-xs font-medium", statusColors[appointment.status])}>
                        {appointment.status}
                      </span>
                    </div>
                    {appointment.description && <p className="text-sm text-muted-foreground mt-1">{appointment.description}</p>}
                    <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                      <div className="flex items-center gap-1"><Calendar className="h-4 w-4" /><span>{formatDate(appointment.start_time)}</span></div>
                      <div className="flex items-center gap-1"><Clock className="h-4 w-4" /><span>{formatTime(appointment.start_time)} - {formatTime(appointment.end_time)}</span></div>
                      {appointment.location && <div className="flex items-center gap-1"><MapPin className="h-4 w-4" /><span>{appointment.location}</span></div>}
                      {appointment.customer && <div className="flex items-center gap-1"><User className="h-4 w-4" /><span>{appointment.customer.company_name}</span></div>}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {data && data.total > 0 && (
          <div className="flex justify-center gap-2 mt-6">
            <span className="flex items-center px-4 text-sm">Showing {appointments.length} of {data.total} appointments</span>
          </div>
        )}
      </div>

      {/* View Appointment Dialog */}
      <Dialog open={isViewOpen} onOpenChange={setIsViewOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{selectedAppointment?.title}</DialogTitle>
          </DialogHeader>
          {selectedAppointment && (
            <div className="grid gap-4 py-4">
              <div className="flex items-center gap-2">
                <span className={cn("px-2 py-1 rounded-full text-xs font-medium", statusColors[selectedAppointment.status])}>{selectedAppointment.status}</span>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><span className="text-muted-foreground">Date:</span><div className="font-medium">{formatDate(selectedAppointment.start_time)}</div></div>
                <div><span className="text-muted-foreground">Time:</span><div className="font-medium">{formatTime(selectedAppointment.start_time)} - {formatTime(selectedAppointment.end_time)}</div></div>
              </div>
              {selectedAppointment.location && <div className="text-sm"><span className="text-muted-foreground">Location:</span><div className="font-medium">{selectedAppointment.location}</div></div>}
              {selectedAppointment.customer && <div className="text-sm"><span className="text-muted-foreground">Customer:</span><div className="font-medium">{selectedAppointment.customer.company_name}</div></div>}
              {selectedAppointment.description && <div className="text-sm"><span className="text-muted-foreground">Description:</span><div className="mt-1 p-2 bg-muted rounded">{selectedAppointment.description}</div></div>}
              {selectedAppointment.notes && <div className="text-sm"><span className="text-muted-foreground">Notes:</span><div className="mt-1 p-2 bg-muted rounded">{selectedAppointment.notes}</div></div>}
            </div>
          )}
          <DialogFooter>
            <Button variant="destructive" onClick={handleDelete}>Delete</Button>
            <Button variant="default" onClick={() => openEditDialog(selectedAppointment)}>Edit</Button>
            <Button variant="secondary" onClick={() => setIsViewOpen(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create/Edit Appointment Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{selectedAppointment ? "Edit Appointment" : "Schedule Appointment"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title">Title *</Label>
              <Input id="title" value={formData.title || ""} onChange={(e) => setFormData((f) => ({ ...f, title: e.target.value }))} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Input id="description" value={formData.description || ""} onChange={(e) => setFormData((f) => ({ ...f, description: e.target.value }))} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="start_time">Start Time *</Label>
                <Input id="start_time" type="datetime-local" value={formData.start_time ? formData.start_time.slice(0, 16) : ""} onChange={(e) => setFormData((f) => ({ ...f, start_time: e.target.value }))} required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="end_time">End Time *</Label>
                <Input id="end_time" type="datetime-local" value={formData.end_time ? formData.end_time.slice(0, 16) : ""} onChange={(e) => setFormData((f) => ({ ...f, end_time: e.target.value }))} required />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="status">Status</Label>
                <Select value={formData.status || "scheduled"} onValueChange={(value) => setFormData((f) => ({ ...f, status: value as any }))}>
                  <SelectTrigger>
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="scheduled">Scheduled</SelectItem>
                    <SelectItem value="confirmed">Confirmed</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                    <SelectItem value="cancelled">Cancelled</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="customer">Customer</Label>
                <Select value={formData.customer_id || "none"} onValueChange={(value) => setFormData((f) => ({ ...f, customer_id: value === "none" ? undefined : value }))}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select customer" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No Customer</SelectItem>
                    {customers.map((customer) => (<SelectItem key={customer.id} value={customer.id}>{customer.company_name}</SelectItem>))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="location">Location</Label>
              <Input id="location" value={formData.location || ""} onChange={(e) => setFormData((f) => ({ ...f, location: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Input id="notes" value={formData.notes || ""} onChange={(e) => setFormData((f) => ({ ...f, notes: e.target.value }))} />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { setIsDialogOpen(false); setSelectedAppointment(null); }}>Cancel</Button>
              <Button type="submit" disabled={createAppointment.isPending || updateAppointment.isPending}>
                {createAppointment.isPending || updateAppointment.isPending 
                  ? (selectedAppointment ? "Updating..." : "Creating...") 
                  : (selectedAppointment ? "Update" : "Schedule")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
