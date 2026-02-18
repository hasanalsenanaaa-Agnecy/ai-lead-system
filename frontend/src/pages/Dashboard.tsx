import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  UsersIcon,
  FireIcon,
  SunIcon,
  CalendarDaysIcon,
  ChatBubbleLeftRightIcon,
  ArrowTrendingUpIcon,
  ClockIcon,
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
} from 'recharts';
import { apiClient, Lead, DashboardStats } from '../utils/api';

const SCORE_COLORS = {
  hot: '#ef4444',
  warm: '#f59e0b',
  cold: '#3b82f6',
};

function StatCard({
  title,
  value,
  icon: Icon,
  change,
  changeType,
}: {
  title: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
          {change && (
            <p
              className={`mt-2 text-sm ${
                changeType === 'positive'
                  ? 'text-green-600'
                  : changeType === 'negative'
                  ? 'text-red-600'
                  : 'text-gray-500'
              }`}
            >
              {change}
            </p>
          )}
        </div>
        <div className="p-3 bg-primary-50 rounded-lg">
          <Icon className="h-6 w-6 text-primary-600" />
        </div>
      </div>
    </div>
  );
}

function LeadScoreBadge({ score }: { score: string }) {
  const styles = {
    hot: 'badge-hot',
    warm: 'badge-warm',
    cold: 'badge-cold',
  };
  return (
    <span className={`badge ${styles[score as keyof typeof styles] || 'badge-cold'}`}>
      {score.toUpperCase()}
    </span>
  );
}

function RecentLeadRow({ lead }: { lead: Lead }) {
  return (
    <Link
      to={`/leads/${lead.id}`}
      className="flex items-center justify-between py-3 px-4 hover:bg-gray-50 rounded-lg transition-colors"
    >
      <div className="flex items-center space-x-4">
        <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
          <span className="text-primary-700 font-semibold text-sm">
            {(lead.name || lead.phone_number).charAt(0).toUpperCase()}
          </span>
        </div>
        <div>
          <p className="text-sm font-medium text-gray-900">
            {lead.name || 'Unknown'}
          </p>
          <p className="text-xs text-gray-500">{lead.phone_number}</p>
        </div>
      </div>
      <div className="flex items-center space-x-3">
        <LeadScoreBadge score={lead.score} />
        <span className="text-xs text-gray-400">
          {new Date(lead.last_contact_at || lead.created_at).toLocaleDateString()}
        </span>
      </div>
    </Link>
  );
}

