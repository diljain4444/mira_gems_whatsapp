import React, { useState, useRef } from 'react'
import {
  ArrowLeft, Search, Copy, CheckCircle, AlertCircle,
  Loader2, Hash, ChevronDown, ChevronUp, MessageSquare, ExternalLink
} from 'lucide-react'
import { api } from '../../services/api'
import type { StoneLookupResponse, StoneDetail, DiamondMatch } from '../../types'

interface Props { onBack: () => void }

// ── Bulletproof clipboard writer with fallback ────────────────────────────────
export async function copyToClipboard(text: string): Promise<boolean> {
  if (!text) return false

  // Ensure iframe window has focus
  try {
    window.focus()
  } catch {}

  // 1. Try modern navigator.clipboard API
  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch (err) {
      console.warn('navigator.clipboard.writeText failed, trying fallback...', err)
    }
  }

  // 2. Fallback: temporary hidden textarea + document.execCommand('copy')
  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.top = '0'
    textarea.style.left = '0'
    textarea.style.width = '24px'
    textarea.style.height = '24px'
    textarea.style.padding = '0'
    textarea.style.border = 'none'
    textarea.style.outline = 'none'
    textarea.style.boxShadow = 'none'
    textarea.style.background = 'transparent'
    textarea.style.color = 'transparent'
    textarea.style.fontSize = '12px'
    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()
    textarea.setSelectionRange(0, textarea.value.length)
    const success = document.execCommand('copy')
    document.body.removeChild(textarea)
    if (success) return true
  } catch (err) {
    console.warn('execCommand fallback failed, sending to parent...', err)
  }

  // 3. Fallback for iframe context: delegate to parent window
  try {
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({ action: 'copyToClipboard', text }, '*')
      return true
    }
  } catch {
    /* ignore */
  }

  return false
}

// ── Normalize availability into standard display string ───────────────────────
export function normalizeAvailability(avail?: string | null): string {
  const upper = (avail || '').trim().toUpperCase()
  if (upper === 'A' || upper === 'AVAILABLE') return 'AVAILABLE'
  if (upper === 'M' || upper === 'MEMO') return 'MEMO'
  if (upper === 'H' || upper === 'HOLD') return 'HOLD'
  return upper || 'AVAILABLE'
}

// ── Format a stone into standard WhatsApp clipboard row ───────────────────────
// Format: B000218   AVAILABLE   ROUND   5.20   E   VS2   EX   EX   EX   NONE   Non   11.23 x 11.15 x 6.67
export function formatStoneForWhatsApp(stone: StoneDetail | DiamondMatch): string {
  const stockId = (stone.StockId || '').trim()
  const availability = normalizeAvailability(stone.Availability)
  const shape = (stone.Shape || '').trim()
  const carat = stone.Weight != null ? Number(stone.Weight).toFixed(2) : ''
  const color = (stone.Color || '').trim()
  const clarity = (stone.Clarity || '').trim()
  const cut = (stone.Cut || (shape.toUpperCase() === 'ROUND' ? 'EX' : '-')).trim()
  const polish = (stone.Polish || '').trim()
  const symm = (stone.Symm || '').trim()
  const lab = (stone.Lab || 'NONE').trim()
  const fls = (stone.Fls || 'Non').trim()
  const measurements = (stone.Measurements || '').trim()

  const parts = [
    stockId || '-',
    availability || 'AVAILABLE',
    shape || '-',
    carat || '-',
    color || '-',
    clarity || '-',
    cut || '-',
    polish || '-',
    symm || '-',
    lab || 'NONE',
    fls || 'Non',
    measurements || '-'
  ]

  return parts.join('   ')
}

// ── Availability badge ────────────────────────────────────────────────────────
const AVAIL_CONFIG: Record<string, { label: string; textCls: string; bgStyle: React.CSSProperties; borderStyle: React.CSSProperties }> = {
  AVAILABLE: {
    label: 'Available',
    textCls: 'text-available',
    bgStyle:     { background: 'rgba(76,175,80,0.10)' },
    borderStyle: { borderColor: 'rgba(76,175,80,0.30)' },
  },
  MEMO: {
    label: 'Memo',
    textCls: 'text-memo',
    bgStyle:     { background: 'rgba(255,152,0,0.10)' },
    borderStyle: { borderColor: 'rgba(255,152,0,0.30)' },
  },
  HOLD: {
    label: 'Hold',
    textCls: 'text-hold',
    bgStyle:     { background: 'rgba(244,67,54,0.10)' },
    borderStyle: { borderColor: 'rgba(244,67,54,0.30)' },
  },
}

