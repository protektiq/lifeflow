"use client"

import { useEffect, useState } from 'react'
import { apiClient } from '@/src/lib/api'
import { DailyPlan, EnergyLevel } from '@/src/types/plan'
import EnergyLevelInput from '@/components/EnergyLevelInput'
import DailyPlanView from '@/components/DailyPlanView'
import SourceReliabilityMetrics from '@/components/SourceReliabilityMetrics'

export const dynamic = 'force-dynamic'

export default function DashboardPage() {
  const [dailyPlan, setDailyPlan] = useState<DailyPlan | null>(null)
  const [planLoading, setPlanLoading] = useState(false)
  const [energyLevel, setEnergyLevel] = useState<EnergyLevel | null>(null)
  const [error, setError] = useState<string | null>(null)
  
  // Get today's date in local timezone
  const [today] = useState(() => {
    const now = new Date()
    const year = now.getFullYear()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const day = String(now.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  })

  useEffect(() => {
    loadDailyPlan()
    loadEnergyLevel()
  }, [])

  const loadDailyPlan = async () => {
    try {
      setPlanLoading(true)
      const plan = await apiClient.getPlanForDate(today)
      setDailyPlan(plan)
    } catch (err) {
      console.log('Error loading plan:', err)
      setDailyPlan(null)
    } finally {
      setPlanLoading(false)
    }
  }

  const loadEnergyLevel = async () => {
    try {
      const energy = await apiClient.getEnergyLevelForDate(today)
      setEnergyLevel(energy)
    } catch (err) {
      setEnergyLevel(null)
    }
  }

  const handleGeneratePlan = async () => {
    try {
      setPlanLoading(true)
      setError(null)
      await apiClient.generatePlan(today)
      await loadDailyPlan()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to generate plan')
    } finally {
      setPlanLoading(false)
    }
  }

  const handleEnergyLevelSaved = () => {
    loadEnergyLevel()
    loadDailyPlan()
  }

  return (
    <div>
      {/* Header Row with Energy Level Card */}
      <div className="mb-6 flex flex-col lg:flex-row lg:items-stretch gap-4 lg:gap-6">
        <div className="flex flex-col justify-center max-w-md shrink-0">
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-800 dark:text-gray-200 mb-4">Today's Plan</h2>
          <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400 leading-relaxed">Set your energy level and view your personalized daily plan</p>
        </div>
        <div className="flex-1 min-w-0">
          <EnergyLevelInput
            date={today}
            initialEnergyLevel={energyLevel?.energy_level}
            onSuccess={handleEnergyLevelSaved}
          />
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-2xl bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 p-4 shadow-lg animate-scale-in">
          <p className="text-sm font-medium text-red-800 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* Full Width Daily Plan Card */}
      <div className="w-full mb-6">
        <DailyPlanView
          plan={dailyPlan}
          onRegenerate={handleGeneratePlan}
          loading={planLoading}
          expectedDate={today}
          onTaskUpdated={loadDailyPlan}
        />
      </div>

      {/* Source Reliability Metrics */}
      <div className="w-full">
        <SourceReliabilityMetrics />
      </div>
    </div>
  )
}
