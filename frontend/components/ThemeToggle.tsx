"use client"

import * as React from "react"
import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"
import { SidebarMenuButton } from "@/components/ui/sidebar"
import { cn } from "@/lib/utils"

export const ThemeToggle = () => {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)

  // Avoid hydration mismatch by only rendering after mount
  React.useEffect(() => {
    setMounted(true)
  }, [])

  const handleToggle = () => {
    setTheme(theme === "dark" ? "light" : "dark")
  }

  if (!mounted) {
    return (
      <SidebarMenuButton
        className="w-full justify-start cursor-pointer transition-all duration-200 rounded-md text-gray-600"
        disabled
      >
        <Sun className="h-4 w-4" />
        <span>Theme</span>
      </SidebarMenuButton>
    )
  }

  const isDark = theme === "dark"

  return (
    <SidebarMenuButton
      onClick={handleToggle}
      className={cn(
        "w-full justify-start cursor-pointer transition-all duration-200 rounded-md",
        "text-gray-600 hover:bg-purple-50 hover:text-purple-600 dark:text-gray-300 dark:hover:bg-purple-900/20 dark:hover:text-purple-400"
      )}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
    >
      {isDark ? (
        <Sun className="h-4 w-4 transition-colors duration-200" />
      ) : (
        <Moon className="h-4 w-4 transition-colors duration-200" />
      )}
      <span>{isDark ? "Light Mode" : "Dark Mode"}</span>
    </SidebarMenuButton>
  )
}

