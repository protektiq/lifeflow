"use client"

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/src/lib/api'
import { RawTask } from '@/src/types/task'
import { DailyPlan, EnergyLevel, Reminder } from '@/src/types/plan'
import { createClient } from '@/src/lib/supabase/client'
import EnergyLevelInput from '@/components/EnergyLevelInput'
import DailyPlanView from '@/components/DailyPlanView'
import RemindersView from '@/components/RemindersView'
import NotificationCenter from '@/components/NotificationCenter'
import TaskManagerIntegration from '@/components/TaskManagerIntegration'
import RawTasksView from '@/components/RawTasksView'

export const dynamic = 'force-dynamic'

export default function DashboardPage() {
  const router = useRouter()
  const [supabase] = useState(() => {
    if (typeof window !== 'undefined') {
      return createClient()
    }
    return null
  })
  const [tasks, setTasks] = useState<RawTask[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [syncingEmail, setSyncingEmail] = useState(false)
  const [refreshingMetrics, setRefreshingMetrics] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [user, setUser] = useState<any>(null)
  const [metrics, setMetrics] = useState<any>(null)
  const [dailyPlan, setDailyPlan] = useState<DailyPlan | null>(null)
  const [planLoading, setPlanLoading] = useState(false)
  const [energyLevel, setEnergyLevel] = useState<EnergyLevel | null>(null)
  const [reminders, setReminders] = useState<Reminder[]>([])
  const [remindersLoading, setRemindersLoading] = useState(false)
  // Get today's date in local timezone (not UTC)
  const [today] = useState(() => {
    const now = new Date()
    const year = now.getFullYear()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const day = String(now.getDate()).padStart(2, '0')
    const dateStr = `${year}-${month}-${day}`
    console.log('Today date calculated:', dateStr, 'Local date:', now.toLocaleDateString())
    return dateStr
  })

  useEffect(() => {
    checkUser()
    loadTasks()
    loadMetrics()
    loadDailyPlan()
    loadEnergyLevel()
    loadReminders()
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

  const loadMetrics = async () => {
    try {
      const response = await apiClient.healthCheck()
      if (response.metrics) {
        setMetrics(response.metrics)
      }
    } catch (err) {
      // Silently fail metrics loading
    }
  }

  const loadTasks = async () => {
    try {
      setLoading(true)
      const response = await apiClient.getRawTasks()
      // Backend returns a list directly, not wrapped in an object
      setTasks(Array.isArray(response) ? response : response.tasks || [])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load tasks')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    if (!supabase) return
    await supabase.auth.signOut()
    router.push('/auth/login')
  }

  const handleConnectGoogle = async () => {
    try {
      setError(null)
      const { url } = await apiClient.getGoogleAuthUrl()
      // Open OAuth URL in same window
      window.location.href = url
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to connect Google Calendar')
    }
  }

  const handleSync = async () => {
    try {
      setSyncing(true)
      setError(null)
      await apiClient.syncCalendar()
      await loadTasks()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Sync failed')
    } finally {
      setSyncing(false)
    }
  }

  const handleSyncEmail = async () => {
    try {
      setSyncingEmail(true)
      setError(null)
      await apiClient.syncEmail()
      await loadTasks()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Email sync failed')
    } finally {
      setSyncingEmail(false)
    }
  }

  const handleRefreshMetrics = async () => {
    try {
      setRefreshingMetrics(true)
      setError(null)
      await loadMetrics()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to refresh metrics')
    } finally {
      setRefreshingMetrics(false)
    }
  }

  const loadDailyPlan = async () => {
    try {
      setPlanLoading(true)
      console.log('Loading plan for date:', today)
      const plan = await apiClient.getPlanForDate(today)
      console.log('Plan loaded:', plan ? `Plan for ${plan.plan_date}` : 'No plan found')
      setDailyPlan(plan)
    } catch (err) {
      // Plan might not exist yet
      console.log('Error loading plan:', err)
      setDailyPlan(null)
    } finally {
      setPlanLoading(false)
    }
  }

  const loadEnergyLevel = async () => {
    try {
      const energy = await apiClient.getEnergyLevelForDate(today)
      setEnergyLevel(energy)
    } catch (err) {
      // Energy level might not exist yet
      setEnergyLevel(null)
    }
  }

  const handleGeneratePlan = async () => {
    try {
      setPlanLoading(true)
      setError(null)
      await apiClient.generatePlan(today)
      await loadDailyPlan()
      await loadReminders() // Reload reminders after regenerating plan
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to generate plan')
    } finally {
      setPlanLoading(false)
    }
  }

  const handleUpdateTaskFlags = async (taskId: string, flags: { is_critical?: boolean; is_urgent?: boolean }) => {
    try {
      await apiClient.updateTaskFlags(taskId, flags)
      await loadTasks()
      await loadDailyPlan() // Reload plan to reflect changes
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update task flags')
    }
  }

  const loadReminders = async () => {
    try {
      setRemindersLoading(true)
      const remindersData = await apiClient.getRemindersForDate(today)
      setReminders(Array.isArray(remindersData) ? remindersData : [])
    } catch (err) {
      // Reminders might not exist yet
      console.log('Error loading reminders:', err)
      setReminders([])
    } finally {
      setRemindersLoading(false)
    }
  }

  const handleReminderConverted = async () => {
    // Reload reminders and regenerate plan to include the converted task
    await loadReminders()
    await loadDailyPlan()
  }

  const handleEnergyLevelSaved = () => {
    loadEnergyLevel()
    loadDailyPlan() // Regenerate plan with new energy level
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-purple-50 via-pink-50 to-blue-50">
      {/* Floating decorative elements */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-20 left-10 w-20 h-20 bg-purple-400/10 rounded-full blur-xl animate-float"></div>
        <div className="absolute top-40 right-20 w-32 h-32 bg-pink-400/10 rounded-full blur-2xl animate-float-reverse"></div>
        <div className="absolute bottom-20 left-1/4 w-24 h-24 bg-blue-400/10 rounded-full blur-xl animate-float"></div>
      </div>
      
      <div className="relative z-10 mx-auto max-w-7xl px-4 py-4 sm:py-6 lg:py-8 sm:px-6 lg:px-8">
        <div className="mb-6 sm:mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 animate-fade-in-up">
          <div>
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold">
              <span className="gradient-text">LifeFlow Dashboard</span>
            </h1>
            <p className="mt-1 sm:mt-2 text-sm sm:text-base text-gray-700">Manage your tasks and calendar integration</p>
          </div>
          {user && (
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-4">
              <span className="text-xs sm:text-sm text-gray-700 break-all">{user.email}</span>
              <button
                onClick={handleLogout}
                className="group relative w-full sm:w-auto px-6 py-2 border-2 border-purple-300 text-purple-700 font-semibold text-sm rounded-full backdrop-blur-sm transition-all duration-300 hover:border-purple-500 hover:bg-purple-50 hover:scale-110 focus:outline-none focus:ring-4 focus:ring-purple-500/50"
              >
                Sign Out
              </button>
            </div>
          )}
        </div>

        <div className="mb-4 sm:mb-6 grid gap-4 sm:gap-6 md:grid-cols-2">
          <div className="group relative rounded-2xl bg-white p-6 sm:p-8 shadow-lg transition-all duration-300 hover:shadow-2xl hover:scale-105 animate-scale-in">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
            <div className="relative z-10">
              <h2 className="text-xl sm:text-2xl font-bold mb-2">
                <span className="gradient-text">Calendar Integration</span>
              </h2>
              <p className="text-sm sm:text-base text-gray-700 mb-4">Connect and sync your Google Calendar events and emails</p>
              <div className="space-y-3">
                <button
                  onClick={handleConnectGoogle}
                  className="group relative w-full px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white font-bold text-sm sm:text-base rounded-full overflow-hidden transition-all duration-300 hover:scale-110 hover:shadow-xl hover:shadow-green-500/50 focus:outline-none focus:ring-4 focus:ring-green-500/50"
                >
                  <span className="relative z-10">Connect Google Calendar</span>
                </button>
                <button
                  onClick={handleSync}
                  disabled={syncing || syncingEmail}
                  className="group relative w-full px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold text-sm sm:text-base rounded-full overflow-hidden transition-all duration-300 hover:scale-110 hover:shadow-xl hover:shadow-purple-500/50 focus:outline-none focus:ring-4 focus:ring-purple-500/50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                >
                  <span className="relative z-10">{syncing ? 'Syncing...' : 'Sync Calendar'}</span>
                </button>
                <button
                  onClick={handleSyncEmail}
                  disabled={syncing || syncingEmail}
                  className="group relative w-full px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-bold text-sm sm:text-base rounded-full overflow-hidden transition-all duration-300 hover:scale-110 hover:shadow-xl hover:shadow-blue-500/50 focus:outline-none focus:ring-4 focus:ring-blue-500/50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                >
                  <span className="relative z-10">{syncingEmail ? 'Syncing...' : 'Sync Email'}</span>
                </button>
              </div>
            </div>
          </div>
          
          {metrics && (
            <div className="group relative rounded-2xl bg-white p-6 sm:p-8 shadow-lg transition-all duration-300 hover:shadow-2xl hover:scale-105 animate-scale-in" style={{ animationDelay: '100ms' }}>
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
              <div className="relative z-10">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl sm:text-2xl font-bold">
                    <span className="gradient-text">Ingestion Metrics</span>
                  </h2>
                  <button
                    onClick={handleRefreshMetrics}
                    disabled={refreshingMetrics}
                    className="px-3 py-1.5 text-xs sm:text-sm font-semibold text-purple-700 bg-purple-100 rounded-full border-2 border-purple-300 transition-all duration-300 hover:bg-purple-200 hover:border-purple-400 hover:scale-110 focus:outline-none focus:ring-4 focus:ring-purple-500/50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                    aria-label="Refresh metrics"
                  >
                    {refreshingMetrics ? 'Refreshing...' : 'Refresh'}
                  </button>
                </div>
                <div className="space-y-3 text-sm sm:text-base">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-700">Success Rate:</span>
                    <span className="font-bold text-purple-600">{metrics.success_rate?.toFixed(1) || 0}%</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-700">Total Events:</span>
                    <span className="font-bold text-gray-900">{metrics.total_events || 0}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-700">Successful:</span>
                    <span className="font-bold text-green-600">{metrics.successful_ingestions || 0}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-700">Failed:</span>
                    <span className="font-bold text-red-600">{metrics.failed_ingestions || 0}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="mb-4 sm:mb-6 grid gap-4 sm:gap-6 md:grid-cols-2">
          <EnergyLevelInput
            date={today}
            initialEnergyLevel={energyLevel?.energy_level}
            onSuccess={handleEnergyLevelSaved}
          />
          <DailyPlanView
            plan={dailyPlan}
            onRegenerate={handleGeneratePlan}
            loading={planLoading}
            expectedDate={today}
            onTaskUpdated={loadDailyPlan}
          />
        </div>

        <div className="mb-4 sm:mb-6">
          <TaskManagerIntegration />
        </div>

        <div className="mb-4 sm:mb-6 grid gap-4 sm:gap-6 md:grid-cols-2">
          <RemindersView
            reminders={reminders}
            loading={remindersLoading}
            expectedDate={today}
            onReminderConverted={handleReminderConverted}
          />
          <NotificationCenter autoRefresh={true} refreshInterval={30000} />
        </div>

        {error && (
          <div className="mb-4 rounded-2xl bg-red-50 border-2 border-red-200 p-4 shadow-lg animate-scale-in">
            <p className="text-sm font-medium text-red-800">{error}</p>
          </div>
        )}

        <RawTasksView
          tasks={tasks}
          loading={loading}
          onTaskFlagsUpdate={handleUpdateTaskFlags}
        />
      </div>
    </div>
  )
}

