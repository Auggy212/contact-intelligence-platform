import { AuthSync } from "@/components/auth-sync"
import { Sidebar } from "@/components/layout/sidebar"
import { Topbar } from "@/components/layout/topbar"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <AuthSync />
      <div className="grain-overlay flex h-screen overflow-hidden">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Topbar />
          <main className="app-canvas flex-1 overflow-y-auto p-6 lg:p-8">
            <div key="page" className="animate-rise mx-auto max-w-[1400px]">
              {children}
            </div>
          </main>
        </div>
      </div>
    </>
  )
}
