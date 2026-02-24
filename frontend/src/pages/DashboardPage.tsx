// Dashboard Overview Page - Connected to Backend API


import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  UserGroupIcon,
  FireIcon,
  CalendarIcon,
  ChatBubbleLeftRightIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
} from '@heroicons/react/24/outline';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend,
} from 'recharts';
import { format, parseISO } from 'date-fns';
import { clsx } from 'clsx';
import { useClientStore } from '../store';
import { dashboardApi, leadsApi } from '../api';
import type { DashboardStats, Lead, LeadsByDay, LeadsByChannel } from '../types';

const COLORS = {
  hot: '#ef4444',
  warm: '#f59e0b',
  cold: '#3b82f6',
  other: '#6b7280',
};


// Loading Skeleton
function StatCardSkeleton() {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 animate-pulse">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <div className="h-4 w-24 bg-gray-200 rounded" />
          <div className="h-8 w-16 bg-gray-200 rounded" />
        </div>
        <div className="h-12 w-12 bg-gray-200 rounded-lg" />
      </div>
    </div>
  );
}

function ChartSkeleton() {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 animate-pulse">
      <div className="h-6 w-32 bg-gray-200 rounded mb-4" />
      <div className="h-64 bg-gray-100 rounded" />
    </div>
  );
}

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  trend?: { value: number; isPositive: boolean };
  color?: string;
  href?: string;
}

function StatCard({ title, value, icon: Icon, trend, color = 'blue', href }: StatCardProps) {
  const content = (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="mt-1 text-3xl font-semibold text-gray-900">{value}</p>
          {trend && (
            <p
              className={clsx(
                'mt-1 flex items-center text-sm',
                trend.isPositive ? 'text-green-600' : 'text-red-600'
              )}
            >
              {trend.isPositive ? (
                <ArrowTrendingUpIcon className="h-4 w-4 mr-1" />
              ) : (
                <ArrowTrendingDownIcon className="h-4 w-4 mr-1" />
              )}
              {Math.abs(trend.value)}% vs last week
            </p>
          )}
        </div>
        <div
          className={clsx(
            'rounded-lg p-3',
            color === 'blue' && 'bg-blue-100 text-blue-600',
            color === 'red' && 'bg-red-100 text-red-600',
            color === 'green' && 'bg-green-100 text-green-600',
            color === 'yellow' && 'bg-yellow-100 text-yellow-600',
            color === 'purple' && 'bg-purple-100 text-purple-600'
          )}
        >
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  );

  if (href) {
    return <Link to={href}>{content}</Link>;
  }
  return content;
}

