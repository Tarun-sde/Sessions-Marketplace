import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { sessionsApi } from '../api/sessions';
import { bookingsApi } from '../api/bookings';
import { useAuth } from '../context/AuthContext';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { formatSessionDate, formatSessionTime } from '../components/SessionCard';
import {
  Calendar,
  Clock,
  MapPin,
  Users,
  CheckCircle,
  AlertTriangle,
  ArrowLeft,
  Sparkles,
  ShieldCheck,
  Loader2,
  ExternalLink,
  Edit
} from 'lucide-react';

export const SessionDetail = () => {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [session, setSession] = useState(null);
  const [isBookedByMe, setIsBookedByMe] = useState(false);
  const [myBookingId, setMyBookingId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isBooking, setIsBooking] = useState(false);
  const [error, setError] = useState(null);
  const [bookingSuccess, setBookingSuccess] = useState(false);

  const fetchSessionAndBookingStatus = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [sessionData, myBookingsData] = await Promise.all([
        sessionsApi.get(id),
        bookingsApi.getMine().catch(() => ({ active: [], past: [] }))
      ]);

      setSession(sessionData);

      // Check if user holds an active booking for this session
      const activeBooking = myBookingsData.active?.find(
        (b) => b.session && Number(b.session.id) === Number(id)
      );

      if (activeBooking) {
        setIsBookedByMe(true);
        setMyBookingId(activeBooking.id);
      } else {
        setIsBookedByMe(false);
        setMyBookingId(null);
      }
    } catch (err) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchSessionAndBookingStatus();
  }, [fetchSessionAndBookingStatus]);

  const handleBook = async () => {
    setIsBooking(true);
    setError(null);
    setBookingSuccess(false);

    try {
      await bookingsApi.create(session.id);
      setBookingSuccess(true);
      setIsBookedByMe(true);
      // Re-fetch to update remaining seats and fresh count
      const updated = await sessionsApi.get(id);
      setSession(updated);
    } catch (err) {
      setError(err);
      // On 409 SESSION_FULL or state conflict, refresh session data to sync remaining seats
      if (err.code === 'SESSION_FULL' || err.status === 409) {
        sessionsApi.get(id).then((fresh) => setSession(fresh)).catch(() => {});
      }
    } finally {
      setIsBooking(false);
    }
  };

  if (isLoading) {
    return (
      <div className="container page-content">
        <Loading message="Loading session details..." />
      </div>
    );
  }

  if (!session) {
    return (
      <div className="container page-content">
        <div className="card text-center" style={{ padding: '3rem' }}>
          <h2>Session Not Found</h2>
          <p style={{ color: 'var(--color-text-muted)', margin: '1rem 0 2rem' }}>
            The session you requested does not exist or has been deleted.
          </p>
          <Link to="/sessions" className="btn btn-primary">
            Back to Sessions
          </Link>
        </div>
      </div>
    );
  }

  const isOwner = user && session.creator && session.creator.id === user.id;
  const isFull = session.remaining_seats === 0;
  const isStarted = session.is_started || new Date(session.starts_at) <= new Date();

  return (
    <div className="container page-content">
      <Link to="/sessions" className="back-link">
        <ArrowLeft size={18} />
        <span>Back to Catalog</span>
      </Link>

      {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

      {bookingSuccess && (
        <div className="alert-success" role="alert">
          <CheckCircle size={20} />
          <div>
            <strong>Booking Confirmed!</strong> Your seat has been reserved. View it in{' '}
            <Link to="/bookings" style={{ color: 'inherit', textDecoration: 'underline' }}>
              My Bookings
            </Link>
            .
          </div>
        </div>
      )}

      <div className="session-detail-layout">
        {/* Main Details Column */}
        <div className="session-detail-main">
          <div className="detail-header-card">
            <div className="session-badges">
              {isStarted ? (
                <span className="badge badge-warning">Started</span>
              ) : isFull ? (
                <span className="badge badge-danger">FULL</span>
              ) : (
                <span className="badge badge-success">
                  {session.remaining_seats} of {session.capacity} seats remaining
                </span>
              )}

              {isBookedByMe && (
                <span className="badge badge-primary">
                  <CheckCircle size={14} />
                  <span>You are Booked</span>
                </span>
              )}
            </div>

            <h1 className="detail-title">{session.title}</h1>

            <div className="detail-meta-grid">
              <div className="detail-meta-card">
                <Calendar className="meta-icon" size={20} />
                <div>
                  <span className="meta-label">Date</span>
                  <strong className="meta-value">{formatSessionDate(session.starts_at)}</strong>
                </div>
              </div>

              <div className="detail-meta-card">
                <Clock className="meta-icon" size={20} />
                <div>
                  <span className="meta-label">Time</span>
                  <strong className="meta-value">{formatSessionTime(session.starts_at)}</strong>
                </div>
              </div>

              <div className="detail-meta-card">
                <MapPin className="meta-icon" size={20} />
                <div>
                  <span className="meta-label">Location</span>
                  <strong className="meta-value">{session.location || 'Online Session'}</strong>
                </div>
              </div>

              <div className="detail-meta-card">
                <Users className="meta-icon" size={20} />
                <div>
                  <span className="meta-label">Capacity</span>
                  <strong className="meta-value">
                    {session.capacity} Attendees max ({session.active_booking_count || 0} enrolled)
                  </strong>
                </div>
              </div>
            </div>
          </div>

          {/* Description Section */}
          <div className="detail-section-card">
            <h2 className="section-title">About this Session</h2>
            <p className="detail-description-text">
              {session.description || 'No detailed description provided by the creator.'}
            </p>
          </div>

          {/* Creator Information Section */}
          <div className="detail-section-card">
            <h2 className="section-title">Hosted By</h2>
            <div className="creator-profile-card">
              {session.creator?.avatar_url ? (
                <img
                  src={session.creator.avatar_url}
                  alt={session.creator.name}
                  className="creator-large-avatar"
                />
              ) : (
                <div className="creator-large-placeholder">
                  {(session.creator?.name || session.creator?.email || 'C')[0].toUpperCase()}
                </div>
              )}
              <div className="creator-profile-text">
                <h3>{session.creator?.name || session.creator?.email}</h3>
                {session.creator?.bio && <p className="creator-bio">{session.creator.bio}</p>}
                <span className="verified-creator-tag">
                  <ShieldCheck size={14} />
                  <span>Verified Ahoum Creator</span>
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Action Sidebar Column */}
        <div className="session-detail-sidebar">
          <div className="booking-card-cta">
            <h3>Reserve Your Seat</h3>
            <p className="cta-subtext">
              Guaranteed reservation with PostgreSQL row-level capacity safety.
            </p>

            <div className="seat-status-box">
              <div className="seat-stat">
                <span className="stat-label">Remaining Seats</span>
                <span className={`stat-value ${isFull ? 'text-danger' : 'text-success'}`}>
                  {session.remaining_seats}
                </span>
              </div>
              <div className="seat-stat">
                <span className="stat-label">Total Capacity</span>
                <span className="stat-value">{session.capacity}</span>
              </div>
            </div>

            {isOwner ? (
              <div className="owner-notice">
                <p>You are the creator of this session.</p>
                <Link
                  to={`/creator/sessions/${session.id}/edit`}
                  className="btn btn-outline btn-block"
                >
                  <Edit size={16} />
                  <span>Edit Session Details</span>
                </Link>
                <Link to="/creator" className="btn btn-secondary btn-block mt-2">
                  <span>View in Creator Dashboard</span>
                </Link>
              </div>
            ) : isBookedByMe ? (
              <div className="booked-state-box">
                <div className="booked-notice">
                  <CheckCircle size={20} className="text-success" />
                  <span>You have an active booking!</span>
                </div>
                <Link to="/bookings" className="btn btn-secondary btn-block mt-2">
                  <span>View in My Bookings</span>
                </Link>
              </div>
            ) : isStarted ? (
              <button className="btn btn-disabled btn-block" disabled>
                Session Already Started
              </button>
            ) : isFull ? (
              <button className="btn btn-disabled btn-block" disabled>
                Session Full (0 Seats Left)
              </button>
            ) : (
              <button
                className="btn btn-primary btn-block btn-lg book-now-btn"
                onClick={handleBook}
                disabled={isBooking}
              >
                {isBooking ? (
                  <>
                    <Loader2 className="spinner" size={18} />
                    <span>Reserving Seat...</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={18} />
                    <span>Book Session Now</span>
                  </>
                )}
              </button>
            )}

            <div className="booking-guarantees">
              <div className="guarantee-item">
                <ShieldCheck size={14} />
                <span>Instant confirmation</span>
              </div>
              <div className="guarantee-item">
                <CheckCircle size={14} />
                <span>Free cancellation anytime before start</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
