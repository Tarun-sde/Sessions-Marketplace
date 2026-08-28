import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi } from '../api/auth';
import { getAccessToken, getStoredUser, clearAuthData } from '../api/client';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(getStoredUser());
  const [isLoading, setIsLoading] = useState(true);

  // Initialize and verify user on mount if token exists
  const initializeAuth = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const freshProfile = await authApi.getMe();
      setUser(freshProfile);
      localStorage.setItem('ahoum_user', JSON.stringify(freshProfile));
    } catch (err) {
      // If profile fetch fails (e.g. invalid/expired token), clear state
      clearAuthData();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  const loginWithGoogle = async (idToken) => {
    setIsLoading(true);
    try {
      const data = await authApi.loginWithGoogleToken(idToken);
      setUser(data.user);
      return data;
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithDevToken = async (email) => {
    setIsLoading(true);
    try {
      const data = await authApi.loginWithDevToken(email);
      setUser(data.user);
      return data;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    authApi.logout();
    setUser(null);
  };

  const refreshUser = async () => {
    try {
      const fresh = await authApi.getMe();
      setUser(fresh);
      localStorage.setItem('ahoum_user', JSON.stringify(fresh));
      return fresh;
    } catch (e) {
      // ignore
    }
  };

  const updateProfile = async (profileData) => {
    const updated = await authApi.updateMe(profileData);
    setUser(updated);
    localStorage.setItem('ahoum_user', JSON.stringify(updated));
    return updated;
  };

  const value = {
    user,
    isAuthenticated: !!user && !!getAccessToken(),
    isCreator: !!user?.is_creator,
    isLoading,
    loginWithGoogle,
    loginWithDevToken,
    logout,
    refreshUser,
    updateProfile
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
