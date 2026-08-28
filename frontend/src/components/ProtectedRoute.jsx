import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Loading } from './Loading';

export const ProtectedRoute = ({ children, requireCreator = false }) => {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <Loading message="Authenticating session..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requireCreator && !user?.is_creator) {
    return (
      <div className="container" style={{ padding: '3rem 1rem', textAlign: 'center' }}>
        <div className="card" style={{ maxWidth: '500px', margin: '0 auto', padding: '2rem' }}>
          <h2>Creator Access Required</h2>
          <p style={{ color: 'var(--color-text-muted)', margin: '1rem 0 1.5rem' }}>
            You need to enable <strong>Creator Mode</strong> on your profile to access Creator tools and create sessions.
          </p>
          <a href="/profile" className="btn btn-primary" style={{ display: 'inline-block' }}>
            Go to Profile & Enable Creator Mode
          </a>
        </div>
      </div>
    );
  }

  return children;
};
