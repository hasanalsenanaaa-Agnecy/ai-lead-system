import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  HomeIcon,
  UserGroupIcon,
  ChatBubbleLeftRightIcon,
  BookOpenIcon,
  Cog6ToothIcon,
  ExclamationTriangleIcon,
  BuildingOfficeIcon,
  ChartBarIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline';
import { useAuthStore, useClientStore } from '../store';

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Leads', href: '/leads', icon: UserGroupIcon },
  { name: 'Conversations', href: '/conversations', icon: ChatBubbleLeftRightIcon },
  { name: 'Escalations', href: '/escalations', icon: ExclamationTriangleIcon },
  { name: 'Knowledge Base', href: '/knowledge', icon: BookOpenIcon },
  { name: 'Analytics', href: '/analytics', icon: ChartBarIcon },
];

const adminNavigation = [
  { name: 'Clients', href: '/clients', icon: BuildingOfficeIcon },
];

const bottomNavigation = [
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
];

export default function DashboardLayout() {
  const { user, logout } = useAuthStore();
  const { currentClient } = useClientStore();
  const location = useLocation();
  const navigate = useNavigate();

  const isAdmin = user?.role === 'super_admin' || user?.role === 'admin';

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (href: string) => {
    if (href === '/') return location.pathname === '/';
    return location.pathname.startsWith(href);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className="hidden md:flex md:flex-col md:w-64 md:fixed md:inset-y-0 bg-white border-r border-gray-200">
        {/* Logo */}
        <div className="flex items-center h-16 px-6 border-b border-gray-200">
          <Link to="/" className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">AI</span>
            </div>
            <span className="text-xl font-bold text-gray-900">Lead System</span>
          </Link>
        </div>

        {/* Client indicator */}
        {currentClient && (
          <div className="px-4 py-3 border-b border-gray-200">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">Client</p>
            <p className="text-sm font-semibold text-gray-900 truncate">{currentClient.name}</p>
            <span className={clsx(
              'inline-flex items-center mt-1 px-2 py-0.5 rounded-full text-xs font-medium',
              currentClient.status === 'active' && 'bg-green-100 text-green-800',
              currentClient.status === 'paused' && 'bg-yellow-100 text-yellow-800',
              currentClient.status === 'onboarding' && 'bg-blue-100 text-blue-800',
              currentClient.status === 'churned' && 'bg-red-100 text-red-800',
            )}>
              {currentClient.status}
            </span>
          </div>
        )}

        {/* Main Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navigation.map((item) => (
            <Link
              key={item.name}
              to={item.href}
              className={clsx(
                'flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-colors',
                isActive(item.href)
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              )}
            >
              <item.icon className={clsx(
                'mr-3 h-5 w-5 flex-shrink-0',
                isActive(item.href) ? 'text-blue-600' : 'text-gray-400'
              )} />
              {item.name}
            </Link>
          ))}

          {/* Admin section */}
          {isAdmin && (
            <>
              <div className="pt-4 pb-1">
                <p className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Admin</p>
              </div>
              {adminNavigation.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                  className={clsx(
                    'flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-colors',
                    isActive(item.href)
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  )}
                >
                  <item.icon className={clsx(
                    'mr-3 h-5 w-5 flex-shrink-0',
                    isActive(item.href) ? 'text-blue-600' : 'text-gray-400'
                  )} />
                  {item.name}
                </Link>
              ))}
            </>
          )}
        </nav>

        {/* Bottom Nav */}
        <div className="px-3 py-3 border-t border-gray-200 space-y-1">
          {bottomNavigation.map((item) => (
            <Link
              key={item.name}
              to={item.href}
              className={clsx(
                'flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-colors',
                isActive(item.href)
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              )}
            >
              <item.icon className={clsx(
                'mr-3 h-5 w-5 flex-shrink-0',
                isActive(item.href) ? 'text-blue-600' : 'text-gray-400'
              )} />
              {item.name}
            </Link>
          ))}

          {/* User & Logout */}
          <div className="flex items-center justify-between px-3 py-2.5">
            <div className="flex items-center min-w-0">
              <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-sm font-medium text-gray-600">
                  {user?.first_name?.[0]}{user?.last_name?.[0]}
                </span>
              </div>
              <div className="ml-2 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {user?.first_name} {user?.last_name}
                </p>
                <p className="text-xs text-gray-500 truncate">{user?.email}</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="ml-2 p-1.5 text-gray-400 hover:text-red-600 rounded-lg hover:bg-gray-50 transition-colors"
              title="Logout"
            >
              <ArrowRightOnRectangleIcon className="h-5 w-5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile header */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-blue-600">AI Leads</Link>
          <div className="flex items-center space-x-3 overflow-x-auto">
            {navigation.slice(0, 4).map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className={clsx(
                  'text-xs font-medium whitespace-nowrap px-2 py-1 rounded',
                  isActive(item.href)
                    ? 'text-blue-700 bg-blue-50'
                    : 'text-gray-500'
                )}
              >
                {item.name}
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Main content */}
      <main className="flex-1 md:ml-64">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 md:py-8 mt-14 md:mt-0">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
