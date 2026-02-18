// Clients Management Page (Admin)

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { format, parseISO } from 'date-fns';
import { clsx } from 'clsx';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  MagnifyingGlassIcon,
  BuildingOfficeIcon,
  PlayIcon,
  PauseIcon,
  TrashIcon,
  PencilIcon,
  EyeIcon,
} from '@heroicons/react/24/outline';
import type { Client, ClientStatus } from '../types';

// Mock data
const mockClients: Client[] = [
  {
    id: '1',
    name: 'Al-Rashid Real Estate',
    slug: 'al-rashid',
    industry: 'Real Estate',
    status: 'active',
    timezone: 'Asia/Riyadh',
    primary_language: 'ar',
    notification_email: 'owner@alrashid.sa',
    tokens_used_this_month: 450000,
    monthly_token_budget: 1000000,
    created_at: new Date(Date.now() - 86400000 * 30).toISOString(),
    updated_at: new Date().toISOString(),
  } as Client,
  {
    id: '2',
    name: 'Premium Motors',
    slug: 'premium-motors',
    industry: 'Automotive',
    status: 'active',
    timezone: 'Asia/Riyadh',
    primary_language: 'en',
    notification_email: 'sales@premium.sa',
    tokens_used_this_month: 280000,
    monthly_token_budget: 500000,
    created_at: new Date(Date.now() - 86400000 * 15).toISOString(),
    updated_at: new Date().toISOString(),
  } as Client,
  {
    id: '3',
    name: 'Gulf Legal Services',
    slug: 'gulf-legal',
    industry: 'Legal',
    status: 'paused',
    timezone: 'Asia/Dubai',
    primary_language: 'en',
    notification_email: 'info@gulflegal.ae',
    tokens_used_this_month: 0,
    monthly_token_budget: 250000,
    created_at: new Date(Date.now() - 86400000 * 45).toISOString(),
    updated_at: new Date(Date.now() - 86400000 * 5).toISOString(),
  } as Client,
  {
    id: '4',
    name: 'Wellness Clinic',
    slug: 'wellness-clinic',
    industry: 'Healthcare',
    status: 'onboarding',
    timezone: 'Asia/Riyadh',
    primary_language: 'ar',
    notification_email: 'admin@wellness.sa',
    tokens_used_this_month: 5000,
    monthly_token_budget: 300000,
    created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
    updated_at: new Date().toISOString(),
  } as Client,
];

const STATUS_COLORS: Record<ClientStatus, { bg: string; text: string; dot: string }> = {
  active: { bg: 'bg-green-100', text: 'text-green-700', dot: 'bg-green-500' },
  paused: { bg: 'bg-yellow-100', text: 'text-yellow-700', dot: 'bg-yellow-500' },
  onboarding: { bg: 'bg-blue-100', text: 'text-blue-700', dot: 'bg-blue-500' },
  churned: { bg: 'bg-red-100', text: 'text-red-700', dot: 'bg-red-500' },
};

interface CreateClientModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (data: { name: string; slug: string; industry: string; email: string }) => void;
}

