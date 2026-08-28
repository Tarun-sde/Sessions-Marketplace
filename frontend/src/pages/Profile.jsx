import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { ErrorMessage } from '../components/ErrorMessage';
import {
  User,
  Mail,
  Shield,
  Sparkles,
  CheckCircle,
  ToggleLeft,
  ToggleRight,
  Loader2,
  Save,
  Image,
  FileText
} from 'lucide-react';

export const Profile = () => {
  const { user, isCreator, updateProfile } = useAuth();

  const [formData, setFormData] = useState({
    name: '',
    bio: '',
    avatar_url: ''
  });

  const [isSaving, setIsSaving] = useState(false);
  const [isTogglingCreator, setIsTogglingCreator] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  useEffect(() => {
    if (user) {
      setFormData({
        name: user.name || `${user.first_name || ''} ${user.last_name || ''}`.trim() || '',
        bio: user.bio || '',
        avatar_url: user.avatar_url || ''
      });
    }
  }, [user]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    setError(null);
    setSuccessMsg(null);

    try {
      await updateProfile(formData);
      setSuccessMsg('Profile updated successfully.');
    } catch (err) {
      setError(err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleCreator = async () => {
    setIsTogglingCreator(true);
    setError(null);
    setSuccessMsg(null);

    const newCreatorState = !isCreator;
    try {
      await updateProfile({ is_creator: newCreatorState });
      setSuccessMsg(
        newCreatorState
          ? 'Creator Mode enabled! You can now create and manage sessions.'
          : 'Creator Mode turned off. Your previously created sessions remain owned by you.'
      );
    } catch (err) {
      setError(err);
    } finally {
      setIsTogglingCreator(false);
    }
  };

  return (
    <div className="container page-content">
      <div className="page-header">
        <div>
          <h1 className="page-title">
            <User className="page-title-icon" size={28} />
            <span>Account & Profile</span>
          </h1>
          <p className="page-subtitle">
            Manage your personal profile, avatar, and marketplace creator permissions.
          </p>
        </div>
      </div>

      {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

      {successMsg && (
        <div className="alert-success" role="alert">
          <CheckCircle size={18} />
          <span>{successMsg}</span>
          <button
            className="alert-close"
            onClick={() => setSuccessMsg(null)}
            aria-label="Dismiss alert"
          >
            ×
          </button>
        </div>
      )}

      <div className="profile-layout">
        {/* Left Column: Creator Mode Toggle & Identity Card */}
        <div className="profile-sidebar">
          {/* Creator Mode Switch Card */}
          <div className={`creator-mode-card ${isCreator ? 'active' : ''}`}>
            <div className="creator-mode-header">
              <div className="creator-icon-wrapper">
                <Sparkles size={24} />
              </div>
              <div>
                <h3>Creator Mode</h3>
                <span className="creator-mode-status">
                  {isCreator ? 'Currently Active' : 'Disabled'}
                </span>
              </div>
            </div>

            <p className="creator-mode-desc">
              When Creator Mode is active, you can host sessions, set capacity parameters, view
              attendees, and manage your offerings.
            </p>

            <button
              type="button"
              className={`btn btn-block creator-toggle-btn ${
                isCreator ? 'btn-outline-danger' : 'btn-primary'
              }`}
              onClick={handleToggleCreator}
              disabled={isTogglingCreator}
            >
              {isTogglingCreator ? (
                <>
                  <Loader2 className="spinner" size={18} />
                  <span>Updating Role...</span>
                </>
              ) : isCreator ? (
                <>
                  <ToggleRight size={20} />
                  <span>Disable Creator Mode</span>
                </>
              ) : (
                <>
                  <ToggleLeft size={20} />
                  <span>Become a Creator</span>
                </>
              )}
            </button>
          </div>

          {/* Account Identity Meta */}
          <div className="identity-card">
            <h4>Account Identity</h4>
            <div className="identity-item">
              <span className="identity-label">Account Email</span>
              <strong className="identity-value">{user?.email}</strong>
            </div>
            <div className="identity-item">
              <span className="identity-label">User ID</span>
              <span className="identity-value">#{user?.id}</span>
            </div>
            <div className="identity-item">
              <span className="identity-label">Role Status</span>
              <span className="identity-value">
                {isCreator ? 'Creator & Attendee' : 'Standard Attendee'}
              </span>
            </div>
          </div>
        </div>

        {/* Right Column: Editable Profile Details */}
        <div className="profile-main">
          <div className="form-card">
            <h2 className="section-title">Profile Information</h2>

            <form onSubmit={handleProfileSubmit} className="profile-form">
              <div className="form-group">
                <label htmlFor="name">
                  <User size={16} />
                  <span>Display Name</span>
                </label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  className="form-control"
                  placeholder="Your full name or spiritual pseudonym"
                  value={formData.name}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label htmlFor="bio">
                  <FileText size={16} />
                  <span>Bio & Background</span>
                </label>
                <textarea
                  id="bio"
                  name="bio"
                  rows={4}
                  className="form-control"
                  placeholder="Share your meditation lineage, certifications, practices, or background..."
                  value={formData.bio}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label htmlFor="avatar_url">
                  <Image size={16} />
                  <span>Avatar Image URL</span>
                </label>
                <input
                  id="avatar_url"
                  name="avatar_url"
                  type="url"
                  className="form-control"
                  placeholder="https://example.com/your-avatar.jpg"
                  value={formData.avatar_url}
                  onChange={handleChange}
                />
                <span className="field-hint">Public HTTPS image link for your profile icon</span>
              </div>

              <div className="form-actions">
                <button
                  type="submit"
                  className="btn btn-primary btn-lg"
                  disabled={isSaving}
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="spinner" size={18} />
                      <span>Saving Profile...</span>
                    </>
                  ) : (
                    <>
                      <Save size={18} />
                      <span>Save Profile Changes</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
