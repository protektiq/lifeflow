export interface DailyPlanTask {
  task_id: string
  predicted_start: string
  predicted_end: string
  priority_score: number
  title: string
  is_critical: boolean
  is_urgent: boolean
}

export interface DailyPlan {
  id: string
  user_id: string
  plan_date: string
  tasks: DailyPlanTask[]
  energy_level: number | null
  status: string
  generated_at: string
  created_at: string
  updated_at: string
}

export interface EnergyLevel {
  id: string
  user_id: string
  date: string
  energy_level: number
  created_at: string
  updated_at: string
}

