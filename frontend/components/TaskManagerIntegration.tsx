"use client"

import { useState, useEffect } from 'react'
import { apiClient } from '@/src/lib/api'
import ConflictResolution from './ConflictResolution'
import { RawTask } from '@/src/types/task'

interface TodoistStatus {
  connected: boolean
  last_sync: string | null
  sync_status: string
  status_counts?: Record<string, number>
  conflicts_count?: number
  errors_count?: number
}

export default function TaskManagerIntegration() {
  const [status, setStatus] = useState<TodoistStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [connecting, setConnecting] = useState(false)
  const [disconnecting, setDisconnecting] = useState(false)
  const [showConflictResolution, setShowConflictResolution] = useState(false)
  const [conflicts, setConflicts] = useState<RawTask[]>([])

  useEffect(() => {
    loadStatus()
  }, [])

  const loadStatus = async () => {
    try {
      setLoading(true)
      setError(null)
      const statusData = await apiClient.getTodoistStatus()
      setStatus(statusData)
    } catch (err: any) {
      setError(err.message || 'Failed to load Todoist status')
    } finally {
      setLoading(false)
    }
  }

  const handleConnect = async () => {
    try {
      setConnecting(true)
      setError(null)
      const response = await apiClient.connectTodoist()
      // Redirect to Todoist OAuth
      if (response.url) {
        window.location.href = response.url
      }
    } catch (err: any) {
      setError(err.message || 'Failed to initiate Todoist connection')
      setConnecting(false)
    }
  }

  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect Todoist? This will stop syncing tasks.')) {
      return
    }

    try {
      setDisconnecting(true)
      setError(null)
      await apiClient.disconnectTodoist()
      await loadStatus()
    } catch (err: any) {
      setError(err.message || 'Failed to disconnect Todoist')
    } finally {
      setDisconnecting(false)
    }
  }

  const handleSync = async () => {
    try {
      setSyncing(true)
      setError(null)
      await apiClient.syncTodoist()
      await loadStatus()
      await loadConflicts()
    } catch (err: any) {
      setError(err.message || 'Failed to sync with Todoist')
    } finally {
      setSyncing(false)
    }
  }

  const loadConflicts = async () => {
    try {
      const tasks = await apiClient.getRawTasks()
      const conflictTasks = Array.isArray(tasks)
        ? tasks.filter((task: RawTask) => task.sync_status === 'conflict' && task.source === 'todoist')
        : []
      setConflicts(conflictTasks)
    } catch (err) {
      console.error('Failed to load conflicts:', err)
    }
  }

  const handleResolveConflicts = async () => {
    await loadConflicts()
    // Use a callback to check conflicts after they're loaded
    const conflictTasks = await apiClient.getRawTasks()
    const filteredConflicts = Array.isArray(conflictTasks)
      ? conflictTasks.filter((task: RawTask) => task.sync_status === 'conflict' && task.source === 'todoist')
      : []
    if (filteredConflicts.length > 0) {
      setConflicts(filteredConflicts)
      setShowConflictResolution(true)
    }
  }

  const handleConflictsResolved = async () => {
    setShowConflictResolution(false)
    await loadStatus()
    await loadConflicts()
  }

  useEffect(() => {
    if (status?.connected) {
      loadConflicts()
    }
  }, [status?.connected])

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow dark:shadow-gray-900/50 p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow dark:shadow-gray-900/50 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200">Todoist Integration</h2>
        {status?.connected && (
          <span className="px-3 py-1 text-sm font-medium text-green-800 dark:text-green-300 bg-green-100 dark:bg-green-900/30 rounded-full">
            Connected
          </span>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-red-700 dark:text-red-300 text-sm">
          {error}
        </div>
      )}

      {!status?.connected ? (
        <div>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Connect your Todoist account to sync tasks bidirectionally with LifeFlow.
          </p>
          <button
            onClick={handleConnect}
            disabled={connecting}
            className="px-4 py-2 bg-blue-600 dark:bg-blue-500 text-white rounded hover:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {connecting ? 'Connecting...' : 'Connect Todoist'}
          </button>
        </div>
      ) : (
        <div>
          <div className="mb-4 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">Sync Status:</span>
              <span className={`font-medium ${
                status.sync_status === 'synced' ? 'text-green-600 dark:text-green-400' : 
                status.sync_status === 'conflict' ? 'text-yellow-600 dark:text-yellow-400' : 
                'text-gray-600 dark:text-gray-400'
              }`}>
                {status.sync_status === 'synced' ? 'Synced' : 
                 status.sync_status === 'conflict' ? 'Conflicts' : 
                 status.sync_status || 'Pending'}
              </span>
            </div>
            
            {status.last_sync && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Last Sync:</span>
                <span className="text-gray-800 dark:text-gray-200">
                  {new Date(status.last_sync).toLocaleString()}
                </span>
              </div>
            )}

            {status.status_counts && Object.keys(status.status_counts).length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-2">Task Status:</div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(status.status_counts).map(([statusKey, count]) => (
                    <span
                      key={statusKey}
                      className="px-2 py-1 text-xs rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                    >
                      {statusKey}: {count}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {status.conflicts_count && status.conflicts_count > 0 && (
              <div className="mt-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                <div className="text-sm text-yellow-800 dark:text-yellow-300 mb-2">
                  {status.conflicts_count} conflict{status.conflicts_count !== 1 ? 's' : ''} detected.
                </div>
                <button
                  onClick={handleResolveConflicts}
                  className="px-4 py-2 bg-yellow-600 dark:bg-yellow-500 text-white text-sm font-semibold rounded hover:bg-yellow-700 dark:hover:bg-yellow-600 transition-colors"
                >
                  Resolve Conflicts
                </button>
              </div>
            )}

            {status.errors_count && status.errors_count > 0 && (
              <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-sm text-red-800 dark:text-red-300">
                {status.errors_count} sync error{status.errors_count !== 1 ? 's' : ''} detected.
              </div>
            )}
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleSync}
              disabled={syncing}
              className="px-4 py-2 bg-blue-600 dark:bg-blue-500 text-white rounded hover:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {syncing ? 'Syncing...' : 'Sync Now'}
            </button>
            <button
              onClick={handleDisconnect}
              disabled={disconnecting}
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {disconnecting ? 'Disconnecting...' : 'Disconnect'}
            </button>
          </div>
        </div>
      )}

      {/* Conflict Resolution Modal */}
      {showConflictResolution && conflicts.length > 0 && (
        <ConflictResolution
          conflicts={conflicts.map((task) => ({
            id: task.id,
            title: task.title,
            sync_status: task.sync_status || 'conflict',
            external_id: task.external_id,
            last_synced_at: task.last_synced_at || undefined,
            external_updated_at: task.external_updated_at || undefined,
            sync_error: task.sync_error || undefined,
          }))}
          onResolved={handleConflictsResolved}
          onClose={() => setShowConflictResolution(false)}
        />
      )}
    </div>
  )
}

