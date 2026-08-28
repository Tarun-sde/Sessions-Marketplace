import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { sessionsApi } from '../api/sessions';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { Edit, ArrowLeft, Calendar, Users, MapPin, AlignLeft, Type, Loader2 } from 'lucide-react';

export const EditSession = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    starts_at: '',
    capacity: 10,
    location: ''
  });

  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadSession = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const session = await sessionsApi.get(id);
        // Format ISO date string into datetime-local format YYYY-MM-DDTHH:MM
        let localDateStr = '';
        if (session.starts_at) {
          const d = new Date(session.starts_at);
          localDateStr = new Date(d.getTime() - d.getTimezoneOffset() * 60000)
            .toISOString()
            .slice(0, 16);
        }

        setFormData({
          title: session.title || '',
          description: session.description || '',
          starts_at: localDateStr,
          capacity: session.capacity || 1,
          location: session.location || ''
        });
      } catch (err) {
        setError(err);
      } finally {
        setIsLoading(false);
      }
    };

    loadSession();
  }, [id]);

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

    if (!formData.title.trim()) {
      setError('Title is required.');
      return;
    }

    if (!formData.capacity || formData.capacity < 1) {
      setError('Capacity must be at least 1.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        title: formData.title,
        description: formData.description,
        starts_at: new Date(formData.starts_at).toISOString(),
        capacity: formData.capacity,
        location: formData.location
      };

      await sessionsApi.update(id, payload);
      navigate('/creator');
    } catch (err) {
      setError(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="container page-content">
        <Loading message="Loading session details for editing..." />
      </div>
    );
  }

  return (
    <div className="container page-content">
      <Link to="/creator" className="back-link">
        <ArrowLeft size={18} />
        <span>Back to Creator Dashboard</span>
      </Link>

      <div className="form-card">
        <div className="form-header">
          <div className="form-icon-badge">
            <Edit size={24} />
          </div>
          <div>
            <h1 className="form-title">Edit Session</h1>
            <p className="form-subtitle">Update session schedule, details, or capacity parameters.</p>
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
                  <span>Saving Changes...</span>
                </>
              ) : (
                <span>Save Changes</span>
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
