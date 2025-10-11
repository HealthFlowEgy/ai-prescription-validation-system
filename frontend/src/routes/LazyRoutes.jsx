/**
 * Lazy-loaded routes for code splitting
 * Reduces initial bundle size
 */

import React, { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import LoadingSpinner from '../components/LoadingSpinner';

// Lazy load route components
const Dashboard = lazy(() => import('../pages/Dashboard'));
const PrescriptionList = lazy(() => import('../pages/PrescriptionList'));
const PrescriptionDetail = lazy(() => import('../pages/PrescriptionDetail'));
const PrescriptionUpload = lazy(() => import('../pages/PrescriptionUpload'));
const Analytics = lazy(() => import('../pages/Analytics'));
const Settings = lazy(() => import('../pages/Settings'));
const UserManagement = lazy(() => import('../pages/UserManagement'));

// Loading fallback component
const LoadingFallback = () => (
  <div className="loading-container" role="status" aria-live="polite">
    <LoadingSpinner />
    <span className="sr-only">Loading page...</span>
  </div>
);

const LazyRoutes = () => {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/prescriptions" element={<PrescriptionList />} />
        <Route path="/prescriptions/:id" element={<PrescriptionDetail />} />
        <Route path="/upload" element={<PrescriptionUpload />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/users" element={<UserManagement />} />
      </Routes>
    </Suspense>
  );
};

export default LazyRoutes;

