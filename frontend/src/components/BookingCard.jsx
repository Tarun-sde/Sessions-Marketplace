import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Calendar, Clock, MapPin, CheckCircle, XCircle, AlertTriangle, Loader2 } from 'lucide-react';
import { formatSessionDate, formatSessionTime } from './SessionCard';

export const BookingCard = ({ booking, onCancel }) => {
  const [isCancelling, setIsCancelling] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const session = booking.session;
  if (!session) return null;

  const isActive = booking.status === 'active';
  const isStarted = new Date(session.starts_at) <= new Date();

  const handleCancelClick = async () => {
    setIsCancelling(true);
    try {
      await onCancel(booking.id);
    } finally {
      setIsCancelling(false);
      setConfirmOpen(false);
    }
  };

  return (
    <div className={`booking-card ${!isActive ? 'booking-cancelled' : ''}`}>
      <div className="booking-card-header">
        <div className="booking-status-wrapper">
          {isActive ? (
            <span className="badge badge-success">
              <CheckCircle size={14} />
              <span>Confirmed</span>
            </span>
          ) : (
            <span className="badge badge-secondary">
              <XCircle size={14} />
              <span>Cancelled</span>
            </span>
          )}

          {isStarted && (
            <span className="badge badge-warning">Past Event</span>
          )}
        </div>

        <span className="booking-date-booked">
          Booked {new Date(booking.created_at).toLocaleDateString()}
        </span>
      </div>

      <h3 className="booking-title">
        <Link to={`/sessions/${session.id}`}>{session.title}</Link>
      </h3>

      <div className="session-meta-list">
        <div className="session-meta-item">
          <Calendar size={16} />
          <span>{formatSessionDate(session.starts_at)}</span>
        </div>
        <div className="session-meta-item">
          <Clock size={16} />
          <span>{formatSessionTime(session.starts_at)}</span>
        </div>
        {session.location && (
          <div className="session-meta-item">
            <MapPin size={16} />
            <span>{session.location}</span>
          </div>
        )}
      </div>

      {session.creator && (
        <div className="booking-creator-info">
          <span>Hosted by <strong>{session.creator.name || session.creator.email}</strong></span>
        </div>
      )}

      {isActive && !isStarted && (
        <div className="booking-actions">
          {confirmOpen ? (
            <div className="cancellation-confirm-box">
              <div className="confirm-text">
                <AlertTriangle size={16} />
                <span>Cancel your reservation for this session?</span>
              </div>
              <div className="confirm-buttons">
                <button
                  className="btn btn-danger btn-sm"
                  onClick={handleCancelClick}
                  disabled={isCancelling}
                >
                  {isCancelling ? <Loader2 className="spinner" size={14} /> : 'Yes, Cancel'}
                </button>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => setConfirmOpen(false)}
                  disabled={isCancelling}
                >
                  Keep Seat
                </button>
              </div>
            </div>
          ) : (
            <button
              className="btn btn-outline-danger btn-sm"
              onClick={() => setConfirmOpen(true)}
            >
              Cancel Booking
            </button>
          )}
        </div>
      )}
    </div>
  );
};
