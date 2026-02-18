import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  ChevronDownIcon,
  PhoneIcon,
  EnvelopeIcon,
  CalendarIcon,
  ChatBubbleLeftIcon,
  EllipsisVerticalIcon,
  FireIcon,
  SunIcon,
  CloudIcon,
  CheckCircleIcon,
  ClockIcon,
  UserIcon,
} from '@heroicons/react/24/outline';
import { apiClient, Lead } from '../utils/api';
import toast from 'react-hot-toast';

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'new', label: 'New' },
  { value: 'contacted', label: 'Contacted' },
  { value: 'qualified', label: 'Qualified' },
  { value: 'appointment_scheduled', label: 'Appointment Scheduled' },
  { value: 'handed_off', label: 'Handed Off' },
];

const SCORE_OPTIONS = [
  { value: '', label: 'All Scores' },
  { value: 'hot', label: 'Hot' },
  { value: 'warm', label: 'Warm' },
  { value: 'cold', label: 'Cold' },
];

function LeadScoreBadge({ score }: { score: string }) {
  const config = {
    hot: { bg: 'bg-red-100', text: 'text-red-700', icon: FireIcon },
    warm: { bg: 'bg-amber-100', text: 'text-amber-700', icon: SunIcon },
    cold: { bg: 'bg-blue-100', text: 'text-blue-700', icon: CloudIcon },
  };
  const { bg, text, icon: Icon } = config[score as keyof typeof config] || config.cold;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${bg} ${text}`}>
      <Icon className="w-3 h-3 mr-1" />
      {score.toUpperCase()}
    </span>
  );
}

function LeadStatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string; icon: React.ComponentType<{ className?: string }> }> = {
    new: { bg: 'bg-purple-100', text: 'text-purple-700', icon: ClockIcon },
    contacted: { bg: 'bg-blue-100', text: 'text-blue-700', icon: ChatBubbleLeftIcon },
    qualified: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircleIcon },
    appointment_scheduled: { bg: 'bg-indigo-100', text: 'text-indigo-700', icon: CalendarIcon },
    handed_off: { bg: 'bg-gray-100', text: 'text-gray-700', icon: UserIcon },
  };
  const { bg, text, icon: Icon } = config[status] || config.new;
  const label = status.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${bg} ${text}`}>
      <Icon className="w-3 h-3 mr-1" />
      {label}
    </span>
  );
}

function LeadRow({ lead }: { lead: Lead }) {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <tr className="hover:bg-gray-50 transition-colors">
      <td className="px-6 py-4 whitespace-nowrap">
        <Link to={`/leads/${lead.id}`} className="flex items-center">
          <div className="flex-shrink-0 h-10 w-10 bg-primary-100 rounded-full flex items-center justify-center">
            <span className="text-primary-700 font-semibold text-sm">
              {(lead.name || lead.phone_number).charAt(0).toUpperCase()}
            </span>
          </div>
          <div className="ml-4">
            <div className="text-sm font-medium text-gray-900 hover:text-primary-600">
              {lead.name || 'Unknown'}
            </div>
            <div className="text-sm text-gray-500">{lead.phone_number}</div>
          </div>
        </Link>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <LeadScoreBadge score={lead.score} />
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <LeadStatusBadge status={lead.status} />
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {lead.service_interest || '-'}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {lead.email || '-'}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        <div className="flex items-center">
          <CalendarIcon className="h-4 w-4 mr-1 text-gray-400" />
          {lead.last_contact_at
            ? new Date(lead.last_contact_at).toLocaleDateString()
            : new Date(lead.created_at).toLocaleDateString()}
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="text-gray-400 hover:text-gray-600 p-1 rounded-lg hover:bg-gray-100"
          >
            <EllipsisVerticalIcon className="h-5 w-5" />
          </button>
          {showMenu && (
            <div className="absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-10">
              <div className="py-1" role="menu">
                <Link
                  to={`/leads/${lead.id}`}
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  View Details
                </Link>
                <a
                  href={`tel:${lead.phone_number}`}
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  <PhoneIcon className="h-4 w-4 inline mr-2" />
                  Call Lead
                </a>
                {lead.email && (
                  <a
                    href={`mailto:${lead.email}`}
                    className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    <EnvelopeIcon className="h-4 w-4 inline mr-2" />
                    Send Email
                  </a>
                )}
              </div>
            </div>
          )}
        </div>
      </td>
    </tr>
  );
}

