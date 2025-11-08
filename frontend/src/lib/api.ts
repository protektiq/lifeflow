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

  // Task endpoints
  async getRawTasks(params?: { start_date?: string; end_date?: string }) {
    const response = await this.client.get('/api/tasks/raw', { params })
    return response.data
  }

  // Health check
  async healthCheck() {
    const response = await this.client.get('/api/health')
    return response.data
  }
}

export const apiClient = new ApiClient()

