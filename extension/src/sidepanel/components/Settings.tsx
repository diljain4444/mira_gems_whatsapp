import React, { useState, useEffect } from 'react'
import { ArrowLeft, Server, Info, Terminal, User, Check } from 'lucide-react'

interface Props { onBack: () => void }

export default function Settings({ onBack }: Props) {
  const [sellerName, setSellerName] = useState('')
  const [savedBadge, setSavedBadge] = useState(false)

  useEffect(() => {
    const saved = localStorage.getItem('mira_seller_name') || ''
    setSellerName(saved)
  }, [])

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    setSellerName(val)
    localStorage.setItem('mira_seller_name', val.trim())
    setSavedBadge(true)
    setTimeout(() => setSavedBadge(false), 2000)
  }

  return (
    <div className="flex flex-col h-full">

      {/* Top bar */}
      <div className="flex-shrink-0 flex items-center gap-3 px-4 py-3 border-b border-border bg-surface">
        <button onClick={onBack} className="p-1.5 hover:bg-surface2 rounded-lg transition-colors">
          <ArrowLeft className="text-muted" style={{ width: 16, height: 16 }} />
        </button>
        <h2 className="text-[13px] font-bold text-text">Settings</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">

        {/* ── Seller Identity ─────────────────────────────────────────────── */}
        <div className="p-4 bg-surface border border-accent/25 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <User className="text-accent" style={{ width: 15, height: 15 }} />
              <p className="text-[12px] font-semibold text-text">Salesperson Profile</p>
            </div>
            {savedBadge && (
              <span className="flex items-center gap-1 text-[10px] text-available font-medium">
                <Check style={{ width: 12, height: 12 }} /> Saved
              </span>
            )}
          </div>

          <p className="text-[11px] text-muted leading-relaxed">
            Every lead you save will automatically be attributed to your name in the central database.
          </p>

          <div>
            <label className="text-[9px] text-muted uppercase tracking-wider font-semibold block mb-1">
              Your Name / Seller ID
            </label>
            <input
              type="text"
              value={sellerName}
              onChange={handleNameChange}
              placeholder="e.g. Ramesh, Priya, Seller 1"
              className="w-full bg-bg border border-border focus:border-accent rounded-lg px-3 py-2 text-[12px] text-text placeholder-muted outline-none transition-colors"
            />
          </div>

          {sellerName && (
            <p className="text-[10px] text-accent/80 font-medium">
              ✓ Active: Saving as &ldquo;{sellerName}&rdquo;
            </p>
          )}
        </div>

        {/* Backend connection */}
        <div className="p-4 bg-surface border border-border rounded-xl space-y-3">
          <div className="flex items-center gap-2">
            <Server className="text-accent" style={{ width: 15, height: 15 }} />
            <p className="text-[12px] font-semibold text-text">Backend Connection</p>
          </div>

          <div>
            <p className="text-[9px] text-muted uppercase tracking-wide">API Endpoint</p>
            <code className="text-[12px] text-accent-light font-mono">http://localhost:8000</code>
          </div>

          <div>
            <p className="text-[9px] text-muted uppercase tracking-wide mb-1">Health Check</p>
            <code className="text-[11px] text-muted font-mono">GET /health</code>
          </div>
        </div>

        {/* Start commands */}
        <div className="p-4 bg-surface border border-border rounded-xl space-y-3">
          <div className="flex items-center gap-2">
            <Terminal className="text-accent" style={{ width: 15, height: 15 }} />
            <p className="text-[12px] font-semibold text-text">Starting the Backend</p>
          </div>

          <div className="space-y-1.5">
            <p className="text-[10px] text-muted">Navigate to the backend folder:</p>
            <div className="bg-bg rounded-lg p-2.5 border border-border">
              <code className="text-[10px] text-available font-mono">
                cd mira-companion/backend
              </code>
            </div>
          </div>

          <div className="space-y-1.5">
            <p className="text-[10px] text-muted">Start the server:</p>
            <div className="bg-bg rounded-lg p-2.5 border border-border">
              <code className="text-[10px] text-available font-mono">
                uvicorn app.main:app --reload --port 8000
              </code>
            </div>
          </div>

          <div className="space-y-1.5">
            <p className="text-[10px] text-muted">Install dependencies (first time only):</p>
            <div className="bg-bg rounded-lg p-2.5 border border-border">
              <code className="text-[10px] text-available font-mono">
                pip install -r requirements.txt
              </code>
            </div>
          </div>
        </div>

        {/* About */}
        <div className="p-4 bg-surface border border-border rounded-xl space-y-2">
          <div className="flex items-center gap-2">
            <Info className="text-accent" style={{ width: 15, height: 15 }} />
            <p className="text-[12px] font-semibold text-text">About</p>
          </div>
          <div className="space-y-1 text-[10px] text-muted leading-relaxed">
            <p className="font-semibold text-text">MIRA COMPANION v1.0.0</p>
            <p>Internal diamond business assistant for Mira Gems</p>
            <div className="mt-2 space-y-0.5">
              <p>✓ Find Stone by ID</p>
              <p>✓ Find Stone by Demand</p>
              <p>✓ Excel Report Generation</p>
              <p>✓ Manual WhatsApp Sharing</p>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
