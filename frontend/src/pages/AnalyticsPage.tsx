// Analytics Page - Deep-dive charts and metrics for lead performance

import { useQuery } from '@tanstack/react-query';
import { format, parseISO } from 'date-fns';
import { clsx } from 'clsx';
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
  LineChart,
  Line,
} from 'recharts';
import {
  ArrowTrendingUpIcon,
  UserGroupIcon,
  FireIcon,
  ChatBubbleLeftRightIcon,
  ClockIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import { useClientStore } from '../store';
import { dashboardApi } from '../api';
import type { LeadsByChannel } from '../types';

const SCORE_COLORS = {
  hot: '#ef4444',
  warm: '#f59e0b',
  cold: '#3b82f6',
};

const CHANNEL_COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#6366f1', '#14b8a6'];

function StatCard({ title, value, subtitle, icon: Icon, color }: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
          {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
        </div>
        <div className={clsx('rounded-lg p-2.5',
          color === 'blue' && 'bg-blue-100 text-blue-600',
          color === 'red' && 'bg-red-100 text-red-600',
          color === 'green' && 'bg-green-100 text-green-600',
          color === 'yellow' && 'bg-yellow-100 text-yellow-600',
          color === 'purple' && 'bg-purple-100 text-purple-600',
        )}>
          <Icon className="h-5 w-5" />
        </div>
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

export default function AnalyticsPage() {
  const { currentClient } = useClientStore();

  const { data: stats, isLoading: loadingStats } = useQuery({
    queryKey: ['analytics-stats', currentClient?.id],
    queryFn: () => dashboardApi.getStats(currentClient!.id),
    enabled: !!currentClient?.id,
  });

  const { data: leadsByDay, isLoading: loadingLeadsByDay } = useQuery({
    queryKey: ['analytics-leads-by-day', currentClient?.id],
    queryFn: () => dashboardApi.getLeadsByDay(currentClient!.id, 30),
    enabled: !!currentClient?.id,
  });

  const { data: leadsByChannel, isLoading: loadingLeadsByChannel } = useQuery({
    queryKey: ['analytics-leads-by-channel', currentClient?.id],
    queryFn: () => dashboardApi.getLeadsByChannel(currentClient!.id),
    enabled: !!currentClient?.id,
  });

  if (!currentClient) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Please select a client to view analytics.</p>
      </div>
    );
  }

  const qualificationRate = stats?.qualification_rate ? `${(stats.qualification_rate * 100).toFixed(1)}%` : '0%';
  const avgResponseTime = stats?.avg_response_time_ms ? `${(stats.avg_response_time_ms / 1000).toFixed(1)}s` : 'N/A';
  const tokenUsagePercent = stats?.tokens_budget ? `${((stats.tokens_used / stats.tokens_budget) * 100).toFixed(0)}%` : 'N/A';

  // Compute cumulative leads for the line chart
  const cumulativeData = (leadsByDay || []).reduce((acc: Array<{ date: string; cumulative: number; daily: number }>, day, i) => {
    const prev = i > 0 ? acc[i - 1].cumulative : 0;
    acc.push({ date: day.date, cumulative: prev + day.total, daily: day.total });
    return acc;
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
        <p className="text-sm text-gray-500 mt-1">Deep-dive into your lead generation performance — last 30 days</p>
      </div>

      {/* KPI Cards */}
      {loadingStats ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 animate-pulse">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-white rounded-xl border p-5">
              <div className="h-4 w-20 bg-gray-200 rounded mb-2" />
              <div className="h-7 w-16 bg-gray-200 rounded" />
            </div>
          ))}
        </div>
      ) : stats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          <StatCard title="Total Leads" value={stats.total_leads} icon={UserGroupIcon} color="blue" />
          <StatCard title="Hot Leads" value={stats.hot_leads} icon={FireIcon} color="red" />
          <StatCard title="Qualification Rate" value={qualificationRate} icon={ArrowTrendingUpIcon} color="green" />
          <StatCard title="Avg Response" value={avgResponseTime} icon={ClockIcon} color="yellow" />
          <StatCard title="Active Chats" value={stats.active_conversations} icon={ChatBubbleLeftRightIcon} color="purple" />
          <StatCard title="Token Usage" value={tokenUsagePercent} subtitle={`${stats.tokens_used.toLocaleString()} used`} icon={ChartBarIcon} color="blue" />
        </div>
      )}

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Leads by Day - Area Chart */}
        {loadingLeadsByDay ? (
          <ChartSkeleton />
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Leads by Day (Last 30 Days)</h3>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={leadsByDay || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: '#9ca3af' }}
                  tickFormatter={(val) => {
                    try { return format(parseISO(val), 'MMM d'); } catch { return val; }
                  }}
                />
                <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '12px' }}
                  labelFormatter={(val) => {
                    try { return format(parseISO(val as string), 'MMM d, yyyy'); } catch { return val; }
                  }}
                />
                <Area type="monotone" dataKey="hot" stackId="1" stroke={SCORE_COLORS.hot} fill={SCORE_COLORS.hot} fillOpacity={0.6} />
                <Area type="monotone" dataKey="warm" stackId="1" stroke={SCORE_COLORS.warm} fill={SCORE_COLORS.warm} fillOpacity={0.6} />
                <Area type="monotone" dataKey="cold" stackId="1" stroke={SCORE_COLORS.cold} fill={SCORE_COLORS.cold} fillOpacity={0.6} />
                <Legend />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Leads by Channel - Pie Chart */}
        {loadingLeadsByChannel ? (
          <ChartSkeleton />
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Leads by Channel</h3>
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={leadsByChannel || []}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={4}
                  dataKey="count"
                  nameKey="channel"
                  label={({ channel, percentage }) => `${channel} (${percentage.toFixed(0)}%)`}
                  labelLine={false}
                >
                  {(leadsByChannel || []).map((_: LeadsByChannel, index: number) => (
                    <Cell key={`cell-${index}`} fill={CHANNEL_COLORS[index % CHANNEL_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '12px' }}
                  formatter={(value: number) => [value, 'Leads']}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cumulative Leads - Line Chart */}
        {loadingLeadsByDay ? (
          <ChartSkeleton />
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Cumulative Lead Growth</h3>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={cumulativeData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: '#9ca3af' }}
                  tickFormatter={(val) => {
                    try { return format(parseISO(val), 'MMM d'); } catch { return val; }
                  }}
                />
                <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '12px' }}
                />
                <Line type="monotone" dataKey="cumulative" stroke="#3b82f6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Lead Score Distribution - Bar Chart */}
        {loadingStats ? (
          <ChartSkeleton />
        ) : stats && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Lead Score Distribution</h3>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart
                data={[
                  { score: 'Hot', count: stats.hot_leads, fill: SCORE_COLORS.hot },
                  { score: 'Warm', count: stats.warm_leads, fill: SCORE_COLORS.warm },
                  { score: 'Cold', count: stats.cold_leads, fill: SCORE_COLORS.cold },
                ]}
                layout="vertical"
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#9ca3af' }} allowDecimals={false} />
                <YAxis type="category" dataKey="score" tick={{ fontSize: 12, fill: '#374151' }} width={50} />
                <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '12px' }} />
                <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={32}>
                  {[
                    { score: 'Hot', fill: SCORE_COLORS.hot },
                    { score: 'Warm', fill: SCORE_COLORS.warm },
                    { score: 'Cold', fill: SCORE_COLORS.cold },
                  ].map((entry, index) => (
                    <Cell key={`bar-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Performance Summary Table */}
      {stats && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Performance Summary</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 px-3 text-xs font-semibold text-gray-500 uppercase">Metric</th>
                  <th className="text-right py-2 px-3 text-xs font-semibold text-gray-500 uppercase">Value</th>
                  <th className="text-left py-2 px-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {[
                  { metric: 'Leads Today', value: stats.leads_today, status: stats.leads_today > 0 ? 'good' : 'neutral' },
                  { metric: 'Appointments Booked', value: stats.appointments_booked, status: stats.appointments_booked > 0 ? 'good' : 'neutral' },
                  { metric: 'Pending Escalations', value: stats.escalations_pending, status: stats.escalations_pending === 0 ? 'good' : stats.escalations_pending > 5 ? 'bad' : 'warning' },
                  { metric: 'Active Conversations', value: stats.active_conversations, status: 'neutral' },
                  { metric: 'Qualification Rate', value: qualificationRate, status: stats.qualification_rate > 0.3 ? 'good' : stats.qualification_rate > 0.1 ? 'warning' : 'bad' },
                  { metric: 'Avg Response Time', value: avgResponseTime, status: (stats.avg_response_time_ms || 0) < 3000 ? 'good' : 'warning' },
                ].map((row) => (
                  <tr key={row.metric}>
                    <td className="py-2.5 px-3 text-sm text-gray-900">{row.metric}</td>
                    <td className="py-2.5 px-3 text-sm text-gray-900 text-right font-medium">{row.value}</td>
                    <td className="py-2.5 px-3">
                      <span className={clsx(
                        'inline-flex px-2 py-0.5 rounded-full text-xs font-medium',
                        row.status === 'good' && 'bg-green-100 text-green-700',
                        row.status === 'warning' && 'bg-yellow-100 text-yellow-700',
                        row.status === 'bad' && 'bg-red-100 text-red-700',
                        row.status === 'neutral' && 'bg-gray-100 text-gray-600',
                      )}>
                        {row.status === 'good' ? '✓ Good' :
                         row.status === 'warning' ? '⚠ Attention' :
                         row.status === 'bad' ? '✗ Action Needed' : '—'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
