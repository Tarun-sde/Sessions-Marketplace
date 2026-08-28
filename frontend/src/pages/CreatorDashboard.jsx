import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { sessionsApi } from '../api/sessions';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { formatSessionDate, formatSessionTime } from '../components/SessionCard';
import {
  LayoutDashboard,
  PlusCircle,
  Calendar,
  Users,
  Eye,
  Edit,
  Trash2,
  AlertTriangle,
  CheckCircle,
  X,
  Sparkles,
  Loader2
} from 'lucide-react';

export const CreatorDashboard = () => {
  const { user } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionSuccessMsg, setActionSuccessMsg] = useState(null);

  // Attendees Modal state
  const [attendeeModalSession, setAttendeeModalSession] = useState(null);
  const [attendees, setAttendees] = useState([]);
  const [isLoadingAttendees, setIsLoadingAttendees] = useState(false);
  const [attendeesError, setAttendeesError] = useState(null);

  // Deletion Confirm state
  const [deletingSessionId, setDeletingSessionId] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchCreatorSessions = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const allSessions = await sessionsApi.list();
      // Filter sessions owned by current creator
      const mySessions = (allSessions || []).filter(
        (s) => s.creator && Number(s.creator.id) === Number(user?.id)
      );
      setSessions(mySessions);
    } catch (err) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  useEffect(() => {
    fetchCreatorSessions();
  }, [fetchCreatorSessions]);

  const handleOpenAttendees = async (session) => {
    setAttendeeModalSession(session);
    setAttendees([]);
    setIsLoadingAttendees(true);
    setAttendeesError(null);

    try {
      const data = await sessionsApi.getBookings(session.id);
      setAttendees(data || []);
    } catch (err) {
      setAttendeesError(err);
    } finally {
      setIsLoadingAttendees(false);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    setIsDeleting(true);
    setError(null);
    try {
      await sessionsApi.delete(sessionId);
      setActionSuccessMsg('Session deleted successfully.');
      setDeletingSessionId(null);
      await fetchCreatorSessions();
    } catch (err) {
      setError(err);
    } finally {
      setIsDeleting(false);
    }
  };

  // Compute summary stats
  const totalCapacity = sessions.reduce((acc, s) => acc + (s.capacity || 0), 0);
  const totalActiveBookings = sessions.reduce((acc, s) => acc + (s.active_booking_count || 0), 0);

  return (
    <div className="container page-content">
      {/* Dashboard Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">
            <LayoutDashboard className="page-title-icon" size={28} />
            <span>Creator Dashboard</span>
          </h1>
          <p className="page-subtitle">
            Manage your created sessions, view enrollment metrics, and track attendees.
          </p>
        </div>

        <Link to="/creator/sessions/new" className="btn btn-primary">
          <PlusCircle size={18} />
          <span>Create New Session</span>
        </Link>
      </div>

      {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

      {actionSuccessMsg && (
        <div className="alert-success" role="alert">
          <CheckCircle size={18} />
          <span>{actionSuccessMsg}</span>
          <button
            className="alert-close"
            onClick={() => setActionSuccessMsg(null)}
            aria-label="Dismiss alert"
          >
            ×
          </button>
        </div>
      )}

      {/* Metrics Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon-wrapper bg-primary-light">
            <Calendar size={24} className="text-primary" />
          </div>
          <div>
            <span className="stat-label">Total Sessions</span>
            <strong className="stat-number">{sessions.length}</strong>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrapper bg-success-light">
            <Users size={24} className="text-success" />
          </div>
          <div>
            <span className="stat-label">Active Attendees</span>
            <strong className="stat-number">{totalActiveBookings}</strong>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrapper bg-purple-light">
            <Sparkles size={24} className="text-purple" />
          </div>
          <div>
            <span className="stat-label">Total Capacity Offered</span>
            <strong className="stat-number">{totalCapacity}</strong>
          </div>
        </div>
      </div>

      {/* Sessions Management Table / List */}
      <div className="dashboard-content-card">
        <h2 className="dashboard-section-title">My Created Sessions</h2>

        {isLoading ? (
          <Loading message="Loading your sessions..." />
        ) : sessions.length === 0 ? (
          <div className="empty-state">
            <Calendar size={48} className="empty-state-icon" />
            <h3>No sessions created yet</h3>
            <p>
              Start hosting by creating your first session for the Ahoum community.
            </p>
            <Link to="/creator/sessions/new" className="btn btn-primary btn-sm">
              <PlusCircle size={16} />
              <span>Create Your First Session</span>
            </Link>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="creator-table">
              <thead>
                <tr>
                  <th>Session</th>
                  <th>Date & Time</th>
                  <th>Capacity / Enrollment</th>
                  <th>Location</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((session) => {
                  const isFull = session.remaining_seats === 0;
                  const isStarted = session.is_started || new Date(session.starts_at) <= new Date();

                  return (
                    <tr key={session.id}>
                      <td>
                        <Link
                          to={`/sessions/${session.id}`}
                          className="session-table-title"
                        >
                          {session.title}
                        </Link>
                      </td>
                      <td>
                        <div className="table-datetime">
                          <span>{formatSessionDate(session.starts_at)}</span>
                          <span className="text-muted">{formatSessionTime(session.starts_at)}</span>
                        </div>
                      </td>
                      <td>
                        <div className="capacity-badge-wrapper">
                          <span className={`badge ${isFull ? 'badge-danger' : 'badge-primary'}`}>
                            {session.active_booking_count || 0} / {session.capacity} Booked
                          </span>
                          {isStarted && <span className="badge badge-warning">Started</span>}
                        </div>
                      </td>
                      <td>
                        <span className="table-location">{session.location || 'Online'}</span>
                      </td>
                      <td>
                        <div className="table-actions">
                          <button
                            className="btn btn-outline btn-xs"
                            onClick={() => handleOpenAttendees(session)}
                            title="View registered attendees"
                          >
                            <Eye size={14} />
                            <span>Attendees</span>
                          </button>
                          <Link
                            to={`/creator/sessions/${session.id}/edit`}
                            className="btn btn-outline btn-xs"
                            title="Edit session details"
                          >
                            <Edit size={14} />
                            <span>Edit</span>
                          </Link>
                          <button
                            className="btn btn-outline-danger btn-xs"
                            onClick={() => setDeletingSessionId(session.id)}
                            title="Delete session"
                          >
                            <Trash2 size={14} />
                            <span>Delete</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {deletingSessionId && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <div className="modal-title-wrapper text-danger">
                <AlertTriangle size={24} />
                <h3>Confirm Deletion</h3>
              </div>
              <button
                className="modal-close-btn"
                onClick={() => setDeletingSessionId(null)}
              >
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <p>
                Are you sure you want to delete this session? This action is irreversible and
                will cancel all attendee bookings.
              </p>
            </div>
            <div className="modal-footer">
              <button
                className="btn btn-danger"
                onClick={() => handleDeleteSession(deletingSessionId)}
                disabled={isDeleting}
              >
                {isDeleting ? <Loader2 className="spinner" size={16} /> : 'Delete Session'}
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => setDeletingSessionId(null)}
                disabled={isDeleting}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Attendees Modal */}
      {attendeeModalSession && (
        <div className="modal-overlay">
          <div className="modal-content modal-large">
            <div className="modal-header">
              <div>
                <h3>Attendees for "{attendeeModalSession.title}"</h3>
                <p className="text-muted" style={{ fontSize: '0.875rem' }}>
                  {attendees.filter((a) => a.status === 'active').length} active attendee(s)
                </p>
              </div>
              <button
                className="modal-close-btn"
                onClick={() => setAttendeeModalSession(null)}
              >
                <X size={20} />
              </button>
            </div>

            <div className="modal-body">
              {attendeesError && <ErrorMessage error={attendeesError} />}

              {isLoadingAttendees ? (
                <Loading message="Fetching attendees list..." />
              ) : attendees.length === 0 ? (
                <div className="empty-state" style={{ padding: '2rem 1rem' }}>
                  <Users size={36} className="empty-state-icon" />
                  <h4>No bookings yet</h4>
                  <p>When users book your session, their details will appear here.</p>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="creator-table">
                    <thead>
                      <tr>
                        <th>Attendee Name</th>
                        <th>Email</th>
                        <th>Status</th>
                        <th>Booked On</th>
                      </tr>
                    </thead>
                    <tbody>
                      {attendees.map((booking) => (
                        <tr key={booking.id}>
                          <td>
                            <strong>{booking.user?.name || 'Anonymous User'}</strong>
                          </td>
                          <td>{booking.user?.email}</td>
                          <td>
                            <span
                              className={`badge ${
                                booking.status === 'active'
                                  ? 'badge-success'
                                  : 'badge-secondary'
                              }`}
                            >
                              {booking.status}
                            </span>
                          </td>
                          <td>
                            {new Date(booking.created_at).toLocaleDateString()} at{' '}
                            {new Date(booking.created_at).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button
                className="btn btn-secondary"
                onClick={() => setAttendeeModalSession(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
