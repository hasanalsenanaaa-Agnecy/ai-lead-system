// Clients Page - Admin: Manage client/tenant accounts

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import { clsx } from 'clsx';
import toast from 'react-hot-toast';
import {
  BuildingOfficeIcon,
  PlusIcon,
  PencilSquareIcon,
  PlayIcon,
  PauseIcon,
  ClipboardDocumentIcon,
  MagnifyingGlassIcon,
  XMarkIcon,

  ChartBarIcon,
} from '@heroicons/react/24/outline';
import { useClientStore } from '../store';
import { clientsApi } from '../api';
import type { Client, CreateClientRequest } from '../types';

function ClientSkeleton() {
  return (
    <div className="animate-pulse space-y-3">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <div className="h-5 w-40 bg-gray-200 rounded" />
              <div className="h-4 w-24 bg-gray-200 rounded" />
            </div>
            <div className="h-8 w-20 bg-gray-200 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function ClientsPage() {
  const { setCurrentClient } = useClientStore();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingClient, setEditingClient] = useState<Client | null>(null);
  const [newApiKey, setNewApiKey] = useState<{ clientId: string; key: string } | null>(null);

  // Create form
  const [createForm, setCreateForm] = useState<CreateClientRequest>({
    name: '',
    slug: '',
    industry: '',
    timezone: 'America/New_York',
    primary_language: 'en',
  });

  const { data: clients, isLoading } = useQuery({
    queryKey: ['clients-admin'],
    queryFn: () => clientsApi.list(),
  });

  const createMutation = useMutation({
    mutationFn: (data: CreateClientRequest) => clientsApi.create(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['clients-admin'] });
      toast.success('Client created successfully');
      setNewApiKey({ clientId: data.id, key: data.api_key });
      setShowCreateModal(false);
      setCreateForm({ name: '', slug: '', industry: '', timezone: 'America/New_York', primary_language: 'en' });
    },
    onError: () => toast.error('Failed to create client'),
  });

  const activateMutation = useMutation({
    mutationFn: (id: string) => clientsApi.activate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients-admin'] });
      toast.success('Client activated');
    },
    onError: () => toast.error('Failed to activate client'),
  });

  const pauseMutation = useMutation({
    mutationFn: (id: string) => clientsApi.pause(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients-admin'] });
      toast.success('Client paused');
    },
    onError: () => toast.error('Failed to pause client'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Client> }) => clientsApi.update(id, data as any),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients-admin'] });
      toast.success('Client updated');
      setEditingClient(null);
    },
    onError: () => toast.error('Failed to update client'),
  });

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const filteredClients = (clients || []).filter((c: Client) => {
    if (!search) return true;
    return (
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.slug.toLowerCase().includes(search.toLowerCase()) ||
      c.industry?.toLowerCase().includes(search.toLowerCase())
    );
  });

  const statusCounts = {
    active: (clients || []).filter((c: Client) => c.status === 'active').length,
    paused: (clients || []).filter((c: Client) => c.status === 'paused').length,
    onboarding: (clients || []).filter((c: Client) => c.status === 'onboarding').length,
    total: (clients || []).length,
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clients</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage client accounts · {statusCounts.active} active · {statusCounts.total} total
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          <PlusIcon className="h-4 w-4 mr-2" />
          New Client
        </button>
      </div>

      {/* New API Key Banner */}
      {newApiKey && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4">
          <div className="flex items-start justify-between">
            <div>
              <h4 className="text-sm font-semibold text-green-800">New Client API Key</h4>
              <p className="text-xs text-green-600 mt-1">Save this key now — it won't be shown again.</p>
              <div className="flex items-center gap-2 mt-2">
                <code className="text-sm bg-green-100 px-3 py-1.5 rounded text-green-800 break-all">{newApiKey.key}</code>
                <button onClick={() => copyToClipboard(newApiKey.key)} className="p-1.5 text-green-600 hover:text-green-800">
                  <ClipboardDocumentIcon className="h-5 w-5" />
                </button>
              </div>
            </div>
            <button onClick={() => setNewApiKey(null)} className="text-green-400 hover:text-green-600">
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search clients..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* Client List */}
      {isLoading ? (
        <ClientSkeleton />
      ) : filteredClients.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <BuildingOfficeIcon className="mx-auto h-12 w-12 text-gray-300" />
          <p className="mt-3 text-sm font-medium text-gray-900">
            {search ? 'No clients match your search' : 'No clients yet'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredClients.map((client: Client) => (
            <div key={client.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="text-base font-semibold text-gray-900">{client.name}</h3>
                    <span className={clsx(
                      'inline-flex px-2 py-0.5 rounded-full text-xs font-medium',
                      client.status === 'active' && 'bg-green-100 text-green-800',
                      client.status === 'paused' && 'bg-yellow-100 text-yellow-800',
                      client.status === 'onboarding' && 'bg-blue-100 text-blue-800',
                      client.status === 'churned' && 'bg-red-100 text-red-800',
                    )}>
                      {client.status}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500">
                    <span>Slug: <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{client.slug}</code></span>
                    {client.industry && <span>Industry: {client.industry}</span>}
                    <span>{client.timezone}</span>
                    <span>Joined {format(new Date(client.created_at), 'MMM d, yyyy')}</span>
                  </div>
                  <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                    <span className="flex items-center gap-1">
                      <ChartBarIcon className="h-3.5 w-3.5" />
                      {client.tokens_used_this_month?.toLocaleString() || 0} / {client.monthly_token_budget?.toLocaleString() || '∞'} tokens
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() => setCurrentClient(client)}
                    className="px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors"
                    title="Switch to this client"
                  >
                    Switch
                  </button>
                  <button
                    onClick={() => setEditingClient(client)}
                    className="p-1.5 text-gray-400 hover:text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                    title="Edit"
                  >
                    <PencilSquareIcon className="h-4 w-4" />
                  </button>
                  {client.status === 'active' ? (
                    <button
                      onClick={() => pauseMutation.mutate(client.id)}
                      className="p-1.5 text-yellow-500 hover:text-yellow-700 border border-yellow-200 rounded-lg hover:bg-yellow-50 transition-colors"
                      title="Pause"
                    >
                      <PauseIcon className="h-4 w-4" />
                    </button>
                  ) : (
                    <button
                      onClick={() => activateMutation.mutate(client.id)}
                      className="p-1.5 text-green-500 hover:text-green-700 border border-green-200 rounded-lg hover:bg-green-50 transition-colors"
                      title="Activate"
                    >
                      <PlayIcon className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Client Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div className="fixed inset-0 bg-black/50" onClick={() => setShowCreateModal(false)} />
            <div className="relative bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">New Client</h3>
                <button onClick={() => setShowCreateModal(false)} className="text-gray-400 hover:text-gray-600">
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Business Name *</label>
                  <input
                    type="text"
                    value={createForm.name}
                    onChange={(e) => setCreateForm({ ...createForm, name: e.target.value, slug: e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/-+$/, '') })}
                    placeholder="Acme Corp"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Slug *</label>
                  <input
                    type="text"
                    value={createForm.slug}
                    onChange={(e) => setCreateForm({ ...createForm, slug: e.target.value })}
                    placeholder="acme-corp"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <p className="text-xs text-gray-400 mt-1">URL-friendly identifier. Lowercase letters, numbers, and hyphens only.</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Industry</label>
                  <input
                    type="text"
                    value={createForm.industry}
                    onChange={(e) => setCreateForm({ ...createForm, industry: e.target.value })}
                    placeholder="Real Estate, Healthcare, etc."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
                    <select
                      value={createForm.timezone}
                      onChange={(e) => setCreateForm({ ...createForm, timezone: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="America/New_York">Eastern</option>
                      <option value="America/Chicago">Central</option>
                      <option value="America/Denver">Mountain</option>
                      <option value="America/Los_Angeles">Pacific</option>
                      <option value="UTC">UTC</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Language</label>
                    <select
                      value={createForm.primary_language}
                      onChange={(e) => setCreateForm({ ...createForm, primary_language: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="en">English</option>
                      <option value="es">Spanish</option>
                      <option value="fr">French</option>
                    </select>
                  </div>
                </div>
                <button
                  onClick={() => createMutation.mutate(createForm)}
                  disabled={!createForm.name.trim() || !createForm.slug.trim() || createMutation.isPending}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {createMutation.isPending ? 'Creating...' : 'Create Client'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Client Modal */}
      {editingClient && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div className="fixed inset-0 bg-black/50" onClick={() => setEditingClient(null)} />
            <div className="relative bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Edit Client</h3>
                <button onClick={() => setEditingClient(null)} className="text-gray-400 hover:text-gray-600">
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                  <input
                    type="text"
                    defaultValue={editingClient.name}
                    id="edit-client-name"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Industry</label>
                  <input
                    type="text"
                    defaultValue={editingClient.industry || ''}
                    id="edit-client-industry"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <button
                  onClick={() => {
                    const name = (document.getElementById('edit-client-name') as HTMLInputElement)?.value;
                    const industry = (document.getElementById('edit-client-industry') as HTMLInputElement)?.value;
                    updateMutation.mutate({ id: editingClient.id, data: { name, industry } });
                  }}
                  disabled={updateMutation.isPending}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
