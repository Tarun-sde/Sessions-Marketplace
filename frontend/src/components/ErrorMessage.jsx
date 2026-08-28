import React from 'react';
import { AlertCircle, X } from 'lucide-react';

export const ErrorMessage = ({ error, onDismiss }) => {
  if (!error) return null;

  let message = typeof error === 'string' ? error : error.message || 'An error occurred.';
  let code = error.code || null;

  // Specific user-friendly mapping for common business conflicts
  if (code === 'SESSION_FULL') {
    message = 'This session just became full. All seats have been claimed.';
  } else if (code === 'ALREADY_BOOKED') {
    message = 'You already have an active booking for this session.';
  } else if (code === 'SESSION_ALREADY_STARTED') {
    message = 'This session has already started and cannot be booked.';
  } else if (code === 'FORBIDDEN' || code === 'forbidden') {
    message = "You don't have permission to perform this action.";
  }

  return (
    <div className="alert-error" role="alert">
      <div className="alert-icon">
        <AlertCircle size={20} />
      </div>
      <div className="alert-content">
        {code && <span className="alert-badge">{code}</span>}
        <span className="alert-message">{message}</span>
      </div>
      {onDismiss && (
        <button className="alert-close" onClick={onDismiss} aria-label="Dismiss alert">
          <X size={16} />
        </button>
      )}
    </div>
  );
};