function AvailBadge({ value }: { value: string }) {
  const cfg = AVAIL_CONFIG[value?.toUpperCase()] ?? {
    label: value || 'Unknown',
    textCls: 'text-muted',
    bgStyle: {},
    borderStyle: { borderColor: '#2A2A3F' },
  }
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${cfg.textCls}`}
      style={{ ...cfg.bgStyle, ...cfg.borderStyle }}
    >
      {cfg.label}
    </span>
  )
}

// ── WhatsApp Quick Copy Box (Multiple Stones, 1 per line) ─────────────────────
export function WhatsAppExportBox({ stones }: { stones: (StoneDetail | DiamondMatch)[] }) {
  const [copiedAll, setCopiedAll] = useState(false)
  const [showPreview, setShowPreview] = useState(true)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const text = stones.map(formatStoneForWhatsApp).join('\n')

  const copyAll = async () => {
    // Also select the textarea content visually
    if (textareaRef.current) {
      textareaRef.current.focus()
      textareaRef.current.select()
    }
    const ok = await copyToClipboard(text)
    if (ok) {
      setCopiedAll(true)
      setTimeout(() => setCopiedAll(false), 2200)
    } else {
      // Fallback: prompt user if browser security completely blocked clipboard
      try {
        window.prompt('Press Ctrl+C to copy diamond specifications:', text)
      } catch {}
      setCopiedAll(true)
      setTimeout(() => setCopiedAll(false), 2200)
    }
  }

  return (
    <div
      className="p-3 rounded-xl border space-y-2.5"
      style={{ background: '#12121A', borderColor: 'rgba(196,163,90,0.25)' }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <MessageSquare className="text-accent" style={{ width: 14, height: 14 }} />
          <span className="text-[12px] font-bold text-accent-light">
            WhatsApp Format ({stones.length} {stones.length === 1 ? 'Stone' : 'Stones'})
          </span>
        </div>
        <button
          onClick={() => setShowPreview(!showPreview)}
          className="text-[10px] text-muted hover:text-text transition-colors underline"
        >
          {showPreview ? 'Hide Preview' : 'Show Preview'}
        </button>
      </div>

      {showPreview && (
        <textarea
          ref={textareaRef}
          readOnly
          value={text}
          onClick={(e) => (e.currentTarget as HTMLTextAreaElement).select()}
          onFocus={(e) => (e.currentTarget as HTMLTextAreaElement).select()}
          rows={Math.min(stones.length + 1, 6)}
          className="w-full bg-bg border border-border rounded-lg p-2.5 text-[11px] font-mono text-text resize-none outline-none leading-relaxed cursor-pointer select-all focus:border-accent"
          title="Click to select all text"
        />
      )}

      <div className="flex gap-2">
        <button
          onClick={copyAll}
          className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-xs font-bold transition-all ${
            copiedAll
              ? 'bg-available/20 border border-available/40 text-available'
              : 'bg-accent hover:bg-accent/90 text-bg'
          }`}
        >
          {copiedAll ? (
            <>
              <CheckCircle style={{ width: 13, height: 13 }} className="text-available" />
              <span>Copied to Clipboard!</span>
            </>
          ) : (
            <>
              <Copy style={{ width: 13, height: 13 }} />
              <span>Copy for WhatsApp ({stones.length})</span>
            </>
          )}
        </button>

        <button
          onClick={() => window.open('https://web.whatsapp.com/', '_blank')}
          className="flex items-center justify-center gap-1 px-3 py-2 bg-surface2 hover:bg-border border border-border rounded-lg text-xs text-muted hover:text-text transition-colors"
          title="Open WhatsApp Web"
        >
          <ExternalLink style={{ width: 13, height: 13 }} />
          <span>WhatsApp Web</span>
        </button>
      </div>
      <p className="text-[9px] text-muted/65 text-center">
        Format: ID · Availability · Shape · Carat · Color · Clarity · Cut · Pol · Sym · Lab · Fls · Measurements
      </p>
    </div>
  )
}

