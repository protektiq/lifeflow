"use client"

import { useState, useMemo } from 'react'
import { RawTask } from '@/src/types/task'
import { Calendar, Clock, MapPin, Users, Search, Filter, ChevronDown, ChevronRight } from 'lucide-react'
import TaskDetailView from './TaskDetailView'

interface RawTasksViewProps {
  tasks: RawTask[]
  loading: boolean
  onTaskFlagsUpdate: (taskId: string, flags: { is_critical?: boolean; is_urgent?: boolean }) => Promise<void>
}

type DateRangeFilter = 'all' | 'today' | 'week' | 'month'
type SortOption = 'date-asc' | 'date-desc' | 'priority' | 'title'

interface GroupedTasks {
  [key: string]: RawTask[]
}

export default function RawTasksView({
  tasks,
  loading,
  onTaskFlagsUpdate,
}: RawTasksViewProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [showCritical, setShowCritical] = useState(false)
  const [showUrgent, setShowUrgent] = useState(false)
  const [dateRange, setDateRange] = useState<DateRangeFilter>('all')
  const [sortOption, setSortOption] = useState<SortOption>('date-asc')
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set())
  const [collapsedDates, setCollapsedDates] = useState<Set<string>>(new Set())
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)

  // Date formatting utilities
  // Helper to get local date from ISO string (handles timezone conversion)
  // The dateString comes from the backend as an ISO string (may be UTC or have timezone)
  // JavaScript's Date constructor automatically converts to local time
  const getLocalDate = (dateString: string) => {
    // Parse the ISO string - JavaScript Date automatically handles timezone conversion
    const date = new Date(dateString)
    // Extract only the date components (year, month, day) in local timezone
    // This ensures we get the correct local date regardless of what timezone the string was in
    return new Date(date.getFullYear(), date.getMonth(), date.getDate())
  }

  const formatDate = (dateString: string) => {
    const date = getLocalDate(dateString)
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  const formatDateShort = (dateString: string) => {
    const date = getLocalDate(dateString)
    const today = new Date()
    const tomorrow = new Date(today)
    tomorrow.setDate(tomorrow.getDate() + 1)
    
    const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate())
    const todayOnly = new Date(today.getFullYear(), today.getMonth(), today.getDate())
    const tomorrowOnly = new Date(tomorrow.getFullYear(), tomorrow.getMonth(), tomorrow.getDate())
    
    if (dateOnly.getTime() === todayOnly.getTime()) {
      return 'Today'
    }
    if (dateOnly.getTime() === tomorrowOnly.getTime()) {
      return 'Tomorrow'
    }
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
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

  const getDateKey = (dateString: string) => {
    // Extract the UTC date directly from the ISO string (YYYY-MM-DD portion)
    // This matches the calendar date stored in the database
    // The database stores dates in UTC, and the date portion represents the intended calendar date
    // Example: "2025-11-09T04:00:00Z" -> "2025-11-09"
    // Handle different ISO formats: "2025-11-09T04:00:00Z", "2025-11-09T04:00:00+00:00", etc.
    const dateMatch = dateString.match(/^(\d{4}-\d{2}-\d{2})/)
    if (dateMatch) {
      const extractedDate = dateMatch[1]
      // Debug: log if we see the ChatGPT event to verify date extraction
      if (dateString.includes('ChatGPT') || dateString.includes('Fox Hill')) {
        console.log('Date extraction debug:', { dateString, extractedDate })
      }
      return extractedDate
    }
    // Fallback: if format is unexpected, use UTC date from parsed Date object
    const date = new Date(dateString)
    const year = date.getUTCFullYear()
    const month = String(date.getUTCMonth() + 1).padStart(2, '0')
    const day = String(date.getUTCDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  const isToday = (dateString: string) => {
    const taskDate = getLocalDate(dateString)
    const today = new Date()
    const todayOnly = new Date(today.getFullYear(), today.getMonth(), today.getDate())
    return taskDate.getTime() === todayOnly.getTime()
  }

  const isThisWeek = (dateString: string) => {
    const taskDate = getLocalDate(dateString)
    const today = new Date()
    const weekStart = new Date(today)
    weekStart.setDate(today.getDate() - today.getDay())
    weekStart.setHours(0, 0, 0, 0)
    const weekEnd = new Date(weekStart)
    weekEnd.setDate(weekStart.getDate() + 6)
    weekEnd.setHours(23, 59, 59, 999)
    return taskDate >= weekStart && taskDate <= weekEnd
  }

  const isThisMonth = (dateString: string) => {
    const taskDate = getLocalDate(dateString)
    const today = new Date()
    return taskDate.getMonth() === today.getMonth() && taskDate.getFullYear() === today.getFullYear()
  }

  // Filter and sort tasks
  const filteredAndSortedTasks = useMemo(() => {
    let filtered = [...tasks]

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(
        (task) =>
          task.title.toLowerCase().includes(query) ||
          (task.description && task.description.toLowerCase().includes(query)) ||
          (task.location && task.location.toLowerCase().includes(query))
      )
    }

    // Critical/Urgent filters
    if (showCritical && showUrgent) {
      filtered = filtered.filter((task) => task.is_critical || task.is_urgent)
    } else if (showCritical) {
      filtered = filtered.filter((task) => task.is_critical)
    } else if (showUrgent) {
      filtered = filtered.filter((task) => task.is_urgent)
    }

    // Date range filter
    if (dateRange === 'today') {
      filtered = filtered.filter((task) => isToday(task.start_time))
    } else if (dateRange === 'week') {
      filtered = filtered.filter((task) => isThisWeek(task.start_time))
    } else if (dateRange === 'month') {
      filtered = filtered.filter((task) => isThisMonth(task.start_time))
    }

    // Sort
    filtered.sort((a, b) => {
      switch (sortOption) {
        case 'date-asc':
          return new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
        case 'date-desc':
          return new Date(b.start_time).getTime() - new Date(a.start_time).getTime()
        case 'priority':
          const aPriority = (a.is_critical ? 2 : 0) + (a.is_urgent ? 1 : 0)
          const bPriority = (b.is_critical ? 2 : 0) + (b.is_urgent ? 1 : 0)
          return bPriority - aPriority
        case 'title':
          return a.title.localeCompare(b.title)
        default:
          return 0
      }
    })

    return filtered
  }, [tasks, searchQuery, showCritical, showUrgent, dateRange, sortOption])

  // Group tasks by date
  const groupedTasks = useMemo(() => {
    const grouped: GroupedTasks = {}
    filteredAndSortedTasks.forEach((task) => {
      const dateKey = getDateKey(task.start_time)
      if (!grouped[dateKey]) {
        grouped[dateKey] = []
      }
      grouped[dateKey].push(task)
    })
    return grouped
  }, [filteredAndSortedTasks])

  const toggleTaskExpansion = (taskId: string) => {
    setExpandedTasks((prev) => {
      const next = new Set(prev)
      if (next.has(taskId)) {
        next.delete(taskId)
      } else {
        next.add(taskId)
      }
      return next
    })
  }

  const toggleDateCollapse = (dateKey: string) => {
    setCollapsedDates((prev) => {
      const next = new Set(prev)
      if (next.has(dateKey)) {
        next.delete(dateKey)
      } else {
        next.add(dateKey)
      }
      return next
    })
  }

  const handleToggleFlag = async (
    taskId: string,
    flagType: 'is_critical' | 'is_urgent',
    currentValue: boolean
  ) => {
    await onTaskFlagsUpdate(taskId, { [flagType]: !currentValue })
  }

  const handleTaskClick = (taskId: string, e: React.MouseEvent) => {
    // Don't open detail view if clicking on toggle switches or buttons
    const target = e.target as HTMLElement
    if (target.closest('label') || target.closest('input[type="checkbox"]') || target.closest('button')) {
      return
    }
    setSelectedTaskId(taskId)
  }

  const handleCloseDetail = () => {
    setSelectedTaskId(null)
  }

  if (loading) {
    return (
      <div className="rounded-2xl bg-white dark:bg-gray-800 shadow-lg dark:shadow-gray-900/50 animate-scale-in">
        <div className="px-6 sm:px-8 py-4 sm:py-6 border-b-2 border-purple-200 dark:border-purple-700">
          <h2 className="text-xl sm:text-2xl font-bold">
            <span className="gradient-text">Raw Tasks</span>
          </h2>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-purple-600 dark:border-purple-400 border-t-transparent"></div>
        </div>
      </div>
    )
  }

  const sortedDateKeys = Object.keys(groupedTasks).sort()

  return (
    <div className="group relative rounded-2xl bg-white dark:bg-gray-800 shadow-lg dark:shadow-gray-900/50 transition-all duration-300 hover:shadow-2xl animate-scale-in">
      <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-blue-500/10 dark:from-purple-500/20 dark:to-blue-500/20 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
      <div className="relative z-10">
        {/* Header */}
        <div className="px-6 sm:px-8 py-4 sm:py-6 border-b-2 border-purple-200 dark:border-purple-700">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl sm:text-2xl font-bold mb-1">
                <span className="gradient-text">Raw Tasks</span>
              </h2>
              <p className="text-sm sm:text-base text-gray-700 dark:text-gray-300 font-medium">
                {filteredAndSortedTasks.length} of {tasks.length} task{tasks.length !== 1 ? 's' : ''}
              </p>
            </div>
          </div>

          {/* Search Bar */}
          <div className="relative mb-4">
            <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-purple-400 dark:text-purple-500" />
            <input
              type="text"
              placeholder="Search tasks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-xl border-2 border-purple-200 dark:border-purple-700 bg-white dark:bg-gray-800 py-3 pl-12 pr-4 text-sm placeholder-gray-400 dark:placeholder-gray-500 text-gray-900 dark:text-gray-100 focus:border-purple-500 dark:focus:border-purple-500 focus:outline-none focus:ring-4 focus:ring-purple-500/50 transition-all duration-300"
            />
          </div>

        {/* Filters and Sort */}
        <div className="flex flex-col sm:flex-row sm:flex-wrap items-stretch sm:items-center gap-2 sm:gap-3">
          {/* Filter Chips */}
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-400 dark:text-gray-500 flex-shrink-0" />
            <button
              onClick={() => setShowCritical(!showCritical)}
              className={`rounded-full px-4 py-2 text-xs font-bold transition-all duration-300 hover:scale-110 ${
                showCritical
                  ? 'bg-gradient-to-r from-red-500 to-pink-500 text-white shadow-md'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border-2 border-gray-300 dark:border-gray-600'
              }`}
            >
              Critical
            </button>
            <button
              onClick={() => setShowUrgent(!showUrgent)}
              className={`rounded-full px-4 py-2 text-xs font-bold transition-all duration-300 hover:scale-110 ${
                showUrgent
                  ? 'bg-gradient-to-r from-orange-500 to-yellow-500 text-white shadow-md'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border-2 border-gray-300 dark:border-gray-600'
              }`}
            >
              Urgent
            </button>
          </div>

          {/* Date Range Filter */}
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-gray-400 dark:text-gray-500 flex-shrink-0" />
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value as DateRangeFilter)}
              className="flex-1 sm:flex-none rounded-xl border-2 border-purple-200 dark:border-purple-700 bg-white dark:bg-gray-800 px-3 sm:px-4 py-2 text-xs font-semibold text-gray-700 dark:text-gray-300 focus:border-purple-500 dark:focus:border-purple-500 focus:outline-none focus:ring-4 focus:ring-purple-500/50 transition-all duration-300"
            >
              <option value="all">All Time</option>
              <option value="today">Today</option>
              <option value="week">This Week</option>
              <option value="month">This Month</option>
            </select>
          </div>

          {/* Sort Options */}
          <div className="flex items-center gap-2 sm:ml-auto">
            <select
              value={sortOption}
              onChange={(e) => setSortOption(e.target.value as SortOption)}
              className="flex-1 sm:flex-none rounded-xl border-2 border-purple-200 dark:border-purple-700 bg-white dark:bg-gray-800 px-3 sm:px-4 py-2 text-xs font-semibold text-gray-700 dark:text-gray-300 focus:border-purple-500 dark:focus:border-purple-500 focus:outline-none focus:ring-4 focus:ring-purple-500/50 transition-all duration-300"
            >
              <option value="date-asc">Date (Oldest First)</option>
              <option value="date-desc">Date (Newest First)</option>
              <option value="priority">Priority</option>
              <option value="title">Title (A-Z)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tasks List */}
      <div>
          {filteredAndSortedTasks.length === 0 ? (
            <div className="px-6 sm:px-8 py-8 sm:py-12 text-center text-gray-600 dark:text-gray-400">
              {tasks.length === 0 ? (
                <>
                  <p className="text-sm sm:text-base font-medium">No tasks found.</p>
                  <p className="mt-2 text-sm">Sync your calendar to get started.</p>
                </>
              ) : (
                <>
                  <p className="text-sm sm:text-base font-medium">No tasks match your filters.</p>
                  <p className="mt-2 text-sm">Try adjusting your search or filters.</p>
                </>
              )}
            </div>
          ) : (
            <div className="divide-y divide-purple-100 dark:divide-purple-800">
              {sortedDateKeys.map((dateKey) => {
                const dateTasks = groupedTasks[dateKey]
                const isCollapsed = collapsedDates.has(dateKey)
                const firstTask = dateTasks[0]

                return (
                  <div key={dateKey} className="bg-gradient-to-br from-purple-50/50 to-blue-50/50 dark:from-purple-900/20 dark:to-blue-900/20">
                    {/* Date Header */}
                    <button
                      onClick={() => toggleDateCollapse(dateKey)}
                      className="w-full px-6 sm:px-8 py-3 sm:py-4 flex items-center justify-between hover:bg-purple-100/50 dark:hover:bg-purple-900/30 transition-all duration-300 focus:outline-none focus:ring-4 focus:ring-purple-500/50 rounded-lg"
                    >
                      <div className="flex items-center gap-2 sm:gap-3">
                        {isCollapsed ? (
                          <ChevronRight className="h-4 w-4 text-gray-400 dark:text-gray-500 flex-shrink-0" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-gray-400 dark:text-gray-500 flex-shrink-0" />
                        )}
                        <div className="text-left">
                          <h3 className="text-sm sm:text-base font-bold text-gray-900 dark:text-gray-100">
                            {formatDateShort(firstTask.start_time)}
                          </h3>
                          <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 mt-1">
                            {formatDate(firstTask.start_time)} • {dateTasks.length} task{dateTasks.length !== 1 ? 's' : ''}
                          </p>
                        </div>
                      </div>
                    </button>

                    {/* Tasks for this date */}
                    {!isCollapsed && (
                      <div className="px-6 sm:px-8 pb-4 sm:pb-6 space-y-3 sm:space-y-4">
                        {dateTasks.map((task, taskIndex) => {
                          const isExpanded = expandedTasks.has(task.id)
                          const cardBgColor = task.is_critical
                            ? 'bg-gradient-to-br from-red-50 to-pink-50 dark:from-red-900/30 dark:to-pink-900/30 border-red-400 dark:border-red-600'
                            : task.is_urgent
                            ? 'bg-gradient-to-br from-orange-50 to-yellow-50 dark:from-orange-900/30 dark:to-yellow-900/30 border-orange-400 dark:border-orange-600'
                            : 'bg-white dark:bg-gray-800 border-purple-200 dark:border-purple-700'

                          return (
                            <div
                              key={task.id}
                              onClick={(e) => handleTaskClick(task.id, e)}
                              className={`rounded-xl border-2 p-4 sm:p-5 transition-all duration-300 hover:shadow-lg animate-scale-in cursor-pointer ${cardBgColor}`}
                              style={{ animationDelay: `${taskIndex * 30}ms` }}
                            >
                              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                                <div className="flex-1 min-w-0">
                                  {/* Title and Badges */}
                                  <div className="flex items-start gap-2 flex-wrap">
                                    <h4 className="text-xs sm:text-sm font-medium text-gray-900 dark:text-gray-100 flex-1 min-w-0 break-words">
                                      {task.title}
                                    </h4>
                                    {task.is_critical && (
                                      <span className="rounded-full bg-gradient-to-r from-red-500 to-pink-500 px-3 py-1 text-xs font-bold text-white whitespace-nowrap shadow-md">
                                        Critical
                                      </span>
                                    )}
                                    {task.is_urgent && (
                                      <span className="rounded-full bg-gradient-to-r from-orange-500 to-yellow-500 px-3 py-1 text-xs font-bold text-white whitespace-nowrap shadow-md">
                                        Urgent
                                      </span>
                                    )}
                                    {task.extracted_priority && (
                                      <span className="rounded-full bg-gradient-to-r from-blue-500 to-purple-500 px-3 py-1 text-xs font-bold text-white whitespace-nowrap shadow-md">
                                        {task.extracted_priority}
                                      </span>
                                    )}
                                  </div>

                                  {/* Time and Metadata */}
                                  <div className="mt-2 flex flex-wrap items-center gap-2 sm:gap-3 text-xs text-gray-600 dark:text-gray-400">
                                    <div className="flex items-center gap-1">
                                      <Clock className="h-3 w-3 flex-shrink-0" />
                                      <span className="whitespace-nowrap">
                                        {formatTime(task.start_time)} - {formatTime(task.end_time)}
                                      </span>
                                    </div>
                                    {task.location && (
                                      <div className="flex items-center gap-1 min-w-0">
                                        <MapPin className="h-3 w-3 flex-shrink-0" />
                                        <span className="truncate max-w-[150px] sm:max-w-[200px]">{task.location}</span>
                                      </div>
                                    )}
                                    {task.attendees.length > 0 && (
                                      <div className="flex items-center gap-1">
                                        <Users className="h-3 w-3 flex-shrink-0" />
                                        <span>{task.attendees.length} attendee{task.attendees.length !== 1 ? 's' : ''}</span>
                                      </div>
                                    )}
                                    {task.source && (
                                      <span className="text-gray-500 dark:text-gray-400 hidden sm:inline">• {task.source}</span>
                                    )}
                                  </div>

                                  {/* Description (expandable) */}
                                  {task.description && (
                                    <div className="mt-2">
                                      {isExpanded ? (
                                        <div>
                                          <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                                            {task.description}
                                          </p>
                                          <button
                                            onClick={() => toggleTaskExpansion(task.id)}
                                            className="mt-2 px-3 py-1 text-xs text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 font-bold rounded-full border-2 border-purple-300 dark:border-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/30 transition-all duration-300"
                                          >
                                            Show less
                                          </button>
                                        </div>
                                      ) : (
                                        <div>
                                          <p className="text-sm text-gray-600 dark:text-gray-400 overflow-hidden" style={{
                                            display: '-webkit-box',
                                            WebkitLineClamp: 2,
                                            WebkitBoxOrient: 'vertical',
                                            maxHeight: '3em',
                                          }}>
                                            {task.description}
                                          </p>
                                          {task.description.length > 100 && (
                                            <button
                                              onClick={() => toggleTaskExpansion(task.id)}
                                              className="mt-2 px-3 py-1 text-xs text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 font-bold rounded-full border-2 border-purple-300 dark:border-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/30 transition-all duration-300"
                                            >
                                              Show more
                                            </button>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </div>

                                {/* Toggle Switches */}
                                <div className="flex flex-row sm:flex-col gap-3 pt-1 sm:pt-0">
                                  {/* Critical Toggle */}
                                  <label className="flex items-center gap-2 cursor-pointer group touch-manipulation">
                                    <div className="relative">
                                      <input
                                        type="checkbox"
                                        checked={task.is_critical}
                                        onChange={() =>
                                          handleToggleFlag(task.id, 'is_critical', task.is_critical)
                                        }
                                        className="sr-only"
                                      />
                                      <div
                                        className={`h-5 w-9 rounded-full transition-colors ${
                                          task.is_critical ? 'bg-red-600' : 'bg-gray-300 dark:bg-gray-600'
                                        }`}
                                      >
                                        <div
                                          className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white dark:bg-gray-200 transition-transform ${
                                            task.is_critical ? 'translate-x-4' : ''
                                          }`}
                                        />
                                      </div>
                                    </div>
                                    <span className="text-xs font-medium text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-gray-100 whitespace-nowrap">
                                      Critical
                                    </span>
                                  </label>

                                  {/* Urgent Toggle */}
                                  <label className="flex items-center gap-2 cursor-pointer group touch-manipulation">
                                    <div className="relative">
                                      <input
                                        type="checkbox"
                                        checked={task.is_urgent}
                                        onChange={() =>
                                          handleToggleFlag(task.id, 'is_urgent', task.is_urgent)
                                        }
                                        className="sr-only"
                                      />
                                      <div
                                        className={`h-5 w-9 rounded-full transition-colors ${
                                          task.is_urgent ? 'bg-orange-600' : 'bg-gray-300 dark:bg-gray-600'
                                        }`}
                                      >
                                        <div
                                          className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white dark:bg-gray-200 transition-transform ${
                                            task.is_urgent ? 'translate-x-4' : ''
                                          }`}
                                        />
                                      </div>
                                    </div>
                                    <span className="text-xs font-medium text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-gray-100 whitespace-nowrap">
                                      Urgent
                                    </span>
                                  </label>
                                </div>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Task Detail Modal */}
      {selectedTaskId && (
        <TaskDetailView
          taskId={selectedTaskId}
          onClose={handleCloseDetail}
          onTaskUpdated={() => {
            // Optionally refresh tasks when task is updated
            handleCloseDetail()
          }}
        />
      )}
    </div>
  )
}

