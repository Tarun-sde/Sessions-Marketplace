import { api } from './client';

export const sessionsApi = {
  /**
   * List all available sessions in the catalog
   * GET /api/sessions/
   */
  list: async () => {
    return api.get('/api/sessions/');
  },

  /**
   * Get single session detail with live remaining seats
   * GET /api/sessions/:id/
   */
  get: async (id) => {
    return api.get(`/api/sessions/${id}/`);
  },

  /**
   * Create a new session (Creator only)
   * POST /api/sessions/
   */
  create: async (sessionData) => {
    return api.post('/api/sessions/', sessionData);
  },

  /**
   * Update an existing session (Owner only)
   * PATCH /api/sessions/:id/
   */
  update: async (id, sessionData) => {
    return api.patch(`/api/sessions/${id}/`, sessionData);
  },

  /**
   * Delete a session (Owner only)
   * DELETE /api/sessions/:id/
   */
  delete: async (id) => {
    return api.delete(`/api/sessions/${id}/`);
  },

  /**
   * List attendee bookings for an owned session (Owner only)
   * GET /api/sessions/:id/bookings/
   */
  getBookings: async (id) => {
    return api.get(`/api/sessions/${id}/bookings/`);
  }
};
