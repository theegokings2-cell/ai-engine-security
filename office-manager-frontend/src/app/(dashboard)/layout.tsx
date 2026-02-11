import { Sidebar } from "@/components/layouts/sidebar";
import { AuthGuard } from "@/components/layouts/auth-guard";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 flex flex-col">{children}</main>
      </div>
    </AuthGuard>
  );
}
