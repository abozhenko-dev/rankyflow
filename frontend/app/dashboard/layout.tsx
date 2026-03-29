import Sidebar from "@/components/dashboard/Sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-[240px]">
        <div className="max-w-[1400px] mx-auto px-6 py-8">
          {children}
        </div>
      </main>
    </div>
  );
}
