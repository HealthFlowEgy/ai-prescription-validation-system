import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import ApiService from '../services/api'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'

const Dashboard: React.FC = () => {
  const [healthStatus, setHealthStatus] = useState<any>(null)

  // Health check query
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: ApiService.healthCheck,
    refetchInterval: 30000, // Refetch every 30 seconds
  })

  // Version info query
  const { data: version, isLoading: versionLoading } = useQuery({
    queryKey: ['version'],
    queryFn: ApiService.getVersion,
  })

  useEffect(() => {
    if (health) {
      setHealthStatus(health)
    }
  }, [health])

  if (healthLoading || versionLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <h1 className="text-2xl font-bold text-gray-900">
                  Enhanced HealthFlow
                </h1>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-500">
                v{version?.service_version || '2.0.0'}
              </span>
              <Link
                to="/login"
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium"
              >
                Login
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {/* Welcome Section */}
          <div className="bg-white overflow-hidden shadow rounded-lg mb-6">
            <div className="px-4 py-5 sm:p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">
                Welcome to Enhanced HealthFlow
              </h2>
              <p className="text-gray-600 mb-4">
                AI-powered digital prescription validation system implementing international best practices from Estonia, NHS, and Netherlands healthcare models.
              </p>
              <div className="flex space-x-4">
                <Link
                  to="/upload"
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium"
                >
                  Upload Prescription
                </Link>
                <Link
                  to="/login"
                  className="bg-gray-200 hover:bg-gray-300 text-gray-800 px-4 py-2 rounded-md text-sm font-medium"
                >
                  Sign In
                </Link>
              </div>
            </div>
          </div>

          {/* System Status */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Health Status */}
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className={`w-3 h-3 rounded-full ${
                      healthStatus?.status === 'healthy' ? 'bg-green-400' : 'bg-red-400'
                    }`}></div>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-gray-900">
                      System Status
                    </h3>
                    <p className="text-sm text-gray-500">
                      {healthStatus?.status || 'Unknown'}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* API Version */}
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-sm font-medium text-gray-900">
                  API Version
                </h3>
                <p className="text-sm text-gray-500">
                  {version?.api_version || 'v1'}
                </p>
              </div>
            </div>

            {/* Environment */}
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-sm font-medium text-gray-900">
                  Environment
                </h3>
                <p className="text-sm text-gray-500">
                  {healthStatus?.environment || 'Production'}
                </p>
              </div>
            </div>
          </div>

          {/* Features */}
          <div className="mt-8">
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Key Features
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-md font-semibold text-gray-900 mb-2">
                  AI Validation
                </h3>
                <p className="text-sm text-gray-600">
                  Advanced AI-powered prescription validation and drug interaction checking.
                </p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-md font-semibold text-gray-900 mb-2">
                  FHIR R4 Integration
                </h3>
                <p className="text-sm text-gray-600">
                  Full HL7 FHIR R4 compliance for seamless healthcare interoperability.
                </p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-md font-semibold text-gray-900 mb-2">
                  Zero-Trust Security
                </h3>
                <p className="text-sm text-gray-600">
                  Enterprise-grade security with multi-factor authentication and encryption.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default Dashboard

