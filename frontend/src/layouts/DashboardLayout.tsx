// Dashboard Layout with Sidebar Navigation

import { useState } from 'react';
import { Link, useLocation, Outlet } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  HomeIcon,
  UserGroupIcon,
  ChatBubbleLeftRightIcon,
  BuildingOfficeIcon,
  BookOpenIcon,
  Cog6ToothIcon,
  ChartBarIcon,
  BellIcon,
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  XMarkIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { useClientStore, useAuthStore, useNotificationStore, useUIStore } from '../store';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
}

const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Leads', href: '/leads', icon: UserGroupIcon },
  { name: 'Conversations', href: '/conversations', icon: ChatBubbleLeftRightIcon },
  { name: 'Escalations', href: '/escalations', icon: ExclamationTriangleIcon },
  { name: 'Knowledge Base', href: '/knowledge', icon: BookOpenIcon },
  { name: 'Analytics', href: '/analytics', icon: ChartBarIcon },
  { name: 'Clients', href: '/clients', icon: BuildingOfficeIcon },
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
];

export default function DashboardLayout() {
  const location = useLocation();
  const { currentClient } = useClientStore();
  const { user, logout } = useAuthStore();
  const { unreadCount } = useNotificationStore();
  const { sidebarOpen, setSidebarOpen } = useUIStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile menu overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-gray-600 bg-opacity-75 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar for desktop */}
      <div
        className={clsx(
          'fixed inset-y-0 left-0 z-50 flex flex-col bg-gray-900 transition-all duration-300',
          sidebarOpen ? 'w-64' : 'w-20',
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        {/* Logo */}
        <div className="flex h-16 items-center justify-between px-4">
          {sidebarOpen ? (
            <span className="text-xl font-bold text-white">AI Lead System</span>
          ) : (
            <span className="text-xl font-bold text-white">AI</span>
          )}
          <button
            onClick={() => setMobileMenuOpen(false)}
            className="lg:hidden text-gray-400 hover:text-white"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        {/* Client selector */}
        {currentClient && sidebarOpen && (
          <div className="mx-4 mb-4 rounded-lg bg-gray-800 p-3">
            <p className="text-xs text-gray-400">Current Client</p>
            <p className="font-medium text-white truncate">{currentClient.name}</p>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-2 py-4">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={clsx(
                  'group flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-gray-800 text-white'
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                )}
                title={!sidebarOpen ? item.name : undefined}
              >
                <item.icon
                  className={clsx(
                    'flex-shrink-0',
                    sidebarOpen ? 'mr-3 h-5 w-5' : 'h-6 w-6'
                  )}
                />
                {sidebarOpen && (
                  <>
                    <span className="flex-1">{item.name}</span>
                    {item.badge && (
                      <span className="ml-2 inline-flex items-center rounded-full bg-red-500 px-2 py-0.5 text-xs font-medium text-white">
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Collapse button */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="hidden lg:flex items-center justify-center h-12 text-gray-400 hover:text-white border-t border-gray-800"
        >
          {sidebarOpen ? (
            <span className="text-sm">← Collapse</span>
          ) : (
            <span className="text-sm">→</span>
          )}
        </button>

        {/* User menu */}
        <div className="border-t border-gray-800 p-4">
          {user && sidebarOpen && (
            <div className="flex items-center">
              <div className="h-9 w-9 rounded-full bg-gray-600 flex items-center justify-center text-white font-medium">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <div className="ml-3 flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">{user.name}</p>
                <p className="text-xs text-gray-400 truncate">{user.email}</p>
              </div>
            </div>
          )}
          <button
            onClick={logout}
            className={clsx(
              'flex items-center text-gray-400 hover:text-white mt-3',
              sidebarOpen ? 'w-full' : 'justify-center'
            )}
          >
            <ArrowRightOnRectangleIcon className="h-5 w-5" />
            {sidebarOpen && <span className="ml-2 text-sm">Sign out</span>}
          </button>
        </div>
      </div>

      {/* Main content area */}
      <div
        className={clsx(
          'transition-all duration-300',
          sidebarOpen ? 'lg:pl-64' : 'lg:pl-20'
        )}
      >
        {/* Top header */}
        <header className="sticky top-0 z-40 flex h-16 items-center gap-4 border-b bg-white px-4 shadow-sm">
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="lg:hidden text-gray-500 hover:text-gray-700"
          >
            <Bars3Icon className="h-6 w-6" />
          </button>

          <div className="flex flex-1 items-center justify-end gap-4">
            {/* Search */}
            <div className="hidden sm:block flex-1 max-w-md">
              <input
                type="search"
                placeholder="Search leads, conversations..."
                className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Notifications */}
            <button className="relative rounded-full p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700">
              <BellIcon className="h-6 w-6" />
              {unreadCount > 0 && (
                <span className="absolute right-1 top-1 h-4 w-4 rounded-full bg-red-500 text-[10px] font-medium text-white flex items-center justify-center">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
