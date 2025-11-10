"use client"

import NotificationCenter from '@/components/NotificationCenter'

export const dynamic = 'force-dynamic'

export default function NotificationsPage() {
  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-800 dark:text-gray-200 mb-2">Notifications</h2>
        <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400">View and manage your notifications</p>
      </div>

      <NotificationCenter autoRefresh={true} refreshInterval={30000} />
    </div>
  )
}

