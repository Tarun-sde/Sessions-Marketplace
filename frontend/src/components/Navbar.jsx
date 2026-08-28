import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Sparkles, Calendar, BookMarked, LayoutDashboard, User, LogOut, LogIn, Menu, X } from 'lucide-react';

export const Navbar = () => {
  const { user, isAuthenticated, isCreator, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/sessions" className="navbar-brand">
          <Sparkles className="brand-icon" size={24} />
          <span className="brand-text">Ahoum</span>
          <span className="brand-subtext">Marketplace</span>
        </Link>

        {/* Mobile menu toggle */}
        <button
          className="mobile-toggle"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle navigation menu"
        >
          {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>

        {/* Desktop Nav Links */}
        <div className={`nav-links ${mobileMenuOpen ? 'mobile-open' : ''}`}>
          {isAuthenticated ? (
            <>
              <Link
                to="/sessions"
                className={`nav-link ${isActive('/sessions') ? 'active' : ''}`}
                onClick={() => setMobileMenuOpen(false)}
              >
                <Calendar size={18} />
                <span>Sessions</span>
              </Link>
              <Link
                to="/bookings"
                className={`nav-link ${isActive('/bookings') ? 'active' : ''}`}
                onClick={() => setMobileMenuOpen(false)}
              >
                <BookMarked size={18} />
                <span>My Bookings</span>
              </Link>
              {isCreator && (
                <Link
                  to="/creator"
                  className={`nav-link ${isActive('/creator') ? 'active' : ''}`}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <LayoutDashboard size={18} />
                  <span>Creator Dashboard</span>
                </Link>
              )}
              <Link
                to="/profile"
                className={`nav-link ${isActive('/profile') ? 'active' : ''}`}
                onClick={() => setMobileMenuOpen(false)}
              >
                <User size={18} />
                <span>Profile</span>
              </Link>

              <div className="nav-user-section">
                <span className="user-greeting">
                  {user?.name || user?.email}
                  {isCreator && <span className="creator-tag">Creator</span>}
                </span>
                <button
                  className="btn btn-outline btn-sm logout-btn"
                  onClick={handleLogout}
                  title="Logout"
                >
                  <LogOut size={16} />
                  <span>Logout</span>
                </button>
              </div>
            </>
          ) : (
            <Link
              to="/login"
              className="btn btn-primary btn-sm"
              onClick={() => setMobileMenuOpen(false)}
            >
              <LogIn size={16} />
              <span>Login</span>
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
};
