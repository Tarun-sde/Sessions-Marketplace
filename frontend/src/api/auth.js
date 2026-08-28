import { api, setAuthData, clearAuthData } from './client';

export const authApi = {
  /**
   * Exchanges Google ID token or dev token for JWT tokens and profile
   * POST /api/auth/google/
   */
  loginWithGoogleToken: async (idToken) => {
    const data = await api.post('/api/auth/google/', { id_token: idToken });
    setAuthData(data.access, data.refresh, data.user);
    return data;
  },

  /**
   * Development login fallback (devtoken:<email>)
   */
  loginWithDevToken: async (email) => {
    const devToken = `devtoken:${email.trim()}`;
    return authApi.loginWithGoogleToken(devToken);
  },

  /**
   * Retrieves current authenticated user profile
   * GET /api/me/
   */
  getMe: async () => {
    return api.get('/api/me/');
  },

  /**
   * Updates current user profile (name, bio, avatar_url, is_creator)
   * PATCH /api/me/
   */
  updateMe: async (profileData) => {
    return api.patch('/api/me/', profileData);
  },

  /**
   * Logs out user and purges stored credentials
   */
  logout: () => {
    clearAuthData();
  }
};
