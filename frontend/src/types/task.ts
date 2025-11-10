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
  is_critical: boolean
  is_urgent: boolean
  is_spam: boolean
  spam_reason: string | null
  spam_score: number | null
  created_at: string
  // Sync tracking fields
  external_id?: string | null
  sync_status?: string | null
  last_synced_at?: string | null
  sync_direction?: string | null
  external_updated_at?: string | null
  sync_error?: string | null
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

