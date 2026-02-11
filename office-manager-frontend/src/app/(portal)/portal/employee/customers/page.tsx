"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layouts/header";
import { portalApiClient } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Users, Search, Mail, Phone, Building, User, Eye } from "lucide-react";

interface PortalUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  permissions: string[];
}

interface Customer {
  id: string;
  company_name: string;
  contact_name?: string;
  email?: string;
  phone?: string;
  customer_type: string;
}

export default function EmployeeCustomersPage() {
  const router = useRouter();
  const [user, setUser] = useState<PortalUser | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);

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

  const fetchCustomers = async () => {
    if (!user) return;

    try {
      setIsLoading(true);
      const response = await portalApiClient.get("/portal/customers", {
        params: { limit: 100 },
      });
      setCustomers(response.data.customers || []);
    } catch (error) {
      console.error("Failed to fetch customers:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchCustomers();
    }
  }, [user]);

  const filteredCustomers = customers.filter((customer) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      customer.company_name.toLowerCase().includes(searchLower) ||
      customer.contact_name?.toLowerCase().includes(searchLower) ||
      customer.email?.toLowerCase().includes(searchLower)
    );
  });

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <>
      <Header title="Customers" />
      <div className="flex-1 p-6">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search customers..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9 w-64"
                />
              </div>
            </div>
            <div className="text-sm text-muted-foreground">
              {filteredCustomers.length} customer{filteredCustomers.length !== 1 ? "s" : ""} found
            </div>
          </div>

          {/* Customers Grid */}
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : filteredCustomers.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-4">
                  {search ? "No customers found matching your search" : "No customers available"}
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredCustomers.map((customer) => (
                <Card key={customer.id} className="group hover:shadow-md transition-shadow">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-100 rounded-lg">
                          <Building className="h-5 w-5 text-blue-600" />
                        </div>
                        <div>
                          <h3 className="font-medium line-clamp-1">{customer.company_name}</h3>
                          <p className="text-sm text-muted-foreground">{customer.customer_type}</p>
                        </div>
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => setSelectedCustomer(customer)}>
                        <Eye className="h-4 w-4" />
                      </Button>
                    </div>

                    {customer.contact_name && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                        <User className="h-4 w-4" />
                        <span>{customer.contact_name}</span>
                      </div>
                    )}

                    {customer.email && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                        <Mail className="h-4 w-4" />
                        <span className="truncate">{customer.email}</span>
                      </div>
                    )}

                    {customer.phone && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Phone className="h-4 w-4" />
                        <span>{customer.phone}</span>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Customer Detail Dialog */}
          {selectedCustomer && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setSelectedCustomer(null)}>
              <Card className="w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
                <CardContent className="p-6">
                  <div className="flex items-center gap-4 mb-6">
                    <div className="p-3 bg-blue-100 rounded-lg">
                      <Building className="h-6 w-6 text-blue-600" />
                    </div>
                    <div>
                      <h2 className="text-xl font-semibold">{selectedCustomer.company_name}</h2>
                      <p className="text-sm text-muted-foreground">{selectedCustomer.customer_type}</p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    {selectedCustomer.contact_name && (
                      <div className="flex items-center gap-3">
                        <User className="h-5 w-5 text-muted-foreground" />
                        <div>
                          <p className="text-sm text-muted-foreground">Contact Name</p>
                          <p className="font-medium">{selectedCustomer.contact_name}</p>
                        </div>
                      </div>
                    )}

                    {selectedCustomer.email && (
                      <div className="flex items-center gap-3">
                        <Mail className="h-5 w-5 text-muted-foreground" />
                        <div>
                          <p className="text-sm text-muted-foreground">Email</p>
                          <p className="font-medium">{selectedCustomer.email}</p>
                        </div>
                      </div>
                    )}

                    {selectedCustomer.phone && (
                      <div className="flex items-center gap-3">
                        <Phone className="h-5 w-5 text-muted-foreground" />
                        <div>
                          <p className="text-sm text-muted-foreground">Phone</p>
                          <p className="font-medium">{selectedCustomer.phone}</p>
                        </div>
                      </div>
                    )}

                    <div className="flex items-center gap-3">
                      <Users className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="text-sm text-muted-foreground">Customer Type</p>
                        <p className="font-medium capitalize">{selectedCustomer.customer_type}</p>
                      </div>
                    </div>
                  </div>

                  <div className="mt-6 flex justify-end">
                    <Button variant="outline" onClick={() => setSelectedCustomer(null)}>
                      Close
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
