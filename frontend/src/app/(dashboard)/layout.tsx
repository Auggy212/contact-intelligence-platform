import { AuthSync } from "@/components/auth-sync"
import { Sidebar } from "@/components/layout/sidebar"
import { Topbar } from "@/components/layout/topbar"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <AuthSync />
      <div className="flex h-screen overflow-hidden bg-background">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Topbar />
          <main className="flex-1 overflow-y-auto bg-background p-6 animate-page-enter">
            {children}
          </main>
        </div>
      </div>
    </>
  )
}
