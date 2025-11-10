"use client"

import { useState, useEffect } from 'react'
import { apiClient } from '@/src/lib/api'
import { X, Calendar, TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface EnergyLevel {
  id: string
  user_id: string
  date: string
  energy_level: number
  created_at: string
  updated_at: string
}

interface EnergyLevelHistoryProps {
  onClose: () => void
}

export default function EnergyLevelHistory({ onClose }: EnergyLevelHistoryProps) {
  const [energyLevels, setEnergyLevels] = useState<EnergyLevel[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dateRange, setDateRange] = useState<'week' | 'month' | 'all'>('month')

  useEffect(() => {
    loadEnergyLevels()
  }, [dateRange])

  const loadEnergyLevels = async () => {
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
      
      const data = await apiClient.getEnergyLevels(
        startDate ? { start_date: startDate } : undefined
      )
      setEnergyLevels(Array.isArray(data) ? data : [])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load energy levels')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const getEnergyLevelColor = (level: number) => {
    if (level <= 2) return 'bg-red-500'
    if (level === 3) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  const getEnergyLevelLabel = (level: number) => {
    const labels = ['Very Low', 'Low', 'Medium', 'High', 'Very High']
    return labels[level - 1] || 'Unknown'
  }

  const sortedLevels = [...energyLevels].sort((a, b) => {
    return new Date(b.date).getTime() - new Date(a.date).getTime()
  })

  const getTrend = (current: EnergyLevel, previous: EnergyLevel | undefined) => {
    if (!previous) return null
    if (current.energy_level > previous.energy_level) return 'up'
    if (current.energy_level < previous.energy_level) return 'down'
    return 'same'
  }

  const averageLevel = energyLevels.length > 0
    ? energyLevels.reduce((sum, el) => sum + el.energy_level, 0) / energyLevels.length
    : 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="rounded-2xl bg-white dark:bg-gray-800 shadow-2xl dark:shadow-gray-900/50 max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white dark:bg-gray-800 border-b-2 border-purple-200 dark:border-purple-700 p-4 sm:p-6 flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              Energy Level History
            </h2>
            {energyLevels.length > 0 && (
              <div className="flex items-center gap-4 text-sm">
                <span className="text-gray-600 dark:text-gray-400">
                  Average: <span className="font-bold text-purple-600 dark:text-purple-400">{averageLevel.toFixed(1)}/5</span>
                </span>
                <span className="text-gray-600 dark:text-gray-400">
                  Total Entries: <span className="font-bold text-gray-900 dark:text-gray-100">{energyLevels.length}</span>
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
          ) : sortedLevels.length === 0 ? (
            <div className="py-12 text-center text-gray-600 dark:text-gray-400">
              <p className="text-lg font-medium mb-2">No energy levels recorded</p>
              <p className="text-sm">Start tracking your energy levels to see your history here.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {sortedLevels.map((level, index) => {
                const previous = index < sortedLevels.length - 1 ? sortedLevels[index + 1] : undefined
                const trend = getTrend(level, previous)
                
                return (
                  <div
                    key={level.id}
                    className="rounded-xl border-2 border-purple-200 dark:border-purple-700 bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/30 dark:to-pink-900/30 p-4 sm:p-5 transition-all duration-300 hover:shadow-lg"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-2">
                          <div className={`w-12 h-12 rounded-full ${getEnergyLevelColor(level.energy_level)} flex items-center justify-center text-white font-bold text-lg shadow-md`}>
                            {level.energy_level}
                          </div>
                          <div>
                            <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                              {getEnergyLevelLabel(level.energy_level)}
                            </p>
                            <p className="text-xs text-gray-600 dark:text-gray-400">{formatDate(level.date)}</p>
                          </div>
                          {trend && (
                            <div className="ml-auto">
                              {trend === 'up' && (
                                <TrendingUp className="h-5 w-5 text-green-600 dark:text-green-400" />
                              )}
                              {trend === 'down' && (
                                <TrendingDown className="h-5 w-5 text-red-600 dark:text-red-400" />
                              )}
                              {trend === 'same' && (
                                <Minus className="h-5 w-5 text-gray-400 dark:text-gray-500" />
                              )}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                          <span>Created: {new Date(level.created_at).toLocaleDateString()}</span>
                          {level.updated_at !== level.created_at && (
                            <span>Updated: {new Date(level.updated_at).toLocaleDateString()}</span>
                          )}
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

