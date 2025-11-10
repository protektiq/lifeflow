"use client"

import { useState } from 'react'
import { DailyPlan, DailyPlanTask } from '@/src/types/plan'
import TaskFeedback from './TaskFeedback'
import PlansHistory from './PlansHistory'
import { apiClient } from '@/src/lib/api'
import { History } from 'lucide-react'

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
  const [showHistory, setShowHistory] = useState(false)
  const [updatingStatus, setUpdatingStatus] = useState(false)
  if (loading) {
    return (
      <div className="rounded-2xl bg-white dark:bg-gray-800 p-6 sm:p-8 shadow-lg dark:shadow-gray-900/50 animate-scale-in">
        <div className="flex items-center justify-center py-8">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-purple-600 dark:border-purple-400 border-t-transparent"></div>
        </div>
      </div>
    )
  }

  if (!plan) {
    return (
      <div className="group relative rounded-2xl bg-white dark:bg-gray-800 p-6 sm:p-8 shadow-lg dark:shadow-gray-900/50 transition-all duration-300 hover:shadow-2xl hover:scale-105 animate-scale-in">
        <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-pink-500/10 dark:from-purple-500/20 dark:to-pink-500/20 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
        <div className="relative z-10 text-center py-8">
          <p className="text-gray-700 dark:text-gray-300 mb-4">
            No plan generated for {expectedDate ? new Date(expectedDate).toLocaleDateString() : 'today'}
          </p>
          {onRegenerate && (
            <button
              onClick={onRegenerate}
              className="px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold text-sm sm:text-base rounded-full transition-all duration-300 hover:scale-110 hover:shadow-xl hover:shadow-purple-500/50 focus:outline-none focus:ring-4 focus:ring-purple-500/50"
            >
              Generate Plan
            </button>
          )}
        </div>
      </div>
    )
  }

  // Helper function to format date strings
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

  // Check if plan is for the expected date
  // Handle different date formats: Date object, ISO string, or date string
  let planDateStr: string
  // Use type assertion for runtime instanceof check since TypeScript types plan_date as string
  const planDate = plan.plan_date as any
  if (planDate instanceof Date) {
    const year = planDate.getFullYear()
    const month = String(planDate.getMonth() + 1).padStart(2, '0')
    const day = String(planDate.getDate()).padStart(2, '0')
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
      <div className="group relative rounded-2xl bg-white dark:bg-gray-800 p-6 sm:p-8 shadow-lg dark:shadow-gray-900/50 transition-all duration-300 hover:shadow-2xl hover:scale-105 animate-scale-in">
        <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-pink-500/10 dark:from-purple-500/20 dark:to-pink-500/20 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
        <div className="relative z-10 text-center py-8">
          <p className="text-gray-700 dark:text-gray-300 mb-4">
            Plan shown is for {formatDate(planDateStr)}, but today is {formatDate(expectedDate)}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Plan date: {planDateStr} | Expected: {expectedDate}
          </p>
          {onRegenerate ? (
            <button
              onClick={onRegenerate}
              className="px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold text-sm sm:text-base rounded-full transition-all duration-300 hover:scale-110 hover:shadow-xl hover:shadow-purple-500/50 focus:outline-none focus:ring-4 focus:ring-purple-500/50"
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

  // Filter out spam/promotional tasks
  // This is a safety measure in case API filtering didn't catch everything
  const isPromotionalTask = (title: string): boolean => {
    const titleLower = title.toLowerCase()
    
    // Promotional phrases that indicate spam
    const promotionalPatterns = [
      'consider purchasing',
      'purchasing the',
      'lifetime membership',
      'percent off',
      '% off',
      'snag your spot',
      'art in action',
      'start bidding',
      'review the rachael ray',
      'rachael ray nutrish',
      'dry dog food',
      'activate the',
      'activate your',
      'limited-time offer',
      'limited time offer',
      'statement credits',
      'earn back',
      'earn 5%',
      'earn 5 %',
    ]
    
    // Check if title contains promotional patterns
    for (const pattern of promotionalPatterns) {
      if (titleLower.includes(pattern)) {
        return true
      }
    }
    
    // Check for very long product review titles (likely promotional)
    if (titleLower.includes('review the') && title.length > 60) {
      // Check for product-related words
      const productWords = ['product', 'dry', 'food', 'protein', 'high', 'stages', 'beef', 'venison', 'lamb']
      if (productWords.some(word => titleLower.includes(word))) {
        return true
      }
    }
    
    return false
  }
  
  const filteredTasks = plan.tasks.filter((task) => {
    // If task has spam flag, exclude it
    if ((task as any).is_spam === true) {
      return false
    }
    
    // Check title for promotional patterns (fallback detection)
    if (isPromotionalTask(task.title)) {
      console.log('DailyPlanView - Filtering promotional task:', task.title)
      return false
    }
    
    return true
  })
  
  const sortedTasks = [...filteredTasks].sort(
    (a, b) => new Date(a.predicted_start).getTime() - new Date(b.predicted_start).getTime()
  )
  
  // Debug: Log task dates
  console.log('DailyPlanView - Plan tasks count:', sortedTasks.length, '(filtered from', plan.tasks.length, 'total)')
  sortedTasks.forEach((t, idx) => {
    const startDate = t.predicted_start ? new Date(t.predicted_start) : null
    const dateStr = startDate ? startDate.toLocaleDateString() : 'N/A'
    const dateOnly = startDate ? startDate.toISOString().split('T')[0] : 'N/A'
    console.log(`  Task ${idx + 1}: "${t.title}" - Start: ${t.predicted_start} (Date: ${dateStr}, ISO date: ${dateOnly})`)
  })

  return (
    <div className="group relative rounded-2xl bg-white dark:bg-gray-800 p-6 sm:p-8 shadow-lg dark:shadow-gray-900/50 transition-all duration-300 hover:shadow-2xl hover:scale-105 animate-scale-in">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-purple-500/10 dark:from-blue-500/20 dark:to-purple-500/20 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
      <div className="relative z-10">
        {/* Header Row: Title and History */}
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <h3 className="text-lg sm:text-xl font-bold">
              <span className="gradient-text">Daily Plan</span>
            </h3>
            <button
              onClick={() => setShowHistory(true)}
              className="flex items-center gap-1 px-2 py-1 text-xs font-semibold text-purple-700 dark:text-purple-300 bg-purple-100 dark:bg-purple-900/30 rounded-full border-2 border-purple-300 dark:border-purple-600 transition-all duration-300 hover:bg-purple-200 dark:hover:bg-purple-900/50 hover:border-purple-400 dark:hover:border-purple-500 hover:scale-110 focus:outline-none focus:ring-4 focus:ring-purple-500/50"
              aria-label="View plans history"
            >
              <History className="h-3 w-3" />
              <span className="hidden sm:inline">History</span>
            </button>
          </div>
          {onRegenerate && (
            <button
              onClick={onRegenerate}
              className="px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold text-xs sm:text-sm rounded-full transition-all duration-300 hover:scale-110 hover:shadow-xl hover:shadow-purple-500/50 focus:outline-none focus:ring-4 focus:ring-purple-500/50 whitespace-nowrap"
            >
              Regenerate
            </button>
          )}
        </div>

        {/* Second Row: Date and Status Controls */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <p className="text-sm sm:text-base text-gray-700 dark:text-gray-300">
            {formatDate(planDateStr)}
          </p>
          <div className="flex flex-wrap items-center gap-3 sm:gap-4">
            {plan.energy_level && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">Energy:</span>
                <div
                  className={`rounded-full px-3 py-1.5 text-sm font-bold border-2 ${
                    plan.energy_level <= 2
                      ? 'bg-red-100 dark:bg-red-900/30 border-red-300 dark:border-red-600 text-red-700 dark:text-red-300'
                      : plan.energy_level === 3
                      ? 'bg-yellow-100 dark:bg-yellow-900/30 border-yellow-300 dark:border-yellow-600 text-yellow-700 dark:text-yellow-300'
                      : 'bg-green-100 dark:bg-green-900/30 border-green-300 dark:border-green-600 text-green-700 dark:text-green-300'
                  }`}
                >
                  {plan.energy_level}/5
                </div>
              </div>
            )}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">Status:</span>
              <select
                value={plan.status}
                onChange={async (e) => {
                  try {
                    setUpdatingStatus(true)
                    await apiClient.updatePlanStatus(plan.id, e.target.value)
                    onTaskUpdated?.()
                  } catch (err) {
                    console.error('Failed to update plan status:', err)
                  } finally {
                    setUpdatingStatus(false)
                  }
                }}
                disabled={updatingStatus}
                className="rounded-full px-3 py-1.5 text-sm font-bold border-2 bg-white dark:bg-gray-800 border-purple-300 dark:border-purple-600 text-gray-700 dark:text-gray-300 focus:border-purple-500 dark:focus:border-purple-500 focus:outline-none focus:ring-4 focus:ring-purple-500/50 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <option value="active">Active</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
          </div>
        </div>

      <div className="space-y-4">
        {sortedTasks.map((task, index) => {
          const taskStatus = taskStatuses[task.task_id] || (task as any).status || 'pending'
          const isDone = taskStatus === 'done'
          const isSnoozed = taskStatus === 'snoozed'
          
          return (
            <div
              key={`${task.task_id}-${index}`}
              className={`rounded-xl border-2 p-4 sm:p-5 transition-all duration-300 hover:shadow-lg animate-scale-in ${
                isDone
                  ? 'border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-700 opacity-75'
                  : task.is_critical
                  ? 'border-red-400 dark:border-red-600 bg-gradient-to-br from-red-50 to-pink-50 dark:from-red-900/30 dark:to-pink-900/30 shadow-md'
                  : task.is_urgent
                  ? 'border-orange-400 dark:border-orange-600 bg-gradient-to-br from-orange-50 to-yellow-50 dark:from-orange-900/30 dark:to-yellow-900/30 shadow-md'
                  : 'border-purple-200 dark:border-purple-700 bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20'
              }`}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h4 className={`text-sm sm:text-base font-medium break-words ${isDone ? 'line-through text-gray-500 dark:text-gray-400' : 'text-gray-900 dark:text-gray-100'}`}>
                      {task.title}
                    </h4>
                    {isDone && (
                      <span className="rounded-full bg-gradient-to-r from-green-500 to-emerald-500 px-3 py-1 text-xs font-bold text-white shadow-md">
                        Done
                      </span>
                    )}
                    {isSnoozed && (
                      <span className="rounded-full bg-gradient-to-r from-yellow-500 to-orange-500 px-3 py-1 text-xs font-bold text-white shadow-md">
                        Snoozed
                      </span>
                    )}
                    {!isDone && !isSnoozed && task.is_critical && (
                      <span className="rounded-full bg-gradient-to-r from-red-500 to-pink-500 px-3 py-1 text-xs font-bold text-white shadow-md">
                        Critical
                      </span>
                    )}
                    {!isDone && !isSnoozed && task.is_urgent && (
                      <span className="rounded-full bg-gradient-to-r from-orange-500 to-yellow-500 px-3 py-1 text-xs font-bold text-white shadow-md">
                        Urgent
                      </span>
                    )}
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-2 sm:gap-4 text-xs sm:text-sm text-gray-600 dark:text-gray-400">
                    <span>
                      {formatTime(task.predicted_start)} - {formatTime(task.predicted_end)}
                    </span>
                    <span className="text-xs">Priority: {(task.priority_score * 100).toFixed(0)}%</span>
                  </div>
                  
                  {/* Display action plan steps if available */}
                  {task.action_plan && task.action_plan.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                      <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">Action Plan:</div>
                      <ol className="space-y-1.5">
                        {task.action_plan.map((step, stepIndex) => (
                          <li key={stepIndex} className="flex items-start gap-2 text-xs text-gray-600 dark:text-gray-400">
                            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-gradient-to-r from-purple-400 to-pink-400 text-white flex items-center justify-center text-[10px] font-bold mt-0.5">
                              {stepIndex + 1}
                            </span>
                            <span className="flex-1">{step}</span>
                          </li>
                        ))}
                      </ol>
                    </div>
                  )}
                </div>
                {!isDone && (
                  <div className="w-full sm:w-auto sm:ml-4 flex justify-start sm:justify-end">
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
          <div className="py-8 text-center text-gray-600 dark:text-gray-400 font-medium">No tasks scheduled for this day</div>
        )}
      </div>

      {/* Plans History Modal */}
      {showHistory && (
        <PlansHistory
          onClose={() => setShowHistory(false)}
          onPlanSelect={(selectedPlan) => {
            // Optionally handle plan selection
            console.log('Selected plan:', selectedPlan)
          }}
        />
      )}
    </div>
  )
}

