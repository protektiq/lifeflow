"use client"

import { useEffect, useState } from 'react'
import { apiClient } from '@/src/lib/api'
import { DailyPlan, EnergyLevel, Reminder } from '@/src/types/plan'
import EnergyLevelInput from '@/components/EnergyLevelInput'
import DailyPlanView from '@/components/DailyPlanView'
import RemindersView from '@/components/RemindersView'

export const dynamic = 'force-dynamic'

export default function PlanningPage() {
  const [dailyPlan, setDailyPlan] = useState<DailyPlan | null>(null)
  const [planLoading, setPlanLoading] = useState(false)
  const [energyLevel, setEnergyLevel] = useState<EnergyLevel | null>(null)
  const [reminders, setReminders] = useState<Reminder[]>([])
  const [remindersLoading, setRemindersLoading] = useState(false)
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
    loadReminders()
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

  const loadReminders = async () => {
    try {
      setRemindersLoading(true)
      const remindersData = await apiClient.getRemindersForDate(today)
      setReminders(Array.isArray(remindersData) ? remindersData : [])
    } catch (err) {
      console.log('Error loading reminders:', err)
      setReminders([])
    } finally {
      setRemindersLoading(false)
    }
  }

  const handleGeneratePlan = async () => {
    try {
      setPlanLoading(true)
      setError(null)
      await apiClient.generatePlan(today)
      await loadDailyPlan()
      await loadReminders()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to generate plan')
    } finally {
      setPlanLoading(false)
    }
  }

  const handleReminderConverted = async () => {
    await loadReminders()
    await loadDailyPlan()
  }

  const handleEnergyLevelSaved = () => {
    loadEnergyLevel()
    loadDailyPlan()
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-800 dark:text-gray-200 mb-2">Planning</h2>
        <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400">Manage your daily plan, energy levels, and reminders</p>
      </div>

      {error && (
        <div className="mb-4 rounded-2xl bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 p-4 shadow-lg animate-scale-in">
          <p className="text-sm font-medium text-red-800 dark:text-red-300">{error}</p>
        </div>
      )}

      <div className="mb-6 grid gap-4 sm:gap-6 md:grid-cols-2">
        <EnergyLevelInput
          date={today}
          initialEnergyLevel={energyLevel?.energy_level}
          onSuccess={handleEnergyLevelSaved}
        />
        <DailyPlanView
          plan={dailyPlan}
          onRegenerate={handleGeneratePlan}
          loading={planLoading}
          expectedDate={today}
          onTaskUpdated={loadDailyPlan}
        />
      </div>

      <div className="mb-6">
        <RemindersView
          reminders={reminders}
          loading={remindersLoading}
          expectedDate={today}
          onReminderConverted={handleReminderConverted}
        />
      </div>
    </div>
  )
}

