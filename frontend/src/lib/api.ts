import axios, { AxiosInstance, AxiosError } from 'axios'
import { createClient } from './supabase/client'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Add request interceptor to include auth token
    this.client.interceptors.request.use(
      async (config) => {
        try {
          // Get token from Supabase session
          const token = await this.getToken()
          if (token) {
            config.headers.Authorization = `Bearer ${token}`
          }
        } catch (error) {
          console.error('Error getting auth token:', error)
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401 || error.response?.status === 403) {
          // Handle token refresh or redirect to login
          await this.handleUnauthorized()
        }
        return Promise.reject(error)
      }
    )
  }

  private async getToken(): Promise<string | null> {
    if (typeof window !== 'undefined') {
      // Get token from Supabase session
      const supabase = createClient()
      const { data: { session } } = await supabase.auth.getSession()
      return session?.access_token || null
    }
    return null
  }

  private async handleUnauthorized(): Promise<void> {
    if (typeof window !== 'undefined') {
      // Sign out from Supabase
      const supabase = createClient()
      await supabase.auth.signOut()
      window.location.href = '/auth/login'
    }
  }

  // Auth endpoints
  async login(email: string, password: string) {
    const response = await this.client.post('/api/auth/login', {
      email,
      password,
    })
    // Backend returns 'access_token', not 'token'
    const token = response.data.access_token || response.data.token
    if (token && typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token)
    }
    return response.data
  }

  async register(email: string, password: string) {
    const response = await this.client.post('/api/auth/register', {
      email,
      password,
    })
    return response.data
  }

  async getGoogleAuthUrl() {
    const response = await this.client.get('/api/auth/google/authorize')
    return response.data
  }

  // Ingestion endpoints
  async syncCalendar() {
    const response = await this.client.post('/api/ingestion/calendar/sync')
    return response.data
  }

  async syncEmail() {
    const response = await this.client.post('/api/ingestion/email/sync')
    return response.data
  }

  // Task endpoints
  async getRawTasks(params?: { start_date?: string; end_date?: string }) {
    const response = await this.client.get('/api/tasks/raw', { params })
    return response.data
  }

  async getRawTask(taskId: string) {
    const response = await this.client.get(`/api/tasks/raw/${taskId}`)
    return response.data
  }

  async updateTaskFlags(taskId: string, flags: { is_critical?: boolean; is_urgent?: boolean; is_spam?: boolean; extracted_priority?: string }) {
    const response = await this.client.patch(`/api/tasks/raw/${taskId}`, flags)
    return response.data
  }

  // Energy Level endpoints
  async createEnergyLevel(date: string, energyLevel: number) {
    const response = await this.client.post('/api/energy-level', {
      date,
      energy_level: energyLevel,
    })
    return response.data
  }

  async getEnergyLevels(params?: { start_date?: string; end_date?: string }) {
    const response = await this.client.get('/api/energy-level', { params })
    return response.data
  }

  async getEnergyLevelForDate(date: string) {
    const response = await this.client.get(`/api/energy-level/${date}`)
    return response.data
  }

  // Plan endpoints
  async generatePlan(planDate: string) {
    const response = await this.client.post('/api/plans/generate', {
      plan_date: planDate,
    })
    return response.data
  }

  async getPlanForDate(date: string) {
    const response = await this.client.get(`/api/plans/${date}`)
    return response.data
  }

  async getPlans(params?: { start_date?: string; end_date?: string }) {
    const response = await this.client.get('/api/plans', { params })
    return response.data
  }

  async updatePlanStatus(planId: string, status: string) {
    const response = await this.client.put(`/api/plans/${planId}?status=${status}`)
    return response.data
  }

  // Feedback endpoints
  async markTaskDone(taskId: string, planId?: string) {
    const response = await this.client.post(`/api/feedback/task/${taskId}/done`, {
      plan_id: planId || null,
    })
    return response.data
  }

  async snoozeTask(taskId: string, durationMinutes: number, planId?: string) {
    const response = await this.client.post(`/api/feedback/task/${taskId}/snooze`, {
      duration_minutes: durationMinutes,
      plan_id: planId || null,
    })
    return response.data
  }

  async getTaskFeedback(taskId: string) {
    const response = await this.client.get(`/api/feedback/task/${taskId}`)
    return response.data
  }

  // Notification endpoints
  async getNotifications(status?: string, limit?: number) {
    const params: any = {}
    if (status) params.status = status
    if (limit) params.limit = limit
    const response = await this.client.get('/api/notifications', { params })
    return response.data
  }

  async getPendingNotifications(limit?: number) {
    const params: any = {}
    if (limit) params.limit = limit
    const response = await this.client.get('/api/notifications/pending', { params })
    return response.data
  }

  async dismissNotification(notificationId: string) {
    const response = await this.client.post(`/api/notifications/${notificationId}/dismiss`)
    return response.data
  }

  async getNotification(notificationId: string) {
    const response = await this.client.get(`/api/notifications/${notificationId}`)
    return response.data
  }

  // Reminders endpoints
  async getRemindersForDate(date: string) {
    const response = await this.client.get(`/api/reminders/${date}`)
    return response.data
  }

  async convertReminderToTask(reminderId: string) {
    const response = await this.client.post(`/api/reminders/${reminderId}/convert-to-task`)
    return response.data
  }

  // Task Manager endpoints
  async connectTodoist() {
    const response = await this.client.get('/api/auth/todoist/connect')
    return response.data
  }

  async syncTodoist() {
    const response = await this.client.post('/api/task-manager/todoist/sync')
    return response.data
  }

  async getTodoistStatus() {
    const response = await this.client.get('/api/task-manager/todoist/status')
    return response.data
  }

  async resolveConflict(taskId: string, resolution: 'local' | 'external') {
    const response = await this.client.post('/api/task-manager/todoist/resolve-conflict', {
      task_id: taskId,
      resolution,
    })
    return response.data
  }

  async disconnectTodoist() {
    const response = await this.client.delete('/api/auth/todoist/disconnect')
    return response.data
  }

  // Analytics endpoints
  async getTaskTypeMetrics(params?: { start_date?: string; end_date?: string }) {
    const response = await this.client.get('/api/analytics/task-type-metrics', { params })
    return response.data
  }

  async getSourceReliabilityMetrics(params?: { start_date?: string; end_date?: string }) {
    const response = await this.client.get('/api/analytics/source-reliability', { params })
    return response.data
  }

  async getComprehensiveAnalytics(params?: { start_date?: string; end_date?: string }) {
    const response = await this.client.get('/api/analytics/comprehensive', { params })
    return response.data
  }

  // Health check
  async healthCheck() {
    const response = await this.client.get('/api/health')
    return response.data
  }
}

export const apiClient = new ApiClient()

