import React, { useState, useEffect } from 'react';
import { sessionsApi } from '../api/sessions';
import { SessionCard } from '../components/SessionCard';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { Search, Filter, RefreshCw, Calendar, Sparkles } from 'lucide-react';

export const Sessions = () => {
  const [sessions, setSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterMode, setFilterMode] = useState('all'); // 'all', 'available', 'upcoming'

  const fetchSessions = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await sessionsApi.list();
      setSessions(data || []);
    } catch (err) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const filteredSessions = sessions.filter((session) => {
    const matchesSearch =
      session.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (session.description && session.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (session.location && session.location.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (session.creator?.name && session.creator.name.toLowerCase().includes(searchQuery.toLowerCase()));

    const isFull = session.remaining_seats === 0;
    const isStarted = session.is_started || new Date(session.starts_at) <= new Date();

    if (!matchesSearch) return false;

    if (filterMode === 'available') {
      return !isFull && !isStarted;
    }
    if (filterMode === 'upcoming') {
      return !isStarted;
    }
    return true;
  });

  return (
    <div className="container page-content">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">
            <Sparkles className="page-title-icon" size={28} />
            <span>Discover Sessions</span>
          </h1>
          <p className="page-subtitle">
            Explore and reserve spots in curated sessions led by verified creators.
          </p>
        </div>

        <button
          className="btn btn-outline btn-sm refresh-btn"
          onClick={fetchSessions}
          disabled={isLoading}
          title="Refresh catalog"
        >
          <RefreshCw size={16} className={isLoading ? 'spinner' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

      {/* Search & Filter Bar */}
      <div className="catalog-toolbar">
        <div className="search-box">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search by title, location, or creator..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="filter-tabs">
          <button
            className={`filter-tab ${filterMode === 'all' ? 'active' : ''}`}
            onClick={() => setFilterMode('all')}
          >
            All Sessions ({sessions.length})
          </button>
          <button
            className={`filter-tab ${filterMode === 'available' ? 'active' : ''}`}
            onClick={() => setFilterMode('available')}
          >
            Available Now
          </button>
          <button
            className={`filter-tab ${filterMode === 'upcoming' ? 'active' : ''}`}
            onClick={() => setFilterMode('upcoming')}
          >
            Upcoming Only
          </button>
        </div>
      </div>

      {/* Content Area */}
      {isLoading ? (
        <Loading message="Loading sessions catalog..." />
      ) : filteredSessions.length === 0 ? (
        <div className="empty-state">
          <Calendar size={48} className="empty-state-icon" />
          <h3>No sessions found</h3>
          <p>
            {searchQuery
              ? `No sessions match "${searchQuery}". Try a different search term.`
              : 'There are currently no sessions available in this view.'}
          </p>
          {searchQuery && (
            <button className="btn btn-outline btn-sm" onClick={() => setSearchQuery('')}>
              Clear Search
            </button>
          )}
        </div>
      ) : (
        <div className="sessions-grid">
          {filteredSessions.map((session) => (
            <SessionCard key={session.id} session={session} />
          ))}
        </div>
      )}
    </div>
  );
};
