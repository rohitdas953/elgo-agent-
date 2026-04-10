import { useState, useEffect } from 'react'
import { Activity, Zap, Search, ShoppingCart, CreditCard, Eye, RefreshCw } from 'lucide-react'
import { fetchActivityLog } from '../lib/api'

const ICON_MAP = {
  vision: Eye,
  search: Search,
  payment: CreditCard,
  order: ShoppingCart,
  bot_cmd: Zap,
}

const LEVEL_COLORS = {
  info: 'text-blue-400 border-blue-400/20 bg-blue-400/5',
  success: 'text-green-400 border-green-400/20 bg-green-400/5',
  warn: 'text-yellow-400 border-yellow-400/20 bg-yellow-400/5',
  error: 'text-red-400 border-red-400/20 bg-red-400/5',
}

const ActivityFeed = () => {
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const data = await fetchActivityLog(30)
      setEntries(data.entries || [])
    } catch {}
    setLoading(false)
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="mt-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold tracking-wide uppercase flex items-center gap-2">
          <Activity size={20} className="text-elite-violet" /> Live Activity Feed
        </h2>
        <button onClick={load} className="text-gray-500 hover:text-elite-gold transition-colors">
          <RefreshCw size={16} />
        </button>
      </div>

      <div className="manga-glass rounded-elite border border-[#2a2a2c] overflow-hidden">
        {loading ? (
          <div className="p-12 flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-elite-gold border-t-transparent rounded-full animate-spin"></div>
            <p className="text-xs text-gray-500 font-mono">Loading activity log...</p>
          </div>
        ) : entries.length === 0 ? (
          <div className="p-12 text-center">
            <Activity size={32} className="text-gray-600 mx-auto mb-3" />
            <p className="text-sm text-gray-500">No activity yet. Search for a product or use the Telegram bot!</p>
          </div>
        ) : (
          <div className="divide-y divide-[#1a1a1c] max-h-[600px] overflow-y-auto">
            {entries.map((entry, i) => {
              const Icon = ICON_MAP[entry.event || entry.category] || Activity
              const levelClass = LEVEL_COLORS[entry.level] || LEVEL_COLORS.info
              const timestamp = entry.ts || entry.timestamp
              const message = entry.title || entry.message || ''
              return (
                <div key={`${timestamp}-${i}`} className="p-4 hover:bg-[#111112] transition-colors flex items-start gap-3">
                  <div className={`p-1.5 rounded border ${levelClass} shrink-0 mt-0.5`}>
                    <Icon size={14} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-200">{message}</p>
                    {entry.detail && <p className="text-[11px] text-gray-500 mt-0.5 truncate">{entry.detail}</p>}
                  </div>
                  <span className="text-[10px] text-gray-600 font-mono shrink-0 mt-0.5">
                    {timestamp ? new Date(timestamp * 1000).toLocaleTimeString() : ''}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default ActivityFeed
