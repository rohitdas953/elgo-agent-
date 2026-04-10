import { ArrowUpRight, ArrowDownRight, Cpu, ShieldCheck, Layers } from 'lucide-react'

const PortfolioPanel = ({ balance = 0, agentScore = 742, expanded = false }) => {
  const stats = [
    { label: "Agent Score", value: `${agentScore}/1000`, trend: agentScore >= 700 ? "+GOLD" : "+SILVER", isPositive: agentScore >= 500 },
    { label: "ALGO Balance", value: `${balance.toFixed(4)}`, trend: balance > 0 ? "Funded" : "Not funded", isPositive: balance > 0 },
    { label: "Platforms", value: "4 Active", trend: "Amazon, Flipkart, Zepto, Instamart", isPositive: true },
  ]

  return (
    <div className={`manga-glass rounded-elite border border-[#2a2a2c] p-6 h-full flex flex-col ${expanded ? 'max-w-4xl mx-auto mt-6' : ''}`}>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-sm font-bold tracking-widest uppercase text-gray-400">Agent Status</h3>
        <button className="text-elite-violet hover:text-white transition-colors bg-elite-violet/10 p-1.5 rounded border border-elite-violet/20">
          <Cpu size={16} />
        </button>
      </div>

      <div className="mb-6">
        <div className="text-xs text-gray-500 uppercase tracking-widest mb-2">Reputation Tier</div>
        <div className="flex items-center gap-2">
          <span className={`text-lg font-bold font-mono ${agentScore >= 700 ? 'text-elite-gold' : agentScore >= 400 ? 'text-gray-300' : 'text-gray-500'}`}>
            {agentScore >= 700 ? 'GOLD' : agentScore >= 400 ? 'SILVER' : 'BRONZE'}
          </span>
          <span className="text-green-400 text-xs flex items-center bg-green-400/10 px-1.5 py-0.5 rounded border border-green-400/20 font-mono">
            <ArrowUpRight size={12} className="mr-0.5" /> Active
          </span>
        </div>
      </div>

      <div className="space-y-3 flex-1">
        {stats.map((stat, i) => (
          <div key={i} className="bg-[#111112] border border-[#333] rounded p-3 group hover:border-[#444] transition-colors">
            <div className="text-[10px] text-gray-500 uppercase tracking-widest mb-1">{stat.label}</div>
            <div className="flex items-end justify-between">
              <div className="text-sm font-semibold font-mono text-gray-200 group-hover:text-white transition-colors">{stat.value}</div>
              <div className={`flex items-center text-[10px] font-mono ${stat.isPositive ? 'text-green-400' : 'text-red-400'}`}>
                {stat.isPositive ? <ArrowUpRight size={10} /> : <ArrowDownRight size={10} />}
                {stat.trend}
              </div>
            </div>
          </div>
        ))}
      </div>
      
      <div className="mt-4 pt-3 border-t border-[#1a1a1c] flex items-center gap-2 text-[10px] text-gray-600">
        <ShieldCheck size={12} className="text-elite-gold" />
        <span>x402 Protocol • Algorand Testnet</span>
      </div>
    </div>
  )
}

export default PortfolioPanel
