import React, { Suspense } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'

// Components
import { LoadingSpinner } from './components/ui/LoadingSpinner'

// Pages (Lazy loaded)
const Dashboard = React.lazy(() => import('./pages/Dashboard'))
const Login = React.lazy(() => import('./pages/Login'))
const Upload = React.lazy(() => import('./pages/Upload'))

// Styles
import './styles/globals.css'

// Query Client Configuration
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      staleTime: 5 * 60 * 1000, // 5 minutes
      refetchOnWindowFocus: false,
    },
  },
})

// Loading Component
const LoadingFallback = () => (
  <div className="min-h-screen flex items-center justify-center">
    <LoadingSpinner />
  </div>
)

// Main App Component
const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <Routes>
            <Route
              path="/login"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <Login />
                </Suspense>
              }
            />
            <Route
              path="/upload"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <Upload />
                </Suspense>
              }
            />
            <Route
              path="/"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <Dashboard />
                </Suspense>
              }
            />
          </Routes>

          {/* Global Toast Notifications */}
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#fff',
                color: '#333',
                border: '1px solid #e5e7eb',
              },
            }}
          />
        </div>
      </Router>
    </QueryClientProvider>
  )
}

export default App

