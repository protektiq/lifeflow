"use client"

import { useState, useEffect } from 'react'
import { apiClient } from '@/src/lib/api'
import { RawTask } from '@/src/types/task'
import { X, Clock, MapPin, Users, Calendar, CheckCircle, Clock as ClockIcon } from 'lucide-react'

interface TaskFeedback {
  id: string
  user_id: string
  task_id: string
  plan_id: string | null
  action: string
  snooze_duration_minutes: number | null
  feedback_at: string
  created_at: string
}

interface TaskDetailViewProps {
  taskId: string
  onClose: () => void
  onTaskUpdated?: () => void
}

export default function TaskDetailView({
  taskId,
  onClose,
  onTaskUpdated,
}: TaskDetailViewProps) {
  const [task, setTask] = useState<RawTask | null>(null)
  const [feedback, setFeedback] = useState<TaskFeedback[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadTaskDetails()
  }, [taskId])

  const loadTaskDetails = async () => {
    try {
      setLoading(true)
      setError(null)
      const [taskData, feedbackData] = await Promise.all([
        apiClient.getRawTask(taskId),
        apiClient.getTaskFeedback(taskId),
      ])
      setTask(taskData)
      setFeedback(Array.isArray(feedbackData) ? feedbackData : [])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load task details')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  const formatTime = (timeString: string) => {
    const date = new Date(timeString)
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    })
  }

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString)
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

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
        <div className="rounded-2xl bg-white dark:bg-gray-800 p-8 shadow-2xl dark:shadow-gray-900/50">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-purple-600 dark:border-purple-400 border-t-transparent"></div>
        </div>
      </div>
    )
  }

  if (error || !task) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
        <div className="rounded-2xl bg-white dark:bg-gray-800 p-6 sm:p-8 shadow-2xl dark:shadow-gray-900/50 max-w-md w-full mx-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">Error</h2>
            <button
              onClick={onClose}
              className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
              aria-label="Close"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
          <p className="text-red-600 dark:text-red-400 mb-4">{error || 'Task not found'}</p>
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-purple-600 dark:bg-purple-500 text-white rounded-full font-semibold hover:bg-purple-700 dark:hover:bg-purple-600 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="rounded-2xl bg-white dark:bg-gray-800 shadow-2xl dark:shadow-gray-900/50 max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white dark:bg-gray-800 border-b-2 border-purple-200 dark:border-purple-700 p-4 sm:p-6 flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2 break-words">
              {task.title}
            </h2>
            <div className="flex flex-wrap items-center gap-2">
              {task.is_critical && (
                <span className="rounded-full bg-gradient-to-r from-red-500 to-pink-500 px-3 py-1 text-xs font-bold text-white">
                  Critical
                </span>
              )}
              {task.is_urgent && (
                <span className="rounded-full bg-gradient-to-r from-orange-500 to-yellow-500 px-3 py-1 text-xs font-bold text-white">
                  Urgent
                </span>
              )}
              {task.is_spam && (
                <span className="rounded-full bg-gray-500 px-3 py-1 text-xs font-bold text-white">
                  Spam
                </span>
              )}
              {task.extracted_priority && (
                <span className="rounded-full bg-gradient-to-r from-blue-500 to-purple-500 px-3 py-1 text-xs font-bold text-white">
                  {task.extracted_priority}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="ml-4 text-gray-400 hover:text-gray-600 transition-colors flex-shrink-0"
            aria-label="Close"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 sm:p-6 space-y-6">
          {/* Task Details */}
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-gray-900">Task Details</h3>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex items-start gap-2">
                <Clock className="h-5 w-5 text-purple-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-gray-700">Time</p>
                  <p className="text-sm text-gray-600">
                    {formatTime(task.start_time)} - {formatTime(task.end_time)}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">{formatDate(task.start_time)}</p>
                </div>
              </div>

              {task.location && (
                <div className="flex items-start gap-2">
                  <MapPin className="h-5 w-5 text-purple-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-semibold text-gray-700">Location</p>
                    <p className="text-sm text-gray-600 break-words">{task.location}</p>
                  </div>
                </div>
              )}

              {task.attendees.length > 0 && (
                <div className="flex items-start gap-2">
                  <Users className="h-5 w-5 text-purple-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-semibold text-gray-700">Attendees</p>
                    <p className="text-sm text-gray-600">{task.attendees.join(', ')}</p>
                  </div>
                </div>
              )}

              <div className="flex items-start gap-2">
                <Calendar className="h-5 w-5 text-purple-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-gray-700">Source</p>
                  <p className="text-sm text-gray-600 capitalize">{task.source}</p>
                </div>
              </div>
            </div>

            {task.description && (
              <div>
                <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Description</p>
                <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap">{task.description}</p>
              </div>
            )}

            {task.recurrence_pattern && (
              <div>
                <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Recurrence</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">{task.recurrence_pattern}</p>
              </div>
            )}

            {task.spam_reason && (
              <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 p-3">
                <p className="text-sm font-semibold text-red-700 dark:text-red-300 mb-1">Spam Reason</p>
                <p className="text-sm text-red-600 dark:text-red-400">{task.spam_reason}</p>
                {task.spam_score !== null && (
                  <p className="text-xs text-red-500 dark:text-red-400 mt-1">Score: {task.spam_score}</p>
                )}
              </div>
            )}

            {/* Sync Status */}
            {(task.sync_status || task.external_id) && (
              <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-200 dark:border-blue-800 p-3">
                <p className="text-sm font-semibold text-blue-700 dark:text-blue-300 mb-2">Sync Status</p>
                <div className="space-y-1 text-sm text-blue-600 dark:text-blue-400">
                  {task.sync_status && <p>Status: <span className="font-medium capitalize">{task.sync_status}</span></p>}
                  {task.external_id && <p>External ID: <span className="font-mono text-xs">{task.external_id}</span></p>}
                  {task.last_synced_at && <p>Last Synced: {formatDateTime(task.last_synced_at)}</p>}
                  {task.sync_error && <p className="text-red-600 dark:text-red-400">Error: {task.sync_error}</p>}
                </div>
              </div>
            )}
          </div>

          {/* Feedback History */}
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">Feedback History</h3>
            {feedback.length === 0 ? (
              <p className="text-sm text-gray-600 dark:text-gray-400">No feedback recorded yet.</p>
            ) : (
              <div className="space-y-3">
                {feedback.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-lg border-2 border-purple-200 dark:border-purple-700 bg-purple-50 dark:bg-purple-900/30 p-4"
                  >
                    <div className="flex items-start gap-3">
                      {item.action === 'done' ? (
                        <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                      ) : (
                        <ClockIcon className="h-5 w-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-semibold text-gray-900 dark:text-gray-100 capitalize">
                            {item.action === 'done' ? 'Marked as Done' : 'Snoozed'}
                          </span>
                          {item.snooze_duration_minutes && (
                            <span className="text-xs text-gray-600 dark:text-gray-400">
                              ({item.snooze_duration_minutes} minutes)
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          {formatDateTime(item.feedback_at)}
                        </p>
                        {item.plan_id && (
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            Plan ID: <span className="font-mono">{item.plan_id}</span>
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-white dark:bg-gray-800 border-t-2 border-purple-200 dark:border-purple-700 p-4 sm:p-6">
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

