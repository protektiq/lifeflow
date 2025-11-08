export interface User {
  id: string
  email: string
  created_at: string
}

export interface UserProfile {
  id: string
  user_id: string
  energy_level: number | null
  preferences: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface UserProfileCreate {
  energy_level?: number | null
  preferences?: Record<string, unknown>
}

export interface UserProfileUpdate {
  energy_level?: number | null
  preferences?: Record<string, unknown>
}