// ── Stone card ────────────────────────────────────────────────────────────────
function StoneCard({ stone }: { stone: StoneDetail }) {
  const [copiedId, setCopiedId] = useState(false)
  const [copiedWa, setCopiedWa] = useState(false)
  const [expanded, setExpanded] = useState(true)

  const copyId = async () => {
    await copyToClipboard(stone.StockId)
    setCopiedId(true)
    setTimeout(() => setCopiedId(false), 1600)
  }

  const copyWhatsAppLine = async () => {
    const line = formatStoneForWhatsApp(stone)
    await copyToClipboard(line)
    setCopiedWa(true)
    setTimeout(() => setCopiedWa(false), 1600)
  }

  const rows: [string, string | number | null | undefined][] = [
    ['Shape',        stone.Shape],
    ['Carat',        stone.Weight != null ? stone.Weight.toFixed(2) : null],
    ['Color',        stone.Color],
    ['Clarity',      stone.Clarity],
    ['Cut',          stone.Cut],
    ['Polish',       stone.Polish],
    ['Symmetry',     stone.Symm],
    ['Category',     stone.business_category],
    ['Lab',          stone.Lab],
    ['Fluorescence', stone.Fls],
    ['Location',     stone.Location],
    ['Measurements', stone.Measurements],
    ['Stock Date',   stone.StockDate],
    ['Days',         stone.Days],
  ]

  return (
    <div className="bg-surface border border-border rounded-xl overflow-hidden">
      {/* Card header */}
      <div className="flex items-center justify-between px-3 py-2.5 bg-surface2 border-b border-border">
        <div className="flex items-center gap-2 min-w-0">
          <Hash className="text-accent flex-shrink-0" style={{ width: 14, height: 14 }} />
          <span className="text-[13px] font-bold text-accent-light font-mono truncate">
            {stone.StockId}
          </span>
          <AvailBadge value={stone.Availability} />
        </div>

        <div className="flex items-center gap-1.5 flex-shrink-0">
          {/* Copy WhatsApp line button */}
          <button
            onClick={copyWhatsAppLine}
            className="flex items-center gap-1 px-2 py-1 bg-accent/10 hover:bg-accent/20 border border-accent/25 rounded-lg text-[10px] font-semibold text-accent-light transition-colors"
            title="Copy row formatted for WhatsApp"
          >
            {copiedWa ? (
              <>
                <CheckCircle className="text-available" style={{ width: 11, height: 11 }} />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <MessageSquare style={{ width: 11, height: 11 }} />
                <span>WhatsApp</span>
              </>
            )}
          </button>

          {/* Copy ID only button */}
          <button
            onClick={copyId}
            className="p-1.5 hover:bg-border rounded-lg transition-colors"
            title="Copy Stock ID only"
          >
            {copiedId
              ? <CheckCircle className="text-available" style={{ width: 13, height: 13 }} />
              : <Copy className="text-muted" style={{ width: 13, height: 13 }} />
            }
          </button>

          {/* Expand/Collapse */}
          <button
            onClick={() => setExpanded(e => !e)}
            className="p-1.5 hover:bg-border rounded-lg transition-colors"
          >
            {expanded
              ? <ChevronUp   className="text-muted" style={{ width: 13, height: 13 }} />
              : <ChevronDown className="text-muted" style={{ width: 13, height: 13 }} />
            }
          </button>
        </div>
      </div>

      {/* Fields */}
      {expanded && (
        <div className="p-3">
          <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
            {rows.map(([label, value]) =>
              value !== null && value !== undefined && value !== '' ? (
                <div key={label as string}>
                  <p className="text-[9px] text-muted uppercase tracking-wide leading-none">{label}</p>
                  <p className="text-[11px] text-text font-medium mt-0.5 leading-snug">{String(value)}</p>
                </div>
              ) : null
            )}
          </div>

          {stone.FinalPrice != null && (
            <div className="mt-3 pt-2.5 border-t border-border">
              <p className="text-[9px] text-muted uppercase tracking-wide">Final Price</p>
              <p className="text-base font-bold text-accent mt-0.5">
                ${stone.FinalPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main screen ───────────────────────────────────────────────────────────────
export default function StoneById({ onBack }: Props) {
  const [input, setInput]     = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)
  const [result, setResult]   = useState<StoneLookupResponse | null>(null)

  const handleSearch = async () => {
    if (!input.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await api.lookupStones(input)
      setResult(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Search failed. Check backend connection.')
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleSearch()
  }

  return (
    <div className="flex flex-col h-full">

      {/* Top bar */}
      <div className="flex-shrink-0 flex items-center gap-3 px-4 py-3 border-b border-border bg-surface">
        <button onClick={onBack} className="p-1.5 hover:bg-surface2 rounded-lg transition-colors">
          <ArrowLeft className="text-muted" style={{ width: 16, height: 16 }} />
        </button>
        <div>
          <h2 className="text-[13px] font-bold text-text">Find Stone by ID</h2>
          <p className="text-[10px] text-muted">Enter one or multiple Stock IDs</p>
        </div>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">

        {/* Input area */}
        <div className="space-y-2">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder={"B000216\nB000217\nB000218\n\nor comma/space/semicolon separated:\nB000216, B000217; B000218"}
            className="w-full h-28 bg-surface border border-border focus:border-accent/50 rounded-xl px-3 py-2.5 text-xs text-text placeholder-muted/40 resize-none outline-none transition-colors font-mono"
            style={{ caretColor: '#C4A35A' }}
          />
          <div className="flex items-center justify-between gap-2">
            <p className="text-[9px] text-muted leading-snug">
              Supports newline · comma · semicolon · space
              <br />Ctrl+Enter to search
            </p>
            <button
              onClick={handleSearch}
              disabled={loading || !input.trim()}
              className="flex items-center gap-1.5 px-4 py-2 bg-accent hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed text-bg text-xs font-bold rounded-lg transition-all flex-shrink-0"
            >
              {loading
                ? <Loader2 className="animate-spin" style={{ width: 13, height: 13 }} />
                : <Search style={{ width: 13, height: 13 }} />
              }
              {loading ? 'Searching…' : 'Search'}
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div
            className="flex items-start gap-2 p-3 rounded-xl border text-hold text-xs"
            style={{ background: 'rgba(244,67,54,0.06)', borderColor: 'rgba(244,67,54,0.25)' }}
          >
            <AlertCircle className="flex-shrink-0 mt-0.5 text-hold" style={{ width: 15, height: 15 }} />
            <div>
              <p className="font-semibold">Search Error</p>
              <p className="text-muted mt-0.5 text-[11px]">{error}</p>
            </div>
          </div>
        )}

        {/* Summary stats */}
        {result && (
          <>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Requested',  value: result.unique_requested, color: 'text-text'       },
                { label: 'Found',      value: result.total_found,      color: 'text-available'  },
                { label: 'Not Found',  value: result.total_not_found,  color: result.total_not_found  > 0 ? 'text-hold' : 'text-muted' },
                { label: 'Duplicates', value: result.total_duplicates, color: result.total_duplicates > 0 ? 'text-memo' : 'text-muted' },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-surface border border-border rounded-xl p-3 text-center">
                  <p className={`text-2xl font-bold ${color}`}>{value}</p>
                  <p className="text-[10px] text-muted mt-0.5">{label}</p>
                </div>
              ))}
            </div>

            {/* Not found */}
            {result.not_found.length > 0 && (
              <div
                className="p-3 rounded-xl border"
                style={{ background: 'rgba(244,67,54,0.04)', borderColor: 'rgba(244,67,54,0.20)' }}
              >
                <p className="text-[9px] text-hold font-bold uppercase tracking-wider mb-2">Not Found</p>
                <div className="flex flex-wrap gap-1.5">
                  {result.not_found.map(id => (
                    <span
                      key={id}
                      className="px-2 py-0.5 rounded text-[10px] font-mono text-hold border"
                      style={{ background: 'rgba(244,67,54,0.08)', borderColor: 'rgba(244,67,54,0.25)' }}
                    >
                      {id}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Duplicates in inventory */}
            {result.duplicates.length > 0 && (
              <div
                className="p-3 rounded-xl border"
                style={{ background: 'rgba(255,152,0,0.04)', borderColor: 'rgba(255,152,0,0.20)' }}
              >
                <p className="text-[9px] text-memo font-bold uppercase tracking-wider mb-2">
                  Duplicate in Inventory
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {result.duplicates.map(id => (
                    <span
                      key={id}
                      className="px-2 py-0.5 rounded text-[10px] font-mono text-memo border"
                      style={{ background: 'rgba(255,152,0,0.08)', borderColor: 'rgba(255,152,0,0.25)' }}
                    >
                      {id}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* WhatsApp Export Box for all matched stones */}
            {result.matched_stones.length > 0 && (
              <WhatsAppExportBox stones={result.matched_stones} />
            )}

            {/* Stone cards */}
            {result.matched_stones.length > 0 && (
              <div className="space-y-3">
                <p className="text-[11px] font-medium text-muted">
                  {result.matched_stones.length} Stone Detail Card{result.matched_stones.length !== 1 ? 's' : ''}
                </p>
                {result.matched_stones.map(stone => (
                  <StoneCard key={stone.StockId} stone={stone} />
                ))}
              </div>
            )}

            {result.matched_stones.length === 0 && result.not_found.length === 0 && (
              <p className="text-center text-xs text-muted py-8">No results found.</p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
