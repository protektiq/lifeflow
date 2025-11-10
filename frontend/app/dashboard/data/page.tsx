"use client"

import { useEffect, useState } from 'react'
import { apiClient } from '@/src/lib/api'
import { RawTask } from '@/src/types/task'
import RawTasksView from '@/components/RawTasksView'

export const dynamic = 'force-dynamic'

export default function DataPage() {
  const [tasks, setTasks] = useState<RawTask[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshingMetrics, setRefreshingMetrics] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [metrics, setMetrics] = useState<any>(null)

  useEffect(() => {
    loadTasks()
    loadMetrics()
  }, [])

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
      setTasks(Array.isArray(response) ? response : response.tasks || [])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load tasks')
    } finally {
      setLoading(false)
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

  const handleUpdateTaskFlags = async (taskId: string, flags: { is_critical?: boolean; is_urgent?: boolean }) => {
    try {
      await apiClient.updateTaskFlags(taskId, flags)
      await loadTasks()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update task flags')
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-800 dark:text-gray-200 mb-2">Data</h2>
        <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400">View and manage your raw tasks and ingestion metrics</p>
      </div>

      {error && (
        <div className="mb-4 rounded-2xl bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 p-4 shadow-lg animate-scale-in">
          <p className="text-sm font-medium text-red-800 dark:text-red-300">{error}</p>
        </div>
      )}

      {metrics && (
        <div className="mb-6">
          <div className="group relative rounded-2xl bg-white dark:bg-gray-800 p-6 sm:p-8 shadow-lg dark:shadow-gray-900/50 transition-all duration-300 hover:shadow-2xl hover:scale-105 animate-scale-in">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-purple-500/10 dark:from-blue-500/20 dark:to-purple-500/20 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
            <div className="relative z-10">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl sm:text-2xl font-bold">
                  <span className="gradient-text">Ingestion Metrics</span>
                </h3>
                <button
                  onClick={handleRefreshMetrics}
                  disabled={refreshingMetrics}
                  className="px-3 py-1.5 text-xs sm:text-sm font-semibold text-purple-700 dark:text-purple-300 bg-purple-100 dark:bg-purple-900/30 rounded-full border-2 border-purple-300 dark:border-purple-600 transition-all duration-300 hover:bg-purple-200 dark:hover:bg-purple-900/50 hover:border-purple-400 dark:hover:border-purple-500 hover:scale-110 focus:outline-none focus:ring-4 focus:ring-purple-500/50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                  aria-label="Refresh metrics"
                >
                  {refreshingMetrics ? 'Refreshing...' : 'Refresh'}
                </button>
              </div>
              <div className="space-y-3 text-sm sm:text-base">
                <div className="flex justify-between items-center">
                  <span className="text-gray-700 dark:text-gray-300">Success Rate:</span>
                  <span className="font-bold text-purple-600 dark:text-purple-400">{metrics.success_rate?.toFixed(1) || 0}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-700 dark:text-gray-300">Total Events:</span>
                  <span className="font-bold text-gray-900 dark:text-gray-100">{metrics.total_events || 0}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-700 dark:text-gray-300">Successful:</span>
                  <span className="font-bold text-green-600 dark:text-green-400">{metrics.successful_ingestions || 0}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-700 dark:text-gray-300">Failed:</span>
                  <span className="font-bold text-red-600 dark:text-red-400">{metrics.failed_ingestions || 0}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <RawTasksView
        tasks={tasks}
        loading={loading}
        onTaskFlagsUpdate={handleUpdateTaskFlags}
      />
    </div>
  )
}

