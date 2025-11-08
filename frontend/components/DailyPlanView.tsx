"use client"

import { useState } from 'react'
import { DailyPlan, DailyPlanTask } from '@/src/types/plan'
import TaskFeedback from './TaskFeedback'

interface DailyPlanViewProps {
  plan: DailyPlan | null
  onRegenerate?: () => void
  loading?: boolean
  expectedDate?: string // Expected date to validate against
  onTaskUpdated?: () => void // Callback when task is marked done or snoozed
}

export default function DailyPlanView({
  plan,
  onRegenerate,
  loading = false,
  expectedDate,
  onTaskUpdated,
}: DailyPlanViewProps) {
  const [taskStatuses, setTaskStatuses] = useState<Record<string, string>>({})
  if (loading) {
    return (
      <div className="rounded-lg bg-white p-6 shadow-sm">
        <div className="flex items-center justify-center py-8">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent"></div>
        </div>
      </div>
    )
  }

  if (!plan) {
    return (
      <div className="rounded-lg bg-white p-6 shadow-sm">
        <div className="text-center py-8">
          <p className="text-gray-500">
            No plan generated for {expectedDate ? new Date(expectedDate).toLocaleDateString() : 'today'}
          </p>
          {onRegenerate && (
            <button
              onClick={onRegenerate}
              className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Generate Plan
            </button>
          )}
        </div>
      </div>
    )
  }

  // Check if plan is for the expected date
  // Handle different date formats: Date object, ISO string, or date string
  let planDateStr: string
  if (plan.plan_date instanceof Date) {
    const year = plan.plan_date.getFullYear()
    const month = String(plan.plan_date.getMonth() + 1).padStart(2, '0')
    const day = String(plan.plan_date.getDate()).padStart(2, '0')
    planDateStr = `${year}-${month}-${day}`
  } else if (typeof plan.plan_date === 'string') {
    planDateStr = plan.plan_date.split('T')[0] // Handle ISO strings
  } else {
    planDateStr = String(plan.plan_date)
  }
  console.log('DailyPlanView - Raw plan.plan_date:', plan.plan_date, 'Parsed planDateStr:', planDateStr, 'Expected date:', expectedDate, 'Match:', planDateStr === expectedDate)
  const datesMatch = expectedDate && planDateStr === expectedDate
  console.log('DailyPlanView - datesMatch:', datesMatch, 'Will show mismatch UI:', expectedDate && !datesMatch)
  if (expectedDate && !datesMatch) {
    return (
      <div className="rounded-lg bg-white p-6 shadow-sm">
        <div className="text-center py-8">
          <p className="text-gray-500 mb-4">
            Plan shown is for {formatDate(planDateStr)}, but today is {formatDate(expectedDate)}
          </p>
          <p className="text-sm text-gray-400 mb-4">
            Plan date: {planDateStr} | Expected: {expectedDate}
          </p>
          {onRegenerate ? (
            <button
              onClick={onRegenerate}
              className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Generate Plan for Today
            </button>
          ) : (
            <p className="text-sm text-red-500">onRegenerate callback not provided</p>
          )}
        </div>
      </div>
    )
  }

  const formatDate = (dateString: string) => {
    // Parse date string as local date (not UTC) to avoid timezone issues
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
    // Parse the ISO string - JavaScript Date constructor handles UTC times correctly
    // If timeString includes timezone info (e.g., +00:00 or Z), it will be parsed as UTC
    // If not, it will be parsed as local time
    const date = new Date(timeString)
    
    // Ensure we're displaying in local timezone
    // Use toLocaleTimeString with explicit timezone options
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone, // Use browser's timezone
    })
  }

  const getEnergyLevelColor = (level: number | null) => {
    if (!level) return 'bg-gray-200'
    if (level <= 2) return 'bg-red-200'
    if (level === 3) return 'bg-yellow-200'
    return 'bg-green-200'
  }

  const sortedTasks = [...plan.tasks].sort(
    (a, b) => new Date(a.predicted_start).getTime() - new Date(b.predicted_start).getTime()
  )
  
  // Debug: Log task dates
  console.log('DailyPlanView - Plan tasks count:', sortedTasks.length)
  sortedTasks.forEach((t, idx) => {
    const startDate = t.predicted_start ? new Date(t.predicted_start) : null
    const dateStr = startDate ? startDate.toLocaleDateString() : 'N/A'
    const dateOnly = startDate ? startDate.toISOString().split('T')[0] : 'N/A'
    console.log(`  Task ${idx + 1}: "${t.title}" - Start: ${t.predicted_start} (Date: ${dateStr}, ISO date: ${dateOnly})`)
  })

  return (
    <div className="rounded-lg bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Daily Plan</h3>
          <p className="text-sm text-gray-600">
            {formatDate(planDateStr)}
          </p>
        </div>
        <div className="flex items-center gap-4">
          {plan.energy_level && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Energy:</span>
              <div
                className={`rounded-full px-3 py-1 text-sm font-medium ${getEnergyLevelColor(plan.energy_level)}`}
              >
                {plan.energy_level}/5
              </div>
            </div>
          )}
          {onRegenerate && (
            <button
              onClick={onRegenerate}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Regenerate
            </button>
          )}
        </div>
      </div>

      <div className="space-y-3">
        {sortedTasks.map((task, index) => {
          const taskStatus = taskStatuses[task.task_id] || (task as any).status || 'pending'
          const isDone = taskStatus === 'done'
          const isSnoozed = taskStatus === 'snoozed'
          
          return (
            <div
              key={`${task.task_id}-${index}`}
              className={`rounded-lg border p-4 ${
                isDone
                  ? 'border-gray-300 bg-gray-100 opacity-75'
                  : task.is_critical
                  ? 'border-red-300 bg-red-50'
                  : task.is_urgent
                  ? 'border-orange-300 bg-orange-50'
                  : 'border-gray-200 bg-gray-50'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className={`font-medium ${isDone ? 'line-through text-gray-500' : 'text-gray-900'}`}>
                      {task.title}
                    </h4>
                    {isDone && (
                      <span className="rounded-full bg-green-600 px-2 py-0.5 text-xs font-medium text-white">
                        Done
                      </span>
                    )}
                    {isSnoozed && (
                      <span className="rounded-full bg-yellow-600 px-2 py-0.5 text-xs font-medium text-white">
                        Snoozed
                      </span>
                    )}
                    {!isDone && !isSnoozed && task.is_critical && (
                      <span className="rounded-full bg-red-600 px-2 py-0.5 text-xs font-medium text-white">
                        Critical
                      </span>
                    )}
                    {!isDone && !isSnoozed && task.is_urgent && (
                      <span className="rounded-full bg-orange-600 px-2 py-0.5 text-xs font-medium text-white">
                        Urgent
                      </span>
                    )}
                  </div>
                  <div className="mt-1 flex items-center gap-4 text-sm text-gray-600">
                    <span>
                      {formatTime(task.predicted_start)} - {formatTime(task.predicted_end)}
                    </span>
                    <span className="text-xs">Priority: {(task.priority_score * 100).toFixed(0)}%</span>
                  </div>
                </div>
                {!isDone && (
                  <div className="ml-4">
                    <TaskFeedback
                      taskId={task.task_id}
                      planId={plan.id}
                      onDone={() => {
                        setTaskStatuses((prev) => ({ ...prev, [task.task_id]: 'done' }))
                        onTaskUpdated?.()
                      }}
                      onSnoozed={() => {
                        setTaskStatuses((prev) => ({ ...prev, [task.task_id]: 'snoozed' }))
                        onTaskUpdated?.()
                      }}
                    />
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {sortedTasks.length === 0 && (
        <div className="py-8 text-center text-gray-500">No tasks scheduled for this day</div>
      )}
    </div>
  )
}

