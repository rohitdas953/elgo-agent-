import { LayoutDashboard, ShoppingBag, PieChart, Clock, Wallet, Activity, LogOut, Wifi, WifiOff } from 'lucide-react'

const Sidebar = ({ currentView, setCurrentView, userName, userRank, backendOnline }) => {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
    { id: 'shop', label: 'AI Search', icon: <ShoppingBag size={20} /> },
    { id: 'portfolio', label: 'Algorand', icon: <PieChart size={20} /> },
    { id: 'history', label: 'History', icon: <Clock size={20} /> },
    { id: 'wallet', label: 'Wallet', icon: <Wallet size={20} /> },
    { id: 'activity', label: 'Live Feed', icon: <Activity size={20} /> },
  ]

  return (
    <aside className="w-64 bg-[#080809] border-r border-[#1a1a1c] flex flex-col h-full shrink-0 z-20">
      <div className="p-6 flex items-center gap-3 border-b border-[#1a1a1c]">
        <div className="w-10 h-10 rounded bg-elite-gray border border-elite-gold flex items-center justify-center shadow-gold-glow">
          <span className="text-elite-gold font-bold font-serif text-xl tracking-tighter">A.</span>
        </div>
        <div>
          <h1 className="text-sm font-bold tracking-widest text-elite-text uppercase">AgentScore</h1>
          <p className="text-[10px] text-elite-gold tracking-[0.2em] uppercase">x402 • Algorand</p>
        </div>
      </div>

      <div className="p-6 border-b border-[#1a1a1c]">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-elite-gray border-2 border-[#333] overflow-hidden">
            <img 
              src="https://api.dicebear.com/7.x/notionists/svg?seed=Agent&backgroundColor=d4af37" 
              alt="User" 
              className="w-full h-full object-cover"
            />
          </div>
          <div>
            <p className="text-sm font-semibold">{userName}</p>
            <div className="flex items-center gap-1 mt-1">
              <div className="w-2 h-2 rounded-full bg-elite-gold shadow-gold-glow"></div>
              <p className="text-xs text-gray-400">{userRank}</p>
            </div>
          </div>
        </div>
      </div>

      <nav className="flex-1 py-6 px-4 flex flex-col gap-2">
        {menuItems.map((item) => (
          <div 
            key={item.id}
            onClick={() => setCurrentView(item.id)}
            className={`nav-item ${currentView === item.id ? 'active' : ''}`}
          >
            {item.icon}
            <span className="font-medium tracking-wide text-sm">{item.label}</span>
          </div>
        ))}
      </nav>

      <div className="p-4 border-t border-[#1a1a1c] space-y-3">
        <div className={`flex items-center gap-2 px-4 py-2 rounded text-xs font-mono uppercase tracking-widest ${
          backendOnline ? 'text-green-400 bg-green-400/5' : 'text-gray-500 bg-gray-500/5'
        }`}>
          {backendOnline ? <Wifi size={12} /> : <WifiOff size={12} />}
          {backendOnline ? 'Backend Live' : 'Offline'}
        </div>
        <div className="nav-item hover:text-red-400 text-gray-500">
          <LogOut size={20} />
          <span className="font-medium tracking-wide text-sm">Disconnect</span>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
