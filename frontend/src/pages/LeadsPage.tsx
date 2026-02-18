// Leads Management Page

import { useState, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { format, parseISO } from 'date-fns';
import { clsx } from 'clsx';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  PhoneIcon,
  EnvelopeIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  FireIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { useClientStore } from '../store';
import { leadsApi } from '../api';
import type { Lead, LeadScore, LeadStatus, ChannelType } from '../types';

const SCORE_COLORS: Record<LeadScore, string> = {
  hot: 'bg-red-100 text-red-700 border-red-200',
  warm: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  cold: 'bg-blue-100 text-blue-700 border-blue-200',
  unscored: 'bg-gray-100 text-gray-700 border-gray-200',
};

const STATUS_COLORS: Record<LeadStatus, string> = {
  new: 'bg-green-100 text-green-700',
  qualifying: 'bg-blue-100 text-blue-700',
  qualified: 'bg-purple-100 text-purple-700',
  appointment_booked: 'bg-indigo-100 text-indigo-700',
  handed_off: 'bg-orange-100 text-orange-700',
  nurturing: 'bg-cyan-100 text-cyan-700',
  closed_won: 'bg-emerald-100 text-emerald-700',
  closed_lost: 'bg-red-100 text-red-700',
  disqualified: 'bg-gray-100 text-gray-700',
};

// Mock data for demo
const mockLeads: Lead[] = [
  {
    id: '1',
    client_id: '1',
    name: 'Ahmed Al-Rashid',
    first_name: 'Ahmed',
    last_name: 'Al-Rashid',
    email: 'ahmed@example.com',
    phone: '+966501234567',
    status: 'qualifying',
    score: 'hot',
    source: 'whatsapp',
    service_interest: 'Home Purchase - Villa',
    urgency: 'This week',
    budget_range: '800K-1.2M SAR',
    location: 'Riyadh',
    qualification_data: {},
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: '2',
    client_id: '1',
    name: 'Sarah Johnson',
    first_name: 'Sarah',
    last_name: 'Johnson',
    email: 'sarah.j@example.com',
    phone: '+14155551234',
    status: 'appointment_booked',
    score: 'warm',
    source: 'web_form',
    service_interest: 'Rental Property',
    urgency: 'Next month',
    budget_range: '5K-8K/month',
    location: 'Jeddah',
    qualification_data: {},
    appointment_at: new Date(Date.now() + 86400000 * 2).toISOString(),
    created_at: new Date(Date.now() - 3600000).toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: '3',
    client_id: '1',
    name: 'Mohammed Hassan',
    first_name: 'Mohammed',
    last_name: 'Hassan',
    email: 'mhassan@company.com',
    phone: '+966551234567',
    status: 'new',
    score: 'cold',
    source: 'sms',
    service_interest: 'Investment Property',
    urgency: 'Exploring options',
    qualification_data: {},
    created_at: new Date(Date.now() - 7200000).toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: '4',
    client_id: '1',
    name: 'Fatima Al-Saud',
    first_name: 'Fatima',
    last_name: 'Al-Saud',
    email: 'fatima@example.com',
    phone: '+966509876543',
    status: 'handed_off',
    score: 'hot',
    source: 'missed_call',
    service_interest: 'Luxury Apartment',
    urgency: 'Urgent - Today',
    budget_range: '2M+ SAR',
    location: 'Riyadh - Diplomatic Quarter',
    qualification_data: {},
    handed_off_at: new Date(Date.now() - 1800000).toISOString(),
    created_at: new Date(Date.now() - 3600000 * 5).toISOString(),
    updated_at: new Date().toISOString(),
  },
] as Lead[];

function ScoreBadge({ score }: { score: LeadScore }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize',
        SCORE_COLORS[score]
      )}
    >
      {score === 'hot' && <FireIcon className="h-3 w-3" />}
      {score}
    </span>
  );
}

function StatusBadge({ status }: { status: LeadStatus }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        STATUS_COLORS[status]
      )}
    >
      {status.replace(/_/g, ' ')}
    </span>
  );
}

function ChannelBadge({ channel }: { channel: string }) {
  const colors: Record<string, string> = {
    web_form: 'bg-blue-50 text-blue-700',
    whatsapp: 'bg-green-50 text-green-700',
    sms: 'bg-purple-50 text-purple-700',
    missed_call: 'bg-orange-50 text-orange-700',
    live_chat: 'bg-cyan-50 text-cyan-700',
    email: 'bg-gray-50 text-gray-700',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center rounded px-2 py-0.5 text-xs font-medium',
        colors[channel] || 'bg-gray-50 text-gray-700'
      )}
    >
      {channel.replace(/_/g, ' ')}
    </span>
  );
}

