// Auth API Client

import api from './index';

// =============================================================================
// Auth Types
// =============================================================================

export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
  requires_2fa?: boolean;
}

export interface TwoFactorRequiredResponse {
  requires_2fa: boolean;
  user_id: string;
  message: string;
}

export interface TwoFactorLoginRequest {
  user_id: string;
  code: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone?: string;
}

export interface RegisterResponse {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  message: string;
}

export interface AuthUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string | null;
  avatar_url: string | null;
  role: 'super_admin' | 'admin' | 'agent' | 'viewer';
  is_verified: boolean;
  two_factor_enabled: boolean;
  client_id: string | null;
  timezone: string;
  language: string;
  created_at: string;
  last_login_at: string | null;
}

export interface TokenRefreshRequest {
  refresh_token: string;
}

export interface TokenRefreshResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
  logout_other_sessions?: boolean;
}

export interface UserUpdateRequest {
  first_name?: string;
  last_name?: string;
  phone?: string;
  timezone?: string;
  language?: string;
}

export interface SessionInfo {
  id: string;
  device_info: string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
  last_activity_at: string;
  expires_at: string;
  is_current: boolean;
}

// =============================================================================
// Auth API
// =============================================================================

export const authApi = {
  // Registration
  register: async (data: RegisterRequest): Promise<RegisterResponse> => {
    const response = await api.post('/api/v1/auth/register', data);
    return response.data;
  },

  // Login
  login: async (data: LoginRequest): Promise<LoginResponse | TwoFactorRequiredResponse> => {
    const response = await api.post('/api/v1/auth/login', data);
    return response.data;
  },

  // 2FA Login
  verify2FA: async (data: TwoFactorLoginRequest): Promise<LoginResponse> => {
    const response = await api.post('/api/v1/auth/login/2fa', data);
    return response.data;
  },

  // Backup code login
  verifyBackupCode: async (user_id: string, backup_code: string): Promise<LoginResponse> => {
    const response = await api.post('/api/v1/auth/login/backup-code', { user_id, backup_code });
    return response.data;
  },

  // Token refresh
  refreshToken: async (refresh_token: string): Promise<TokenRefreshResponse> => {
    const response = await api.post('/api/v1/auth/refresh', { refresh_token });
    return response.data;
  },

  // Logout
  logout: async (): Promise<void> => {
    await api.post('/api/v1/auth/logout');
  },

  // Logout all sessions
  logoutAll: async (): Promise<{ message: string; sessions_invalidated: number }> => {
    const response = await api.post('/api/v1/auth/logout/all');
    return response.data;
  },

  // Password management
  forgotPassword: async (email: string): Promise<{ message: string }> => {
    const response = await api.post('/api/v1/auth/password/forgot', { email });
    return response.data;
  },

  resetPassword: async (data: ResetPasswordRequest): Promise<{ message: string }> => {
    const response = await api.post('/api/v1/auth/password/reset', data);
    return response.data;
  },

  changePassword: async (data: ChangePasswordRequest): Promise<{ message: string }> => {
    const response = await api.post('/api/v1/auth/password/change', data);
    return response.data;
  },

  // Email verification
  verifyEmail: async (token: string): Promise<{ message: string; verified: boolean }> => {
    const response = await api.post('/api/v1/auth/verify-email', { token });
    return response.data;
  },

  resendVerification: async (email: string): Promise<{ message: string }> => {
    const response = await api.post('/api/v1/auth/resend-verification', { email });
    return response.data;
  },

  // 2FA management
  enable2FA: async (): Promise<{ secret: string; backup_codes: string[]; message: string }> => {
    const response = await api.post('/api/v1/auth/2fa/enable');
    return response.data;
  },

  disable2FA: async (password: string): Promise<{ message: string }> => {
    const response = await api.post('/api/v1/auth/2fa/disable', { password });
    return response.data;
  },

  regenerateBackupCodes: async (password: string): Promise<{ backup_codes: string[]; message: string }> => {
    const response = await api.post('/api/v1/auth/2fa/backup-codes', { password });
    return response.data;
  },

  // Sessions
  getSessions: async (): Promise<{ sessions: SessionInfo[]; total: number }> => {
    const response = await api.get('/api/v1/auth/sessions');
    return response.data;
  },

  revokeSession: async (sessionId: string): Promise<{ message: string }> => {
    const response = await api.delete(`/api/v1/auth/sessions/${sessionId}`);
    return response.data;
  },

  // Current user
  getCurrentUser: async (): Promise<AuthUser> => {
    const response = await api.get('/api/v1/auth/me');
    return response.data;
  },

  updateProfile: async (data: UserUpdateRequest): Promise<{ user: AuthUser; message: string }> => {
    const response = await api.patch('/api/v1/auth/me', data);
    return response.data;
  },
};

export default authApi;
