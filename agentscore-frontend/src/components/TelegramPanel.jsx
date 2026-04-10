import { MessageSquare, Wifi, WifiOff, Send, Bot, ExternalLink } from 'lucide-react'

const TelegramPanel = ({ backendOnline }) => {
  return (
    <div className="manga-glass rounded-elite border border-[#2a2a2c] p-6 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-32 h-32 bg-[#0088cc]/5 rounded-full blur-3xl translate-x-1/3 -translate-y-1/3 pointer-events-none"></div>

      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Bot size={18} className="text-[#0088cc]" />
          <h3 className="text-sm font-bold tracking-widest uppercase">Telegram Bot</h3>
        </div>
        <div className={`flex items-center gap-1.5 text-[10px] px-2.5 py-1 rounded-full border font-mono uppercase tracking-widest ${
          backendOnline 
            ? 'text-green-400 border-green-400/20 bg-green-400/5' 
            : 'text-gray-500 border-gray-500/20 bg-gray-500/5'
        }`}>
          {backendOnline ? <><Wifi size={9} /> Polling</> : <><WifiOff size={9} /> Offline</>}
        </div>
      </div>

      <div className="space-y-3">
        <div className="bg-[#111112] border border-[#1a1a1c] rounded p-3 flex items-start gap-3">
          <div className="p-1.5 bg-[#0088cc]/10 rounded border border-[#0088cc]/20">
            <MessageSquare size={14} className="text-[#0088cc]" />
          </div>
          <div className="text-xs">
            <p className="text-gray-300 mb-1">Send a product photo → AI identifies it → Searches 4 platforms → Orders via ALGO</p>
            <p className="text-gray-600 font-mono text-[10px]">@AgentScoreBot on Telegram</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 text-[10px]">
          <div className="bg-[#111112] border border-[#1a1a1c] rounded p-2 text-center">
            <span className="text-gray-500 block mb-0.5">Commands</span>
            <span className="text-gray-300 font-mono">/start /wallet /help</span>
          </div>
          <div className="bg-[#111112] border border-[#1a1a1c] rounded p-2 text-center">
            <span className="text-gray-500 block mb-0.5">Vision AI</span>
            <span className="text-gray-300 font-mono">Gemini 2.0 Flash</span>
          </div>
        </div>

        <a
          href="https://t.me/AgentScoreBot"
          target="_blank"
          rel="noreferrer"
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-elite bg-[#0088cc]/10 border border-[#0088cc]/30 text-[#0088cc] text-xs font-semibold uppercase tracking-widest hover:bg-[#0088cc]/20 transition-all"
        >
          <Send size={14} /> Open in Telegram <ExternalLink size={10} />
        </a>
      </div>
    </div>
  )
}

export default TelegramPanel