export default function LeadsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { currentClient } = useClientStore();
  
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [scoreFilter, setScoreFilter] = useState<LeadScore | ''>(
    (searchParams.get('score') as LeadScore) || ''
  );
  const [statusFilter, setStatusFilter] = useState<LeadStatus | ''>(
    (searchParams.get('status') as LeadStatus) || ''
  );
  const [channelFilter, setChannelFilter] = useState<ChannelType | ''>(
    (searchParams.get('channel') as ChannelType) || ''
  );
  const [page, setPage] = useState(1);
  const perPage = 10;

  // Filter leads (replace with API call in production)
  const filteredLeads = useMemo(() => {
    return mockLeads.filter((lead) => {
      if (search) {
        const searchLower = search.toLowerCase();
        const matchesSearch =
          lead.name?.toLowerCase().includes(searchLower) ||
          lead.email?.toLowerCase().includes(searchLower) ||
          lead.phone?.includes(search);
        if (!matchesSearch) return false;
      }
      if (scoreFilter && lead.score !== scoreFilter) return false;
      if (statusFilter && lead.status !== statusFilter) return false;
      if (channelFilter && lead.source !== channelFilter) return false;
      return true;
    });
  }, [search, scoreFilter, statusFilter, channelFilter]);

  const totalPages = Math.ceil(filteredLeads.length / perPage);
  const paginatedLeads = filteredLeads.slice((page - 1) * perPage, page * perPage);

  const handleSearch = (value: string) => {
    setSearch(value);
    setPage(1);
  };

  const clearFilters = () => {
    setSearch('');
    setScoreFilter('');
    setStatusFilter('');
    setChannelFilter('');
    setPage(1);
    setSearchParams({});
  };

  const hasFilters = search || scoreFilter || statusFilter || channelFilter;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Leads</h1>
          <p className="text-gray-500">
            {filteredLeads.length} total leads
            {hasFilters && ' (filtered)'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <ArrowPathIcon className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search by name, email, or phone..."
                value={search}
                onChange={(e) => handleSearch(e.target.value)}
                className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Score Filter */}
          <select
            value={scoreFilter}
            onChange={(e) => {
              setScoreFilter(e.target.value as LeadScore | '');
              setPage(1);
            }}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Scores</option>
            <option value="hot">🔥 Hot</option>
            <option value="warm">🌡️ Warm</option>
            <option value="cold">❄️ Cold</option>
            <option value="unscored">Unscored</option>
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as LeadStatus | '');
              setPage(1);
            }}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Statuses</option>
            <option value="new">New</option>
            <option value="qualifying">Qualifying</option>
            <option value="qualified">Qualified</option>
            <option value="appointment_booked">Appointment Booked</option>
            <option value="handed_off">Handed Off</option>
            <option value="nurturing">Nurturing</option>
            <option value="closed_won">Closed Won</option>
            <option value="closed_lost">Closed Lost</option>
          </select>

          {/* Channel Filter */}
          <select
            value={channelFilter}
            onChange={(e) => {
              setChannelFilter(e.target.value as ChannelType | '');
              setPage(1);
            }}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Channels</option>
            <option value="web_form">Web Form</option>
            <option value="whatsapp">WhatsApp</option>
            <option value="sms">SMS</option>
            <option value="missed_call">Missed Call</option>
            <option value="live_chat">Live Chat</option>
          </select>

          {hasFilters && (
            <button
              onClick={clearFilters}
              className="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Lead
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Contact
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Channel
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Interest
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {paginatedLeads.map((lead) => (
                <tr key={lead.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <Link
                        to={`/leads/${lead.id}`}
                        className="font-medium text-gray-900 hover:text-blue-600"
                      >
                        {lead.name || 'Unknown'}
                      </Link>
                      {lead.location && (
                        <p className="text-sm text-gray-500">{lead.location}</p>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="space-y-1">
                      {lead.phone && (
                        <a
                          href={`tel:${lead.phone}`}
                          className="flex items-center gap-1 text-sm text-gray-600 hover:text-blue-600"
                        >
                          <PhoneIcon className="h-4 w-4" />
                          {lead.phone}
                        </a>
                      )}
                      {lead.email && (
                        <a
                          href={`mailto:${lead.email}`}
                          className="flex items-center gap-1 text-sm text-gray-600 hover:text-blue-600"
                        >
                          <EnvelopeIcon className="h-4 w-4" />
                          {lead.email}
                        </a>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <ScoreBadge score={lead.score} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <StatusBadge status={lead.status} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {lead.source && <ChannelBadge channel={lead.source} />}
                  </td>
                  <td className="px-6 py-4">
                    <div className="max-w-xs">
                      <p className="text-sm text-gray-900 truncate">
                        {lead.service_interest || '-'}
                      </p>
                      {lead.urgency && (
                        <p className="text-xs text-gray-500">{lead.urgency}</p>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {format(parseISO(lead.created_at), 'MMM d, h:mm a')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <Link
                      to={`/leads/${lead.id}`}
                      className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))}
              {paginatedLeads.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-gray-500">
                    No leads found
                    {hasFilters && (
                      <button
                        onClick={clearFilters}
                        className="block mx-auto mt-2 text-blue-600 hover:text-blue-800"
                      >
                        Clear filters
                      </button>
                    )}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6">
            <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
              <p className="text-sm text-gray-700">
                Showing <span className="font-medium">{(page - 1) * perPage + 1}</span> to{' '}
                <span className="font-medium">
                  {Math.min(page * perPage, filteredLeads.length)}
                </span>{' '}
                of <span className="font-medium">{filteredLeads.length}</span> results
              </p>
              <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                  className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeftIcon className="h-5 w-5" />
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={clsx(
                      'relative inline-flex items-center px-4 py-2 text-sm font-semibold ring-1 ring-inset ring-gray-300',
                      p === page
                        ? 'z-10 bg-blue-600 text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600'
                        : 'text-gray-900 hover:bg-gray-50'
                    )}
                  >
                    {p}
                  </button>
                ))}
                <button
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page === totalPages}
                  className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRightIcon className="h-5 w-5" />
                </button>
              </nav>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
