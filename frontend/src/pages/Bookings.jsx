import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { bookingsApi } from '../api/bookings';
import { BookingCard } from '../components/BookingCard';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { BookMarked, Calendar, CheckCircle, Clock, Sparkles } from 'lucide-react';

export const Bookings = () => {
  const [activeBookings, setActiveBookings] = useState([]);
  const [pastBookings, setPastBookings] = useState([]);
  const [activeTab, setActiveTab] = useState('active'); // 'active' or 'past'
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [cancelSuccessMsg, setCancelSuccessMsg] = useState(null);

  const fetchBookings = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await bookingsApi.getMine();
      setActiveBookings(data.active || []);
      setPastBookings(data.past || []);
    } catch (err) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBookings();
  }, [fetchBookings]);

  const handleCancelBooking = async (bookingId) => {
    setError(null);
    setCancelSuccessMsg(null);
    try {
      await bookingsApi.cancel(bookingId);
      setCancelSuccessMsg('Booking cancelled successfully. Your seat has been freed.');
      // Refresh list to update active/past separation
      await fetchBookings();
    } catch (err) {
      setError(err);
    }
  };

  const currentBookings = activeTab === 'active' ? activeBookings : pastBookings;

  return (
    <div className="container page-content">
      <div className="page-header">
        <div>
          <h1 className="page-title">
            <BookMarked className="page-title-icon" size={28} />
            <span>My Bookings</span>
          </h1>
          <p className="page-subtitle">
            Manage your registered sessions and review your attendance history.
          </p>
        </div>
      </div>

      {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

      {cancelSuccessMsg && (
        <div className="alert-success" role="alert">
          <CheckCircle size={18} />
          <span>{cancelSuccessMsg}</span>
          <button
            className="alert-close"
            onClick={() => setCancelSuccessMsg(null)}
            aria-label="Dismiss alert"
          >
            ×
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="tabs-container">
        <button
          className={`tab-button ${activeTab === 'active' ? 'active' : ''}`}
          onClick={() => setActiveTab('active')}
        >
          <span>Active Bookings</span>
          <span className="tab-count">{activeBookings.length}</span>
        </button>
        <button
          className={`tab-button ${activeTab === 'past' ? 'active' : ''}`}
          onClick={() => setActiveTab('past')}
        >
          <span>Past & Cancelled</span>
          <span className="tab-count">{pastBookings.length}</span>
        </button>
      </div>

      {/* Content */}
      {isLoading ? (
        <Loading message="Loading your bookings..." />
      ) : currentBookings.length === 0 ? (
        <div className="empty-state">
          <Calendar size={48} className="empty-state-icon" />
          <h3>
            {activeTab === 'active'
              ? 'No active bookings'
              : 'No past or cancelled bookings'}
          </h3>
          <p>
            {activeTab === 'active'
              ? 'You have not booked any upcoming sessions yet. Explore the catalog to join a session.'
              : 'Your booking history will appear here once sessions conclude.'}
          </p>
          {activeTab === 'active' && (
            <Link to="/sessions" className="btn btn-primary btn-sm">
              <Sparkles size={16} />
              <span>Browse Catalog</span>
            </Link>
          )}
        </div>
      ) : (
        <div className="bookings-grid">
          {currentBookings.map((booking) => (
            <BookingCard
              key={booking.id}
              booking={booking}
              onCancel={handleCancelBooking}
            />
          ))}
        </div>
      )}
    </div>
  );
};
