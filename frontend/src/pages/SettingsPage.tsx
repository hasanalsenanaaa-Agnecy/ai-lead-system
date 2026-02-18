// Settings Page - Client configuration, API keys, and preferences

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import toast from 'react-hot-toast';
import {
  Cog6ToothIcon,
  KeyIcon,
  BellIcon,
  GlobeAltIcon,
  ClipboardDocumentIcon,
  ArrowPathIcon,
  ShieldCheckIcon,
  UserIcon,
  BuildingOfficeIcon,
} from '@heroicons/react/24/outline';
import { useClientStore, useAuthStore } from '../store';
import { clientsApi } from '../api';
import type { Client } from '../types';

type TabType = 'general' | 'notifications' | 'api' | 'security';

function TabButton({ active, onClick, icon: Icon, label }: {
  active: boolean;
  onClick: () => void;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg transition-colors',
        active ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
      )}
    >
      <Icon className={clsx('h-4 w-4', active ? 'text-blue-600' : 'text-gray-400')} />
      {label}
    </button>
  );
}

export default function SettingsPage() {
  const { currentClient, setCurrentClient } = useClientStore();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabType>('general');
  const [apiKeyVisible, setApiKeyVisible] = useState(false);
  const [newApiKey, setNewApiKey] = useState<string | null>(null);

  // General settings form
  const [name, setName] = useState(currentClient?.name || '');
  const [industry, setIndustry] = useState(currentClient?.industry || '');
  const [timezone, setTimezone] = useState(currentClient?.timezone || 'UTC');
  const [language, setLanguage] = useState(currentClient?.primary_language || 'en');

  // Notification settings
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [escalationAlerts, setEscalationAlerts] = useState(true);
  const [dailyDigest, setDailyDigest] = useState(true);
  const [leadAlerts, setLeadAlerts] = useState(true);

  const updateMutation = useMutation({
    mutationFn: (data: { name?: string; industry?: string; timezone?: string; primary_language?: string }) =>
      clientsApi.update(currentClient!.id, data),
    onSuccess: (updatedClient: Client) => {
      setCurrentClient(updatedClient);
      queryClient.invalidateQueries({ queryKey: ['client'] });
      toast.success('Settings updated');
    },
    onError: () => toast.error('Failed to update settings'),
  });

  const rotateKeyMutation = useMutation({
    mutationFn: () => clientsApi.rotateApiKey(currentClient!.id),
    onSuccess: (data) => {
      setNewApiKey(data.api_key);
      toast.success('API key rotated. Copy your new key — it won\'t be shown again.');
    },
    onError: () => toast.error('Failed to rotate API key'),
  });

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  if (!currentClient) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Please select a client to manage settings.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">Manage your account configuration and preferences</p>
      </div>

      <div className="flex flex-col md:flex-row gap-6">
        {/* Tab Navigation */}
        <nav className="flex flex-row md:flex-col md:w-48 gap-1">
          <TabButton active={activeTab === 'general'} onClick={() => setActiveTab('general')} icon={Cog6ToothIcon} label="General" />
          <TabButton active={activeTab === 'notifications'} onClick={() => setActiveTab('notifications')} icon={BellIcon} label="Notifications" />
          <TabButton active={activeTab === 'api'} onClick={() => setActiveTab('api')} icon={KeyIcon} label="API Keys" />
          <TabButton active={activeTab === 'security'} onClick={() => setActiveTab('security')} icon={ShieldCheckIcon} label="Security" />
        </nav>

        {/* Tab Content */}
        <div className="flex-1 bg-white rounded-xl border border-gray-200 p-6">
          {/* General Tab */}
          {activeTab === 'general' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-1">General Settings</h3>
                <p className="text-sm text-gray-500">Update your business information and preferences</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Business Name</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Industry</label>
                  <input
                    type="text"
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    placeholder="e.g., Real Estate, Legal, Healthcare"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
                  <select
                    value={timezone}
                    onChange={(e) => setTimezone(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="UTC">UTC</option>
                    <option value="America/New_York">Eastern Time (ET)</option>
                    <option value="America/Chicago">Central Time (CT)</option>
                    <option value="America/Denver">Mountain Time (MT)</option>
                    <option value="America/Los_Angeles">Pacific Time (PT)</option>
                    <option value="Europe/London">London (GMT/BST)</option>
                    <option value="Europe/Berlin">Berlin (CET)</option>
                    <option value="Asia/Tokyo">Tokyo (JST)</option>
                    <option value="Australia/Sydney">Sydney (AEST)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Primary Language</label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="en">English</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                    <option value="pt">Portuguese</option>
                    <option value="ar">Arabic</option>
                    <option value="zh">Chinese</option>
                    <option value="ja">Japanese</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center gap-3 pt-4 border-t border-gray-200">
                <button
                  onClick={() => updateMutation.mutate({ name, industry, timezone, primary_language: language })}
                  disabled={updateMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
                </button>
              </div>

              {/* Account info */}
              <div className="pt-4 border-t border-gray-200">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Account Information</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                  <div className="flex items-center gap-2 text-gray-600">
                    <BuildingOfficeIcon className="h-4 w-4 text-gray-400" />
                    <span>Client ID: <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{currentClient.id.slice(0, 8)}...</code></span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-600">
                    <UserIcon className="h-4 w-4 text-gray-400" />
                    <span>Slug: <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{currentClient.slug}</code></span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-600">
                    <GlobeAltIcon className="h-4 w-4 text-gray-400" />
                    <span>Status: <strong className={clsx(
                      currentClient.status === 'active' ? 'text-green-600' :
                      currentClient.status === 'paused' ? 'text-yellow-600' : 'text-gray-600'
                    )}>{currentClient.status}</strong></span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Notifications Tab */}
          {activeTab === 'notifications' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-1">Notification Preferences</h3>
                <p className="text-sm text-gray-500">Control how and when you receive notifications</p>
              </div>

              <div className="space-y-4">
                {[
                  { label: 'Email Notifications', description: 'Receive notifications via email', value: emailNotifications, setter: setEmailNotifications },
                  { label: 'Escalation Alerts', description: 'Get alerted when a conversation is escalated', value: escalationAlerts, setter: setEscalationAlerts },
                  { label: 'Hot Lead Alerts', description: 'Get notified when a new hot lead is identified', value: leadAlerts, setter: setLeadAlerts },
                  { label: 'Daily Digest', description: 'Receive a daily summary of lead activity', value: dailyDigest, setter: setDailyDigest },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{item.label}</p>
                      <p className="text-xs text-gray-500">{item.description}</p>
                    </div>
                    <button
                      onClick={() => item.setter(!item.value)}
                      className={clsx(
                        'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                        item.value ? 'bg-blue-600' : 'bg-gray-200'
                      )}
                    >
                      <span className={clsx(
                        'inline-block h-4 w-4 rounded-full bg-white transition-transform',
                        item.value ? 'translate-x-6' : 'translate-x-1'
                      )} />
                    </button>
                  </div>
                ))}
              </div>

              <button
                onClick={() => toast.success('Notification preferences saved')}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                Save Preferences
              </button>
            </div>
          )}

          {/* API Keys Tab */}
          {activeTab === 'api' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-1">API Keys</h3>
                <p className="text-sm text-gray-500">Manage API keys for webhook integrations and external access</p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">Current API Key</span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setApiKeyVisible(!apiKeyVisible)}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      {apiKeyVisible ? 'Hide' : 'Show'}
                    </button>
                  </div>
                </div>
                {newApiKey ? (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <code className="flex-1 text-sm bg-green-50 border border-green-200 px-3 py-2 rounded-lg text-green-800 break-all">
                        {newApiKey}
                      </code>
                      <button
                        onClick={() => copyToClipboard(newApiKey)}
                        className="p-2 text-gray-400 hover:text-blue-600 transition-colors"
                        title="Copy"
                      >
                        <ClipboardDocumentIcon className="h-5 w-5" />
                      </button>
                    </div>
                    <p className="text-xs text-amber-600 font-medium">⚠ Save this key now — it won't be shown again.</p>
                  </div>
                ) : (
                  <code className="text-sm text-gray-500">
                    {apiKeyVisible ? 'sk_live_••••••••••••••••••••' : '••••••••••••••••••••••••••••'}
                  </code>
                )}
              </div>

              <div>
                <button
                  onClick={() => {
                    if (confirm('Are you sure? The current API key will stop working immediately.')) {
                      rotateKeyMutation.mutate();
                    }
                  }}
                  disabled={rotateKeyMutation.isPending}
                  className="inline-flex items-center px-4 py-2 border border-red-300 text-red-700 rounded-lg text-sm font-medium hover:bg-red-50 disabled:opacity-50 transition-colors"
                >
                  <ArrowPathIcon className="h-4 w-4 mr-2" />
                  {rotateKeyMutation.isPending ? 'Rotating...' : 'Rotate API Key'}
                </button>
                <p className="text-xs text-gray-500 mt-2">Rotating will invalidate the current key. Update your integrations before rotating.</p>
              </div>

              <div className="pt-4 border-t border-gray-200">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Webhook Endpoint</h4>
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-sm bg-gray-50 border border-gray-200 px-3 py-2 rounded-lg text-gray-700">
                    {window.location.origin.replace('3000', '8000')}/api/v1/webhooks/{currentClient.slug}/inbound
                  </code>
                  <button
                    onClick={() => copyToClipboard(`${window.location.origin.replace('3000', '8000')}/api/v1/webhooks/${currentClient.slug}/inbound`)}
                    className="p-2 text-gray-400 hover:text-blue-600"
                  >
                    <ClipboardDocumentIcon className="h-5 w-5" />
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-1">Use this URL to receive incoming messages from Twilio, web forms, etc.</p>
              </div>
            </div>
          )}

          {/* Security Tab */}
          {activeTab === 'security' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-1">Security</h3>
                <p className="text-sm text-gray-500">Account security settings and activity</p>
              </div>

              <div className="space-y-4">
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Account Details</h4>
                  <div className="space-y-2 text-sm text-gray-600">
                    <p>Email: <strong>{user?.email}</strong></p>
                    <p>Role: <strong className="capitalize">{user?.role?.replace('_', ' ')}</strong></p>
                    <p>2FA: <strong className={user?.two_factor_enabled ? 'text-green-600' : 'text-gray-400'}>
                      {user?.two_factor_enabled ? 'Enabled' : 'Disabled'}
                    </strong></p>
                    <p>Email Verified: <strong className={user?.is_verified ? 'text-green-600' : 'text-amber-600'}>
                      {user?.is_verified ? 'Yes' : 'No'}
                    </strong></p>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Token Usage</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm text-gray-600">
                      <span>Used this month</span>
                      <span className="font-medium">{currentClient.tokens_used_this_month?.toLocaleString() || 0}</span>
                    </div>
                    <div className="flex justify-between text-sm text-gray-600">
                      <span>Monthly budget</span>
                      <span className="font-medium">{currentClient.monthly_token_budget?.toLocaleString() || 'Unlimited'}</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                      <div
                        className={clsx(
                          'h-2 rounded-full',
                          (currentClient.tokens_used_this_month / (currentClient.monthly_token_budget || 1)) > 0.9 ? 'bg-red-500' :
                          (currentClient.tokens_used_this_month / (currentClient.monthly_token_budget || 1)) > 0.7 ? 'bg-yellow-500' : 'bg-blue-500'
                        )}
                        style={{ width: `${Math.min(100, (currentClient.tokens_used_this_month / (currentClient.monthly_token_budget || 1)) * 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
