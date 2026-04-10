import { useState, useEffect, useRef } from 'react'
import { Blocks, ExternalLink, Clock, Wifi, WifiOff } from 'lucide-react'

const ALGOD_URL = 'https://testnet-api.algonode.cloud'

const AlgoBlockPanel = () => {
  const [blocks, setBlocks] = useState([])
  const [isLive, setIsLive] = useState(false)
  const latestRef = useRef(0)
  const scrollRef = useRef(null)

  const fetchBlock = async (round) => {
    try {
      const r = await fetch(`${ALGOD_URL}/v2/blocks/${round}`, { headers: { 'X-Algo-API-Token': '' } })
      if (!r.ok) return null
      const data = await r.json()
      const txns = data.block?.txns || []
      const ts = data.block?.ts || Math.floor(Date.now() / 1000)
      const prp = data.block?.prp || ''
      let hasAS = false
      for (const t of txns) {
        try {
          const note = t?.txn?.note
          if (note && atob(note).includes('agentscore')) { hasAS = true; break }
        } catch {}
      }
      return {
        round, timestamp: new Date(ts * 1000).toLocaleTimeString(),
        txnCount: txns.length, proposer: prp ? `${prp.slice(0,6)}...${prp.slice(-4)}` : 'N/A',
        hasAS, real: true,
      }
    } catch { return null }
  }

  useEffect(() => {
    let cancelled = false
    const init = async () => {
      try {
        const r = await fetch(`${ALGOD_URL}/v2/status`, { headers: { 'X-Algo-API-Token': '' } })
        const s = await r.json()
        const latest = s['last-round']
        latestRef.current = latest
        const ps = []
        for (let i = 5; i >= 0; i--) ps.push(fetchBlock(latest - i))
        const res = await Promise.all(ps)
        if (!cancelled) { setBlocks(res.filter(Boolean)); setIsLive(true) }
      } catch {
        if (!cancelled) setIsLive(false)
      }
    }
    init()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const r = await fetch(`${ALGOD_URL}/v2/status`, { headers: { 'X-Algo-API-Token': '' } })
        const s = await r.json()
        const latest = s['last-round']
        if (latest > latestRef.current) {
          const nb = []
          for (let i = latestRef.current + 1; i <= latest; i++) {
            const b = await fetchBlock(i)
            if (b) nb.push(b)
          }
          latestRef.current = latest
          if (nb.length) setBlocks(p => [...p, ...nb].slice(-10))
        }
      } catch {}
    }, 4500)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [blocks])

  return (
    <div className="manga-glass rounded-elite border border-[#2a2a2c] p-6 mt-6 relative overflow-hidden">
      <div className="absolute bottom-0 left-0 w-40 h-40 bg-elite-violet/5 rounded-full blur-3xl -ml-10 -mb-10 pointer-events-none"></div>
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <Blocks className="text-elite-gold" size={18} />
          <h3 className="text-sm font-bold tracking-widest uppercase">Algorand Testnet</h3>
        </div>
        <div className={`flex items-center gap-2 text-[10px] px-3 py-1 rounded-full border font-mono uppercase tracking-widest ${
          isLive ? 'text-green-400 border-green-400/20 bg-green-400/5' : 'text-yellow-400 border-yellow-400/20 bg-yellow-400/5'
        }`}>
          {isLive ? <><Wifi size={10} /> Live</> : <><WifiOff size={10} /> Offline</>}
        </div>
      </div>

      <div ref={scrollRef} className="space-y-2 max-h-[350px] overflow-y-auto pr-1">
        {blocks.map(b => (
          <div key={b.round} className="flex items-center justify-between p-3 rounded bg-[#111112] border border-[#1a1a1c] hover:border-elite-gold/20 transition-colors group text-sm">
            <div className="flex items-center gap-3">
              <span className="text-elite-gold font-mono font-bold text-xs">#</span>
              <div>
                <p className="font-mono text-gray-200">{b.round.toLocaleString()}</p>
                <div className="flex items-center gap-1 mt-0.5">
                  <Clock size={8} className="text-gray-600" />
                  <span className="text-[10px] text-gray-600">{b.timestamp}</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-500">{b.txnCount} txns</span>
              {b.hasAS && (
                <span className="text-[10px] px-2 py-0.5 rounded bg-elite-gold/10 text-elite-gold border border-elite-gold/20 font-mono">x402</span>
              )}
              <a href={`https://testnet.explorer.perawallet.app/block/${b.round}`} target="_blank" rel="noreferrer"
                className="text-gray-600 hover:text-elite-gold transition-colors opacity-0 group-hover:opacity-100">
                <ExternalLink size={12} />
              </a>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 pt-3 border-t border-[#1a1a1c] flex items-center justify-between text-[10px] text-gray-600 font-mono">
        <span>~4.5s block time{isLive && ` • Round ${latestRef.current?.toLocaleString()}`}</span>
        <a href="https://testnet.explorer.perawallet.app" target="_blank" rel="noreferrer" className="flex items-center gap-1 hover:text-elite-gold transition-colors">
          <ExternalLink size={10} /> Pera Explorer
        </a>
      </div>
    </div>
  )
}

export default AlgoBlockPanel
