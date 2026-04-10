import { useState } from 'react'
import { CreditCard, Smartphone, ShieldCheck, Zap, Copy, ExternalLink, Check } from 'lucide-react'

const WalletDashboard = ({ balance, setBalance, walletAddress }) => {
  const [amount, setAmount] = useState('')
  const [method, setMethod] = useState('algo')
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleDeposit = (e) => {
    e.preventDefault()
    if(!amount || isNaN(amount)) return;
    
    setLoading(true)
    setTimeout(() => {
      setBalance(b => b + parseFloat(amount))
      setAmount('')
      setLoading(false)
    }, 1500)
  }

  const copyAddress = () => {
    if (walletAddress) {
      navigator.clipboard.writeText(walletAddress)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="mt-6 max-w-4xl mx-auto">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* Balance Card */}
        <div className="manga-glass rounded-elite border border-[#2a2a2c] p-8 flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 right-0 w-48 h-48 bg-elite-gold/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3"></div>
          
          <div>
            <h3 className="text-xs font-bold tracking-widest uppercase text-gray-400 mb-2">ALGO Balance</h3>
            <div className="text-5xl font-mono tracking-tight text-white font-light">
              {balance.toFixed(4)}
            </div>
            <div className="text-sm text-gray-500 font-mono mt-1">
              ≈ ₹{(balance * 18.85).toFixed(2)} INR
            </div>
          </div>

          {walletAddress && (
            <div className="mt-6 bg-[#111112] border border-[#1a1a1c] rounded p-3">
              <div className="text-[10px] text-gray-500 uppercase tracking-widest mb-1">Wallet Address</div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-300 font-mono truncate flex-1">{walletAddress}</span>
                <button onClick={copyAddress} className="p-1.5 rounded bg-[#1a1a1c] border border-[#333] text-gray-500 hover:text-elite-gold transition-colors">
                  {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
                </button>
              </div>
            </div>
          )}
          
          <div className="mt-6 pt-4 border-t border-[#2a2a2c] flex items-center justify-between text-sm text-gray-400">
            <span className="flex items-center gap-2"><ShieldCheck size={16} className="text-elite-gold" /> Algorand Testnet</span>
            <a href={walletAddress ? `https://testnet.explorer.perawallet.app/address/${walletAddress}` : '#'} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-[10px] uppercase tracking-widest hover:text-elite-gold transition-colors">
              Explorer <ExternalLink size={10} />
            </a>
          </div>
        </div>

        {/* Fund Wallet */}
        <div className="manga-glass rounded-elite border border-[#2a2a2c] p-8">
          <h3 className="text-sm font-bold tracking-widest uppercase mb-6">Fund Wallet</h3>
          
          <div className="flex gap-4 mb-6">
            <button 
              onClick={() => setMethod('algo')}
              className={`flex-1 py-3 px-4 rounded border flex flex-col items-center gap-2 transition-all duration-300 ${method === 'algo' ? 'bg-elite-gray border-elite-gold text-elite-gold shadow-gold-glow' : 'bg-[#111112] border-[#333] text-gray-400 hover:border-[#555]'}`}
            >
              <CreditCard size={20} />
              <span className="text-xs uppercase tracking-widest font-semibold">Algorand</span>
            </button>
            <button 
              onClick={() => setMethod('faucet')}
              className={`flex-1 py-3 px-4 rounded border flex flex-col items-center gap-2 transition-all duration-300 ${method === 'faucet' ? 'bg-elite-gray border-elite-violet text-elite-violet shadow-violet-glow' : 'bg-[#111112] border-[#333] text-gray-400 hover:border-[#555]'}`}
            >
              <Smartphone size={20} />
              <span className="text-xs uppercase tracking-widest font-semibold">Testnet Faucet</span>
            </button>
          </div>

          {method === 'faucet' ? (
            <div className="space-y-4">
              <p className="text-sm text-gray-400">Get free testnet ALGO from the Algorand Dispenser:</p>
              <a
                href="https://dispenser.testnet.aws.algodev.network/"
                target="_blank"
                rel="noreferrer"
                className="w-full elite-button bg-elite-violet text-white hover:bg-elite-gold hover:text-black flex items-center justify-center gap-2 h-12 border-elite-violet"
              >
                Open Faucet <ExternalLink size={16} />
              </a>
              <p className="text-[10px] text-gray-600 text-center">Paste your wallet address above into the faucet</p>
            </div>
          ) : (
            <form onSubmit={handleDeposit} className="space-y-4">
              <div>
                <label className="block text-[10px] text-gray-500 uppercase tracking-widest mb-2">Amount (ALGO)</label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 font-mono text-sm">Ⱥ</span>
                  <input 
                    type="number" 
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    className="elite-input pl-8 font-mono text-lg"
                    placeholder="0.00"
                    step="0.1"
                    min="0"
                    required
                  />
                </div>
              </div>
              
              <button 
                type="submit" 
                disabled={loading}
                className="w-full elite-button bg-elite-gold text-black hover:bg-white flex items-center justify-center gap-2 mt-2 h-12"
              >
                {loading ? (
                  <div className="w-5 h-5 border-2 border-black border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <>Simulate Deposit <Zap size={16} /></>
                )}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}

export default WalletDashboard