export default function Leads() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '');
  const [scoreFilter, setScoreFilter] = useState(searchParams.get('score') || '');

  const clientId = localStorage.getItem('clientId') || '';

  const { data: leads, isLoading, refetch } = useQuery({
    queryKey: ['leads', clientId, statusFilter, scoreFilter, searchQuery],
    queryFn: () =>
      apiClient.getLeads(clientId, {
        status: statusFilter || undefined,
        score: scoreFilter || undefined,
        search: searchQuery || undefined,
      }),
    enabled: !!clientId,
  });

  const handleFilterChange = (type: 'status' | 'score', value: string) => {
    if (type === 'status') {
      setStatusFilter(value);
      if (value) {
        searchParams.set('status', value);
      } else {
        searchParams.delete('status');
      }
    } else {
      setScoreFilter(value);
      if (value) {
        searchParams.set('score', value);
      } else {
        searchParams.delete('score');
      }
    }
    setSearchParams(searchParams);
  };

  const filteredLeads = leads || [];

  const stats = {
    total: filteredLeads.length,
    hot: filteredLeads.filter((l) => l.score === 'hot').length,
    warm: filteredLeads.filter((l) => l.score === 'warm').length,
    cold: filteredLeads.filter((l) => l.score === 'cold').length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Leads</h1>
          <p className="text-gray-500 mt-1">Manage and track all your leads in one place</p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => refetch()}
            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium text-sm"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Total Leads</p>
          <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center space-x-2">
            <FireIcon className="h-4 w-4 text-red-500" />
            <p className="text-sm text-gray-500">Hot</p>
          </div>
          <p className="text-2xl font-bold text-red-600">{stats.hot}</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center space-x-2">
            <SunIcon className="h-4 w-4 text-amber-500" />
            <p className="text-sm text-gray-500">Warm</p>
          </div>
          <p className="text-2xl font-bold text-amber-600">{stats.warm}</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center space-x-2">
            <CloudIcon className="h-4 w-4 text-blue-500" />
            <p className="text-sm text-gray-500">Cold</p>
          </div>
          <p className="text-2xl font-bold text-blue-600">{stats.cold}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search by name, phone, or email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </div>

          {/* Status Filter */}
          <div className="w-full md:w-48">
            <div className="relative">
              <FunnelIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => handleFilterChange('status', e.target.value)}
                className="w-full pl-10 pr-10 py-2 border border-gray-300 rounded-lg appearance-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white"
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <ChevronDownIcon className="absolute right-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none" />
            </div>
          </div>

          {/* Score Filter */}
          <div className="w-full md:w-40">
            <div className="relative">
              <select
                value={scoreFilter}
                onChange={(e) => handleFilterChange('score', e.target.value)}
                className="w-full pl-4 pr-10 py-2 border border-gray-300 rounded-lg appearance-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white"
              >
                {SCORE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <ChevronDownIcon className="absolute right-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Active Filters */}
        {(statusFilter || scoreFilter || searchQuery) && (
          <div className="flex items-center gap-2 mt-4 pt-4 border-t border-gray-100">
            <span className="text-sm text-gray-500">Active filters:</span>
            {searchQuery && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                Search: {searchQuery}
                <button
                  onClick={() => setSearchQuery('')}
                  className="ml-1 text-gray-400 hover:text-gray-600"
                >
                  ×
                </button>
              </span>
            )}
            {statusFilter && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                Status: {statusFilter}
                <button
                  onClick={() => handleFilterChange('status', '')}
                  className="ml-1 text-blue-400 hover:text-blue-600"
                >
                  ×
                </button>
              </span>
            )}
            {scoreFilter && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                Score: {scoreFilter}
                <button
                  onClick={() => handleFilterChange('score', '')}
                  className="ml-1 text-green-400 hover:text-green-600"
                >
                  ×
                </button>
              </span>
            )}
            <button
              onClick={() => {
                setSearchQuery('');
                setStatusFilter('');
                setScoreFilter('');
                setSearchParams({});
              }}
              className="text-sm text-primary-600 hover:text-primary-700 font-medium"
            >
              Clear all
            </button>
          </div>
        )}
      </div>

      {/* Leads Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : filteredLeads.length === 0 ? (
          <div className="text-center py-12">
            <UserIcon className="mx-auto h-12 w-12 text-gray-300" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No leads found</h3>
            <p className="mt-1 text-sm text-gray-500">
              {searchQuery || statusFilter || scoreFilter
                ? 'Try adjusting your filters'
                : 'Leads will appear here when they contact you'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Lead
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Score
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Interest
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last Contact
                  </th>
                  <th className="relative px-6 py-3">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredLeads.map((lead) => (
                  <LeadRow key={lead.id} lead={lead} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination placeholder */}
      {filteredLeads.length > 0 && (
        <div className="flex items-center justify-between px-4">
          <p className="text-sm text-gray-500">
            Showing <span className="font-medium">{filteredLeads.length}</span> leads
          </p>
        </div>
      )}
    </div>
  );
}
