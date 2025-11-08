export interface RawTask {
  id: string
  user_id: string
  source: string
  title: string
  description: string | null
  start_time: string
  end_time: string
  attendees: string[]
  location: string | null
  recurrence_pattern: string | null
  extracted_priority: string | null
  created_at: string
}

export interface RawTaskCreate {
  source: string
  title: string
  description?: string | null
  start_time: string
  end_time: string
  attendees?: string[]
  location?: string | null
  recurrence_pattern?: string | null
  extracted_priority?: string | null
  raw_data: Record<string, unknown>
}

