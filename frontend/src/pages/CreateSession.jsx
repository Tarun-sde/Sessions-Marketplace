import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { sessionsApi } from '../api/sessions';
import { ErrorMessage } from '../components/ErrorMessage';
import { PlusCircle, ArrowLeft, Calendar, Users, MapPin, AlignLeft, Type, Loader2 } from 'lucide-react';

export const CreateSession = () => {
  const navigate = useNavigate();

  // Compute a default starts_at value 2 days in the future at 10:00 AM
  const defaultFutureDate = () => {
    const d = new Date();
    d.setDate(d.getDate() + 2);
    d.setHours(10, 0, 0, 0);
    return d.toISOString().slice(0, 16);
  };

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    starts_at: defaultFutureDate(),
    capacity: 10,
    location: 'Online'
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'capacity' ? (value === '' ? '' : parseInt(value, 10)) : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Client-side validation checks
    if (!formData.title.trim()) {
      setError('Title is required.');
      return;
    }

    if (!formData.starts_at) {
      setError('Session start time is required.');
      return;
    }

    const startTime = new Date(formData.starts_at);
    if (startTime <= new Date()) {
      setError('Session start time must be in the future.');
      return;
    }

    if (!formData.capacity || formData.capacity < 1) {
      setError('Capacity must be at least 1.');
      return;
    }

    if (formData.capacity > 10000) {
      setError('Capacity cannot exceed 10,000.');
      return;
    }

    setIsSubmitting(true);
    try {
      // Format datetime to standard ISO string
      const payload = {
        ...formData,
        starts_at: new Date(formData.starts_at).toISOString()
      };
      await sessionsApi.create(payload);
      navigate('/creator');
    } catch (err) {
      setError(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="container page-content">
      <Link to="/creator" className="back-link">
        <ArrowLeft size={18} />
        <span>Back to Creator Dashboard</span>
      </Link>

      <div className="form-card">
        <div className="form-header">
          <div className="form-icon-badge">
            <PlusCircle size={24} />
          </div>
          <div>
            <h1 className="form-title">Create New Session</h1>
            <p className="form-subtitle">
              Publish a new session. Seats are strictly concurrency-safe and verified on PostgreSQL.
            </p>
          </div>
        </div>

        {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

        <form onSubmit={handleSubmit} className="session-form">
          <div className="form-group">
            <label htmlFor="title">
              <Type size={16} />
              <span>Session Title *</span>
            </label>
            <input
              id="title"
              name="title"
              type="text"
              className="form-control"
              placeholder="e.g. Guided Morning Breathwork & Meditation"
              value={formData.title}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="description">
              <AlignLeft size={16} />
              <span>Description</span>
            </label>
            <textarea
              id="description"
              name="description"
              rows={4}
              className="form-control"
              placeholder="Detail what attendees will experience, prerequisites, and preparation tips..."
              value={formData.description}
              onChange={handleChange}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="starts_at">
                <Calendar size={16} />
                <span>Start Date & Time *</span>
              </label>
              <input
                id="starts_at"
                name="starts_at"
                type="datetime-local"
                className="form-control"
                value={formData.starts_at}
                onChange={handleChange}
                required
              />
              <span className="field-hint">Must be scheduled in the future</span>
            </div>

            <div className="form-group">
              <label htmlFor="capacity">
                <Users size={16} />
                <span>Capacity (Seats) *</span>
              </label>
              <input
                id="capacity"
                name="capacity"
                type="number"
                min="1"
                max="10000"
                className="form-control"
                value={formData.capacity}
                onChange={handleChange}
                required
              />
              <span className="field-hint">Min: 1, Max: 10,000</span>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="location">
              <MapPin size={16} />
              <span>Location / Platform *</span>
            </label>
            <input
              id="location"
              name="location"
              type="text"
              className="form-control"
              placeholder="e.g. Google Meet, Zoom, Studio Lotus Room 4"
              value={formData.location}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-actions">
            <button
              type="submit"
              className="btn btn-primary btn-lg"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="spinner" size={18} />
                  <span>Publishing Session...</span>
                </>
              ) : (
                <>
                  <PlusCircle size={18} />
                  <span>Publish Session</span>
                </>
              )}
            </button>
            <Link to="/creator" className="btn btn-secondary btn-lg">
              Cancel
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
};
