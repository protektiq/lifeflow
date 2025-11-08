"use client"

import { useState } from 'react'
import { apiClient } from '@/src/lib/api'

interface TaskFeedbackProps {
  taskId: string
  planId?: string
  onDone?: () => void
  onSnoozed?: () => void
  disabled?: boolean
}

export default function TaskFeedback({
  taskId,
  planId,
  onDone,
  onSnoozed,
  disabled = false,
}: TaskFeedbackProps) {
  const [loading, setLoading] = useState(false)
  const [showSnoozeMenu, setShowSnoozeMenu] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDone = async () => {
    try {
      setLoading(true)
      setError(null)
      await apiClient.markTaskDone(taskId, planId)
      onDone?.()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to mark task as done')
    } finally {
      setLoading(false)
    }
  }

  const handleSnooze = async (durationMinutes: number) => {
    try {
      setLoading(true)
      setError(null)
      setShowSnoozeMenu(false)
      await apiClient.snoozeTask(taskId, durationMinutes, planId)
      onSnoozed?.()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to snooze task')
      setShowSnoozeMenu(false)
    } finally {
      setLoading(false)
    }
  }

  const snoozeOptions = [
    { label: '5 minutes', minutes: 5 },
    { label: '15 minutes', minutes: 15 },
    { label: '30 minutes', minutes: 30 },
    { label: '1 hour', minutes: 60 },
  ]

  return (
    <div className="flex items-center gap-2">
      {error && (
        <span className="text-xs text-red-600" role="alert">
          {error}
        </span>
      )}
      <button
        onClick={handleDone}
        disabled={loading || disabled}
        className="rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
        aria-label="Mark task as done"
      >
        {loading ? '...' : 'Done'}
      </button>
      <div className="relative">
        <button
          onClick={() => setShowSnoozeMenu(!showSnoozeMenu)}
          disabled={loading || disabled}
          className="rounded-md bg-yellow-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Snooze task"
          aria-expanded={showSnoozeMenu}
        >
          {loading ? '...' : 'Snooze'}
        </button>
        {showSnoozeMenu && (
          <div className="absolute right-0 mt-1 w-40 rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 z-10">
            <div className="py-1" role="menu">
              {snoozeOptions.map((option) => (
                <button
                  key={option.minutes}
                  onClick={() => handleSnooze(option.minutes)}
                  className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  role="menuitem"
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