export default function Dashboard() {
  const clientId = localStorage.getItem('clientId') || '';

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats', clientId],
    queryFn: () => apiClient.getDashboardStats(clientId),
    enabled: !!clientId,
  });

  const { data: hotLeads, isLoading: hotLeadsLoading } = useQuery({
    queryKey: ['hot-leads', clientId],
    queryFn: () => apiClient.getHotLeads(clientId),
    enabled: !!clientId,
  });

  const { data: recentLeads, isLoading: recentLeadsLoading } = useQuery({
    queryKey: ['recent-leads', clientId],
    queryFn: () => apiClient.getLeads(clientId, { limit: 10 }),
    enabled: !!clientId,
  });

  // Mock chart data - in production, this would come from the API
  const activityData = [
    { name: 'Mon', leads: 12, conversations: 45 },
    { name: 'Tue', leads: 19, conversations: 62 },
    { name: 'Wed', leads: 15, conversations: 51 },
    { name: 'Thu', leads: 22, conversations: 78 },
    { name: 'Fri', leads: 28, conversations: 89 },
    { name: 'Sat', leads: 8, conversations: 23 },
    { name: 'Sun', leads: 5, conversations: 15 },
  ];

  const scoreDistribution = stats
    ? [
        { name: 'Hot', value: stats.hot_leads_count, color: SCORE_COLORS.hot },
        { name: 'Warm', value: stats.warm_leads_count, color: SCORE_COLORS.warm },
        {
          name: 'Cold',
          value: stats.total_leads - stats.hot_leads_count - stats.warm_leads_count,
          color: SCORE_COLORS.cold,
        },
      ]
    : [];

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Welcome back! Here's what's happening with your leads.</p>
        </div>
        <div className="flex items-center space-x-2 text-sm text-gray-500">
          <ClockIcon className="h-4 w-4" />
          <span>Last updated: {new Date().toLocaleTimeString()}</span>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Leads"
          value={stats?.total_leads || 0}
          icon={UsersIcon}
          change={`+${stats?.new_leads_today || 0} today`}
          changeType="positive"
        />
        <StatCard
          title="Hot Leads"
          value={stats?.hot_leads_count || 0}
          icon={FireIcon}
          change="Ready to convert"
          changeType="neutral"
        />
        <StatCard
          title="Warm Leads"
          value={stats?.warm_leads_count || 0}
          icon={SunIcon}
          change="Nurturing"
          changeType="neutral"
        />
        <StatCard
          title="Appointments"
          value={stats?.appointments_scheduled || 0}
          icon={CalendarDaysIcon}
          change="This week"
          changeType="neutral"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity Chart */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Weekly Activity</h2>
              <p className="text-sm text-gray-500">Leads and conversations over time</p>
            </div>
            <div className="flex items-center space-x-4 text-sm">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-primary-500"></div>
                <span className="text-gray-600">Leads</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-green-500"></div>
                <span className="text-gray-600">Conversations</span>
              </div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={activityData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} stroke="#9ca3af" />
              <YAxis tick={{ fontSize: 12 }} stroke="#9ca3af" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                }}
              />
              <Area
                type="monotone"
                dataKey="leads"
                stackId="1"
                stroke="#0ea5e9"
                fill="#0ea5e9"
                fillOpacity={0.6}
              />
              <Area
                type="monotone"
                dataKey="conversations"
                stackId="2"
                stroke="#22c55e"
                fill="#22c55e"
                fillOpacity={0.4}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Score Distribution */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Lead Distribution</h2>
          <p className="text-sm text-gray-500 mb-4">By qualification score</p>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={scoreDistribution}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={2}
                dataKey="value"
              >
                {scoreDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center space-x-4 mt-4">
            {scoreDistribution.map((item) => (
              <div key={item.name} className="flex items-center space-x-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: item.color }}
                ></div>
                <span className="text-sm text-gray-600">
                  {item.name}: {item.value}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Hot Leads */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <FireIcon className="h-5 w-5 text-red-500" />
              <h2 className="text-lg font-semibold text-gray-900">Hot Leads</h2>
            </div>
            <Link
              to="/leads?score=hot"
              className="text-sm text-primary-600 hover:text-primary-700 font-medium"
            >
              View all →
            </Link>
          </div>
          <div className="space-y-1">
            {hotLeadsLoading ? (
              <div className="text-center py-8 text-gray-500">Loading...</div>
            ) : hotLeads && hotLeads.length > 0 ? (
              hotLeads.slice(0, 5).map((lead) => (
                <RecentLeadRow key={lead.id} lead={lead} />
              ))
            ) : (
              <div className="text-center py-8 text-gray-500">
                <FireIcon className="h-12 w-12 mx-auto text-gray-300 mb-2" />
                <p>No hot leads yet</p>
                <p className="text-sm">Hot leads will appear here when qualified</p>
              </div>
            )}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <ChatBubbleLeftRightIcon className="h-5 w-5 text-primary-500" />
              <h2 className="text-lg font-semibold text-gray-900">Recent Leads</h2>
            </div>
            <Link
              to="/leads"
              className="text-sm text-primary-600 hover:text-primary-700 font-medium"
            >
              View all →
            </Link>
          </div>
          <div className="space-y-1">
            {recentLeadsLoading ? (
              <div className="text-center py-8 text-gray-500">Loading...</div>
            ) : recentLeads && recentLeads.length > 0 ? (
              recentLeads.slice(0, 5).map((lead) => (
                <RecentLeadRow key={lead.id} lead={lead} />
              ))
            ) : (
              <div className="text-center py-8 text-gray-500">
                <UsersIcon className="h-12 w-12 mx-auto text-gray-300 mb-2" />
                <p>No leads yet</p>
                <p className="text-sm">Leads will appear here as they come in</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-xl shadow-lg p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">Need to take action?</h2>
            <p className="text-primary-100 mt-1">
              You have {stats?.hot_leads_count || 0} hot leads waiting for follow-up
            </p>
          </div>
          <div className="flex space-x-3">
            <Link
              to="/leads?score=hot"
              className="px-4 py-2 bg-white text-primary-700 rounded-lg font-medium hover:bg-primary-50 transition-colors"
            >
              View Hot Leads
            </Link>
            <Link
              to="/knowledge"
              className="px-4 py-2 bg-primary-500 text-white rounded-lg font-medium hover:bg-primary-400 transition-colors border border-primary-400"
            >
              Update Knowledge Base
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
