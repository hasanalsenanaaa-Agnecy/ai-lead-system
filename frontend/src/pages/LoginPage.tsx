// Login Page - Connected to Backend API

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuthStore, useClientStore } from '../store';
import { authApi, LoginResponse, TwoFactorRequiredResponse } from '../api/auth';
import { clientsApi } from '../api';

export default function LoginPage() {
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();
  const { setCurrentClient, setClients } = useClientStore();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  
  // 2FA state
  const [requires2FA, setRequires2FA] = useState(false);
  const [userId2FA, setUserId2FA] = useState<string | null>(null);
  const [twoFactorCode, setTwoFactorCode] = useState('');
  const [useBackupCode, setUseBackupCode] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await authApi.login({
        email,
        password,
        remember_me: rememberMe,
      });

      // Check if 2FA is required
      if ('requires_2fa' in response && response.requires_2fa) {
        const twoFAResponse = response as TwoFactorRequiredResponse;
        setRequires2FA(true);
        setUserId2FA(twoFAResponse.user_id);
        toast.success('Please enter your 2FA code');
      } else {
        // Successful login without 2FA
        await completeLogin(response as LoginResponse);
      }
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Login failed';
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handle2FASubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId2FA) return;
    
    setIsLoading(true);

    try {
      let response: LoginResponse;
      
      if (useBackupCode) {
        response = await authApi.verifyBackupCode(userId2FA, twoFactorCode);
      } else {
        response = await authApi.verify2FA({
          user_id: userId2FA,
          code: twoFactorCode,
        });
      }

      await completeLogin(response);
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Invalid code';
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const completeLogin = async (response: LoginResponse) => {
    // Set auth state
    setAuth(response.user, response.access_token, response.refresh_token);

    // Load client data if user has a client_id
    if (response.user.client_id) {
      try {
        const client = await clientsApi.get(response.user.client_id);
        setCurrentClient(client);
      } catch (e) {
        console.error('Failed to load client:', e);
      }
    }

    // Load all clients for super_admin/admin
    if (response.user.role === 'super_admin' || response.user.role === 'admin') {
      try {
        const clients = await clientsApi.list();
        setClients(clients);
        if (clients.length > 0 && !response.user.client_id) {
          setCurrentClient(clients[0]);
        }
      } catch (e) {
        console.error('Failed to load clients:', e);
      }
    }

    toast.success(`Welcome back, ${response.user.first_name}!`);
    navigate('/');
  };

  // 2FA Form
  if (requires2FA) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="flex justify-center">
            <div className="h-12 w-12 bg-blue-600 rounded-xl flex items-center justify-center">
              <span className="text-white text-xl font-bold">AI</span>
            </div>
          </div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            Two-Factor Authentication
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            {useBackupCode 
              ? 'Enter one of your backup codes'
              : 'Enter the 6-digit code from your authenticator app'}
          </p>
        </div>

        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-white py-8 px-4 shadow-lg sm:rounded-xl sm:px-10 border border-gray-200">
            <form className="space-y-6" onSubmit={handle2FASubmit}>
              <div>
                <label htmlFor="code" className="block text-sm font-medium text-gray-700">
                  {useBackupCode ? 'Backup Code' : 'Verification Code'}
                </label>
                <div className="mt-1">
                  <input
                    id="code"
                    name="code"
                    type="text"
                    required
                    value={twoFactorCode}
                    onChange={(e) => setTwoFactorCode(e.target.value)}
                    className="block w-full appearance-none rounded-lg border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 text-center text-2xl tracking-widest"
                    placeholder={useBackupCode ? 'xxxx-xxxx' : '000000'}
                    maxLength={useBackupCode ? 17 : 6}
                    autoFocus
                  />
                </div>
              </div>

              <div>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex w-full justify-center rounded-lg bg-blue-600 py-2.5 px-4 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? <LoadingSpinner /> : 'Verify'}
                </button>
              </div>

              <div className="text-center">
                <button
                  type="button"
                  onClick={() => setUseBackupCode(!useBackupCode)}
                  className="text-sm text-blue-600 hover:text-blue-500"
                >
                  {useBackupCode ? 'Use authenticator code' : 'Use backup code instead'}
                </button>
              </div>

              <div className="text-center">
                <button
                  type="button"
                  onClick={() => {
                    setRequires2FA(false);
                    setUserId2FA(null);
                    setTwoFactorCode('');
                  }}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  ← Back to login
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    );
  }

  // Regular Login Form
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="h-12 w-12 bg-blue-600 rounded-xl flex items-center justify-center">
            <span className="text-white text-xl font-bold">AI</span>
          </div>
        </div>
        <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
          AI Lead System
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Sign in to manage your leads and conversations
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-lg sm:rounded-xl sm:px-10 border border-gray-200">
          <form className="space-y-6" onSubmit={handleLogin}>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email address
              </label>
              <div className="mt-1">
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="block w-full appearance-none rounded-lg border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="you@example.com"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <div className="mt-1">
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full appearance-none rounded-lg border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  id="remember-me"
                  name="remember-me"
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-700">
                  Remember me
                </label>
              </div>

              <div className="text-sm">
                <Link to="/forgot-password" className="font-medium text-blue-600 hover:text-blue-500">
                  Forgot password?
                </Link>
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="flex w-full justify-center rounded-lg bg-blue-600 py-2.5 px-4 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? <LoadingSpinner /> : 'Sign in'}
              </button>
            </div>
          </form>

          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="bg-white px-2 text-gray-500">New to the platform?</span>
              </div>
            </div>

            <div className="mt-4 text-center">
              <Link to="/register" className="font-medium text-blue-600 hover:text-blue-500">
                Create an account
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function LoadingSpinner() {
  return (
    <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  );
}
