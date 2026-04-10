import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { CheckCircle2, XCircle, Clock, RefreshCw } from 'lucide-react'
import { fetchRecentTransactions } from '../lib/api'

const HistoryDashboard = () => {
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const data = await fetchRecentTransactions()
      const txns = Array.isArray(data) ? data : (data.transactions || [])
      setTransactions(txns)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  // Build chart data from transactions
  const chartData = transactions.length > 0
    ? transactions.slice(0, 6).reverse().map((t, i) => ({
        name: t.timestamp ? new Date(t.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : `Txn ${i+1}`,
        value: (t.amount_usdc || t.amount_algo || 0) * 100,
      }))
    : [
        { name: 'Jan', value: 2400 }, { name: 'Feb', value: 4100 },
        { name: 'Mar', value: 3800 }, { name: 'Apr', value: 5900 },
        { name: 'May', value: 4800 }, { name: 'Jun', value: 8800 },
      ]

  // Format transactions for display
  const displayTxns = transactions.length > 0
    ? transactions.map((t, i) => ({
        id: t.tx_id || t.txn_hash || `TRX-${i}`,
        item: t.service_name || t.product_name || 'Transaction',
        date: t.timestamp ? new Date(t.timestamp).toLocaleDateString() : 'N/A',
        amount: t.amount_usdc ? `$${t.amount_usdc}` : t.amount_algo ? `${t.amount_algo} ALGO` : '$0',
        status: t.success ? 'completed' : t.success === false ? 'failed' : 'pending',
      }))
    : [
        { id: 'TRX-9482', item: "iPhone 15 Pro Max (Amazon)", date: "Today", amount: "₹1,34,900", status: 'completed' },
        { id: 'TRX-9481', item: "JBL Flip 6 Speaker", date: "Yesterday", amount: "₹2,037", status: 'pending' },
        { id: 'TRX-9480', item: "Lays Classic Chips 100g (Zepto)", date: "Apr 08", amount: "₹30", status: 'completed' },
        { id: 'TRX-9479', item: "Samsung Galaxy S24 (Flipkart)", date: "Apr 05", amount: "₹79,999", status: 'failed' },
      ]

  return (
    <div className="space-y-6 mt-6">
      <div className="manga-glass rounded-elite border border-[#2a2a2c] p-6 lg:p-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-xl font-bold tracking-wide uppercase">Purchase History</h2>
            <p className="text-xs text-gray-500 tracking-widest uppercase mt-1">Transaction Velocity</p>
          </div>
          <button onClick={load} className="text-gray-500 hover:text-elite-gold transition-colors">
            <RefreshCw size={16} />
          </button>
        </div>
        
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1c" vertical={false} />
              <XAxis dataKey="name" stroke="#555" tick={{fill: '#555', fontSize: 12}} tickLine={false} axisLine={false} />
              <YAxis stroke="#555" tick={{fill: '#555', fontSize: 12, fontFamily: 'monospace'}} tickLine={false} axisLine={false} tickFormatter={(val) => `₹${val > 1000 ? `${(val/1000).toFixed(0)}k` : val}`} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0b0b0c', borderColor: '#d4af37', borderRadius: '4px', boxShadow: '0 0 15px rgba(212, 175, 55, 0.1)' }}
                itemStyle={{ color: '#d4af37', fontFamily: 'monospace' }}
              />
              <Line type="monotone" dataKey="value" stroke="#d4af37" strokeWidth={3} dot={{r: 4, fill: '#0b0b0c', stroke: '#d4af37', strokeWidth: 2}} activeDot={{r: 6, fill: '#d4af37', stroke: '#0b0b0c', strokeWidth: 2}} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="manga-glass rounded-elite border border-[#2a2a2c] overflow-hidden">
        <div className="p-6 border-b border-[#1a1a1c]">
          <h3 className="text-sm font-bold tracking-widest uppercase">Transaction Ledger</h3>
        </div>

        {loading ? (
          <div className="p-12 flex justify-center">
            <div className="w-8 h-8 border-2 border-elite-gold border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : (
          <div className="divide-y divide-[#1a1a1c]">
            {displayTxns.map((tx) => (
              <div key={tx.id} className="p-4 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-[#111112] transition-colors">
                <div className="flex flex-col">
                  <span className="text-sm font-semibold text-gray-200">{tx.item}</span>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-[10px] text-gray-500 font-mono">{tx.id.length > 20 ? `${tx.id.slice(0,8)}...${tx.id.slice(-6)}` : tx.id}</span>
                    <span className="text-[10px] text-gray-500 uppercase tracking-widest bg-[#111112] px-2 py-0.5 rounded">{tx.date}</span>
                  </div>
                </div>
                <div className="flex items-center justify-between sm:justify-end sm:w-1/3 gap-6">
                  <span className="font-mono font-medium">{tx.amount}</span>
                  <div className="w-24 flex justify-end">
                    {tx.status === 'completed' && <div className="flex items-center gap-1.5 text-xs text-green-400 font-semibold uppercase tracking-wider"><CheckCircle2 size={14} /> Done</div>}
                    {tx.status === 'pending' && <div className="flex items-center gap-1.5 text-xs text-yellow-500 font-semibold uppercase tracking-wider"><Clock size={14} /> Pend</div>}
                    {tx.status === 'failed' && <div className="flex items-center gap-1.5 text-xs text-red-500 font-semibold uppercase tracking-wider"><XCircle size={14} /> Fail</div>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default HistoryDashboard
