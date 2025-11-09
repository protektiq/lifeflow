"use client"

import { useState } from 'react'
import { Reminder } from '@/src/types/plan'
import { apiClient } from '@/src/lib/api'

interface RemindersViewProps {
  reminders: Reminder[]
  loading?: boolean
  expectedDate?: string
  onReminderConverted?: () => void // Callback when reminder is converted to task
}

export default function RemindersView({
  reminders,
  loading = false,
  expectedDate,
  onReminderConverted,
}: RemindersViewProps) {
  const [convertingIds, setConvertingIds] = useState<Set<string>>(new Set())

  const formatDate = (dateString: string) => {
    const [year, month, day] = dateString.split('T')[0].split('-').map(Number)
    const date = new Date(year, month - 1, day)
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

  const handleConvertToTask = async (reminderId: string) => {
    try {
      setConvertingIds((prev) => new Set(prev).add(reminderId))
      await apiClient.convertReminderToTask(reminderId)
      onReminderConverted?.()
    } catch (error) {
      console.error('Failed to convert reminder to task:', error)
      alert('Failed to convert reminder to task. Please try again.')
    } finally {
      setConvertingIds((prev) => {
        const next = new Set(prev)
        next.delete(reminderId)
        return next
      })
    }
  }

  if (loading) {
    return (
      <div className="rounded-2xl bg-white p-6 sm:p-8 shadow-lg animate-scale-in">
        <div className="flex items-center justify-center py-8">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-purple-600 border-t-transparent"></div>
        </div>
      </div>
    )
  }

  const sortedReminders = [...reminders].sort((a, b) => {
    if (a.is_all_day && !b.is_all_day) return -1
    if (!a.is_all_day && b.is_all_day) return 1
    return new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
  })

  return (
    <div className="group relative rounded-2xl bg-white p-6 sm:p-8 shadow-lg transition-all duration-300 hover:shadow-2xl hover:scale-105 animate-scale-in">
      <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
      <div className="relative z-10">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h3 className="text-lg sm:text-xl font-bold mb-1">
              <span className="gradient-text">Reminders</span>
            </h3>
            <p className="text-sm sm:text-base text-gray-700">
              {expectedDate ? formatDate(expectedDate) : 'Today'}
            </p>
          </div>
        </div>

        <div className="space-y-4">
          {sortedReminders.map((reminder, index) => {
            const isConverting = convertingIds.has(reminder.id)

            return (
              <div
                key={reminder.id}
                className="rounded-xl border-2 border-purple-300 bg-gradient-to-br from-purple-50 to-pink-50 p-4 sm:p-5 shadow-md transition-all duration-300 hover:shadow-lg animate-scale-in"
                style={{ animationDelay: `${index * 50}ms` }}
              >
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <svg
                      className="h-4 w-4 sm:h-5 sm:w-5 text-purple-600 flex-shrink-0"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                      />
                    </svg>
                    <h4 className="text-sm sm:text-base font-bold text-gray-900 break-words">{reminder.title}</h4>
                    <span className="rounded-full bg-gradient-to-r from-purple-500 to-pink-500 px-3 py-1 text-xs font-bold text-white whitespace-nowrap shadow-md">
                      Reminder
                    </span>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-2 sm:gap-4 text-xs sm:text-sm text-gray-600">
                    {reminder.is_all_day ? (
                      <span>All day</span>
                    ) : (
                      <span>
                        {formatTime(reminder.start_time)} - {formatTime(reminder.end_time)}
                      </span>
                    )}
                  </div>
                  {reminder.description && (
                    <p className="mt-2 text-xs sm:text-sm text-gray-600 break-words">{reminder.description}</p>
                  )}
                </div>
                <div className="w-full sm:w-auto sm:ml-4 flex justify-start sm:justify-end">
                  <button
                    onClick={() => handleConvertToTask(reminder.id)}
                    disabled={isConverting}
                    className="w-full sm:w-auto px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold text-xs sm:text-sm rounded-full transition-all duration-300 hover:scale-110 hover:shadow-xl hover:shadow-purple-500/50 focus:outline-none focus:ring-4 focus:ring-purple-500/50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                  >
                    {isConverting ? 'Converting...' : 'Convert to Task'}
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>

        {sortedReminders.length === 0 && (
          <div className="py-8 text-center text-gray-600 font-medium">No reminders for this day</div>
        )}
      </div>
    </div>
  )
}

