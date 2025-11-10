"use client"

import { useState, useEffect } from 'react'
import { apiClient } from '@/src/lib/api'
import { X, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react'

interface ConflictTask {
  id: string
  title: string
  sync_status: string
  external_id?: string | null
  last_synced_at?: string | null
  external_updated_at?: string | null
  sync_error?: string | null
}

interface ConflictResolutionProps {
  conflicts: ConflictTask[]
  onResolved: () => void
  onClose: () => void
}

export default function ConflictResolution({
  conflicts,
  onResolved,
  onClose,
}: ConflictResolutionProps) {
  const [resolving, setResolving] = useState<Record<string, boolean>>({})
  const [error, setError] = useState<string | null>(null)

  const handleResolve = async (taskId: string, resolution: 'local' | 'external') => {
    try {
      setResolving((prev) => ({ ...prev, [taskId]: true }))
      setError(null)
      await apiClient.resolveConflict(taskId, resolution)
      onResolved()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to resolve conflict')
    } finally {
      setResolving((prev) => ({ ...prev, [taskId]: false }))
    }
  }

  const formatDateTime = (timeString: string | null | undefined) => {
    if (!timeString) return 'N/A'
    const date = new Date(timeString)
    return date.toLocaleString('en-US', {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="rounded-2xl bg-white dark:bg-gray-800 shadow-2xl dark:shadow-gray-900/50 max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white dark:bg-gray-800 border-b-2 border-yellow-200 dark:border-yellow-700 p-4 sm:p-6 flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="h-6 w-6 text-yellow-600 dark:text-yellow-400" />
              <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-gray-100">
                Resolve Sync Conflicts
              </h2>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {conflicts.length} conflict{conflicts.length !== 1 ? 's' : ''} detected. Choose which version to keep for each task.
            </p>
          </div>
          <button
            onClick={onClose}
            className="ml-4 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors flex-shrink-0"
            aria-label="Close"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 sm:p-6 space-y-4">
          {error && (
            <div className="rounded-xl bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 p-4 text-red-800 dark:text-red-300">
              {error}
            </div>
          )}

          {conflicts.length === 0 ? (
            <div className="py-12 text-center text-gray-600 dark:text-gray-400">
              <CheckCircle className="h-12 w-12 text-green-600 dark:text-green-400 mx-auto mb-4" />
              <p className="text-lg font-medium mb-2">No conflicts found</p>
              <p className="text-sm">All tasks are synced successfully.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {conflicts.map((task) => {
                const isResolving = resolving[task.id] || false
                
                return (
                  <div
                    key={task.id}
                    className="rounded-xl border-2 border-yellow-300 dark:border-yellow-600 bg-gradient-to-br from-yellow-50 to-orange-50 dark:from-yellow-900/30 dark:to-orange-900/30 p-4 sm:p-5"
                  >
                    <div className="mb-4">
                      <h3 className="text-base sm:text-lg font-bold text-gray-900 dark:text-gray-100 mb-2 break-words">
                        {task.title}
                      </h3>
                      <div className="space-y-1 text-xs sm:text-sm text-gray-600 dark:text-gray-400">
                        {task.external_id && (
                          <p>
                            <span className="font-semibold">External ID:</span>{' '}
                            <span className="font-mono">{task.external_id}</span>
                          </p>
                        )}
                        {task.last_synced_at && (
                          <p>
                            <span className="font-semibold">Last Synced:</span>{' '}
                            {formatDateTime(task.last_synced_at)}
                          </p>
                        )}
                        {task.external_updated_at && (
                          <p>
                            <span className="font-semibold">External Updated:</span>{' '}
                            {formatDateTime(task.external_updated_at)}
                          </p>
                        )}
                        {task.sync_error && (
                          <p className="text-red-600 dark:text-red-400">
                            <span className="font-semibold">Error:</span> {task.sync_error}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-col sm:flex-row gap-3">
                      <button
                        onClick={() => handleResolve(task.id, 'local')}
                        disabled={isResolving}
                        className="flex-1 px-4 py-2 bg-blue-600 dark:bg-blue-500 text-white font-semibold rounded-full transition-all duration-300 hover:bg-blue-700 dark:hover:bg-blue-600 hover:scale-105 focus:outline-none focus:ring-4 focus:ring-blue-500/50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center justify-center gap-2"
                      >
                        {isResolving ? (
                          <>
                            <RefreshCw className="h-4 w-4 animate-spin" />
                            <span>Resolving...</span>
                          </>
                        ) : (
                          <>
                            <CheckCircle className="h-4 w-4" />
                            <span>Use Local Version</span>
                          </>
                        )}
                      </button>
                      <button
                        onClick={() => handleResolve(task.id, 'external')}
                        disabled={isResolving}
                        className="flex-1 px-4 py-2 bg-green-600 dark:bg-green-500 text-white font-semibold rounded-full transition-all duration-300 hover:bg-green-700 dark:hover:bg-green-600 hover:scale-105 focus:outline-none focus:ring-4 focus:ring-green-500/50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center justify-center gap-2"
                      >
                        {isResolving ? (
                          <>
                            <RefreshCw className="h-4 w-4 animate-spin" />
                            <span>Resolving...</span>
                          </>
                        ) : (
                          <>
                            <CheckCircle className="h-4 w-4" />
                            <span>Use External Version</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-white dark:bg-gray-800 border-t-2 border-yellow-200 dark:border-yellow-700 p-4 sm:p-6">
          <button
            onClick={onClose}
            className="w-full px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold rounded-full transition-all duration-300 hover:scale-105 hover:shadow-xl hover:shadow-purple-500/50 focus:outline-none focus:ring-4 focus:ring-purple-500/50"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

