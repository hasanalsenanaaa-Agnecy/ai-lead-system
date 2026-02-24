// Global State Store using Zustand

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Client, DashboardStats } from '../types';
import type { AuthUser } from '../api/auth';

// =============================================================================
// Auth Store
// =============================================================================

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setAuth: (user: AuthUser, accessToken: string, refreshToken: string) => void;
  setUser: (user: AuthUser) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
  setLoading: (loading: boolean) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: true,
      setAuth: (user, accessToken, refreshToken) => {
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
        set({ user, accessToken, refreshToken, isAuthenticated: true, isLoading: false });
      },
      setUser: (user) => set({ user }),
      setTokens: (accessToken, refreshToken) => {
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
        set({ accessToken, refreshToken });
      },
      setLoading: (isLoading) => set({ isLoading }),
      logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('auth-storage');
        localStorage.removeItem('client-storage');
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false, isLoading: false });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        user: state.user, 
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        // Check if tokens are still in localStorage (they persist separately)
        const accessToken = localStorage.getItem('access_token');
        if (state && accessToken) {
          state.isLoading = false;
        } else if (state) {
          state.isLoading = false;
          state.isAuthenticated = false;
        }
      },
    }
  )
);

// =============================================================================
// Client Store (Multi-tenant)
// =============================================================================

interface ClientState {
  currentClient: Client | null;
  clients: Client[];
  setCurrentClient: (client: Client | null) => void;
  setClients: (clients: Client[]) => void;
  updateClient: (client: Client) => void;
}

export const useClientStore = create<ClientState>()(
  persist(
    (set) => ({
      currentClient: null,
      clients: [],
      setCurrentClient: (client) => set({ currentClient: client }),
      setClients: (clients) => set({ clients }),
      updateClient: (client) =>
        set((state) => ({
          clients: state.clients.map((c) => (c.id === client.id ? client : c)),
          currentClient: state.currentClient?.id === client.id ? client : state.currentClient,
        })),
    }),
    {
      name: 'client-storage',
      partialize: (state) => ({ currentClient: state.currentClient }),
    }
  )
);

// =============================================================================
// Dashboard Store
// =============================================================================

interface DashboardState {
  stats: DashboardStats | null;
  isLoading: boolean;
  lastRefresh: Date | null;
  setStats: (stats: DashboardStats) => void;
  setLoading: (loading: boolean) => void;
  refresh: () => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  stats: null,
  isLoading: false,
  lastRefresh: null,
  setStats: (stats) => set({ stats, lastRefresh: new Date() }),
  setLoading: (isLoading) => set({ isLoading }),
  refresh: () => set({ lastRefresh: new Date() }),
}));

// =============================================================================
// UI Store
// =============================================================================

interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark';
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setTheme: (theme: 'light' | 'dark') => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      theme: 'light',
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'ui-storage',
    }
  )
);

// =============================================================================
// Notifications Store
// =============================================================================

interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  read: boolean;
  createdAt: Date;
}

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (notification: Omit<Notification, 'id' | 'read' | 'createdAt'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  clearNotifications: () => void;
}

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: [],
  unreadCount: 0,
  addNotification: (notification) =>
    set((state) => {
      const newNotification: Notification = {
        ...notification,
        id: crypto.randomUUID(),
        read: false,
        createdAt: new Date(),
      };
      return {
        notifications: [newNotification, ...state.notifications].slice(0, 50),
        unreadCount: state.unreadCount + 1,
      };
    }),
  markAsRead: (id) =>
    set((state) => ({
      notifications: state.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      ),
      unreadCount: Math.max(0, state.unreadCount - 1),
    })),
  markAllAsRead: () =>
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),
  clearNotifications: () => set({ notifications: [], unreadCount: 0 }),
}));
