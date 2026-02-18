// Auth Hook and Provider

import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore, useClientStore } from '../store';
import { authApi } from '../api/auth';
import { clientsApi } from '../api';

/**
 * Hook for authentication operations
 */
export function useAuth() {
  const navigate = useNavigate();
  const { user, isAuthenticated, isLoading, setUser, setLoading, logout: storeLogout } = useAuthStore();
  const { setCurrentClient, setClients } = useClientStore();

  // Initialize auth state on mount
  useEffect(() => {
    const initAuth = async () => {
      const accessToken = localStorage.getItem('access_token');
      
      if (!accessToken) {
        setLoading(false);
        return;
      }

      try {
        // Verify token by fetching current user
        const currentUser = await authApi.getCurrentUser();
        setUser(currentUser);

        // Load client data
        if (currentUser.client_id) {
          try {
            const client = await clientsApi.get(currentUser.client_id);
            setCurrentClient(client);
          } catch (e) {
            console.error('Failed to load client:', e);
          }
        }

        // Load all clients for admin users
        if (currentUser.role === 'super_admin' || currentUser.role === 'admin') {
          try {
            const clients = await clientsApi.list();
            setClients(clients);
            if (clients.length > 0 && !currentUser.client_id) {
              setCurrentClient(clients[0]);
            }
          } catch (e) {
            console.error('Failed to load clients:', e);
          }
        }
      } catch (error) {
        // Token invalid, clear auth
        storeLogout();
      } finally {
        setLoading(false);
      }
    };

    if (isLoading) {
      initAuth();
    }
  }, [isLoading, setUser, setLoading, storeLogout, setCurrentClient, setClients]);

  // Logout function
  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch (error) {
      // Ignore errors, proceed with logout anyway
    } finally {
      storeLogout();
      navigate('/login');
    }
  }, [storeLogout, navigate]);

  // Logout from all devices
  const logoutAll = useCallback(async () => {
    try {
      const result = await authApi.logoutAll();
      return result;
    } catch (error) {
      throw error;
    }
  }, []);

  // Refresh user data
  const refreshUser = useCallback(async () => {
    try {
      const currentUser = await authApi.getCurrentUser();
      setUser(currentUser);
      return currentUser;
    } catch (error) {
      throw error;
    }
  }, [setUser]);

  return {
    user,
    isAuthenticated,
    isLoading,
    logout,
    logoutAll,
    refreshUser,
  };
}

/**
 * Hook for checking specific permissions
 */
export function usePermissions() {
  const { user } = useAuthStore();

  const hasRole = useCallback((roles: string | string[]) => {
    if (!user) return false;
    const roleArray = Array.isArray(roles) ? roles : [roles];
    return roleArray.includes(user.role);
  }, [user]);

  const isAdmin = useCallback(() => {
    return hasRole(['super_admin', 'admin']);
  }, [hasRole]);

  const isSuperAdmin = useCallback(() => {
    return hasRole('super_admin');
  }, [hasRole]);

  const canManageUsers = useCallback(() => {
    return hasRole(['super_admin', 'admin']);
  }, [hasRole]);

  const canManageClients = useCallback(() => {
    return hasRole('super_admin');
  }, [hasRole]);

  const canViewAnalytics = useCallback(() => {
    return hasRole(['super_admin', 'admin', 'agent']);
  }, [hasRole]);

  return {
    hasRole,
    isAdmin,
    isSuperAdmin,
    canManageUsers,
    canManageClients,
    canViewAnalytics,
  };
}

export default useAuth;
