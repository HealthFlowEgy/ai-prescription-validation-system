/**
 * Enhanced HealthFlow API Service
 * Handles all API communications with the backend
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios'

// API Configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || '/api/v1'

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for authentication
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// API Service Class
export class ApiService {
  // Authentication
  static async login(username: string, password: string) {
    const response = await apiClient.post('/auth/login', {
      username,
      password,
    })
    return response.data
  }

  static async register(userData: any) {
    const response = await apiClient.post('/auth/register', userData)
    return response.data
  }

  // Prescriptions
  static async getPrescriptions(page = 1, perPage = 10) {
    const response = await apiClient.get('/prescriptions', {
      params: { page, per_page: perPage },
    })
    return response.data
  }

  static async uploadPrescription(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await apiClient.post('/prescriptions/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  static async getPrescription(id: string) {
    const response = await apiClient.get(`/prescriptions/${id}`)
    return response.data
  }

  // Health Check
  static async healthCheck() {
    const response = await apiClient.get('/health')
    return response.data
  }

  // Version Info
  static async getVersion() {
    const response = await apiClient.get('/version')
    return response.data
  }
}

export default ApiService

