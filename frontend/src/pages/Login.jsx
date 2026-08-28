import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ErrorMessage } from '../components/ErrorMessage';
import { Sparkles, KeyRound, ArrowRight, ShieldCheck, UserCheck, Loader2 } from 'lucide-react';

export const Login = () => {
  const { loginWithGoogle, loginWithDevToken, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [devEmail, setDevEmail] = useState('user1@example.com');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const from = location.state?.from?.pathname || '/sessions';

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  // Google GSI button initialization if Google Client ID is configured
  useEffect(() => {
    const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (window.google?.accounts?.id && googleClientId) {
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: async (response) => {
          if (response.credential) {
            setIsLoading(true);
            setError(null);
            try {
              await loginWithGoogle(response.credential);
              navigate(from, { replace: true });
            } catch (err) {
              setError(err);
            } finally {
              setIsLoading(false);
            }
          }
        }
      });

      const btnContainer = document.getElementById('google-btn-container');
      if (btnContainer) {
        window.google.accounts.id.renderButton(btnContainer, {
          theme: 'filled_blue',
          size: 'large',
          text: 'continue_with',
          shape: 'rectangular',
          width: 320
        });
      }
    }
  }, [loginWithGoogle, navigate, from]);

  const handleDevLogin = async (e) => {
    e.preventDefault();
    if (!devEmail.trim()) return;

    setIsLoading(true);
    setError(null);
    try {
      await loginWithDevToken(devEmail);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickSelect = (email) => {
    setDevEmail(email);
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo">
            <Sparkles size={32} />
          </div>
          <h1 className="login-title">Welcome to Ahoum</h1>
          <p className="login-subtitle">
            Sign in to discover, host, and book verified wellbeing & spiritual sessions.
          </p>
        </div>

        {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

        {/* Google OAuth Login Section */}
        <div className="login-section">
          <div id="google-btn-container" className="google-btn-wrapper"></div>
          {!import.meta.env.VITE_GOOGLE_CLIENT_ID && (
            <p className="google-note">
              (Live Google OAuth is active when <code>VITE_GOOGLE_CLIENT_ID</code> is configured)
            </p>
          )}
        </div>

        <div className="divider">
          <span>DEVELOPMENT / TESTING AUTH</span>
        </div>

        {/* Developer Authentication Escape Hatch */}
        <div className="dev-auth-box">
          <div className="dev-auth-badge">
            <KeyRound size={16} />
            <span>Dev Token Login (Active in Debug Mode)</span>
          </div>
          <p className="dev-auth-desc">
            Use simulated authentication to test different User & Creator flows without third-party credentials.
          </p>

          <form onSubmit={handleDevLogin} className="dev-login-form">
            <div className="form-group">
              <label htmlFor="dev-email">Test Email Address</label>
              <input
                id="dev-email"
                type="email"
                className="form-control"
                value={devEmail}
                onChange={(e) => setDevEmail(e.target.value)}
                placeholder="e.g. creator@example.com"
                required
              />
            </div>

            <div className="quick-presets">
              <span className="preset-label">Presets:</span>
              <button
                type="button"
                className="preset-btn"
                onClick={() => handleQuickSelect('creator_alice@ahoum.com')}
              >
                Creator Alice
              </button>
              <button
                type="button"
                className="preset-btn"
                onClick={() => handleQuickSelect('user_bob@ahoum.com')}
              >
                User Bob
              </button>
              <button
                type="button"
                className="preset-btn"
                onClick={() => handleQuickSelect('user_charlie@ahoum.com')}
              >
                User Charlie
              </button>
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-block dev-submit-btn"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="spinner" size={18} />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <span>Sign In as {devEmail}</span>
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>
        </div>

        <div className="login-footer">
          <div className="security-item">
            <ShieldCheck size={16} />
            <span>JWT Signed & Encrypted</span>
          </div>
          <div className="security-item">
            <UserCheck size={16} />
            <span>PostgreSQL Verified Invariants</span>
          </div>
        </div>
      </div>
    </div>
  );
};
