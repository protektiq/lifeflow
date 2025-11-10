"use client"

import { useState } from 'react'
import { apiClient } from '@/src/lib/api'
import TaskManagerIntegration from '@/components/TaskManagerIntegration'

export const dynamic = 'force-dynamic'

export default function IntegrationsPage() {
  const [syncing, setSyncing] = useState(false)
  const [syncingEmail, setSyncingEmail] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleConnectGoogle = async () => {
    try {
      setError(null)
      const { url } = await apiClient.getGoogleAuthUrl()
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
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Email sync failed')
    } finally {
      setSyncingEmail(false)
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-800 dark:text-gray-200 mb-2">Integrations</h2>
        <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400">Connect and manage your calendar and task manager integrations</p>
      </div>

      {error && (
        <div className="mb-4 rounded-2xl bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 p-4 shadow-lg animate-scale-in">
          <p className="text-sm font-medium text-red-800 dark:text-red-300">{error}</p>
        </div>
      )}

      <div className="grid gap-4 sm:gap-6 md:grid-cols-2">
        {/* Calendar Integration */}
        <div className="group relative rounded-2xl bg-white dark:bg-gray-800 p-6 sm:p-8 shadow-lg dark:shadow-gray-900/50 transition-all duration-300 hover:shadow-2xl hover:scale-105 animate-scale-in">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-pink-500/10 dark:from-purple-500/20 dark:to-pink-500/20 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          <div className="relative z-10">
            <h3 className="text-xl sm:text-2xl font-bold mb-2">
              <span className="gradient-text">Calendar Integration</span>
            </h3>
            <p className="text-sm sm:text-base text-gray-700 dark:text-gray-300 mb-4">Connect and sync your Google Calendar events and emails</p>
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

        {/* Task Manager Integration */}
        <div className="animate-scale-in" style={{ animationDelay: '100ms' }}>
          <TaskManagerIntegration />
        </div>
      </div>
    </div>
  )
}

