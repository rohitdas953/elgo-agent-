import { Search, Bell, Settings, Zap, Wallet, Wifi, WifiOff } from 'lucide-react'

const Navbar = ({ balance = 0, userName, backendOnline, walletAddress }) => {
  return (
    <header className="h-20 bg-[#0b0b0c]/90 backdrop-blur-md border-b border-[#1a1a1c] flex items-center justify-between px-6 z-10 sticky top-0">
      
      {/* Left info */}
      <div className="flex items-center gap-4">
        <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded border text-[10px] font-mono uppercase tracking-widest ${
          backendOnline ? 'text-green-400 border-green-400/20 bg-green-400/5' : 'text-gray-500 border-gray-500/20'
        }`}>
          {backendOnline ? <Wifi size={10} /> : <WifiOff size={10} />}
          {backendOnline ? 'Live' : 'Demo'}
        </div>

        {walletAddress && (
          <div className="hidden lg:flex items-center gap-2 text-[10px] text-gray-500 font-mono bg-[#111112] px-3 py-1.5 rounded border border-[#1a1a1c]">
            <Wallet size={10} />
            {walletAddress.slice(0, 8)}...{walletAddress.slice(-6)}
          </div>
        )}
      </div>

      {/* Right Side */}
      <div className="flex items-center gap-4">
        
        {/* Balance Badge */}
        <div className="flex items-center gap-2 bg-[#1a1a1c] border border-[#333] px-4 py-1.5 rounded-elite">
          <span className="text-xs text-gray-400 uppercase tracking-wider">ALGO</span>
          <span className="text-sm font-medium text-elite-gold font-mono">{balance.toFixed(4)}</span>
        </div>

        {/* INR Approx */}
        <div className="hidden md:flex items-center gap-2 bg-[#1a1a1c] border border-[#333] px-3 py-1.5 rounded-elite">
          <span className="text-xs text-gray-400">≈</span>
          <span className="text-xs text-gray-300 font-mono">₹{(balance * 18.85).toFixed(0)}</span>
        </div>

        {/* Icons */}
        <div className="flex items-center gap-2">
          <button className="relative w-9 h-9 rounded-elite bg-[#111112] border border-[#333] flex items-center justify-center text-gray-400 hover:text-elite-gold hover:border-elite-gold transition-all">
            <Bell size={16} />
            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-elite-violet rounded-full shadow-violet-glow"></span>
          </button>
          <button className="w-9 h-9 rounded-elite bg-[#111112] border border-[#333] flex items-center justify-center text-gray-400 hover:text-elite-gold hover:border-elite-gold transition-all">
            <Settings size={16} />
          </button>
        </div>

      </div>
    </header>
  )
}

export default Navbar
