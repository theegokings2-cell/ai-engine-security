"use client";

import { useState } from "react";
import { Header } from "@/components/layouts/header";
import {
  useDepartments,
  useCreateDepartment,
  useLocations,
  useRooms,
  Department,
} from "@/lib/queries/office";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Plus, Building2, MapPin, DoorOpen, Users } from "lucide-react";

type DepartmentFormData = Partial<Department>;

export default function SettingsPage() {
  const [isDepartmentDialogOpen, setIsDepartmentDialogOpen] = useState(false);
  const [departmentFormData, setDepartmentFormData] = useState<DepartmentFormData>({});

  const { data: departmentsData, isLoading: loadingDepts } = useDepartments();
  const { data: locationsData, isLoading: loadingLocations } = useLocations();
  const { data: roomsData, isLoading: loadingRooms } = useRooms();

  const createDepartment = useCreateDepartment();

  const departments = departmentsData?.data ?? [];
  const locations = locationsData?.data ?? [];
  const rooms = roomsData?.data ?? [];

  const handleCreateDepartment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!departmentFormData.name) return;

    await createDepartment.mutateAsync(departmentFormData);
    setIsDepartmentDialogOpen(false);
    setDepartmentFormData({});
  };

  return (
    <>
      <Header title="Settings" />
      <div className="flex-1 p-6">
        <Tabs defaultValue="departments" className="space-y-6">
          <TabsList>
            <TabsTrigger value="departments" className="gap-2">
              <Building2 className="h-4 w-4" />
              Departments
            </TabsTrigger>
            <TabsTrigger value="locations" className="gap-2">
              <MapPin className="h-4 w-4" />
              Locations
            </TabsTrigger>
            <TabsTrigger value="rooms" className="gap-2">
              <DoorOpen className="h-4 w-4" />
              Rooms
            </TabsTrigger>
          </TabsList>

          <TabsContent value="departments" className="space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-lg font-semibold">Departments</h2>
                <p className="text-sm text-muted-foreground">
                  Manage your organization's departments
                </p>
              </div>
              <Button onClick={() => setIsDepartmentDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Department
              </Button>
            </div>

            {loadingDepts ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : departments.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <Building2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">No departments created yet.</p>
                  <Button
                    variant="link"
                    className="mt-2"
                    onClick={() => setIsDepartmentDialogOpen(true)}
                  >
                    Create your first department
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {departments.map((dept) => (
                  <Card key={dept.id}>
                    <CardHeader>
                      <CardTitle className="text-base">{dept.name}</CardTitle>
                      {dept.description && (
                        <CardDescription>{dept.description}</CardDescription>
                      )}
                    </CardHeader>
                    <CardContent>
                      <p className="text-xs text-muted-foreground">
                        Created: {new Date(dept.created_at).toLocaleDateString()}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="locations" className="space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-lg font-semibold">Locations</h2>
                <p className="text-sm text-muted-foreground">
                  Manage office locations
                </p>
              </div>
              <Button disabled>
                <Plus className="h-4 w-4 mr-2" />
                Add Location
              </Button>
            </div>

            {loadingLocations ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : locations.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <MapPin className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">No locations added yet.</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {locations.map((location) => (
                  <Card key={location.id}>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        {location.name}
                        {location.is_active ? (
                          <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">
                            Active
                          </span>
                        ) : (
                          <span className="text-xs bg-gray-100 text-gray-800 px-2 py-0.5 rounded-full">
                            Inactive
                          </span>
                        )}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-muted-foreground space-y-1">
                      <p>{location.address}</p>
                      {(location.city || location.state) && (
                        <p>
                          {location.city}
                          {location.city && location.state && ", "}
                          {location.state}
                        </p>
                      )}
                      {location.country && <p>{location.country}</p>}
                      {location.timezone && (
                        <p className="text-xs">Timezone: {location.timezone}</p>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="rooms" className="space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-lg font-semibold">Meeting Rooms</h2>
                <p className="text-sm text-muted-foreground">
                  Manage meeting rooms and their availability
                </p>
              </div>
              <Button disabled>
                <Plus className="h-4 w-4 mr-2" />
                Add Room
              </Button>
            </div>

            {loadingRooms ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : rooms.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <DoorOpen className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">No meeting rooms added yet.</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {rooms.map((room) => (
                  <Card key={room.id}>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        {room.name}
                        {room.is_active ? (
                          <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">
                            Active
                          </span>
                        ) : (
                          <span className="text-xs bg-gray-100 text-gray-800 px-2 py-0.5 rounded-full">
                            Inactive
                          </span>
                        )}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-muted-foreground space-y-2">
                      <div className="flex items-center gap-2">
                        <Users className="h-4 w-4" />
                        <span>Capacity: {room.capacity}</span>
                      </div>
                      {room.amenities && room.amenities.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {room.amenities.map((amenity) => (
                            <span
                              key={amenity}
                              className="text-xs bg-secondary px-2 py-0.5 rounded"
                            >
                              {amenity}
                            </span>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>

      <Dialog open={isDepartmentDialogOpen} onOpenChange={setIsDepartmentDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add Department</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateDepartment} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="dept_name">Name *</Label>
              <Input
                id="dept_name"
                value={departmentFormData.name || ""}
                onChange={(e) =>
                  setDepartmentFormData((f) => ({ ...f, name: e.target.value }))
                }
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="dept_description">Description</Label>
              <Input
                id="dept_description"
                value={departmentFormData.description || ""}
                onChange={(e) =>
                  setDepartmentFormData((f) => ({ ...f, description: e.target.value }))
                }
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsDepartmentDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={createDepartment.isPending}>
                {createDepartment.isPending ? "Creating..." : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
