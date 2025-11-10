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
    <div className="group relative rounded-2xl bg-white p-6 sm:p-8 shadow-lg transition-all duration-300 hover:shadow-2xl hover:scale-105 animate-scale-in">
      <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg sm:text-xl font-bold">
            <span className="gradient-text">Daily Energy Level</span>
          </h3>
          <button
            onClick={() => setShowHistory(true)}
            className="flex items-center gap-2 px-3 py-1.5 text-xs sm:text-sm font-semibold text-purple-700 bg-purple-100 rounded-full border-2 border-purple-300 transition-all duration-300 hover:bg-purple-200 hover:border-purple-400 hover:scale-110 focus:outline-none focus:ring-4 focus:ring-purple-500/50"
            aria-label="View energy level history"
          >
            <History className="h-3 w-3 sm:h-4 sm:w-4" />
            <span className="hidden sm:inline">History</span>
          </button>
        </div>
        <div className="mb-6">
          <label className="mb-3 block text-sm sm:text-base font-medium text-gray-700">
            Select your energy level for {new Date(date).toLocaleDateString()}
          </label>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
            <input
              type="range"
              min="1"
              max="5"
              value={energyLevel}
              onChange={(e) => setEnergyLevel(Number(e.target.value))}
              className="h-3 w-full cursor-pointer appearance-none rounded-lg bg-gray-200"
              style={{
                background: `linear-gradient(to right, #ef4444 0%, #f59e0b 25%, #eab308 50%, #84cc16 75%, #22c55e 100%)`,
              }}
            />
            <div className="flex w-full sm:w-auto sm:min-w-[120px] items-center justify-center rounded-xl bg-gradient-to-br from-purple-100 to-pink-100 px-4 py-3 border-2 border-purple-200">
              <span className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">{energyLevel}</span>
              <span className="ml-2 text-sm sm:text-base text-gray-600">/ 5</span>
            </div>
          </div>
          <p className="mt-3 text-sm sm:text-base font-medium text-gray-700">
            {energyLabels[energyLevel - 1]}
          </p>
        </div>
        {error && (
          <div className="mb-4 rounded-xl bg-red-50 border-2 border-red-200 p-3 text-sm font-medium text-red-800">
            {error}
          </div>
        )}
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="group relative w-full px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold text-sm sm:text-base rounded-full overflow-hidden transition-all duration-300 hover:scale-110 hover:shadow-xl hover:shadow-purple-500/50 focus:outline-none focus:ring-4 focus:ring-purple-500/50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
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

