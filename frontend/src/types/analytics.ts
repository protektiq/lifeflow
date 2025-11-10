export interface TaskTypeMetrics {
  task_type: string
  total_tasks: number
  completed_tasks: number
  completion_rate: number // percentage
  average_time_minutes: number | null // average duration in minutes
}

export interface SourceReliabilityMetrics {
  source: string
  total_tasks: number
  completed_tasks: number
  completion_rate: number // percentage
}

export interface AnalyticsResponse {
  task_type_metrics: TaskTypeMetrics[]
  source_reliability: SourceReliabilityMetrics[]
  period_start: string
  period_end: string
}

