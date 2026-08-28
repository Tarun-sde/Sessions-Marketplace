import { api } from './client';

export const bookingsApi = {
  /**
   * Concurrency-safe booking endpoint
   * POST /api/bookings/
   */
  create: async (sessionId) => {
    return api.post('/api/bookings/', { session_id: sessionId });
  },

  /**
   * Retrieve user's bookings split into active and past
   * GET /api/bookings/mine/
   */
  getMine: async () => {
    return api.get('/api/bookings/mine/');
  },

  /**
   * Cancel an active booking with session row locking
   * DELETE /api/bookings/:id/
   */
  cancel: async (bookingId) => {
    return api.delete(`/api/bookings/${bookingId}/`);
  }
};
