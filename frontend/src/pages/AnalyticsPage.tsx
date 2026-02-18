// Analytics Page

import { useState } from 'react';
import { format, subDays } from 'date-fns';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { clsx } from 'clsx';
import {
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  CalendarIcon,
} from '@heroicons/react/24/outline';

// Generate mock data
const generateDailyData = (days: number) =>
  Array.from({ length: days }, (_, i) => {
    const date = subDays(new Date(), days - 1 - i);
    return {
      date: format(date, 'MMM d'),
      leads: Math.floor(Math.random() * 30) + 10,
      conversations: Math.floor(Math.random() * 40) + 15,
      qualified: Math.floor(Math.random() * 15) + 5,
      appointments: Math.floor(Math.random() * 8) + 2,
    };
  });

const leadsBySource = [
  { name: 'WhatsApp', value: 35, color: '#25D366' },
  { name: 'Web Form', value: 28, color: '#3B82F6' },
  { name: 'SMS', value: 18, color: '#8B5CF6' },
  { name: 'Missed Call', value: 12, color: '#F59E0B' },
  { name: 'Live Chat', value: 7, color: '#10B981' },
];

const conversionFunnel = [
  { stage: 'Leads', count: 156, percent: 100 },
  { stage: 'Engaged', count: 142, percent: 91 },
  { stage: 'Qualified', count: 89, percent: 57 },
  { stage: 'Appointment', count: 45, percent: 29 },
  { stage: 'Closed', count: 23, percent: 15 },
];

const responseTimeData = [
  { hour: '12am', avg: 2.1 },
  { hour: '4am', avg: 2.3 },
  { hour: '8am', avg: 1.8 },
  { hour: '12pm', avg: 2.5 },
  { hour: '4pm', avg: 3.1 },
  { hour: '8pm', avg: 2.4 },
];

const qualificationByDay = [
  { day: 'Sun', hot: 8, warm: 15, cold: 22 },
  { day: 'Mon', hot: 12, warm: 18, cold: 28 },
  { day: 'Tue', hot: 10, warm: 22, cold: 25 },
  { day: 'Wed', hot: 15, warm: 20, cold: 30 },
  { day: 'Thu', hot: 11, warm: 17, cold: 24 },
  { day: 'Fri', hot: 6, warm: 10, cold: 15 },
  { day: 'Sat', hot: 4, warm: 8, cold: 12 },
];

interface MetricCardProps {
  title: string;
  value: string | number;
  change: number;
  changeLabel: string;
}

function MetricCard({ title, value, change, changeLabel }: MetricCardProps) {
  const isPositive = change >= 0;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <p className="text-sm font-medium text-gray-500">{title}</p>
      <p className="mt-2 text-3xl font-semibold text-gray-900">{value}</p>
      <div className="mt-2 flex items-center gap-2">
        <span
          className={clsx(
            'inline-flex items-center text-sm font-medium',
            isPositive ? 'text-green-600' : 'text-red-600'
          )}
        >
          {isPositive ? (
            <ArrowTrendingUpIcon className="h-4 w-4 mr-1" />
          ) : (
            <ArrowTrendingDownIcon className="h-4 w-4 mr-1" />
          )}
          {Math.abs(change)}%
        </span>
        <span className="text-sm text-gray-500">{changeLabel}</span>
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const [dateRange, setDateRange] = useState<'7d' | '30d' | '90d'>('30d');
  const days = dateRange === '7d' ? 7 : dateRange === '30d' ? 30 : 90;
  const dailyData = generateDailyData(days);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-gray-500">Performance metrics and insights</p>
        </div>
        <div className="flex items-center gap-2">
          {(['7d', '30d', '90d'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setDateRange(range)}
              className={clsx(
                'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                dateRange === range
                  ? 'bg-gray-900 text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              )}
            >
              {range === '7d' ? 'Last 7 days' : range === '30d' ? 'Last 30 days' : 'Last 90 days'}
            </button>
          ))}
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Leads"
          value="156"
          change={12}
          changeLabel="vs last period"
        />
        <MetricCard
          title="Qualification Rate"
          value="57%"
          change={8}
          changeLabel="vs last period"
        />
        <MetricCard
          title="Avg Response Time"
          value="2.4s"
          change={-15}
          changeLabel="faster"
        />
        <MetricCard
          title="Appointment Rate"
          value="29%"
          change={5}
          changeLabel="vs last period"
        />
      </div>

      {/* Lead Trend Chart */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Lead Activity</h3>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={dailyData}>
              <defs>
                <linearGradient id="colorLeads" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorQualified" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" stroke="#9ca3af" fontSize={12} />
              <YAxis stroke="#9ca3af" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                }}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="leads"
                stroke="#3B82F6"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorLeads)"
                name="New Leads"
              />
              <Area
                type="monotone"
                dataKey="qualified"
                stroke="#10B981"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorQualified)"
                name="Qualified"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Leads by Source */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Leads by Source</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={leadsBySource}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {leadsBySource.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Conversion Funnel */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Conversion Funnel</h3>
          <div className="space-y-4">
            {conversionFunnel.map((stage, i) => (
              <div key={stage.stage}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium text-gray-700">{stage.stage}</span>
                  <span className="text-gray-500">
                    {stage.count} ({stage.percent}%)
                  </span>
                </div>
                <div className="h-6 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${stage.percent}%`,
                      backgroundColor: `hsl(${220 - i * 25}, 80%, 55%)`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Response Time */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Avg Response Time by Hour</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={responseTimeData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="hour" stroke="#9ca3af" fontSize={12} />
                <YAxis
                  stroke="#9ca3af"
                  fontSize={12}
                  tickFormatter={(value) => `${value}s`}
                />
                <Tooltip
                  formatter={(value: number) => [`${value}s`, 'Response Time']}
                />
                <Line
                  type="monotone"
                  dataKey="avg"
                  stroke="#8B5CF6"
                  strokeWidth={2}
                  dot={{ fill: '#8B5CF6' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Qualification by Day */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Lead Quality by Day</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={qualificationByDay}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="day" stroke="#9ca3af" fontSize={12} />
                <YAxis stroke="#9ca3af" fontSize={12} />
                <Tooltip />
                <Legend />
                <Bar dataKey="hot" fill="#EF4444" name="Hot" stackId="a" />
                <Bar dataKey="warm" fill="#F59E0B" name="Warm" stackId="a" />
                <Bar dataKey="cold" fill="#3B82F6" name="Cold" stackId="a" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* AI Performance */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">AI Performance Metrics</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <p className="text-3xl font-bold text-gray-900">94%</p>
            <p className="text-sm text-gray-500 mt-1">Avg Confidence Score</p>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <p className="text-3xl font-bold text-gray-900">8.2</p>
            <p className="text-sm text-gray-500 mt-1">Avg Messages/Conversation</p>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <p className="text-3xl font-bold text-gray-900">3.8%</p>
            <p className="text-sm text-gray-500 mt-1">Escalation Rate</p>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <p className="text-3xl font-bold text-gray-900">450K</p>
            <p className="text-sm text-gray-500 mt-1">Tokens Used This Month</p>
          </div>
        </div>
      </div>
    </div>
  );
}
