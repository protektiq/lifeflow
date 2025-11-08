import axios, { AxiosInstance, AxiosError } from 'axios'

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
      (config) => {
        // Get token from localStorage or cookies
        const token = this.getToken()
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
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
        if (error.response?.status === 401) {
          // Handle token refresh or redirect to login
          this.handleUnauthorized()
        }
        return Promise.reject(error)
      }
    )
  }

  private getToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('auth_token')
    }
    return null
  }

  private handleUnauthorized(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token')
      window.location.href = '/auth/login'
    }
  }

  // Auth endpoints
  async login(email: string, password: string) {
    const response = await this.client.post('/api/auth/login', {
      email,
      password,
    })
    if (response.data.token && typeof window !== 'undefined') {
      localStorage.setItem('auth_token', response.data.token)
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

