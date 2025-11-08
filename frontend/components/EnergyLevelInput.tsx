"use client"

import { useState } from 'react'
import { apiClient } from '@/src/lib/api'

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
    <div className="rounded-lg bg-white p-6 shadow-sm">
      <h3 className="mb-4 text-lg font-semibold text-gray-900">Daily Energy Level</h3>
      <div className="mb-4">
        <label className="mb-2 block text-sm font-medium text-gray-700">
          Select your energy level for {new Date(date).toLocaleDateString()}
        </label>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min="1"
            max="5"
            value={energyLevel}
            onChange={(e) => setEnergyLevel(Number(e.target.value))}
            className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-gray-200"
            style={{
              background: `linear-gradient(to right, #ef4444 0%, #f59e0b 25%, #eab308 50%, #84cc16 75%, #22c55e 100%)`,
            }}
          />
          <div className="flex min-w-[120px] items-center justify-center rounded-md bg-gray-100 px-4 py-2">
            <span className="text-2xl font-bold text-gray-900">{energyLevel}</span>
            <span className="ml-2 text-sm text-gray-600">/ 5</span>
          </div>
        </div>
        <p className="mt-2 text-sm text-gray-600">
          {energyLabels[energyLevel - 1]}
        </p>
      </div>
      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      )}
      <button
        onClick={handleSubmit}
        disabled={loading}
        className="w-full rounded-md bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
      >
        {loading ? 'Saving...' : 'Save Energy Level'}
      </button>
    </div>
  )
}

