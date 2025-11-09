export interface Notification {
  id: string
  user_id: string
  task_id: string
  plan_id: string | null
  type: string
  message: string
  scheduled_at: string
  sent_at: string | null
  status: 'pending' | 'sent' | 'dismissed'
  created_at: string
  updated_at: string | null
}

