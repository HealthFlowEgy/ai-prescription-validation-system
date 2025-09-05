/**
 * Enhanced HealthFlow API Service - Mock Implementation
 */

// Mock API service for demo purposes
export class ApiService {
  // Mock authentication
  static async login(username: string, password: string) {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    if (username === 'demo' && password === 'password') {
      return {
        access_token: 'mock-jwt-token',
        user: {
          id: '1',
          username: username,
          role: 'doctor'
        }
      }
    } else {
      throw new Error('Invalid credentials')
    }
  }

  // Mock health check
  static async healthCheck() {
    await new Promise(resolve => setTimeout(resolve, 500))
    return {
      status: 'healthy',
      service: 'Enhanced HealthFlow API',
      version: '2.0.0',
      timestamp: new Date().toISOString(),
      environment: 'production'
    }
  }

  // Mock version info
  static async getVersion() {
    return {
      api_version: 'v1',
      service_version: '2.0.0',
      status: 'active'
    }
  }

  // Mock prescriptions
  static async getPrescriptions() {
    await new Promise(resolve => setTimeout(resolve, 800))
    return {
      prescriptions: [
        {
          id: '1',
          patient_name: 'John Doe',
          doctor_name: 'Dr. Smith',
          date: '2024-01-15',
          status: 'validated'
        },
        {
          id: '2',
          patient_name: 'Jane Smith',
          doctor_name: 'Dr. Johnson',
          date: '2024-01-14',
          status: 'pending'
        }
      ],
      total: 2,
      page: 1,
      per_page: 10
    }
  }

  // Mock upload
  static async uploadPrescription(file: File) {
    await new Promise(resolve => setTimeout(resolve, 2000))
    return {
      prescription_id: 'mock-prescription-' + Date.now(),
      status: 'processing',
      message: 'Prescription uploaded successfully'
    }
  }
}

export default ApiService

