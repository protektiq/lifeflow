"use client"

import { useEffect, useState } from 'react'
import { apiClient } from '@/src/lib/api'
import { Notification } from '@/src/types/notification'

interface NotificationCenterProps {
  autoRefresh?: boolean
  refreshInterval?: number // milliseconds
}

export default function NotificationCenter({
  autoRefresh = true,
  refreshInterval = 30000, // 30 seconds
}: NotificationCenterProps) {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showAll, setShowAll] = useState(false)

  const loadNotifications = async () => {
    try {
      setError(null)
      const data = await apiClient.getNotifications(undefined, 20)
      setNotifications(data || [])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load notifications')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadNotifications()

    if (autoRefresh) {
      const interval = setInterval(loadNotifications, refreshInterval)
      return () => clearInterval(interval)
    }
  }, [autoRefresh, refreshInterval])

  const handleDismiss = async (notificationId: string) => {
    try {
      await apiClient.dismissNotification(notificationId)
      setNotifications((prev) =>
        prev.filter((n) => n.id !== notificationId)
      )
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to dismiss notification')
    }
  }

  const formatTime = (timeString: string) => {
    const date = new Date(timeString)
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    })
  }

  const getNotificationIcon = (type: string, isCritical?: boolean, isUrgent?: boolean) => {
    if (isCritical) return '🔴'
    if (isUrgent) return '⚠️'
    if (type === 'nudge') return '📋'
    return '🔔'
  }

  const getNotificationColor = (type: string, isCritical?: boolean, isUrgent?: boolean) => {
    if (isCritical) return 'border-red-500 bg-red-50'
    if (isUrgent) return 'border-orange-500 bg-orange-50'
    return 'border-blue-500 bg-blue-50'
  }

  const pendingNotifications = notifications.filter((n) => n.status === 'pending' || n.status === 'sent')
  const dismissedNotifications = notifications.filter((n) => n.status === 'dismissed')
  const displayedNotifications = showAll ? notifications : pendingNotifications

  if (loading && notifications.length === 0) {
    return (
      <div className="rounded-lg bg-white p-6 shadow-sm">
        <div className="flex items-center justify-center py-4">
          <div className="h-6 w-6 animate-spin rounded-full border-4 border-blue-600 border-t-transparent"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-lg bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Notifications</h3>
          <p className="text-sm text-gray-600">
            {pendingNotifications.length} pending
            {dismissedNotifications.length > 0 && ` • ${dismissedNotifications.length} dismissed`}
          </p>
        </div>
        {dismissedNotifications.length > 0 && (
          <button
            onClick={() => setShowAll(!showAll)}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            {showAll ? 'Show Pending' : 'Show All'}
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {displayedNotifications.length === 0 ? (
          <div className="py-8 text-center text-gray-500">
            No notifications
          </div>
        ) : (
          displayedNotifications.map((notification) => {
            const isCritical = notification.message.includes('CRITICAL')
            const isUrgent = notification.message.includes('URGENT')
            
            return (
              <div
                key={notification.id}
                className={`rounded-lg border p-4 ${getNotificationColor(
                  notification.type,
                  isCritical,
                  isUrgent
                )} ${notification.status === 'dismissed' ? 'opacity-60' : ''}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">
                        {getNotificationIcon(notification.type, isCritical, isUrgent)}
                      </span>
                      <p className="font-medium text-gray-900">{notification.message}</p>
                    </div>
                    <div className="mt-1 flex items-center gap-4 text-xs text-gray-600">
                      <span>{formatTime(notification.scheduled_at)}</span>
                      {notification.sent_at && (
                        <span>Sent: {formatTime(notification.sent_at)}</span>
                      )}
                      <span className="capitalize">{notification.status}</span>
                    </div>
                  </div>
                  {notification.status !== 'dismissed' && (
                    <button
                      onClick={() => handleDismiss(notification.id)}
                      className="ml-4 rounded-md bg-gray-200 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-300"
                      aria-label="Dismiss notification"
                    >
                      Dismiss
                    </button>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

