"use client"

import { useState, useEffect } from 'react'
import { apiClient } from '@/src/lib/api'
import { DailyPlan } from '@/src/types/plan'
import { X, Calendar, CheckCircle, Clock, XCircle } from 'lucide-react'

interface PlansHistoryProps {
  onClose: () => void
  onPlanSelect?: (plan: DailyPlan) => void
}

export default function PlansHistory({ onClose, onPlanSelect }: PlansHistoryProps) {
  const [plans, setPlans] = useState<DailyPlan[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dateRange, setDateRange] = useState<'week' | 'month' | 'all'>('month')

  useEffect(() => {
    loadPlans()
  }, [dateRange])

  const loadPlans = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const now = new Date()
      let startDate: string | undefined
      
      if (dateRange === 'week') {
        const weekAgo = new Date(now)
        weekAgo.setDate(now.getDate() - 7)
        startDate = weekAgo.toISOString().split('T')[0]
      } else if (dateRange === 'month') {
        const monthAgo = new Date(now)
        monthAgo.setMonth(now.getMonth() - 1)
        startDate = monthAgo.toISOString().split('T')[0]
      }
      
      const data = await apiClient.getPlans(
        startDate ? { start_date: startDate } : undefined
      )
      setPlans(Array.isArray(data) ? data : [])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load plans')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string | Date) => {
    const date = typeof dateString === 'string' ? new Date(dateString) : dateString
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
      case 'cancelled':
        return <XCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
      case 'active':
        return <Clock className="h-5 w-5 text-blue-600 dark:text-blue-400" />
      default:
        return <Clock className="h-5 w-5 text-gray-600 dark:text-gray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'bg-green-100 dark:bg-green-900/30 border-green-300 dark:border-green-600 text-green-700 dark:text-green-300'
      case 'cancelled':
        return 'bg-red-100 dark:bg-red-900/30 border-red-300 dark:border-red-600 text-red-700 dark:text-red-300'
      case 'active':
        return 'bg-blue-100 dark:bg-blue-900/30 border-blue-300 dark:border-blue-600 text-blue-700 dark:text-blue-300'
      default:
        return 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300'
    }
  }

  const sortedPlans = [...plans].sort((a, b) => {
    const dateA = typeof a.plan_date === 'string' ? new Date(a.plan_date) : a.plan_date
    const dateB = typeof b.plan_date === 'string' ? new Date(b.plan_date) : b.plan_date
    return dateB.getTime() - dateA.getTime()
  })

  const handlePlanClick = (plan: DailyPlan) => {
    if (onPlanSelect) {
      onPlanSelect(plan)
      onClose()
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="rounded-2xl bg-white dark:bg-gray-800 shadow-2xl dark:shadow-gray-900/50 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white dark:bg-gray-800 border-b-2 border-purple-200 dark:border-purple-700 p-4 sm:p-6 flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              Plans History
            </h2>
            {plans.length > 0 && (
              <div className="flex items-center gap-4 text-sm">
                <span className="text-gray-600 dark:text-gray-400">
                  Total Plans: <span className="font-bold text-gray-900 dark:text-gray-100">{plans.length}</span>
                </span>
                <span className="text-gray-600 dark:text-gray-400">
                  Tasks Scheduled: <span className="font-bold text-purple-600 dark:text-purple-400">
                    {plans.reduce((sum, p) => sum + (p.tasks?.length || 0), 0)}
                  </span>
                </span>
              </div>
            )}
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
          {/* Date Range Filter */}
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-gray-400 dark:text-gray-500" />
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value as 'week' | 'month' | 'all')}
              className="rounded-xl border-2 border-purple-200 dark:border-purple-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm font-semibold text-gray-700 dark:text-gray-300 focus:border-purple-500 dark:focus:border-purple-500 focus:outline-none focus:ring-4 focus:ring-purple-500/50 transition-all duration-300"
            >
              <option value="week">Last Week</option>
              <option value="month">Last Month</option>
              <option value="all">All Time</option>
            </select>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-purple-600 dark:border-purple-400 border-t-transparent"></div>
            </div>
          ) : error ? (
            <div className="rounded-xl bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 p-4 text-red-800 dark:text-red-300">
              {error}
            </div>
          ) : sortedPlans.length === 0 ? (
            <div className="py-12 text-center text-gray-600 dark:text-gray-400">
              <p className="text-lg font-medium mb-2">No plans found</p>
              <p className="text-sm">Generate your first plan to see it here.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {sortedPlans.map((plan) => {
                const planDate = typeof plan.plan_date === 'string' ? new Date(plan.plan_date) : plan.plan_date
                const taskCount = plan.tasks?.length || 0
                
                return (
                  <div
                    key={plan.id}
                    onClick={() => handlePlanClick(plan)}
                    className={`rounded-xl border-2 p-4 sm:p-5 transition-all duration-300 hover:shadow-lg cursor-pointer ${
                      onPlanSelect ? 'hover:scale-[1.02]' : ''
                    } bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-900/30 dark:to-blue-900/30 border-purple-200 dark:border-purple-700`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-2">
                          <Calendar className="h-5 w-5 text-purple-600 dark:text-purple-400 flex-shrink-0" />
                          <div>
                            <h3 className="text-base sm:text-lg font-bold text-gray-900 dark:text-gray-100">
                              {formatDate(planDate)}
                            </h3>
                            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                              Generated: {new Date(plan.generated_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                        
                        <div className="flex flex-wrap items-center gap-3 mt-3">
                          <div className="flex items-center gap-2">
                            {getStatusIcon(plan.status)}
                            <span className={`px-3 py-1 rounded-full text-xs font-bold border-2 ${getStatusColor(plan.status)}`}>
                              {plan.status}
                            </span>
                          </div>
                          
                          {plan.energy_level && (
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-gray-600 dark:text-gray-400">Energy:</span>
                              <span className={`px-3 py-1 rounded-full text-xs font-bold border-2 ${
                                plan.energy_level <= 2
                                  ? 'bg-red-100 dark:bg-red-900/30 border-red-300 dark:border-red-600 text-red-700 dark:text-red-300'
                                  : plan.energy_level === 3
                                  ? 'bg-yellow-100 dark:bg-yellow-900/30 border-yellow-300 dark:border-yellow-600 text-yellow-700 dark:text-yellow-300'
                                  : 'bg-green-100 dark:bg-green-900/30 border-green-300 dark:border-green-600 text-green-700 dark:text-green-300'
                              }`}>
                                {plan.energy_level}/5
                              </span>
                            </div>
                          )}
                          
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-600 dark:text-gray-400">Tasks:</span>
                            <span className="px-3 py-1 rounded-full text-xs font-bold bg-purple-100 dark:bg-purple-900/30 border-2 border-purple-300 dark:border-purple-600 text-purple-700 dark:text-purple-300">
                              {taskCount}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
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

