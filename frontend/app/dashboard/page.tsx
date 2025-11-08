"use client"

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/src/lib/api'
import { RawTask } from '@/src/types/task'
import { createClient } from '@/src/lib/supabase/client'

export default function DashboardPage() {
  const router = useRouter()
  const supabase = createClient()
  const [tasks, setTasks] = useState<RawTask[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [user, setUser] = useState<any>(null)
  const [metrics, setMetrics] = useState<any>(null)

  useEffect(() => {
    checkUser()
    loadTasks()
    loadMetrics()
  }, [])

  const checkUser = async () => {
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

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">LifeFlow Dashboard</h1>
            <p className="mt-2 text-gray-600">Manage your tasks and calendar integration</p>
          </div>
          {user && (
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600">{user.email}</span>
              <button
                onClick={handleLogout}
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Sign Out
              </button>
            </div>
          )}
        </div>

        <div className="mb-6 grid gap-6 md:grid-cols-2">
          <div className="rounded-lg bg-white p-6 shadow">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Calendar Integration</h2>
            <p className="text-sm text-gray-600 mb-4">Connect and sync your Google Calendar events</p>
            <div className="space-y-2">
              <button
                onClick={handleConnectGoogle}
                className="w-full rounded-md bg-green-600 px-4 py-2 font-medium text-white hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
              >
                Connect Google Calendar
              </button>
              <button
                onClick={handleSync}
                disabled={syncing}
                className="w-full rounded-md bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
              >
                {syncing ? 'Syncing...' : 'Sync Calendar'}
              </button>
            </div>
          </div>
          
          {metrics && (
            <div className="rounded-lg bg-white p-6 shadow">
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Ingestion Metrics</h2>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Success Rate:</span>
                  <span className="font-medium">{metrics.success_rate?.toFixed(1) || 0}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Events:</span>
                  <span className="font-medium">{metrics.total_events || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Successful:</span>
                  <span className="font-medium text-green-600">{metrics.successful_ingestions || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Failed:</span>
                  <span className="font-medium text-red-600">{metrics.failed_ingestions || 0}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="mb-4 rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        <div className="rounded-lg bg-white shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Raw Tasks</h2>
            <p className="text-sm text-gray-600">
              {tasks.length} task{tasks.length !== 1 ? 's' : ''} ingested
            </p>
          </div>

          {loading ? (
            <div className="px-6 py-8 text-center text-gray-500">Loading tasks...</div>
          ) : tasks.length === 0 ? (
            <div className="px-6 py-8 text-center text-gray-500">
              No tasks found. Sync your calendar to get started.
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {tasks.map((task) => (
                <div key={task.id} className="px-6 py-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="text-sm font-medium text-gray-900">{task.title}</h3>
                      {task.description && (
                        <p className="mt-1 text-sm text-gray-600">{task.description}</p>
                      )}
                      <div className="mt-2 flex flex-wrap gap-2 text-xs text-gray-500">
                        <span>
                          {new Date(task.start_time).toLocaleString()}
                        </span>
                        {task.location && <span>• {task.location}</span>}
                        {task.attendees.length > 0 && (
                          <span>• {task.attendees.length} attendee{task.attendees.length !== 1 ? 's' : ''}</span>
                        )}
                        {task.extracted_priority && (
                          <span className="rounded bg-blue-100 px-2 py-0.5 text-blue-800">
                            {task.extracted_priority}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

