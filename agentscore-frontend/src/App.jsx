import { useState, useEffect, useCallback, useRef } from 'react'
import Sidebar from './components/Sidebar'
import Navbar from './components/Navbar'
import HeroSection from './components/HeroSection'
import PortfolioPanel from './components/PortfolioPanel'
import HistoryDashboard from './components/HistoryDashboard'
import WalletDashboard from './components/WalletDashboard'
import SearchPanel from './components/SearchPanel'
import ActivityFeed from './components/ActivityFeed'
import AlgoBlockPanel from './components/AlgoBlockPanel'
import TelegramPanel from './components/TelegramPanel'
import { fetchHealth, fetchWallet, fetchActivityLog, fetchStats } from './lib/api'

function App() {
  const [currentView, setCurrentView] = useState('dashboard')
  const [walletBalance, setWalletBalance] = useState(0)
  const [walletAddress, setWalletAddress] = useState('')
  const [backendOnline, setBackendOnline] = useState(false)
  const [userName, setUserName] = useState('Agent')
  const [userRank, setUserRank] = useState('GOLD Tier')
  const [agentScore, setAgentScore] = useState(742)

  // Probe backend + load wallet
  const loadBackendData = useCallback(async () => {
    try {
      await fetchHealth()
      setBackendOnline(true)

      const wallet = await fetchWallet()
      if (wallet?.balance_algo !== undefined) {
        setWalletBalance(wallet.balance_algo)
        setWalletAddress(wallet.wallet_address || '')
      }

      try {
        const stats = await fetchStats()
        if (stats?.agent_count) {
          setAgentScore(Math.min(1000, 650 + stats.agent_count * 15))
        }
      } catch {}
    } catch {
      setBackendOnline(false)
    }
  }, [])

  useEffect(() => {
    loadBackendData()
    const interval = setInterval(loadBackendData, 20000)
    return () => clearInterval(interval)
  }, [loadBackendData])

  const handleOrderPlaced = (result) => {
    setWalletBalance(b => Math.max(0, b - (result?.amount_algo || 0.5)))
    setAgentScore(s => Math.min(1000, s + 15))
  }

  const renderView = () => {
    switch(currentView) {
      case 'dashboard':
        return (
          <>
            <HeroSection backendOnline={backendOnline} agentScore={agentScore} />
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mt-6">
              <div className="xl:col-span-2">
                <SearchPanel onOrderPlaced={handleOrderPlaced} />
              </div>
              <div className="space-y-6">
                <PortfolioPanel balance={walletBalance} agentScore={agentScore} />
                <TelegramPanel backendOnline={backendOnline} />
              </div>
            </div>
          </>
        )
      case 'shop':
        return <SearchPanel onOrderPlaced={handleOrderPlaced} fullWidth />
      case 'portfolio':
        return (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mt-6">
            <div className="xl:col-span-2">
              <AlgoBlockPanel />
            </div>
            <div>
              <PortfolioPanel balance={walletBalance} agentScore={agentScore} expanded />
            </div>
          </div>
        )
      case 'history':
        return <HistoryDashboard />
      case 'wallet':
        return <WalletDashboard balance={walletBalance} setBalance={setWalletBalance} walletAddress={walletAddress} />
      case 'activity':
        return <ActivityFeed />
      default:
        return <HeroSection backendOnline={backendOnline} agentScore={agentScore} />
    }
  }

  return (
    <div className="flex h-screen overflow-hidden bg-elite-black selection:bg-elite-gold selection:text-black transition-colors duration-300">
      <Sidebar 
        currentView={currentView} 
        setCurrentView={setCurrentView} 
        userName={userName}
        userRank={userRank}
        backendOnline={backendOnline}
      />
      
      <main className="flex-1 flex flex-col h-screen overflow-hidden relative">
        <Navbar 
          balance={walletBalance} 
          userName={userName}
          backendOnline={backendOnline}
          walletAddress={walletAddress}
        />
        
        <div className="flex-1 overflow-y-auto p-4 md:p-8 scroll-smooth pb-20">
          <div className="max-w-7xl mx-auto animate-fade-in">
            {renderView()}
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