function LeadsChart({ data }: { data: LeadsByDay[] }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Leads Over Time</h3>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="date"
              tickFormatter={(value) => format(parseISO(value), 'MMM d')}
              stroke="#9ca3af"
              fontSize={12}
            />
            <YAxis stroke="#9ca3af" fontSize={12} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
              }}
              labelFormatter={(value) => format(parseISO(value as string), 'MMMM d, yyyy')}
            />
            <Area
              type="monotone"
              dataKey="total"
              stroke="#3b82f6"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorTotal)"
              name="Total Leads"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function LeadsByScoreChart({ stats }: { stats: DashboardStats }) {
  const data = [
    { name: 'Hot', value: stats.hot_leads, color: COLORS.hot },
    { name: 'Warm', value: stats.warm_leads, color: COLORS.warm },
    { name: 'Cold', value: stats.cold_leads, color: COLORS.cold },
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Leads by Score</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={80}
              paddingAngle={5}
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function ChannelChart({ data }: { data: LeadsByChannel[] }) {
  const chartData = data.map((item) => ({
    name: item.channel.replace('_', ' ').toUpperCase(),
    leads: item.count,
  }));

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Leads by Channel</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis type="number" stroke="#9ca3af" fontSize={12} />
            <YAxis type="category" dataKey="name" stroke="#9ca3af" fontSize={12} width={100} />
            <Tooltip />
            <Bar dataKey="leads" fill="#3b82f6" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function RecentLeads({ leads, isLoading }: { leads: Lead[]; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 animate-pulse">
        <div className="h-6 w-32 bg-gray-200 rounded mb-4" />
        <div className="space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex items-center justify-between py-2">
              <div className="flex items-center space-x-3">
                <div className="h-2 w-2 bg-gray-200 rounded-full" />
                <div className="space-y-1">
                  <div className="h-4 w-32 bg-gray-200 rounded" />
                  <div className="h-3 w-24 bg-gray-200 rounded" />
                </div>
              </div>
              <div className="h-6 w-16 bg-gray-200 rounded-full" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Recent Leads</h3>
        <Link to="/leads" className="text-sm text-blue-600 hover:text-blue-800">
          View all →
        </Link>
      </div>
      <div className="space-y-4">
        {leads.slice(0, 5).map((lead) => (
          <Link 
            key={lead.id} 
            to={`/leads/${lead.id}`}
            className="flex items-center justify-between py-2 border-b last:border-0 hover:bg-gray-50 -mx-2 px-2 rounded"
          >
            <div className="flex items-center">
              <div
                className={clsx(
                  'h-2 w-2 rounded-full mr-3',
                  lead.score === 'hot' && 'bg-red-500',
                  lead.score === 'warm' && 'bg-yellow-500',
                  lead.score === 'cold' && 'bg-blue-500',
                  lead.score === 'unscored' && 'bg-gray-400'
                )}
              />
              <div>
                <p className="font-medium text-gray-900">{lead.name || 'Unknown'}</p>
                <p className="text-sm text-gray-500">{lead.email || lead.phone}</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-500">
                {format(parseISO(lead.created_at), 'MMM d, h:mm a')}
              </p>
              <span
                className={clsx(
                  'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
                  lead.score === 'hot' && 'bg-red-100 text-red-700',
                  lead.score === 'warm' && 'bg-yellow-100 text-yellow-700',
                  lead.score === 'cold' && 'bg-blue-100 text-blue-700'
                )}
              >
                {lead.score}
              </span>
            </div>
          </Link>
        ))}
        {leads.length === 0 && (
          <p className="text-gray-500 text-center py-4">No leads yet</p>
        )}
      </div>
    </div>
  );
}

function TokenUsage({ used, budget }: { used: number; budget: number }) {
  const percent = Math.round((used / budget) * 100);
  const isWarning = percent >= 80;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Token Usage</h3>
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Monthly Budget</span>
          <span className="font-medium">
            {(used / 1000).toFixed(0)}K / {(budget / 1000).toFixed(0)}K
          </span>
        </div>
        <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={clsx(
              'h-full rounded-full transition-all',
              isWarning ? 'bg-yellow-500' : 'bg-blue-500'
            )}
            style={{ width: `${Math.min(percent, 100)}%` }}
          />
        </div>
        <p className={clsx('text-sm', isWarning ? 'text-yellow-600' : 'text-gray-500')}>
          {percent}% used
          {isWarning && ' — Consider upgrading'}
        </p>
      </div>
    </div>
  );
}

function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
      <ExclamationTriangleIcon className="h-8 w-8 text-red-500 mx-auto mb-2" />
      <p className="text-red-700">{message}</p>
      <button
        onClick={() => window.location.reload()}
        className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
      >
        Retry
      </button>
    </div>
  );
}

