// Settings Page for Client Configuration

import { useState } from 'react';
import { clsx } from 'clsx';
import toast from 'react-hot-toast';
import {
  Cog6ToothIcon,
  BellIcon,
  ChatBubbleLeftRightIcon,
  KeyIcon,
  BuildingOfficeIcon,
  ClipboardDocumentIcon,
  EyeIcon,
  EyeSlashIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { useClientStore } from '../store';

interface TabProps {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const tabs: TabProps[] = [
  { id: 'business', label: 'Business Info', icon: BuildingOfficeIcon },
  { id: 'ai', label: 'AI Configuration', icon: ChatBubbleLeftRightIcon },
  { id: 'notifications', label: 'Notifications', icon: BellIcon },
  { id: 'integrations', label: 'Integrations', icon: Cog6ToothIcon },
  { id: 'api', label: 'API Keys', icon: KeyIcon },
];

function BusinessInfoTab() {
  const [formData, setFormData] = useState({
    businessName: 'Al-Rashid Real Estate',
    industry: 'real_estate',
    timezone: 'Asia/Riyadh',
    primaryLanguage: 'ar',
    businessHours: 'Sunday-Thursday 9:00 AM - 6:00 PM',
    address: 'King Fahd Road, Riyadh, Saudi Arabia',
    website: 'https://example-realty.sa',
  });

  const handleSave = () => {
    toast.success('Business information saved');
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900">Business Information</h3>
        <p className="text-sm text-gray-500">
          Basic information about your business for the AI to reference
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Business Name
          </label>
          <input
            type="text"
            value={formData.businessName}
            onChange={(e) => setFormData({ ...formData, businessName: e.target.value })}
            className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Industry
          </label>
          <select
            value={formData.industry}
            onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
            className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="real_estate">Real Estate</option>
            <option value="automotive">Automotive</option>
            <option value="healthcare">Healthcare</option>
            <option value="legal">Legal Services</option>
            <option value="finance">Financial Services</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Timezone
          </label>
          <select
            value={formData.timezone}
            onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
            className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="Asia/Riyadh">Saudi Arabia (GMT+3)</option>
            <option value="Asia/Dubai">UAE (GMT+4)</option>
            <option value="America/New_York">Eastern Time (GMT-5)</option>
            <option value="America/Los_Angeles">Pacific Time (GMT-8)</option>
            <option value="Europe/London">London (GMT+0)</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Primary Language
          </label>
          <select
            value={formData.primaryLanguage}
            onChange={(e) => setFormData({ ...formData, primaryLanguage: e.target.value })}
            className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="ar">Arabic</option>
            <option value="en">English</option>
            <option value="ar-en">Arabic & English (Bilingual)</option>
          </select>
        </div>

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Business Hours
          </label>
          <input
            type="text"
            value={formData.businessHours}
            onChange={(e) => setFormData({ ...formData, businessHours: e.target.value })}
            placeholder="e.g., Sunday-Thursday 9:00 AM - 6:00 PM"
            className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Website
          </label>
          <input
            type="url"
            value={formData.website}
            onChange={(e) => setFormData({ ...formData, website: e.target.value })}
            className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Save Changes
        </button>
      </div>
    </div>
  );
}

function AIConfigTab() {
  const [formData, setFormData] = useState({
    tone: 'professional_friendly',
    responseDelay: 2000,
    maxTurns: 20,
    customInstructions: 'Always greet customers warmly. Focus on understanding their needs before presenting options. If they mention a specific property, try to gather their timeline and budget.',
    qualificationQuestions: [
      'What type of property are you looking for?',
      'What is your preferred location?',
      'What is your budget range?',
      'What is your timeline for moving?',
    ],
    hotLeadTriggers: [
      'Ready to buy this week',
      'Have financing approved',
      'Looking for specific property',
    ],
  });

  const [newQuestion, setNewQuestion] = useState('');
  const [newTrigger, setNewTrigger] = useState('');

  const handleSave = () => {
    toast.success('AI configuration saved');
  };

  const addQuestion = () => {
    if (newQuestion.trim()) {
      setFormData({
        ...formData,
        qualificationQuestions: [...formData.qualificationQuestions, newQuestion.trim()],
      });
      setNewQuestion('');
    }
  };

  const removeQuestion = (index: number) => {
    setFormData({
      ...formData,
      qualificationQuestions: formData.qualificationQuestions.filter((_, i) => i !== index),
    });
  };

  const addTrigger = () => {
    if (newTrigger.trim()) {
      setFormData({
        ...formData,
        hotLeadTriggers: [...formData.hotLeadTriggers, newTrigger.trim()],
      });
      setNewTrigger('');
    }
  };

  const removeTrigger = (index: number) => {
    setFormData({
      ...formData,
      hotLeadTriggers: formData.hotLeadTriggers.filter((_, i) => i !== index),
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900">AI Configuration</h3>
        <p className="text-sm text-gray-500">
          Customize how the AI interacts with your leads
        </p>
      </div>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Conversation Tone
          </label>
          <select
            value={formData.tone}
            onChange={(e) => setFormData({ ...formData, tone: e.target.value })}
            className="w-full max-w-md rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="professional">Professional</option>
            <option value="professional_friendly">Professional & Friendly</option>
            <option value="casual">Casual & Conversational</option>
            <option value="formal">Formal</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Response Delay (ms)
          </label>
          <input
            type="number"
            value={formData.responseDelay}
            onChange={(e) => setFormData({ ...formData, responseDelay: parseInt(e.target.value) })}
            min={0}
            max={10000}
            step={500}
            className="w-40 rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            Delay before sending AI responses (makes it feel more natural)
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Custom Instructions
          </label>
          <textarea
            value={formData.customInstructions}
            onChange={(e) => setFormData({ ...formData, customInstructions: e.target.value })}
            rows={4}
            className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="Add any specific instructions for the AI..."
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Qualification Questions
          </label>
          <div className="space-y-2 mb-3">
            {formData.qualificationQuestions.map((q, i) => (
              <div key={i} className="flex items-center gap-2 bg-gray-50 px-3 py-2 rounded-lg">
                <span className="flex-1 text-sm">{q}</span>
                <button
                  onClick={() => removeQuestion(i)}
                  className="text-red-500 hover:text-red-700 text-sm"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={newQuestion}
              onChange={(e) => setNewQuestion(e.target.value)}
              placeholder="Add a qualification question..."
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button
              onClick={addQuestion}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
            >
              Add
            </button>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Hot Lead Triggers
          </label>
          <p className="text-xs text-gray-500 mb-2">
            Keywords or phrases that indicate a high-intent lead
          </p>
          <div className="flex flex-wrap gap-2 mb-3">
            {formData.hotLeadTriggers.map((t, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 bg-red-100 text-red-700 px-3 py-1 rounded-full text-sm"
              >
                {t}
                <button onClick={() => removeTrigger(i)} className="hover:text-red-900">
                  ×
                </button>
              </span>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={newTrigger}
              onChange={(e) => setNewTrigger(e.target.value)}
              placeholder="Add a trigger phrase..."
              className="flex-1 max-w-md rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button
              onClick={addTrigger}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
            >
              Add
            </button>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Save Changes
        </button>
      </div>
    </div>
  );
}

function NotificationsTab() {
  const [settings, setSettings] = useState({
    emailHotLeads: true,
    emailEscalations: true,
    emailDailySummary: true,
    smsHotLeads: true,
    smsEscalations: false,
    notificationEmail: 'owner@example-realty.sa',
    notificationPhone: '+966501234567',
  });

  const handleSave = () => {
    toast.success('Notification settings saved');
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900">Notification Settings</h3>
        <p className="text-sm text-gray-500">
          Configure how you want to be notified about leads and escalations
        </p>
      </div>

      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notification Email
            </label>
            <input
              type="email"
              value={settings.notificationEmail}
              onChange={(e) => setSettings({ ...settings, notificationEmail: e.target.value })}
              className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notification Phone
            </label>
            <input
              type="tel"
              value={settings.notificationPhone}
              onChange={(e) => setSettings({ ...settings, notificationPhone: e.target.value })}
              className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="space-y-4">
          <h4 className="font-medium text-gray-900">Email Notifications</h4>
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={settings.emailHotLeads}
              onChange={(e) => setSettings({ ...settings, emailHotLeads: e.target.checked })}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Hot lead alerts</span>
          </label>
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={settings.emailEscalations}
              onChange={(e) => setSettings({ ...settings, emailEscalations: e.target.checked })}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Escalation alerts</span>
          </label>
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={settings.emailDailySummary}
              onChange={(e) => setSettings({ ...settings, emailDailySummary: e.target.checked })}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Daily summary</span>
          </label>
        </div>

        <div className="space-y-4">
          <h4 className="font-medium text-gray-900">SMS Notifications</h4>
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={settings.smsHotLeads}
              onChange={(e) => setSettings({ ...settings, smsHotLeads: e.target.checked })}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Hot lead alerts (SMS)</span>
          </label>
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={settings.smsEscalations}
              onChange={(e) => setSettings({ ...settings, smsEscalations: e.target.checked })}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Escalation alerts (SMS)</span>
          </label>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Save Changes
        </button>
      </div>
    </div>
  );
}

function IntegrationsTab() {
  const [integrations, setIntegrations] = useState({
    twilio: {
      enabled: true,
      phoneNumber: '+1234567890',
      whatsappNumber: '+1234567891',
    },
    hubspot: {
      enabled: false,
      portalId: '',
    },
    calcom: {
      enabled: true,
      eventTypeId: '12345',
    },
  });

  const handleSave = () => {
    toast.success('Integration settings saved');
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900">Integrations</h3>
        <p className="text-sm text-gray-500">
          Connect external services to enhance lead management
        </p>
      </div>

      <div className="space-y-6">
        {/* Twilio */}
        <div className="p-6 bg-gray-50 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 bg-red-100 rounded-lg flex items-center justify-center">
                <span className="text-red-600 font-bold">T</span>
              </div>
              <div>
                <h4 className="font-medium text-gray-900">Twilio</h4>
                <p className="text-sm text-gray-500">SMS & WhatsApp messaging</p>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={integrations.twilio.enabled}
                onChange={(e) =>
                  setIntegrations({
                    ...integrations,
                    twilio: { ...integrations.twilio, enabled: e.target.checked },
                  })
                }
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>
          {integrations.twilio.enabled && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  SMS Phone Number
                </label>
                <input
                  type="text"
                  value={integrations.twilio.phoneNumber}
                  onChange={(e) =>
                    setIntegrations({
                      ...integrations,
                      twilio: { ...integrations.twilio, phoneNumber: e.target.value },
                    })
                  }
                  className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  WhatsApp Number
                </label>
                <input
                  type="text"
                  value={integrations.twilio.whatsappNumber}
                  onChange={(e) =>
                    setIntegrations({
                      ...integrations,
                      twilio: { ...integrations.twilio, whatsappNumber: e.target.value },
                    })
                  }
                  className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>
          )}
        </div>

        {/* HubSpot */}
        <div className="p-6 bg-gray-50 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 bg-orange-100 rounded-lg flex items-center justify-center">
                <span className="text-orange-600 font-bold">H</span>
              </div>
              <div>
                <h4 className="font-medium text-gray-900">HubSpot</h4>
                <p className="text-sm text-gray-500">CRM synchronization</p>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={integrations.hubspot.enabled}
                onChange={(e) =>
                  setIntegrations({
                    ...integrations,
                    hubspot: { ...integrations.hubspot, enabled: e.target.checked },
                  })
                }
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>
          {integrations.hubspot.enabled && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Portal ID
              </label>
              <input
                type="text"
                value={integrations.hubspot.portalId}
                onChange={(e) =>
                  setIntegrations({
                    ...integrations,
                    hubspot: { ...integrations.hubspot, portalId: e.target.value },
                  })
                }
                placeholder="Enter your HubSpot Portal ID"
                className="w-full max-w-md rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          )}
        </div>

        {/* Cal.com */}
        <div className="p-6 bg-gray-50 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 bg-gray-900 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold">C</span>
              </div>
              <div>
                <h4 className="font-medium text-gray-900">Cal.com</h4>
                <p className="text-sm text-gray-500">Appointment scheduling</p>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={integrations.calcom.enabled}
                onChange={(e) =>
                  setIntegrations({
                    ...integrations,
                    calcom: { ...integrations.calcom, enabled: e.target.checked },
                  })
                }
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>
          {integrations.calcom.enabled && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Default Event Type ID
              </label>
              <input
                type="text"
                value={integrations.calcom.eventTypeId}
                onChange={(e) =>
                  setIntegrations({
                    ...integrations,
                    calcom: { ...integrations.calcom, eventTypeId: e.target.value },
                  })
                }
                className="w-full max-w-md rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          )}
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Save Changes
        </button>
      </div>
    </div>
  );
}

function APIKeysTab() {
  const [showKey, setShowKey] = useState(false);
  const [apiKey] = useState('sk_live_abc123def456ghi789jkl012mno345pqr678');

  const copyToClipboard = () => {
    navigator.clipboard.writeText(apiKey);
    toast.success('API key copied to clipboard');
  };

  const rotateKey = () => {
    if (confirm('Are you sure? This will invalidate the current key.')) {
      toast.success('API key rotated. Save the new key securely.');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900">API Keys</h3>
        <p className="text-sm text-gray-500">
          Manage API keys for webhook authentication
        </p>
      </div>

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-sm text-yellow-800">
          <strong>Security Warning:</strong> Keep your API keys secure and never share them publicly.
          Rotate keys immediately if you suspect they've been compromised.
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Production API Key
          </label>
          <div className="flex items-center gap-2">
            <div className="flex-1 flex items-center bg-gray-100 rounded-lg px-4 py-2 font-mono text-sm">
              <span className="flex-1 overflow-hidden">
                {showKey ? apiKey : '•'.repeat(40)}
              </span>
              <button
                onClick={() => setShowKey(!showKey)}
                className="ml-2 text-gray-500 hover:text-gray-700"
              >
                {showKey ? (
                  <EyeSlashIcon className="h-5 w-5" />
                ) : (
                  <EyeIcon className="h-5 w-5" />
                )}
              </button>
            </div>
            <button
              onClick={copyToClipboard}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
              title="Copy to clipboard"
            >
              <ClipboardDocumentIcon className="h-5 w-5" />
            </button>
            <button
              onClick={rotateKey}
              className="inline-flex items-center gap-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg"
            >
              <ArrowPathIcon className="h-5 w-5" />
              Rotate
            </button>
          </div>
        </div>

        <div className="pt-4">
          <h4 className="font-medium text-gray-900 mb-2">Webhook Endpoints</h4>
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2 bg-gray-50 px-4 py-2 rounded-lg font-mono">
              <span className="text-gray-500">POST</span>
              <span>/api/v1/webhook/web-form</span>
            </div>
            <div className="flex items-center gap-2 bg-gray-50 px-4 py-2 rounded-lg font-mono">
              <span className="text-gray-500">POST</span>
              <span>/api/v1/webhook/sms</span>
            </div>
            <div className="flex items-center gap-2 bg-gray-50 px-4 py-2 rounded-lg font-mono">
              <span className="text-gray-500">POST</span>
              <span>/api/v1/webhook/whatsapp</span>
            </div>
            <div className="flex items-center gap-2 bg-gray-50 px-4 py-2 rounded-lg font-mono">
              <span className="text-gray-500">POST</span>
              <span>/api/v1/webhook/live-chat</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('business');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500">Manage your account and preferences</p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar */}
        <div className="lg:w-64 flex-shrink-0">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={clsx(
                  'w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors',
                  activeTab === tab.id
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-50'
                )}
              >
                <tab.icon className="h-5 w-5" />
                <span className="font-medium">{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          {activeTab === 'business' && <BusinessInfoTab />}
          {activeTab === 'ai' && <AIConfigTab />}
          {activeTab === 'notifications' && <NotificationsTab />}
          {activeTab === 'integrations' && <IntegrationsTab />}
          {activeTab === 'api' && <APIKeysTab />}
        </div>
      </div>
    </div>
  );
}
