import React, { useState } from 'react'
import {
  ArrowLeft, Sparkles, Loader2, AlertCircle,
  FileSpreadsheet, Download, CheckCircle, ExternalLink,
  ChevronDown, ChevronUp, MessageSquare, Copy, Lightbulb,
} from 'lucide-react'
import { api } from '../../services/api'
import type {
  DemandSearchResponse, DiamondMatch, ExtractedRequirement, SimilarDiamondMatch,
} from '../../types'
import { formatStoneForWhatsApp, copyToClipboard, WhatsAppExportBox } from './StoneById'

interface Props { onBack: () => void }

// ── Extracted requirement display ─────────────────────────────────────────────
function ReqTag({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (value === null || value === undefined || value === '' || value === '—') return null
  const display = Array.isArray(value) ? (value as string[]).join(', ') : String(value)
  if (!display) return null
  return (
    <div
      className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border"
      style={{ background: 'rgba(196,163,90,0.08)', borderColor: 'rgba(196,163,90,0.22)' }}
    >
      <span className="text-[9px] text-muted uppercase tracking-wide">{label}</span>
      <span className="text-[11px] font-semibold text-accent-light">{display}</span>
    </div>
  )
}

function ExtractedReqPanel({ req }: { req: ExtractedRequirement }) {
  const colorDisplay   = Array.isArray(req.color)   ? req.color.join(', ')   : req.color
  const clarityDisplay = Array.isArray(req.clarity) ? req.clarity.join(', ') : req.clarity

  let caratDisplay: string | null = null
  if (req.carat_min !== null && req.carat_max !== null) {
    caratDisplay = req.carat_min === req.carat_max
      ? `${req.carat_min} ct`
      : `${req.carat_min} – ${req.carat_max} ct`
  } else if (req.carat_min !== null) {
    caratDisplay = `≥ ${req.carat_min} ct`
  } else if (req.carat_max !== null) {
    caratDisplay = `≤ ${req.carat_max} ct`
  }

  const hasAny = req.shape || colorDisplay || clarityDisplay || caratDisplay ||
    req.business_category || req.certification || req.fluorescence

  return (
    <div
      className="p-3 rounded-xl border"
      style={{ background: '#12121A', borderColor: 'rgba(196,163,90,0.20)' }}
    >
      <p className="text-[10px] text-accent font-bold uppercase tracking-wider mb-2">
        Extracted Requirements
      </p>
      {hasAny ? (
        <div className="flex flex-wrap gap-1.5">
          <ReqTag label="Shape"    value={req.shape}             />
          <ReqTag label="Color"    value={colorDisplay}          />
          <ReqTag label="Clarity"  value={clarityDisplay}        />
          <ReqTag label="Carat"    value={caratDisplay}          />
          <ReqTag label="Category" value={req.business_category} />
          <ReqTag label="Lab"      value={req.certification}     />
          <ReqTag label="Fls"      value={req.fluorescence}      />
        </div>
      ) : (
        <p className="text-[11px] text-muted">
          No specific requirements extracted — will match all available diamonds.
        </p>
      )}
    </div>
  )
}

// ── Diamond match card ────────────────────────────────────────────────────────
function MatchCard({ diamond }: { diamond: DiamondMatch }) {
  const [expanded, setExpanded] = useState(false)
  const [copiedWa, setCopiedWa] = useState(false)
  const [copiedId, setCopiedId] = useState(false)

  const copyId = async () => {
    await copyToClipboard(diamond.StockId)
    setCopiedId(true)
    setTimeout(() => setCopiedId(false), 1600)
  }

  const copyWhatsAppLine = async () => {
    const line = formatStoneForWhatsApp(diamond)
    await copyToClipboard(line)
    setCopiedWa(true)
    setTimeout(() => setCopiedWa(false), 1600)
  }

  const avail = diamond.Availability?.toUpperCase()
  const availCls =
    avail === 'AVAILABLE' || avail === 'A' ? 'text-available'
    : avail === 'MEMO'    || avail === 'M' ? 'text-memo'
    : 'text-hold'

  const fields: [string, string | number | null | undefined][] = [
    ['Cut',          diamond.Cut],
    ['Polish',       diamond.Polish],
    ['Symmetry',     diamond.Symm],
    ['Lab',          diamond.Lab],
    ['Fluorescence', diamond.Fls],
    ['Location',     diamond.Location],
    ['Measurements', diamond.Measurements],
  ]

  return (
    <div className="bg-surface border border-border rounded-xl overflow-hidden">
      {/* Compact header — always visible */}
      <div className="flex items-center justify-between px-3 py-2.5 bg-surface2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[12px] font-bold font-mono text-accent-light truncate">
            {diamond.StockId}
          </span>
          {diamond.business_category && (
            <span
              className="px-1.5 py-0.5 rounded text-[9px] font-bold text-accent border flex-shrink-0"
              style={{ background: 'rgba(196,163,90,0.12)', borderColor: 'rgba(196,163,90,0.25)' }}
            >
              {diamond.business_category}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <span className={`text-[10px] font-semibold mr-1 ${availCls}`}>
            {avail === 'A' ? 'Available' : diamond.Availability}
          </span>

          {/* Copy WhatsApp line button */}
          <button
            onClick={copyWhatsAppLine}
            className="flex items-center gap-1 px-2 py-1 bg-accent/10 hover:bg-accent/20 border border-accent/25 rounded-lg text-[10px] font-semibold text-accent-light transition-colors"
            title="Copy row formatted for WhatsApp with Availability"
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

          <button onClick={() => setExpanded(e => !e)} className="p-1 hover:bg-border rounded transition-colors">
            {expanded
              ? <ChevronUp   className="text-muted" style={{ width: 13, height: 13 }} />
              : <ChevronDown className="text-muted" style={{ width: 13, height: 13 }} />
            }
          </button>
        </div>
      </div>

      {/* Always-visible summary row */}
      <div className="px-3 py-2 grid grid-cols-4 gap-x-2 border-b border-border">
        {[
          ['Shape',   diamond.Shape],
          ['Carat',   diamond.Weight != null ? diamond.Weight.toFixed(2) : null],
          ['Color',   diamond.Color],
          ['Clarity', diamond.Clarity],
        ].map(([l, v]) => v ? (
          <div key={l as string}>
            <p className="text-[8px] text-muted uppercase">{l}</p>
            <p className="text-[11px] text-text font-semibold">{v}</p>
          </div>
        ) : null)}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-3 py-2.5">
          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            {fields.map(([l, v]) => v ? (
              <div key={l as string}>
                <p className="text-[8px] text-muted uppercase tracking-wide">{l}</p>
                <p className="text-[11px] text-text font-medium mt-0.5">{String(v)}</p>
              </div>
            ) : null)}
          </div>
          {diamond.FinalPrice != null && (
            <div className="mt-2.5 pt-2 border-t border-border">
              <p className="text-[9px] text-muted uppercase">Final Price</p>
              <p className="text-[15px] font-bold text-accent mt-0.5">
                ${diamond.FinalPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Similar alternatives — WhatsApp clipboard ─────────────────────────────────

/**
 * Format one similar diamond as a WhatsApp line WITH a reason prefix.
 * Example:
 *   (Better →Color D, Clarity VVS1)M044494  AVAILABLE  ROUND  1.10  D  VVS1 ...
 *   (Lower →Carat 9.80ct -2.0%)M045158  AVAILABLE  ROUND  9.80  F  VS2 ...
 */
function formatSimilarForWhatsApp(diamond: SimilarDiamondMatch): string {
  const stoneLine = formatStoneForWhatsApp(diamond)

  if (!diamond.diff_tags || diamond.diff_tags.length === 0) {
    return stoneLine
  }

  // Classify each tag: contains "(better)" → Better group; "(lower)" → Lower group;
  // others (Fls, Lab, Category, Carat%) → put in whichever group, default Lower.
  const betterParts: string[] = []
  const lowerParts: string[] = []

  for (const tag of diamond.diff_tags) {
    const lower = tag.toLowerCase()
    if (lower.includes('(better)')) {
      // e.g. "Color: D (better)" → "Color D"
      betterParts.push(tag.replace(/\s*\(better\)/i, '').replace(/:\s*/, ' ').trim())
    } else if (lower.includes('(lower)')) {
      lowerParts.push(tag.replace(/\s*\(lower\)/i, '').replace(/:\s*/, ' ').trim())
    } else {
      // Carat %, Fls, Lab, Category — treat as lower/note
      lowerParts.push(tag.replace(/:\s*/, ' ').trim())
    }
  }

  const parts: string[] = []
  if (betterParts.length > 0) parts.push('Better \u2192' + betterParts.join(', '))
  if (lowerParts.length  > 0) parts.push('Lower \u2192'  + lowerParts.join(', '))

  const prefix = parts.length > 0 ? `(${parts.join(' | ')})` : ''
  return prefix ? `${stoneLine}  ${prefix}` : stoneLine
}

/** WhatsApp clipboard box specifically for the similar-alternatives section */
function SimilarAlternativesWhatsAppBox({ stones }: { stones: SimilarDiamondMatch[] }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    const text = stones.map(formatSimilarForWhatsApp).join('\n')
    await copyToClipboard(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div
      className="p-3 rounded-xl border space-y-2"
      style={{ background: 'rgba(196,163,90,0.06)', borderColor: 'rgba(196,163,90,0.28)' }}
    >
      <div className="flex items-center gap-2">
        <MessageSquare className="text-accent" style={{ width: 13, height: 13 }} />
        <p className="text-[11px] font-semibold text-accent-light">Share Alternatives via WhatsApp</p>
      </div>
      <p className="text-[9px] text-muted leading-snug">
        Each line ends with the reason it differs from your demand
        (e.g. <span className="text-accent-light font-mono">(Better →Color D)</span> or <span className="text-accent-light font-mono">(Lower →Carat 9.80ct -2.0%)</span>).
        Copy all and paste into WhatsApp.
      </p>

      {/* Preview — first 3 lines */}
      <div
        className="rounded-lg px-2.5 py-2 space-y-1 overflow-hidden"
        style={{ background: 'rgba(0,0,0,0.25)', maxHeight: 72 }}
      >
        {stones.slice(0, 3).map((d, i) => (
          <p key={i} className="text-[9px] font-mono text-muted truncate">
            {formatSimilarForWhatsApp(d)}
          </p>
        ))}
        {stones.length > 3 && (
          <p className="text-[9px] text-muted/50 italic">+{stones.length - 3} more…</p>
        )}
      </div>

      <button
        onClick={handleCopy}
        className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg text-[11px] font-semibold transition-colors"
        style={copied
          ? { background: 'rgba(76,175,80,0.12)', color: '#4CAF50', border: '1px solid rgba(76,175,80,0.35)' }
          : { background: 'rgba(196,163,90,0.10)', color: '#C4A35A', border: '1px solid rgba(196,163,90,0.30)' }
        }
      >
        {copied
          ? <><CheckCircle style={{ width: 12, height: 12 }} /> Copied to clipboard!</>
          : <><Copy style={{ width: 12, height: 12 }} /> Copy all alternatives for WhatsApp</>
        }
      </button>
    </div>
  )
}

// ── Similar alternative card ──────────────────────────────────────────────────
function SimilarCard({ diamond }: { diamond: SimilarDiamondMatch }) {
  const [expanded, setExpanded] = useState(false)
  const [copiedWa, setCopiedWa] = useState(false)
  const [copiedId, setCopiedId] = useState(false)

  const copyId = async () => {
    await copyToClipboard(diamond.StockId)
    setCopiedId(true)
    setTimeout(() => setCopiedId(false), 1600)
  }

  const copyWhatsAppLine = async () => {
    const line = formatSimilarForWhatsApp(diamond)
    await copyToClipboard(line)
    setCopiedWa(true)
    setTimeout(() => setCopiedWa(false), 1600)
  }

  const avail = diamond.Availability?.toUpperCase()
  const availCls =
    avail === 'AVAILABLE' || avail === 'A' ? 'text-available'
    : avail === 'MEMO'    || avail === 'M' ? 'text-memo'
    : 'text-hold'

  const fields: [string, string | number | null | undefined][] = [
    ['Cut',          diamond.Cut],
    ['Polish',       diamond.Polish],
    ['Symmetry',     diamond.Symm],
    ['Lab',          diamond.Lab],
    ['Fluorescence', diamond.Fls],
    ['Location',     diamond.Location],
    ['Measurements', diamond.Measurements],
  ]

  return (
    <div className="bg-surface border border-border rounded-xl overflow-hidden" style={{ borderColor: 'rgba(196,163,90,0.30)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2.5 bg-surface2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[12px] font-bold font-mono text-accent-light truncate">
            {diamond.StockId}
          </span>
          {diamond.business_category && (
            <span
              className="px-1.5 py-0.5 rounded text-[9px] font-bold text-accent border flex-shrink-0"
              style={{ background: 'rgba(196,163,90,0.12)', borderColor: 'rgba(196,163,90,0.25)' }}
            >
              {diamond.business_category}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <span className={`text-[10px] font-semibold mr-1 ${availCls}`}>
            {avail === 'A' ? 'Available' : diamond.Availability}
          </span>
          <button
            onClick={copyWhatsAppLine}
            className="flex items-center gap-1 px-2 py-1 bg-accent/10 hover:bg-accent/20 border border-accent/25 rounded-lg text-[10px] font-semibold text-accent-light transition-colors"
            title="Copy row formatted for WhatsApp"
          >
            {copiedWa ? (
              <><CheckCircle className="text-available" style={{ width: 11, height: 11 }} /><span>Copied!</span></>
            ) : (
              <><MessageSquare style={{ width: 11, height: 11 }} /><span>WhatsApp</span></>
            )}
          </button>
          <button onClick={copyId} className="p-1.5 hover:bg-border rounded-lg transition-colors" title="Copy Stock ID">
            {copiedId
              ? <CheckCircle className="text-available" style={{ width: 13, height: 13 }} />
              : <Copy className="text-muted" style={{ width: 13, height: 13 }} />
            }
          </button>
          <button onClick={() => setExpanded(e => !e)} className="p-1 hover:bg-border rounded transition-colors">
            {expanded
              ? <ChevronUp   className="text-muted" style={{ width: 13, height: 13 }} />
              : <ChevronDown className="text-muted" style={{ width: 13, height: 13 }} />
            }
          </button>
        </div>
      </div>

      {/* Core specs */}
      <div className="px-3 py-2 grid grid-cols-4 gap-x-2 border-b border-border">
        {[
          ['Shape',   diamond.Shape],
          ['Carat',   diamond.Weight != null ? diamond.Weight.toFixed(2) : null],
          ['Color',   diamond.Color],
          ['Clarity', diamond.Clarity],
        ].map(([l, v]) => v ? (
          <div key={l as string}>
            <p className="text-[8px] text-muted uppercase">{l}</p>
            <p className="text-[11px] text-text font-semibold">{v}</p>
          </div>
        ) : null)}
      </div>

      {/* Diff tags — always visible */}
      {diamond.diff_tags && diamond.diff_tags.length > 0 && (
        <div className="px-3 py-2 flex flex-wrap gap-1 border-b border-border">
          {diamond.diff_tags.map((tag, i) => (
            <span
              key={i}
              className="px-2 py-0.5 rounded-full text-[9px] font-semibold"
              style={{ background: 'rgba(196,163,90,0.13)', color: '#C4A35A', border: '1px solid rgba(196,163,90,0.28)' }}
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Expanded detail */}
      {expanded && (
        <div className="px-3 py-2.5">
          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            {fields.map(([l, v]) => v ? (
              <div key={l as string}>
                <p className="text-[8px] text-muted uppercase tracking-wide">{l}</p>
                <p className="text-[11px] text-text font-medium mt-0.5">{String(v)}</p>
              </div>
            ) : null)}
          </div>
          {diamond.FinalPrice != null && (
            <div className="mt-2.5 pt-2 border-t border-border">
              <p className="text-[9px] text-muted uppercase">Final Price</p>
              <p className="text-[15px] font-bold text-accent mt-0.5">
                ${diamond.FinalPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main screen ───────────────────────────────────────────────────────────────
export default function StoneByDemand({ onBack }: Props) {
  const [message,       setMessage]       = useState('')
  const [loading,       setLoading]       = useState(false)
  const [reportLoading, setReportLoading] = useState(false)
  const [error,         setError]         = useState<string | null>(null)
  const [result,        setResult]        = useState<DemandSearchResponse | null>(null)
  const [reportId,      setReportId]      = useState<string | null>(null)
  const [reportFilename,setReportFilename]= useState('')
  const [customerPhone, setCustomerPhone] = useState('')

  const handleSearch = async () => {
    if (!message.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    setReportId(null)
    try {
      const data = await api.searchByDemand(message)
      setResult(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Search failed.')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateExcel = async () => {
    if (!result) return
    setReportLoading(true)
    setError(null)
    try {
      const report = await api.generateReport({
        customer_message: result.customer_message,
        extracted_requirement: result.extracted_requirement,
        matched_diamonds: result.matched_diamonds,
        total_inventory: result.total_inventory,
        total_available: result.total_available,
        total_matched: result.total_matched,
        total_available_not_matched: result.total_available_not_matched,
      })
      setReportId(report.report_id)
      setReportFilename(report.filename)
    } catch (e: unknown) {
      setError(`Excel generation failed: ${e instanceof Error ? e.message : 'Unknown error'}`)
    } finally {
      setReportLoading(false)
    }
  }

  const handleDownload = () => {
    if (!reportId) return
    const url = api.getReportDownloadUrl(reportId)
    const a = document.createElement('a')
    a.href = url
    a.download = reportFilename || 'mira_gems_report.xlsx'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  const handleWhatsApp = async () => {
    if (result && result.matched_diamonds.length > 0) {
      const text = result.matched_diamonds.map(formatStoneForWhatsApp).join('\n')
      await copyToClipboard(text)
    }
    const digits = customerPhone.replace(/\D/g, '')
    const textParam = result && result.matched_diamonds.length > 0
      ? encodeURIComponent(result.matched_diamonds.map(formatStoneForWhatsApp).join('\n'))
      : ''
    const url = digits
      ? `https://web.whatsapp.com/send?phone=${digits}${textParam ? `&text=${textParam}` : ''}`
      : 'https://web.whatsapp.com/'
    window.open(url, '_blank')
  }

  return (
    <div className="flex flex-col h-full">

      {/* Top bar */}
      <div className="flex-shrink-0 flex items-center gap-3 px-4 py-3 border-b border-border bg-surface">
        <button onClick={onBack} className="p-1.5 hover:bg-surface2 rounded-lg transition-colors">
          <ArrowLeft className="text-muted" style={{ width: 16, height: 16 }} />
        </button>
        <div>
          <h2 className="text-[13px] font-bold text-text">Find Stone by Demand</h2>
          <p className="text-[10px] text-muted">AI-powered extraction & matching</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">

        {/* Customer message input */}
        <div className="space-y-2">
          <label className="text-[10px] text-muted uppercase tracking-wider font-medium">
            Customer Requirement
          </label>
          <textarea
            value={message}
            onChange={e => setMessage(e.target.value)}
            placeholder={"VS-SI D/E/G 3ct EX EX VG\n\nor\n\n2.6ct round E VS1 3EX IGI\n\nor\n\nNeed 1.00–1.10 oval D-F VVS-VS non certi"}
            className="w-full h-28 bg-surface border border-border focus:border-accent/50 rounded-xl px-3 py-2.5 text-xs text-text placeholder-muted/40 resize-none outline-none transition-colors"
            style={{ caretColor: '#C4A35A' }}
          />
          <button
            onClick={handleSearch}
            disabled={loading || !message.trim()}
            className="w-full flex items-center justify-center gap-2 py-2.5 bg-accent hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed text-bg text-[13px] font-bold rounded-xl transition-all"
          >
            {loading
              ? <><Loader2 className="animate-spin" style={{ width: 14, height: 14 }} />Extracting &amp; Matching…</>
              : <><Sparkles style={{ width: 14, height: 14 }} />Find Matching Diamonds</>
            }
          </button>
        </div>

        {/* Error */}
        {error && (
          <div
            className="flex items-start gap-2 p-3 rounded-xl border"
            style={{ background: 'rgba(244,67,54,0.06)', borderColor: 'rgba(244,67,54,0.25)' }}
          >
            <AlertCircle className="text-hold flex-shrink-0 mt-0.5" style={{ width: 15, height: 15 }} />
            <div>
              <p className="text-xs font-semibold text-hold">Error</p>
              <p className="text-[11px] text-muted mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* Results */}
        {result && (
          <>
            {/* Extracted requirement */}
            <ExtractedReqPanel req={result.extracted_requirement} />

            {/* Stats grid */}
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Total Inventory', value: result.total_inventory.toLocaleString(), color: 'text-text' },
                { label: 'Available',       value: result.total_available.toLocaleString(), color: 'text-text' },
                { label: 'Matched',         value: result.total_matched.toLocaleString(),   color: result.total_matched > 0 ? 'text-available' : 'text-muted' },
                { label: 'Not Matched',     value: result.total_available_not_matched.toLocaleString(), color: 'text-muted' },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-surface border border-border rounded-xl p-3 text-center">
                  <p className={`text-xl font-bold ${color}`}>{value}</p>
                  <p className="text-[10px] text-muted mt-0.5">{label}</p>
                </div>
              ))}
            </div>

            {/* Excel + WhatsApp section */}
            {result.total_matched > 0 && (
              <div className="p-3 bg-surface border border-border rounded-xl space-y-3">
                {/* Excel header */}
                <div className="flex items-center gap-2">
                  <FileSpreadsheet className="text-accent" style={{ width: 14, height: 14 }} />
                  <p className="text-[12px] font-semibold text-text">Excel Report</p>
                </div>

                {/* Generate / Download */}
                {!reportId ? (
                  <button
                    onClick={handleGenerateExcel}
                    disabled={reportLoading}
                    className="w-full flex items-center justify-center gap-1.5 py-2 bg-surface2 hover:bg-border border border-border hover:border-accent/30 rounded-lg text-xs text-text transition-colors"
                  >
                    {reportLoading
                      ? <><Loader2 className="animate-spin" style={{ width: 13, height: 13 }} />Generating…</>
                      : <><FileSpreadsheet style={{ width: 13, height: 13 }} className="text-accent" />Generate Excel Report</>
                    }
                  </button>
                ) : (
                  <div className="space-y-2">
                    <div className="flex items-center gap-1.5 text-[11px] text-available">
                      <CheckCircle style={{ width: 13, height: 13 }} />
                      Report ready · {reportFilename}
                    </div>
                    <button
                      onClick={handleDownload}
                      className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold text-available border transition-colors"
                      style={{ background: 'rgba(76,175,80,0.08)', borderColor: 'rgba(76,175,80,0.30)' }}
                    >
                      <Download style={{ width: 13, height: 13 }} />
                      Download Excel
                    </button>
                  </div>
                )}

                {/* WhatsApp manual sharing */}
                <div className="pt-2 border-t border-border space-y-2">
                  <p className="text-[10px] text-muted font-medium">
                    Manual WhatsApp sharing
                  </p>
                  <input
                    type="text"
                    value={customerPhone}
                    onChange={e => setCustomerPhone(e.target.value)}
                    placeholder="Customer phone with country code (optional)"
                    className="w-full bg-bg border border-border focus:border-accent/40 rounded-lg px-2.5 py-1.5 text-[11px] text-text outline-none transition-colors"
                    style={{ caretColor: '#C4A35A' }}
                  />
                  <button
                    onClick={handleWhatsApp}
                    className="w-full flex items-center justify-center gap-1.5 py-2 bg-surface2 hover:bg-border border border-border rounded-lg text-[11px] text-muted hover:text-text transition-colors"
                  >
                    <ExternalLink style={{ width: 12, height: 12 }} />
                    Open WhatsApp Web
                  </button>
                  <p className="text-[9px] text-muted/55 text-center leading-snug">
                    Specifications with Availability copied to clipboard automatically!<br />
                    Paste directly into WhatsApp Web, or attach the Excel report.
                  </p>
                </div>
              </div>
            )}

            {/* Quick Copy for WhatsApp */}
            {result.matched_diamonds.length > 0 && (
              <WhatsAppExportBox stones={result.matched_diamonds} />
            )}

            {/* Diamond list */}
            <div className="space-y-2">
              <p className="text-[11px] font-medium text-muted">
                {result.total_matched > 0
                  ? `${result.total_matched} matching diamond${result.total_matched !== 1 ? 's' : ''}`
                  : 'No exact match found'
                }
              </p>
              {result.matched_diamonds.map((d, i) => (
                <MatchCard key={d.StockId || i} diamond={d} />
              ))}
            </div>

            {/* Similar alternatives — shown only when no exact match */}
            {result.total_matched === 0 && result.similar_diamonds && result.similar_diamonds.length > 0 && (
              <div className="space-y-2">
                {/* Section header */}
                <div
                  className="flex items-center gap-2 px-3 py-2 rounded-xl border"
                  style={{ background: 'rgba(196,163,90,0.06)', borderColor: 'rgba(196,163,90,0.25)' }}
                >
                  <Lightbulb className="text-accent flex-shrink-0" style={{ width: 13, height: 13 }} />
                  <div>
                    <p className="text-[11px] font-bold text-accent-light">
                      Closest Available Alternatives
                    </p>
                    <p className="text-[9px] text-muted leading-snug mt-0.5">
                      Exact diamond not in stock — nearest matches shown below.
                      Better-quality stones appear first. Gold badges show what differs.
                    </p>
                  </div>
                </div>

                {/* WhatsApp bulk-copy box */}
                <SimilarAlternativesWhatsAppBox stones={result.similar_diamonds} />

                {result.similar_diamonds.map((d, i) => (
                  <SimilarCard key={d.StockId || i} diamond={d} />
                ))}
              </div>
            )}

            {/* Truly nothing — no exact, no similar */}
            {result.total_matched === 0 && (!result.similar_diamonds || result.similar_diamonds.length === 0) && (
              <div
                className="flex items-start gap-2 p-3 rounded-xl border"
                style={{ background: 'rgba(196,163,90,0.05)', borderColor: 'rgba(196,163,90,0.18)' }}
              >
                <Lightbulb className="text-accent flex-shrink-0 mt-0.5" style={{ width: 14, height: 14 }} />
                <p className="text-[11px] text-muted">
                  No matching or similar diamonds found in current inventory.
                  Try adjusting your requirements (wider carat range, adjacent color/clarity).
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
