"use client"

import { useState } from 'react'
import { apiClient } from '@/src/lib/api'
import EnergyLevelHistory from './EnergyLevelHistory'
import { History } from 'lucide-react'

interface EnergyLevelInputProps {
  date: string
  initialEnergyLevel?: number
  onSuccess?: () => void
}

export default function EnergyLevelInput({
  date,
  initialEnergyLevel,
  onSuccess,
}: EnergyLevelInputProps) {
  const [energyLevel, setEnergyLevel] = useState<number>(initialEnergyLevel || 3)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showHistory, setShowHistory] = useState(false)

  const handleSubmit = async () => {
    try {
      setLoading(true)
      setError(null)
      await apiClient.createEnergyLevel(date, energyLevel)
      onSuccess?.()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save energy level')
    } finally {
      setLoading(false)
    }
  }

  const energyLabels = ['Very Low', 'Low', 'Medium', 'High', 'Very High']

  return (
    <div className="group relative rounded-2xl bg-white dark:bg-gray-800 p-4 sm:p-5 shadow-lg dark:shadow-gray-900/50 transition-all duration-300 hover:shadow-2xl hover:scale-105 animate-scale-in h-full w-full flex flex-col">
      <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-pink-500/10 dark:from-purple-500/20 dark:to-pink-500/20 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
      <div className="relative z-10 flex flex-col flex-1">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg sm:text-xl font-bold">
            <span className="gradient-text">Daily Energy Level</span>
          </h3>
          <button
            onClick={() => setShowHistory(true)}
            className="flex items-center gap-2 px-3 py-1.5 text-xs sm:text-sm font-semibold text-purple-700 dark:text-purple-300 bg-purple-100 dark:bg-purple-900/30 rounded-full border-2 border-purple-300 dark:border-purple-600 transition-all duration-300 hover:bg-purple-200 dark:hover:bg-purple-900/50 hover:border-purple-400 dark:hover:border-purple-500 hover:scale-110 focus:outline-none focus:ring-4 focus:ring-purple-500/50"
            aria-label="View energy level history"
          >
            <History className="h-3 w-3 sm:h-4 sm:w-4" />
            <span className="hidden sm:inline">History</span>
          </button>
        </div>
        <div className="mb-3">
          <label className="mb-2 block text-sm sm:text-base font-medium text-gray-700 dark:text-gray-300">
            Select your energy level for {new Date(date).toLocaleDateString()}
          </label>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <input
              type="range"
              min="1"
              max="5"
              value={energyLevel}
              onChange={(e) => setEnergyLevel(Number(e.target.value))}
              className="h-3 w-full cursor-pointer appearance-none rounded-lg bg-gray-200 dark:bg-gray-700"
              style={{
                background: `linear-gradient(to right, #ef4444 0%, #f59e0b 25%, #eab308 50%, #84cc16 75%, #22c55e 100%)`,
              }}
            />
            <div className="flex w-full sm:w-auto sm:min-w-[120px] items-center justify-center rounded-xl bg-gradient-to-br from-purple-100 to-pink-100 dark:from-purple-900/30 dark:to-pink-900/30 px-4 py-2 border-2 border-purple-200 dark:border-purple-700">
              <span className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 dark:from-purple-400 dark:to-pink-400 bg-clip-text text-transparent">{energyLevel}</span>
              <span className="ml-2 text-sm sm:text-base text-gray-600 dark:text-gray-400">/ 5</span>
            </div>
          </div>
          <p className="mt-2 text-sm sm:text-base font-medium text-gray-700 dark:text-gray-300">
            {energyLabels[energyLevel - 1]}
          </p>
        </div>
        {error && (
          <div className="mb-3 rounded-xl bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 p-2 text-sm font-medium text-red-800 dark:text-red-300">
            {error}
          </div>
        )}
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="group relative w-full px-5 py-2.5 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold text-sm sm:text-base rounded-full overflow-hidden transition-all duration-300 hover:scale-110 hover:shadow-xl hover:shadow-purple-500/50 focus:outline-none focus:ring-4 focus:ring-purple-500/50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 mt-auto"
        >
          <span className="relative z-10">{loading ? 'Saving...' : 'Save Energy Level'}</span>
        </button>
      </div>

      {/* Energy Level History Modal */}
      {showHistory && (
        <EnergyLevelHistory onClose={() => setShowHistory(false)} />
      )}
    </div>
  )
}

