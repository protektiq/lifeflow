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
  const [selectedNotificationId, setSelectedNotificationId] = useState<string | null>(null)
  const [selectedNotification, setSelectedNotification] = useState<Notification | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

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

  const handleNotificationClick = async (notificationId: string, e: React.MouseEvent) => {
    // Don't open detail if clicking dismiss button
    const target = e.target as HTMLElement
    if (target.closest('button')) {
      return
    }
    
    try {
      setLoadingDetail(true)
      setSelectedNotificationId(notificationId)
      const detail = await apiClient.getNotification(notificationId)
      setSelectedNotification(detail)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load notification details')
      setSelectedNotificationId(null)
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleCloseDetail = () => {
    setSelectedNotificationId(null)
    setSelectedNotification(null)
  }

  const formatDateTime = (timeString: string) => {
    const date = new Date(timeString)
    return date.toLocaleString('en-US', {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    })
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
      <div className="rounded-2xl bg-white p-6 sm:p-8 shadow-lg animate-scale-in">
        <div className="flex items-center justify-center py-4">
          <div className="h-6 w-6 animate-spin rounded-full border-4 border-purple-600 border-t-transparent"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="group relative rounded-2xl bg-white p-6 sm:p-8 shadow-lg transition-all duration-300 hover:shadow-2xl hover:scale-105 animate-scale-in">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
      <div className="relative z-10">
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h3 className="text-lg sm:text-xl font-bold mb-1">
              <span className="gradient-text">Notifications</span>
            </h3>
            <p className="text-sm sm:text-base text-gray-700">
              {pendingNotifications.length} pending
              {dismissedNotifications.length > 0 && ` • ${dismissedNotifications.length} dismissed`}
            </p>
          </div>
          {dismissedNotifications.length > 0 && (
            <button
              onClick={() => setShowAll(!showAll)}
              className="px-4 py-2 border-2 border-purple-300 text-purple-700 font-semibold text-xs sm:text-sm rounded-full backdrop-blur-sm transition-all duration-300 hover:border-purple-500 hover:bg-purple-50 hover:scale-110 focus:outline-none focus:ring-4 focus:ring-purple-500/50"
            >
              {showAll ? 'Show Pending' : 'Show All'}
            </button>
          )}
        </div>

        {error && (
          <div className="mb-4 rounded-xl bg-red-50 border-2 border-red-200 p-3 text-sm font-medium text-red-800">
            {error}
          </div>
        )}

        <div className="space-y-3 max-h-96 overflow-y-auto">
          {displayedNotifications.length === 0 ? (
            <div className="py-6 sm:py-8 text-center text-gray-600 font-medium text-sm sm:text-base">
              No notifications
            </div>
          ) : (
            displayedNotifications.map((notification, index) => {
              const isCritical = notification.message.includes('CRITICAL')
              const isUrgent = notification.message.includes('URGENT')
              const detailIsCritical = selectedNotification?.message.includes('CRITICAL')
              const detailIsUrgent = selectedNotification?.message.includes('URGENT')
              
              return (
                <div
                  key={notification.id}
                  onClick={(e) => handleNotificationClick(notification.id, e)}
                  className={`rounded-xl border-2 p-4 sm:p-5 transition-all duration-300 hover:shadow-lg animate-scale-in cursor-pointer ${getNotificationColor(
                    notification.type,
                    isCritical,
                    isUrgent
                  )} ${notification.status === 'dismissed' ? 'opacity-60' : ''}`}
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 sm:gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start gap-2">
                      <span className="text-base sm:text-lg flex-shrink-0">
                        {getNotificationIcon(notification.type, isCritical, isUrgent)}
                      </span>
                      <p className="text-sm sm:text-base font-medium text-gray-900 break-words">{notification.message}</p>
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-2 sm:gap-4 text-xs text-gray-600">
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
                      className="w-full sm:w-auto sm:ml-4 px-4 py-2 border-2 border-gray-300 text-gray-700 font-semibold text-xs rounded-full transition-all duration-300 hover:border-gray-400 hover:bg-gray-100 hover:scale-110 focus:outline-none focus:ring-4 focus:ring-gray-400/50"
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

      {/* Notification Detail Modal */}
      {selectedNotificationId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="rounded-2xl bg-white shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            {loadingDetail ? (
              <div className="p-8 flex items-center justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-purple-600 border-t-transparent"></div>
              </div>
            ) : selectedNotification ? (
              <>
                <div className="sticky top-0 bg-white border-b-2 border-purple-200 p-4 sm:p-6 flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start gap-2 mb-2">
                      <span className="text-2xl flex-shrink-0">
                        {getNotificationIcon(selectedNotification.type, detailIsCritical, detailIsUrgent)}
                      </span>
                      <h2 className="text-xl sm:text-2xl font-bold text-gray-900 break-words">
                        Notification Details
                      </h2>
                    </div>
                  </div>
                  <button
                    onClick={handleCloseDetail}
                    className="ml-4 text-gray-400 hover:text-gray-600 transition-colors flex-shrink-0"
                    aria-label="Close"
                  >
                    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                <div className="p-4 sm:p-6 space-y-4">
                  <div className={`rounded-lg border-2 p-4 ${getNotificationColor(selectedNotification.type, detailIsCritical, detailIsUrgent)}`}>
                    <p className="text-base sm:text-lg font-medium text-gray-900 break-words mb-4">
                      {selectedNotification.message}
                    </p>
                    
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="font-semibold text-gray-700">Type:</span>
                        <span className="text-gray-600 capitalize">{selectedNotification.type}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="font-semibold text-gray-700">Status:</span>
                        <span className="text-gray-600 capitalize">{selectedNotification.status}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="font-semibold text-gray-700">Scheduled:</span>
                        <span className="text-gray-600">{formatDateTime(selectedNotification.scheduled_at)}</span>
                      </div>
                      {selectedNotification.sent_at && (
                        <div className="flex justify-between">
                          <span className="font-semibold text-gray-700">Sent:</span>
                          <span className="text-gray-600">{formatDateTime(selectedNotification.sent_at)}</span>
                        </div>
                      )}
                      {selectedNotification.task_id && (
                        <div className="flex justify-between">
                          <span className="font-semibold text-gray-700">Task ID:</span>
                          <span className="text-gray-600 font-mono text-xs break-all">{selectedNotification.task_id}</span>
                        </div>
                      )}
                      {selectedNotification.plan_id && (
                        <div className="flex justify-between">
                          <span className="font-semibold text-gray-700">Plan ID:</span>
                          <span className="text-gray-600 font-mono text-xs break-all">{selectedNotification.plan_id}</span>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span className="font-semibold text-gray-700">Created:</span>
                        <span className="text-gray-600">{formatDateTime(selectedNotification.created_at)}</span>
                      </div>
                      {selectedNotification.updated_at && (
                        <div className="flex justify-between">
                          <span className="font-semibold text-gray-700">Updated:</span>
                          <span className="text-gray-600">{formatDateTime(selectedNotification.updated_at)}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="sticky bottom-0 bg-white border-t-2 border-purple-200 p-4 sm:p-6">
                  <div className="flex gap-3">
                    {selectedNotification.status !== 'dismissed' && (
                      <button
                        onClick={() => {
                          handleDismiss(selectedNotification.id)
                          handleCloseDetail()
                        }}
                        className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 font-semibold rounded-full transition-all duration-300 hover:bg-gray-300 hover:scale-105 focus:outline-none focus:ring-4 focus:ring-gray-400/50"
                      >
                        Dismiss
                      </button>
                    )}
                    <button
                      onClick={handleCloseDetail}
                      className="flex-1 px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold rounded-full transition-all duration-300 hover:scale-105 hover:shadow-xl hover:shadow-purple-500/50 focus:outline-none focus:ring-4 focus:ring-purple-500/50"
                    >
                      Close
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="p-6 text-center">
                <p className="text-red-600 mb-4">Failed to load notification details</p>
                <button
                  onClick={handleCloseDetail}
                  className="px-4 py-2 bg-purple-600 text-white rounded-full font-semibold hover:bg-purple-700 transition-colors"
                >
                  Close
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