function CreateClientModal({ isOpen, onClose, onCreate }: CreateClientModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    slug: '',
    industry: 'real_estate',
    email: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.name && formData.slug && formData.email) {
      onCreate(formData);
      setFormData({ name: '', slug: '', industry: 'real_estate', email: '' });
      onClose();
    }
  };

  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        <div className="p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Add New Client</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Business Name
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => {
                  setFormData({
                    ...formData,
                    name: e.target.value,
                    slug: generateSlug(e.target.value),
                  });
                }}
                placeholder="e.g., Acme Real Estate"
                className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Slug (URL identifier)
              </label>
              <input
                type="text"
                value={formData.slug}
                onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                placeholder="e.g., acme-real-estate"
                className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono text-sm"
                required
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
                Contact Email
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="owner@example.com"
                className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                required
              />
            </div>
            <div className="flex justify-end gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Create Client
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function ClientsPage() {
  const [clients, setClients] = useState(mockClients);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<ClientStatus | ''>('');
  const [showCreateModal, setShowCreateModal] = useState(false);

  const filteredClients = clients.filter((client) => {
    if (search) {
      const searchLower = search.toLowerCase();
      if (
        !client.name.toLowerCase().includes(searchLower) &&
        !client.slug.toLowerCase().includes(searchLower)
      ) {
        return false;
      }
    }
    if (statusFilter && client.status !== statusFilter) return false;
    return true;
  });

  const handleCreateClient = (data: { name: string; slug: string; industry: string; email: string }) => {
    const newClient: Client = {
      id: crypto.randomUUID(),
      name: data.name,
      slug: data.slug,
      industry: data.industry,
      status: 'onboarding',
      timezone: 'Asia/Riyadh',
      primary_language: 'en',
      notification_email: data.email,
      tokens_used_this_month: 0,
      monthly_token_budget: 500000,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      config: {},
    };
    setClients([newClient, ...clients]);
    toast.success(`Client "${data.name}" created. API key has been generated.`);
  };

  const toggleClientStatus = (client: Client) => {
    const newStatus: ClientStatus = client.status === 'active' ? 'paused' : 'active';
    setClients(
      clients.map((c) => (c.id === client.id ? { ...c, status: newStatus } : c))
    );
    toast.success(`Client ${newStatus === 'active' ? 'activated' : 'paused'}`);
  };

  const deleteClient = (client: Client) => {
    if (confirm(`Are you sure you want to delete "${client.name}"? This action cannot be undone.`)) {
      setClients(clients.filter((c) => c.id !== client.id));
      toast.success('Client deleted');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clients</h1>
          <p className="text-gray-500">{clients.length} total clients</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <PlusIcon className="h-4 w-4" />
          Add Client
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search clients..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as ClientStatus | '')}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="paused">Paused</option>
          <option value="onboarding">Onboarding</option>
          <option value="churned">Churned</option>
        </select>
      </div>

      {/* Clients Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredClients.map((client) => {
          const usagePercent = Math.round(
            (client.tokens_used_this_month / client.monthly_token_budget) * 100
          );
          const statusColor = STATUS_COLORS[client.status];

          return (
            <div
              key={client.id}
              className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="h-12 w-12 rounded-lg bg-gray-100 flex items-center justify-center">
                    <BuildingOfficeIcon className="h-6 w-6 text-gray-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{client.name}</h3>
                    <p className="text-sm text-gray-500">{client.industry}</p>
                  </div>
                </div>
                <span
                  className={clsx(
                    'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium',
                    statusColor.bg,
                    statusColor.text
                  )}
                >
                  <span className={clsx('h-1.5 w-1.5 rounded-full', statusColor.dot)} />
                  {client.status}
                </span>
              </div>

              <div className="space-y-3 mb-4">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Token Usage</span>
                  <span className="font-medium">
                    {(client.tokens_used_this_month / 1000).toFixed(0)}K /{' '}
                    {(client.monthly_token_budget / 1000).toFixed(0)}K
                  </span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={clsx(
                      'h-full rounded-full transition-all',
                      usagePercent >= 90
                        ? 'bg-red-500'
                        : usagePercent >= 70
                        ? 'bg-yellow-500'
                        : 'bg-blue-500'
                    )}
                    style={{ width: `${Math.min(usagePercent, 100)}%` }}
                  />
                </div>

                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Slug</span>
                  <span className="font-mono text-gray-700">{client.slug}</span>
                </div>

                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Created</span>
                  <span className="text-gray-700">
                    {format(parseISO(client.created_at), 'MMM d, yyyy')}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-4 border-t">
                <Link
                  to={`/clients/${client.id}`}
                  className="flex-1 inline-flex items-center justify-center gap-1 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded-lg"
                >
                  <EyeIcon className="h-4 w-4" />
                  View
                </Link>
                <button
                  onClick={() => toggleClientStatus(client)}
                  className={clsx(
                    'flex-1 inline-flex items-center justify-center gap-1 py-2 text-sm font-medium rounded-lg',
                    client.status === 'active'
                      ? 'text-yellow-600 hover:bg-yellow-50'
                      : 'text-green-600 hover:bg-green-50'
                  )}
                >
                  {client.status === 'active' ? (
                    <>
                      <PauseIcon className="h-4 w-4" />
                      Pause
                    </>
                  ) : (
                    <>
                      <PlayIcon className="h-4 w-4" />
                      Activate
                    </>
                  )}
                </button>
                <button
                  onClick={() => deleteClient(client)}
                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                >
                  <TrashIcon className="h-4 w-4" />
                </button>
              </div>
            </div>
          );
        })}

        {filteredClients.length === 0 && (
          <div className="col-span-full text-center py-12 bg-white rounded-xl border border-dashed border-gray-300">
            <BuildingOfficeIcon className="h-12 w-12 mx-auto text-gray-300 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No clients found</h3>
            <p className="text-gray-500 mb-4">
              {search || statusFilter
                ? 'Try adjusting your filters'
                : 'Add your first client to get started'}
            </p>
            {!search && !statusFilter && (
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                <PlusIcon className="h-4 w-4" />
                Add Client
              </button>
            )}
          </div>
        )}
      </div>

      <CreateClientModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreate={handleCreateClient}
      />
    </div>
  );
}
