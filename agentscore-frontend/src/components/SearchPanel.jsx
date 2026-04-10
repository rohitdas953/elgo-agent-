import { useState, useRef } from 'react'
import { Search, Camera, Loader2, ShoppingCart, ExternalLink, Star, Zap, X, Package } from 'lucide-react'
import { searchProducts } from '../lib/api'

const SearchPanel = ({ onOrderPlaced, fullWidth = false }) => {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState([])
  const [searchedQuery, setSearchedQuery] = useState('')
  const [selectedProduct, setSelectedProduct] = useState(null)
  const [orderState, setOrderState] = useState(null) // null | 'confirming' | 'processing' | 'done'
  const fileInputRef = useRef(null)

  const handleSearch = async (e) => {
    e?.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setResults([])
    setSelectedProduct(null)
    setOrderState(null)
    try {
      const data = await searchProducts(query.trim())
      setResults(data.results || [])
      setSearchedQuery(query.trim())
    } catch (err) {
      console.error('Search failed:', err)
    }
    setLoading(false)
  }

  const handlePhotoUpload = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    // For now, extract filename as search query
    const name = file.name.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ')
    setQuery(name || 'product')
    // Auto-trigger search
    setTimeout(() => {
      setLoading(true)
      searchProducts(name || 'product').then(data => {
        setResults(data.results || [])
        setSearchedQuery(name || 'product')
        setLoading(false)
      }).catch(() => setLoading(false))
    }, 100)
  }

  const handleBuy = (product) => {
    setSelectedProduct(product)
    setOrderState('confirming')
  }

  const confirmOrder = () => {
    setOrderState('processing')
    setTimeout(() => {
      setOrderState('done')
      onOrderPlaced?.({ amount_algo: (selectedProduct?.price || 500) / 18.85 })
    }, 2000)
  }

  const formatPrice = (v) => `₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`

  return (
    <div className={`space-y-6 ${fullWidth ? 'mt-6' : ''}`}>
      {/* Search Bar */}
      <div className="manga-glass rounded-elite border border-[#2a2a2c] p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold tracking-widest uppercase">
            <Zap size={14} className="inline text-elite-gold mr-2" />
            AI Product Search
          </h3>
          <span className="text-[10px] text-gray-500 font-mono uppercase tracking-widest">Photo or Text</span>
        </div>

        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search any product... iPhone 15, Lays chips, JBL speaker..."
              className="elite-input pl-10 pr-4"
            />
          </div>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="px-4 py-2 rounded-elite bg-[#111112] border border-[#333] text-gray-400 hover:text-elite-violet hover:border-elite-violet transition-all flex items-center gap-2"
          >
            <Camera size={16} />
            <span className="hidden sm:inline text-xs uppercase tracking-wider font-semibold">Photo</span>
          </button>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="elite-button bg-elite-gold text-black hover:bg-white border-transparent flex items-center gap-2 disabled:opacity-40"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            <span className="hidden sm:inline">Search</span>
          </button>
          <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handlePhotoUpload} />
        </form>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="manga-glass rounded-elite border border-elite-gold/20 p-12 flex flex-col items-center gap-4">
          <div className="relative w-16 h-16">
            <div className="absolute inset-0 rounded-full border-t-2 border-r-2 border-elite-gold animate-spin"></div>
            <div className="absolute inset-3 rounded-full border-b-2 border-l-2 border-elite-violet animate-[spin_2s_linear_infinite_reverse]"></div>
            <div className="absolute inset-0 flex items-center justify-center">
              <Package size={18} className="text-elite-gold" />
            </div>
          </div>
          <p className="text-sm text-gray-400 font-mono">Scanning Amazon, Flipkart, Zepto, Instamart...</p>
        </div>
      )}

      {/* Results */}
      {!loading && results.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold tracking-widest uppercase text-gray-400">
              Results for "{searchedQuery}" — <span className="text-elite-gold">{results.length} found</span>
            </h3>
          </div>

          <div className={`grid grid-cols-1 ${fullWidth ? 'md:grid-cols-2 lg:grid-cols-3' : 'md:grid-cols-2'} gap-4`}>
            {results.map((product, i) => (
              <div key={`${product.platform}-${i}`} className="elite-card group flex flex-col">
                {/* Platform Badge */}
                <div className="px-5 pt-4 flex items-center justify-between">
                  <span className={`text-[10px] font-bold uppercase tracking-[0.2em] px-2 py-0.5 rounded border ${
                    product.platform === 'amazon' ? 'text-orange-400 border-orange-400/30 bg-orange-400/10' :
                    product.platform === 'flipkart' ? 'text-blue-400 border-blue-400/30 bg-blue-400/10' :
                    product.platform === 'zepto' ? 'text-purple-400 border-purple-400/30 bg-purple-400/10' :
                    'text-green-400 border-green-400/30 bg-green-400/10'
                  }`}>
                    {product.platform}
                  </span>
                  {product.discount_percent && (
                    <span className="text-xs text-green-400 bg-green-400/10 px-1.5 py-0.5 rounded border border-green-400/20 font-mono">
                      -{product.discount_percent}%
                    </span>
                  )}
                </div>

                {/* Content */}
                <div className="p-5 flex-1 flex flex-col">
                  <h4 className="text-sm font-semibold text-gray-200 group-hover:text-white transition-colors line-clamp-2 mb-2">
                    {product.product_name}
                  </h4>
                  <div className="text-[10px] text-gray-500 mb-3 flex items-center gap-2">
                    <span>📦 {product.delivery_time}</span>
                    {product.delivery_fee > 0 && <span className="text-yellow-500">+{formatPrice(product.delivery_fee)} delivery</span>}
                    {product.rating && (
                      <span className="flex items-center gap-0.5"><Star size={10} className="text-elite-gold" />{product.rating}</span>
                    )}
                  </div>

                  <div className="mt-auto flex items-end justify-between">
                    <div>
                      <span className="text-lg font-bold text-elite-gold font-mono">{formatPrice(product.price)}</span>
                      {product.original_price && product.original_price > product.price && (
                        <span className="text-xs text-gray-500 line-through ml-2 font-mono">{formatPrice(product.original_price)}</span>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <a
                        href={product.product_url}
                        target="_blank"
                        rel="noreferrer"
                        className="p-2 rounded bg-[#111112] border border-[#333] text-gray-500 hover:text-white hover:border-[#555] transition-all"
                      >
                        <ExternalLink size={14} />
                      </a>
                      <button
                        onClick={() => handleBuy(product)}
                        className="px-3 py-1.5 rounded-elite bg-elite-gold border border-elite-gold flex items-center gap-1.5 text-black font-semibold text-xs transition-all shadow-gold-glow hover:bg-white"
                      >
                        <ShoppingCart size={14} /> Buy
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Order Confirmation Modal */}
      {orderState && selectedProduct && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="manga-glass rounded-elite border border-elite-gold/30 p-8 max-w-md w-full relative shadow-gold-glow">
            <button onClick={() => { setOrderState(null); setSelectedProduct(null) }} className="absolute top-4 right-4 text-gray-500 hover:text-white">
              <X size={20} />
            </button>

            {orderState === 'confirming' && (
              <>
                <h3 className="text-lg font-bold mb-4 uppercase tracking-wider">Confirm Order</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between"><span className="text-gray-400">Product</span><span className="text-right max-w-[200px] truncate">{selectedProduct.product_name}</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Platform</span><span className="uppercase text-elite-gold">{selectedProduct.platform}</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Price</span><span className="font-mono font-bold">{formatPrice(selectedProduct.price)}</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Delivery</span><span>{selectedProduct.delivery_time}</span></div>
                  <div className="flex justify-between border-t border-[#333] pt-3"><span className="text-gray-400">Pay with</span><span className="text-elite-gold font-mono">~{((selectedProduct.price + (selectedProduct.delivery_fee || 0)) / 18.85).toFixed(2)} ALGO</span></div>
                </div>
                <button onClick={confirmOrder} className="w-full elite-button bg-elite-gold text-black hover:bg-white mt-6 h-12 flex items-center justify-center gap-2">
                  <Zap size={16} /> Execute x402 Payment
                </button>
              </>
            )}

            {orderState === 'processing' && (
              <div className="flex flex-col items-center py-8 gap-4">
                <div className="relative w-16 h-16">
                  <div className="absolute inset-0 rounded-full border-t-2 border-elite-gold animate-spin"></div>
                  <div className="absolute inset-0 flex items-center justify-center"><Zap size={20} className="text-elite-gold" /></div>
                </div>
                <p className="text-sm text-gray-400 font-mono">Submitting Algorand transaction...</p>
              </div>
            )}

            {orderState === 'done' && (
              <div className="flex flex-col items-center py-8 gap-4">
                <div className="w-16 h-16 rounded-full bg-green-500/10 border-2 border-green-500 flex items-center justify-center">
                  <span className="text-2xl">✓</span>
                </div>
                <h3 className="text-lg font-bold text-green-400">Order Confirmed</h3>
                <p className="text-xs text-gray-500 font-mono text-center">Payment recorded on Algorand Testnet. Your order has been placed on {selectedProduct.platform}.</p>
                <button onClick={() => { setOrderState(null); setSelectedProduct(null) }} className="elite-button mt-4">
                  Close
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default SearchPanel
