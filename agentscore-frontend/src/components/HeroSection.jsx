import { Cpu, TrendingUp, Zap, Wifi, WifiOff } from 'lucide-react'

const HeroSection = ({ backendOnline = false, agentScore = 742 }) => {
  return (
    <div className="relative w-full rounded-elite overflow-hidden bg-[#111112] border border-[#2a2a2c] p-8 md:p-12">
      {/* Background Elements */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-elite-violet/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3"></div>
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-elite-gold/10 rounded-full blur-3xl translate-y-1/2 -translate-x-1/3"></div>
      
      <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-8">
        
        {/* Left Content */}
        <div className="max-w-xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-elite-gold/10 border border-elite-gold/30 text-elite-gold text-xs font-semibold tracking-widest uppercase mb-6">
            <Zap size={14} className="animate-pulse" />
            {backendOnline ? 'AI Engine Active' : 'Demo Mode'}
          </div>
          
          <h2 className="text-4xl md:text-5xl font-bold mb-4 tracking-tight leading-tight">
            Autonomous <span className="text-transparent bg-clip-text bg-gradient-to-r from-elite-gold to-[#f9d976]">Shopping Agent</span>
          </h2>
          
          <p className="text-gray-400 text-lg mb-8 leading-relaxed max-w-md">
            Send a photo or type any product name. AI identifies it, searches Amazon, Flipkart, Zepto & Instamart, then pays with ALGO via x402.
          </p>
          
          <div className="flex gap-4 flex-wrap">
            <div className={`flex items-center gap-2 px-4 py-2 rounded border text-xs font-semibold uppercase tracking-widest ${
              backendOnline ? 'bg-green-400/5 border-green-400/20 text-green-400' : 'bg-gray-500/5 border-gray-500/20 text-gray-500'
            }`}>
              {backendOnline ? <Wifi size={14} /> : <WifiOff size={14} />}
              {backendOnline ? 'Backend Connected' : 'Backend Offline'}
            </div>
            <div className="flex items-center gap-2 px-4 py-2 rounded border border-elite-violet/20 bg-elite-violet/5 text-elite-violet text-xs font-semibold uppercase tracking-widest">
              <TrendingUp size={14} />
              Score: {agentScore}/1000
            </div>
          </div>
        </div>
        
        {/* Right Status Panel */}
        <div className="w-full md:w-auto relative group">
          <div className="absolute inset-0 bg-elite-gold/5 blur-2xl rounded-full block group-hover:bg-elite-gold/10 transition-all duration-700"></div>
          
          <div className="relative manga-glass rounded-elite p-6 flex flex-col items-center justify-center min-w-[240px] border border-[#333] group-hover:border-elite-gold/50 transition-all duration-500">
            <div className="relative w-24 h-24 mb-6">
              <div className="absolute inset-0 rounded-full border-t-2 border-r-2 border-elite-gold animate-spin-slow shadow-gold-glow"></div>
              <div className="absolute inset-3 rounded-full border-b-2 border-l-2 border-elite-violet animate-[spin_4s_linear_infinite_reverse] shadow-violet-glow"></div>
              <div className="absolute inset-0 flex items-center justify-center">
                <Cpu size={24} className="text-elite-gold opacity-80" />
              </div>
            </div>
            
            <h3 className="text-sm font-semibold tracking-widest uppercase text-elite-text mb-1">AgentScore Engine</h3>
            <p className="text-xs text-gray-500 font-mono mb-4">Gemini Vision • Algorand x402</p>
            
            <div className="w-full bg-[#111112] rounded-full h-1.5 overflow-hidden">
              <div className="bg-gradient-to-r from-elite-violet to-elite-gold h-full relative" style={{ width: `${(agentScore / 1000) * 100}%` }}>
                <div className="absolute inset-0 w-full h-full bg-white/20 animate-[pulse_2s_ease-in-out_infinite]"></div>
              </div>
            </div>
          </div>
        </div>
        
      </div>
    </div>
  )
}

export default HeroSection
