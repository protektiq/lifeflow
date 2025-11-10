"use client"

import { useState, useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { createClient } from '@/src/lib/supabase/client'
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar'
import DashboardSidebar from '@/components/DashboardSidebar'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const pathname = usePathname()
  const [supabase] = useState(() => {
    if (typeof window !== 'undefined') {
      return createClient()
    }
    return null
  })
  const [user, setUser] = useState<any>(null)

  useEffect(() => {
    checkUser()
  }, [])

  const checkUser = async () => {
    if (!supabase) return
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) {
      router.push('/auth/login')
      return
    }
    setUser(user)
  }

  const handleLogout = async () => {
    if (!supabase) return
    await supabase.auth.signOut()
    router.push('/auth/login')
  }

  return (
    <SidebarProvider>
      <DashboardSidebar />
      <SidebarInset className="min-h-screen bg-gradient-to-b from-purple-50 via-pink-50 to-blue-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
        {/* Floating decorative elements */}
        <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
          <div className="absolute top-20 left-10 w-20 h-20 bg-purple-400/10 dark:bg-purple-500/20 rounded-full blur-xl animate-float"></div>
          <div className="absolute top-40 right-20 w-32 h-32 bg-pink-400/10 dark:bg-pink-500/20 rounded-full blur-2xl animate-float-reverse"></div>
          <div className="absolute bottom-20 left-1/4 w-24 h-24 bg-blue-400/10 dark:bg-blue-500/20 rounded-full blur-xl animate-float"></div>
        </div>
        
        <div className="relative z-10 mx-auto max-w-7xl px-4 py-4 sm:py-6 lg:py-8 sm:px-6 lg:px-8">
          {/* Header */}
          <div className="mb-6 sm:mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 animate-fade-in-up">
            <div className="flex items-center gap-3">
              <SidebarTrigger className="md:hidden" />
              <div>
                <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold">
                  <span className="gradient-text">LifeFlow Dashboard</span>
                </h1>
                <p className="mt-1 sm:mt-2 text-sm sm:text-base text-gray-700 dark:text-gray-300">Manage your tasks and calendar integration</p>
              </div>
            </div>
            {user && (
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-4">
                <span className="text-xs sm:text-sm text-gray-700 dark:text-gray-300 break-all">{user.email}</span>
                <button
                  onClick={handleLogout}
                  className="group relative w-full sm:w-auto px-6 py-2 border-2 border-purple-300 dark:border-purple-600 text-purple-700 dark:text-purple-300 font-semibold text-sm rounded-full backdrop-blur-sm transition-all duration-300 hover:border-purple-500 dark:hover:border-purple-500 hover:bg-purple-50 dark:hover:bg-purple-900/30 hover:scale-110 focus:outline-none focus:ring-4 focus:ring-purple-500/50"
                >
                  Sign Out
                </button>
              </div>
            )}
          </div>

          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}

