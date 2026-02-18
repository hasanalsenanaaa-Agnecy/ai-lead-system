// Global State Store using Zustand

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Client, User, DashboardStats } from '../types';

// =============================================================================
// Auth Store
// =============================================================================

interface AuthState {
  user: User | null;
  token: string | null;
  apiKey: string | null;
  isAuthenticated: boolean;
  setAuth: (user: User, token: string) => void;
  setApiKey: (apiKey: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      apiKey: null,
      isAuthenticated: false,
      setAuth: (user, token) => {
        localStorage.setItem('auth_token', token);
        set({ user, token, isAuthenticated: true });
      },
      setApiKey: (apiKey) => {
        localStorage.setItem('api_key', apiKey);
        set({ apiKey });
      },
      logout: () => {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('api_key');
        set({ user: null, token: null, apiKey: null, isAuthenticated: false });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ user: state.user, token: state.token, apiKey: state.apiKey }),
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
