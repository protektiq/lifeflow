"use client"

import { useEffect, useState } from 'react'
import { apiClient } from '@/src/lib/api'
import { SourceReliabilityMetrics as SourceReliabilityMetricsType } from '@/src/types/analytics'
import { BarChart3, Mail, Calendar, CheckCircle2, TrendingUp } from 'lucide-react'

interface SourceReliabilityMetricsProps {
  startDate?: string
  endDate?: string
}

const sourceIcons: Record<string, React.ReactNode> = {
  email: <Mail className="w-5 h-5" />,
  gmail: <Mail className="w-5 h-5" />,
  google_calendar: <Calendar className="w-5 h-5" />,
  calendar: <Calendar className="w-5 h-5" />,
  todoist: <CheckCircle2 className="w-5 h-5" />,
}

const sourceLabels: Record<string, string> = {
  email: 'Email',
  gmail: 'Gmail',
  google_calendar: 'Google Calendar',
  calendar: 'Calendar',
  todoist: 'Todoist',
}

const getSourceLabel = (source: string): string => {
  return sourceLabels[source.toLowerCase()] || source.charAt(0).toUpperCase() + source.slice(1).replace(/_/g, ' ')
}

const getSourceIcon = (source: string): React.ReactNode => {
  return sourceIcons[source.toLowerCase()] || <BarChart3 className="w-5 h-5" />
}

export default function SourceReliabilityMetrics({
  startDate,
  endDate,
}: SourceReliabilityMetricsProps) {
  const [metrics, setMetrics] = useState<SourceReliabilityMetricsType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadMetrics()
  }, [startDate, endDate])

  const loadMetrics = async () => {
    try {
      setLoading(true)
      setError(null)
      const params: { start_date?: string; end_date?: string } = {}
      if (startDate) params.start_date = startDate
      if (endDate) params.end_date = endDate
      
      const data = await apiClient.getSourceReliabilityMetrics(params)
      setMetrics(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load source reliability metrics')
      console.error('Error loading source reliability metrics:', err)
    } finally {
      setLoading(false)
    }
  }

  const getCompletionColor = (rate: number): string => {
    if (rate >= 80) return 'text-green-600 dark:text-green-400'
    if (rate >= 60) return 'text-yellow-600 dark:text-yellow-400'
    if (rate >= 40) return 'text-orange-600 dark:text-orange-400'
    return 'text-red-600 dark:text-red-400'
  }

  const getCompletionBgColor = (rate: number): string => {
    if (rate >= 80) return 'bg-green-100 dark:bg-green-900/30'
    if (rate >= 60) return 'bg-yellow-100 dark:bg-yellow-900/30'
    if (rate >= 40) return 'bg-orange-100 dark:bg-orange-900/30'
    return 'bg-red-100 dark:bg-red-900/30'
  }

  const getCompletionBarColor = (rate: number): string => {
    if (rate >= 80) return 'bg-green-500'
    if (rate >= 60) return 'bg-yellow-500'
    if (rate >= 40) return 'bg-orange-500'
    return 'bg-red-500'
  }

  if (loading) {
    return (
      <div className="rounded-2xl bg-white dark:bg-gray-800 p-4 sm:p-5 shadow-lg dark:shadow-gray-900/50 animate-scale-in">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-2xl bg-white dark:bg-gray-800 p-4 sm:p-5 shadow-lg dark:shadow-gray-900/50 animate-scale-in">
        <div className="text-center py-4">
          <p className="text-sm font-medium text-red-600 dark:text-red-400">{error}</p>
        </div>
      </div>
    )
  }

  if (metrics.length === 0) {
    return (
      <div className="rounded-2xl bg-white dark:bg-gray-800 p-4 sm:p-5 shadow-lg dark:shadow-gray-900/50 animate-scale-in">
        <h3 className="text-lg sm:text-xl font-bold mb-4">
          <span className="gradient-text">Source Reliability</span>
        </h3>
        <div className="text-center py-8">
          <BarChart3 className="w-12 h-12 mx-auto text-gray-400 dark:text-gray-600 mb-3" />
          <p className="text-sm text-gray-600 dark:text-gray-400">No data available yet</p>
          <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">Complete some tasks to see metrics</p>
        </div>
      </div>
    )
  }

  return (
    <div className="group relative rounded-2xl bg-white dark:bg-gray-800 p-4 sm:p-5 shadow-lg dark:shadow-gray-900/50 transition-all duration-300 hover:shadow-2xl animate-scale-in">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-purple-500/10 dark:from-blue-500/20 dark:to-purple-500/20 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg sm:text-xl font-bold">
            <span className="gradient-text">Source Reliability</span>
          </h3>
          <TrendingUp className="w-5 h-5 text-purple-600 dark:text-purple-400" />
        </div>
        <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 mb-4">
          Task completion rates by source
        </p>

        <div className="space-y-4">
          {metrics.map((metric) => (
            <div
              key={metric.source}
              className="rounded-xl border-2 border-gray-200 dark:border-gray-700 p-3 sm:p-4 transition-all duration-300 hover:border-purple-300 dark:hover:border-purple-600 hover:shadow-md"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2 sm:gap-3">
                  <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400">
                    {getSourceIcon(metric.source)}
                  </div>
                  <div>
                    <h4 className="text-sm sm:text-base font-semibold text-gray-800 dark:text-gray-200">
                      {getSourceLabel(metric.source)}
                    </h4>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {metric.completed_tasks} of {metric.total_tasks} completed
                    </p>
                  </div>
                </div>
                <div className={`px-3 py-1 rounded-full text-sm font-bold ${getCompletionColor(metric.completion_rate)} ${getCompletionBgColor(metric.completion_rate)}`}>
                  {metric.completion_rate.toFixed(1)}%
                </div>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${getCompletionBarColor(metric.completion_rate)}`}
                  style={{ width: `${Math.min(metric.completion_rate, 100)}%` }}
                ></div>
              </div>
            </div>
          ))}
        </div>

        {metrics.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
              Based on tasks from the last 30 days
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

