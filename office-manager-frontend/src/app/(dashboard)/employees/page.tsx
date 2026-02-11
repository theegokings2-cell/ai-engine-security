"use client";

import { useState } from "react";
import { Header } from "@/components/layouts/header";
import {
  useEmployees,
  useDepartments,
  Employee,
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
import { Plus, Trash2, Mail, Phone, Building, Briefcase } from "lucide-react";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
import apiClient from "@/lib/api/client";

interface CreateEmployeeData {
  email: string;
  full_name: string;
  password: string;
  employee_id: string;
  department_id?: string;
  custom_department?: string;
  job_title?: string;
  phone?: string;
  hire_date?: string;
}

// Safe error message extractor
function getErrorMessage(error: any): string {
  if (!error) return "An unknown error occurred";
  if (typeof error === "string") return error;
  if (error.message) return error.message;
  if (Array.isArray(error)) return error.join(", ");
  if (typeof error === "object") {
    if (error.detail) return String(error.detail);
    if (error.response?.data?.detail) return String(error.response.data.detail);
    return JSON.stringify(error);
  }
  return String(error);
}

export default function EmployeesPage() {
  const [page, setPage] = useState(1);
  const [departmentFilter, setDepartmentFilter] = useState<string | undefined>();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [formData, setFormData] = useState<CreateEmployeeData>({
    email: "",
    full_name: "",
    password: "",
    employee_id: "",
    department_id: "",
    custom_department: "",
    job_title: "",
    phone: "",
    hire_date: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { toast } = useToast();

  const { data, isLoading, refetch } = useEmployees({
    skip: (page - 1) * 20,
    limit: 20,
    department_id: departmentFilter,
  });

  const { data: departmentsData } = useDepartments();

  // Filter to only UUID-based departments (not enterprise departments with IDs like "exec", "ceo-office")
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const departments = (departmentsData?.data ?? []).filter((dept) => uuidRegex.test(dept.id));
  const employees = data?.data ?? [];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.email || !formData.full_name || !formData.password || !formData.employee_id) {
      toast({ title: "Error", description: "Please fill in all required fields", variant: "destructive" });
      return;
    }

    setIsSubmitting(true);
    
    try {
      // Handle "Other" department option
      let departmentId = formData.department_id;
      
      // Validate department_id is a valid UUID (not enterprise department IDs like "exec", "ceo-office")
      if (departmentId && departmentId !== "general" && departmentId !== "other") {
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        if (!uuidRegex.test(departmentId)) {
          // Clear invalid department_id (enterprise department IDs are not valid UUIDs)
          departmentId = undefined;
        }
      }
      
      if (formData.department_id === "other") {
        if (!formData.custom_department) {
          toast({ title: "Error", description: "Please specify the department name", variant: "destructive" });
          setIsSubmitting(false);
          return;
        }
        // Create the custom department first
        try {
          const deptForm = new URLSearchParams();
          deptForm.append("name", formData.custom_department);
          const deptResponse = await apiClient.post<{ department: { id: string } }>("/office/departments", deptForm);
          departmentId = deptResponse.data.department.id;
        } catch (deptError: any) {
          toast({ 
            title: "Error", 
            description: getErrorMessage(deptError), 
            variant: "destructive" 
          });
          setIsSubmitting(false);
          return;
        }
      }

      // Create the employee — backend expects Form(...) parameters
      // Pass URLSearchParams directly so Axios auto-sets Content-Type
      const form = new URLSearchParams();
      form.append("email", formData.email);
      form.append("full_name", formData.full_name);
      form.append("password", formData.password);
      form.append("employee_id", formData.employee_id);
      if (departmentId && departmentId !== "general") form.append("department_id", departmentId);
      if (formData.job_title) form.append("job_title", formData.job_title);
      if (formData.phone) form.append("phone", formData.phone);
      if (formData.hire_date) form.append("hire_date", formData.hire_date);

      await apiClient.post("/office/employees/with-user", form);

      toast({ title: "Success", description: "Employee created successfully" });
      setIsDialogOpen(false);
      setFormData({
        email: "",
        full_name: "",
        password: "",
        employee_id: "",
        department_id: "",
        custom_department: "",
        job_title: "",
        phone: "",
        hire_date: "",
      });
      refetch();
    } catch (error: any) {
      console.error("Employee creation error:", error);
      toast({ 
        title: "Error", 
        description: getErrorMessage(error), 
        variant: "destructive" 
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await apiClient.delete(`/office/employees/${deleteId}`);
      toast({ title: "Success", description: "Employee deleted successfully" });
      setIsDeleteDialogOpen(false);
      setDeleteId(null);
      refetch();
    } catch (error: any) {
      toast({ 
        title: "Error", 
        description: getErrorMessage(error), 
        variant: "destructive" 
      });
    }
  };

  return (
    <>
      <Header title="Employees" />
      <div className="flex-1 p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex gap-2">
            <Select
              value={departmentFilter || "all"}
              onValueChange={(value) =>
                setDepartmentFilter(value === "all" ? undefined : value)
              }
            >
              <SelectTrigger className="w-48">
                <SelectValue placeholder="All Departments" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Departments</SelectItem>
                <SelectItem value="general">General (No Dept)</SelectItem>
                {departments.map((dept) => (
                  <SelectItem key={dept.id} value={dept.id}>
                    {dept.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Employee
          </Button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : employees.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No employees found.</p>
            <Button variant="link" className="mt-2" onClick={() => setIsDialogOpen(true)}>
              Add your first employee
            </Button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {employees.map((employee: Employee) => (
              <Card key={employee.id}>
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-lg">
                        {employee.user?.full_name || employee.employee_id}
                      </CardTitle>
                      <p className="text-sm text-muted-foreground">
                        {employee.employee_id}
                      </p>
                      <span
                        className={cn(
                          "inline-block px-2 py-1 rounded-full text-xs font-medium mt-1",
                          employee.is_active
                            ? "bg-green-100 text-green-800"
                            : "bg-gray-100 text-gray-800"
                        )}
                      >
                        {employee.is_active ? "Active" : "Inactive"}
                      </span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  {employee.user?.email && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Mail className="h-4 w-4" />
                      <span>{employee.user.email}</span>
                    </div>
                  )}
                  {employee.phone && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Phone className="h-4 w-4" />
                      <span>{employee.phone}</span>
                    </div>
                  )}
                  {employee.job_title && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Briefcase className="h-4 w-4" />
                      <span>{employee.job_title}</span>
                    </div>
                  )}
                  {employee.department && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Building className="h-4 w-4" />
                      <span>{employee.department.name}</span>
                    </div>
                  )}
                  {employee.hire_date && (
                    <p className="text-xs text-muted-foreground mt-2">
                      Hired: {new Date(employee.hire_date).toLocaleDateString()}
                    </p>
                  )}
                </CardContent>
                <div className="px-4 pb-4 pt-0">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    onClick={() => {
                      setDeleteId(employee.id);
                      setIsDeleteDialogOpen(true);
                    }}
                  >
                    <Trash2 className="h-4 w-4 mr-1" />
                    Delete
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}

        {data && data.total > 20 && (
          <div className="flex justify-center gap-2 mt-6">
            <Button variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Previous
            </Button>
            <span className="flex items-center px-4 text-sm">Page {page}</span>
            <Button variant="outline" disabled={employees.length < 20} onClick={() => setPage((p) => p + 1)}>
              Next
            </Button>
          </div>
        )}
      </div>

      {/* Create Employee Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Add New Employee</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="full_name">Full Name *</Label>
                <Input
                  id="full_name"
                  value={formData.full_name}
                  onChange={(e) => setFormData((f) => ({ ...f, full_name: e.target.value }))}
                  placeholder="John Doe"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="employee_id">Employee ID *</Label>
                <Input
                  id="employee_id"
                  value={formData.employee_id}
                  onChange={(e) => setFormData((f) => ({ ...f, employee_id: e.target.value }))}
                  placeholder="EMP-001"
                  required
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email Address *</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData((f) => ({ ...f, email: e.target.value }))}
                placeholder="john@company.com"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password *</Label>
              <Input
                id="password"
                type="password"
                value={formData.password}
                onChange={(e) => setFormData((f) => ({ ...f, password: e.target.value }))}
                placeholder="Initial password"
                required
              />
              <p className="text-xs text-muted-foreground">Employee will use this to log in</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="job_title">Job Title</Label>
                <Input
                  id="job_title"
                  value={formData.job_title || ""}
                  onChange={(e) => setFormData((f) => ({ ...f, job_title: e.target.value }))}
                  placeholder="Software Engineer"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="phone">Phone</Label>
                <Input
                  id="phone"
                  value={formData.phone || ""}
                  onChange={(e) => setFormData((f) => ({ ...f, phone: e.target.value }))}
                  placeholder="(555) 123-4567"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="department">Department</Label>
                <Select
                  value={formData.department_id || "general"}
                  onValueChange={(value) =>
                    setFormData((f) => ({
                      ...f,
                      department_id: value === "general" ? "" : value,
                      custom_department: value === "other" ? f.custom_department || "" : "",
                    }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select department" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="general">General (No Dept)</SelectItem>
                    <SelectItem value="other">Other (Specify)</SelectItem>
                    {departments.map((dept) => (
                      <SelectItem key={dept.id} value={dept.id}>
                        {dept.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="hire_date">Hire Date</Label>
                <Input
                  id="hire_date"
                  type="date"
                  value={formData.hire_date || ""}
                  onChange={(e) => setFormData((f) => ({ ...f, hire_date: e.target.value }))}
                />
              </div>
            </div>
            {formData.department_id === "other" && (
              <div className="space-y-2">
                <Label htmlFor="custom_department">Custom Department Name *</Label>
                <Input
                  id="custom_department"
                  value={formData.custom_department || ""}
                  onChange={(e) => setFormData((f) => ({ ...f, custom_department: e.target.value }))}
                  placeholder="Enter department name"
                  required={formData.department_id === "other"}
                />
              </div>
            )}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Creating..." : "Create Employee"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete Employee</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-muted-foreground">
              Are you sure you want to delete this employee? This will also deactivate their user account. This action cannot be undone.
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
