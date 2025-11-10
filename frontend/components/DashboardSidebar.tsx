"use client"

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import {
  Plug,
  Target,
  Database,
  Bell,
  Sparkles,
  LayoutDashboard,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ThemeToggle } from '@/components/ThemeToggle'

interface SidebarSection {
  id: string
  title: string
  icon: typeof Plug
  href: string
}

const sidebarSections: SidebarSection[] = [
  {
    id: 'dashboard',
    title: 'Dashboard',
    icon: LayoutDashboard,
    href: '/dashboard',
  },
  {
    id: 'integrations',
    title: 'Integrations',
    icon: Plug,
    href: '/dashboard/integrations',
  },
  {
    id: 'planning',
    title: 'Planning',
    icon: Target,
    href: '/dashboard/planning',
  },
  {
    id: 'data',
    title: 'Data',
    icon: Database,
    href: '/dashboard/data',
  },
  {
    id: 'notifications',
    title: 'Notifications',
    icon: Bell,
    href: '/dashboard/notifications',
  },
]

export default function DashboardSidebar() {
  const pathname = usePathname()
  
  // Determine active section from pathname
  const getActiveSectionId = () => {
    if (pathname === '/dashboard') return 'dashboard'
    if (pathname.startsWith('/dashboard/integrations')) return 'integrations'
    if (pathname.startsWith('/dashboard/planning')) return 'planning'
    if (pathname.startsWith('/dashboard/data')) return 'data'
    if (pathname.startsWith('/dashboard/notifications')) return 'notifications'
    return undefined
  }

  const activeSectionId = getActiveSectionId()

  return (
    <Sidebar collapsible="offcanvas" className="border-r border-purple-200/50 dark:border-purple-800/50 bg-white/90 dark:bg-gray-900/90 backdrop-blur-md shadow-lg">
      <SidebarHeader className="p-4 border-b border-purple-200/50 dark:border-purple-800/50 bg-gradient-to-r from-purple-50/50 to-pink-50/50 dark:from-purple-900/30 dark:to-pink-900/30">
        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="h-6 w-6 text-purple-600 dark:text-purple-400 animate-pulse" />
          <span className="font-bold text-lg bg-gradient-to-r from-purple-600 to-pink-600 dark:from-purple-400 dark:to-pink-400 bg-clip-text text-transparent">
            LifeFlow
          </span>
        </div>
        <SidebarTrigger className="mt-2 hover:bg-purple-100 dark:hover:bg-purple-900/30 transition-colors" />
      </SidebarHeader>
      <SidebarContent className="p-2">
        <SidebarGroup>
          <SidebarMenu>
            {sidebarSections.map((section) => {
              const Icon = section.icon
              const isActive = activeSectionId === section.id

              return (
                <SidebarMenuItem key={section.id}>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive}
                    className={cn(
                      'w-full justify-start cursor-pointer transition-all duration-200 rounded-md',
                      isActive
                        ? 'bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 font-medium shadow-sm dark:from-purple-900/30 dark:to-pink-900/30 dark:text-purple-300'
                        : 'text-gray-600 hover:bg-purple-50 hover:text-purple-600 dark:text-gray-300 dark:hover:bg-purple-900/20 dark:hover:text-purple-400'
                    )}
                  >
                    <Link href={section.href}>
                      <Icon
                        className={cn(
                          'h-4 w-4 transition-colors duration-200',
                          isActive ? 'text-purple-600 dark:text-purple-300' : 'text-gray-600 dark:text-gray-300'
                        )}
                      />
                      <span>{section.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              )
            })}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="p-2 border-t border-purple-200/50 dark:border-purple-800/50">
        <SidebarMenu>
          <SidebarMenuItem>
            <ThemeToggle />
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}

