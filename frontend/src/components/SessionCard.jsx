import React from 'react';
import { Link } from 'react-router-dom';
import { Calendar, Clock, MapPin, Users, ArrowRight } from 'lucide-react';

export const formatSessionDate = (dateStr) => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  }).format(date);
};

export const formatSessionTime = (dateStr) => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short'
  }).format(date);
};

export const SessionCard = ({ session }) => {
  const isFull = session.remaining_seats === 0;
  const isStarted = session.is_started || new Date(session.starts_at) <= new Date();

  return (
    <div className={`session-card ${isFull ? 'session-full' : ''} ${isStarted ? 'session-started' : ''}`}>
      <div className="session-card-header">
        <div className="creator-info">
          {session.creator?.avatar_url ? (
            <img
              src={session.creator.avatar_url}
              alt={session.creator.name}
              className="creator-avatar"
            />
          ) : (
            <div className="creator-avatar-placeholder">
              {(session.creator?.name || session.creator?.email || 'C')[0].toUpperCase()}
            </div>
          )}
          <span className="creator-name">{session.creator?.name || session.creator?.email}</span>
        </div>

        <div className="session-badges">
          {isStarted ? (
            <span className="badge badge-warning">Started</span>
          ) : isFull ? (
            <span className="badge badge-danger">FULL</span>
          ) : (
            <span className="badge badge-success">
              {session.remaining_seats} / {session.capacity} seats left
            </span>
          )}
        </div>
      </div>

      <h3 className="session-title">{session.title}</h3>
      <p className="session-description">
        {session.description || 'No description provided.'}
      </p>

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

      <div className="session-card-footer">
        <Link to={`/sessions/${session.id}`} className="btn btn-outline btn-block">
          <span>View Details</span>
          <ArrowRight size={16} />
        </Link>
      </div>
    </div>
  );
};
