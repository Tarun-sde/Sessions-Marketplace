import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { ProtectedRoute } from './components/ProtectedRoute';

// Pages
import { Login } from './pages/Login';
import { Sessions } from './pages/Sessions';
import { SessionDetail } from './pages/SessionDetail';
import { Bookings } from './pages/Bookings';
import { CreatorDashboard } from './pages/CreatorDashboard';
import { CreateSession } from './pages/CreateSession';
import { EditSession } from './pages/EditSession';
import { Profile } from './pages/Profile';

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="app-shell">
          <Navbar />
          <main className="main-content">
            <Routes>
              {/* Public Auth Route */}
              <Route path="/login" element={<Login />} />

              {/* Authenticated User Routes */}
              <Route
                path="/sessions"
                element={
                  <ProtectedRoute>
                    <Sessions />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/sessions/:id"
                element={
                  <ProtectedRoute>
                    <SessionDetail />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/bookings"
                element={
                  <ProtectedRoute>
                    <Bookings />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/profile"
                element={
                  <ProtectedRoute>
                    <Profile />
                  </ProtectedRoute>
                }
              />

              {/* Creator-Only Routes */}
              <Route
                path="/creator"
                element={
                  <ProtectedRoute requireCreator={true}>
                    <CreatorDashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/creator/sessions/new"
                element={
                  <ProtectedRoute requireCreator={true}>
                    <CreateSession />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/creator/sessions/:id/edit"
                element={
                  <ProtectedRoute requireCreator={true}>
                    <EditSession />
                  </ProtectedRoute>
                }
              />

              {/* Root & Catch-all Redirects */}
              <Route path="/" element={<Navigate to="/sessions" replace />} />
              <Route path="*" element={<Navigate to="/sessions" replace />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