export default function DashboardPage() {
  const { currentClient } = useClientStore();
  const clientId = currentClient?.id;

  // Fetch dashboard stats
  const {
    data: stats,
    isLoading: statsLoading,
    error: statsError,
  } = useQuery({
    queryKey: ['dashboard-stats', clientId],
    queryFn: () => dashboardApi.getStats(clientId!),
    enabled: !!clientId,
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // Refresh every minute
  });

  // Fetch leads by day
  const {
    data: leadsByDay,
    isLoading: leadsByDayLoading,
  } = useQuery({
    queryKey: ['leads-by-day', clientId],
    queryFn: () => dashboardApi.getLeadsByDay(clientId!, 14),
    enabled: !!clientId,
    staleTime: 60000,
  });

  // Fetch leads by channel
  const {
    data: leadsByChannel,
    isLoading: leadsByChannelLoading,
  } = useQuery({
    queryKey: ['leads-by-channel', clientId],
    queryFn: () => dashboardApi.getLeadsByChannel(clientId!),
    enabled: !!clientId,
    staleTime: 60000,
  });

  // Fetch recent leads
  const {
    data: recentLeadsData,
    isLoading: recentLeadsLoading,
  } = useQuery({
    queryKey: ['recent-leads', clientId],
    queryFn: () => leadsApi.list(clientId!, {}, 1, 5),
    enabled: !!clientId,
    staleTime: 30000,
  });

  const recentLeads = recentLeadsData?.items || [];

  // No client selected
  if (!clientId) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-gray-500">Please select a client to view the dashboard</p>
        </div>
      </div>
    );
  }

  // Error state
  if (statsError) {
    return <ErrorMessage message="Failed to load dashboard data" />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">
          Welcome back{currentClient ? `, ${currentClient.name}` : ''}. Here's what's happening.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {statsLoading ? (
          <>
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </>
        ) : stats ? (
          <>
            <StatCard
              title="Total Leads"
              value={stats.total_leads}
              icon={UserGroupIcon}
              color="blue"
              href="/leads"
            />
            <StatCard
              title="Hot Leads"
              value={stats.hot_leads}
              icon={FireIcon}
              color="red"
              href="/leads?score=hot"
            />
            <StatCard
              title="Appointments"
              value={stats.appointments_booked}
              icon={CalendarIcon}
              color="green"
            />
            <StatCard
              title="Escalations"
              value={stats.escalations_pending}
              icon={ExclamationTriangleIcon}
              color="yellow"
              href="/escalations"
            />
          </>
        ) : null}
      </div>

      {/* Second Row */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {statsLoading ? (
          <>
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </>
        ) : stats ? (
          <>
            <StatCard
              title="Active Conversations"
              value={stats.active_conversations}
              icon={ChatBubbleLeftRightIcon}
              color="purple"
              href="/conversations?active=true"
            />
            <StatCard
              title="Avg Response Time"
              value={`${(stats.avg_response_time_ms / 1000).toFixed(1)}s`}
              icon={ClockIcon}
              color="blue"
            />
            <StatCard
              title="Qualification Rate"
              value={`${stats.qualification_rate}%`}
              icon={ArrowTrendingUpIcon}
              color="green"
            />
            <StatCard
              title="Today's Leads"
              value={stats.leads_today}
              icon={UserGroupIcon}
              color="blue"
            />
          </>
        ) : null}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {leadsByDayLoading ? (
          <ChartSkeleton />
        ) : leadsByDay && leadsByDay.length > 0 ? (
          <LeadsChart data={leadsByDay} />
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Leads Over Time</h3>
            <p className="text-gray-500 text-center py-20">No data available</p>
          </div>
        )}
        
        {statsLoading ? (
          <ChartSkeleton />
        ) : stats ? (
          <LeadsByScoreChart stats={stats} />
        ) : null}
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {leadsByChannelLoading ? (
          <ChartSkeleton />
        ) : leadsByChannel && leadsByChannel.length > 0 ? (
          <ChannelChart data={leadsByChannel} />
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Leads by Channel</h3>
            <p className="text-gray-500 text-center py-20">No data available</p>
          </div>
        )}
        
        <RecentLeads leads={recentLeads} isLoading={recentLeadsLoading} />
        
        {stats ? (
          <TokenUsage used={stats.tokens_used} budget={stats.tokens_budget} />
        ) : (
          <ChartSkeleton />
        )}
      </div>
    </div>
  );
}
