/**
 * SaveLead.tsx — "Save Chat Lead" screen for Mira Companion.
 *
 * Flow:
 *  1. Mount → asks content script to extract the active WhatsApp chat
 *  2. Shows extracted messages count + customer info + optional manual note
 *  3. On "Analyze & Save": POST to /api/leads/save → show result preview
 */
import React, { useState, useEffect, useCallback } from 'react'
import {
  ArrowLeft, Users, MessageCircle, Brain, CheckCircle2,
  AlertCircle, Loader2, ChevronDown, ChevronUp, Gem,
  TrendingUp, TrendingDown, Clock, Zap, FileText, RefreshCw, User,
} from 'lucide-react'
import { api } from '../../services/api'
import type { SaveLeadResponse, ChatMessagePayload } from '../../types'

interface SaveLeadProps {
  onBack: () => void
}

// ─── Colour badges ────────────────────────────────────────────────────────────

function outcomeBadge(outcome: string | null) {
  const map: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
    WON:          { bg: 'bg-available/15 border-available/30 text-available', text: 'WON ✅', icon: null },
    LOST:         { bg: 'bg-hold/15 border-hold/30 text-hold',               text: 'LOST ❌', icon: null },
    NEGOTIATING:  { bg: 'bg-yellow-500/15 border-yellow-500/30 text-yellow-400', text: 'NEGOTIATING 🤝', icon: null },
    PENDING:      { bg: 'bg-blue-500/15 border-blue-500/30 text-blue-400',    text: 'PENDING ⏳', icon: null },
    INQUIRY_ONLY: { bg: 'bg-surface2 border-border text-muted',               text: 'INQUIRY ONLY 👀', icon: null },
    GHOSTED:      { bg: 'bg-surface2 border-border text-muted',               text: 'GHOSTED 👻', icon: null },
  }
  const style = map[outcome ?? ''] ?? { bg: 'bg-surface2 border-border text-muted', text: outcome ?? '—', icon: null }
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-[11px] font-semibold border ${style.bg}`}>
      {style.text}
    </span>
  )
}

function Badge({ label, value, accent = false }: { label: string; value?: string | null; accent?: boolean }) {
  if (!value) return null
  return (
    <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-[10px] ${
      accent ? 'bg-accent/10 border-accent/25 text-accent' : 'bg-surface border-border text-text'
    }`}>
      <span className="text-muted">{label}:</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

type Phase = 'extracting' | 'ready' | 'saving' | 'done' | 'error' | 'no-whatsapp'

export default function SaveLead({ onBack }: SaveLeadProps) {
  const [phase,       setPhase]      = useState<Phase>('extracting')
  const [messages,    setMessages]   = useState<ChatMessagePayload[]>([])
  const [phone,       setPhone]      = useState('')
  const [name,        setName]       = useState('')
  const [sellerName,  setSellerName] = useState(() => localStorage.getItem('mira_seller_name') || '')
  const [manualNote,  setManualNote] = useState('')
  const [errorMsg,    setErrorMsg]   = useState('')
  const [result,      setResult]     = useState<SaveLeadResponse | null>(null)
  const [showRaw,     setShowRaw]    = useState(false)
  const [showDemands, setShowDemands]= useState(true)

  // ── Step 1: ask content script to extract the WhatsApp chat ────────────────
  const requestExtraction = useCallback(() => {
    setPhase('extracting')
    setErrorMsg('')
    try {
      // Mira runs inside an iframe injected by content.js.
      // We postMessage to the parent (content.js) which reads the WhatsApp DOM.
      window.parent.postMessage({ action: 'extractWhatsAppChat' }, '*')
    } catch {
      setPhase('error')
      setErrorMsg('Could not communicate with the page. Please reload WhatsApp Web.')
    }
  }, [])

  useEffect(() => {
    requestExtraction()

    const handler = (e: MessageEvent) => {
      if (!e.data) return

      if (e.data.action === 'chatExtracted') {
        const { messages: msgs, phone: ph, name: nm } = e.data
        if (!msgs || msgs.length === 0) {
          setPhase('no-whatsapp')
          return
        }
        setMessages(msgs)
        setPhone(ph || '')
        setName(nm || '')
        setPhase('ready')
      }

      if (e.data.action === 'chatExtractionFailed') {
        setPhase('no-whatsapp')
      }
    }

    window.addEventListener('message', handler)
    return () => window.removeEventListener('message', handler)
  }, [requestExtraction])

  // ── Step 2: Analyze & Save ─────────────────────────────────────────────────
  const handleSave = async (forceUpdate = false) => {
    if (!messages.length) return
    setPhase('saving')
    try {
      const res = await api.saveLead({
        customer_phone: phone,
        customer_name:  name || null,
        messages,
        manual_note:    manualNote.trim() || null,
        force_update:   forceUpdate,
        seller_name:    sellerName.trim() || null,
      })
      setResult(res)
      setPhase('done')
    } catch (err: unknown) {
      setPhase('error')
      setErrorMsg(err instanceof Error ? err.message : 'Unknown error. Please try again.')
    }
  }

  // ─── Renders ───────────────────────────────────────────────────────────────

  const latestDate = messages.length ? messages[messages.length - 1]?.date : null
  const dateGroups = messages.reduce<Record<string, number>>((acc, m) => {
    acc[m.date] = (acc[m.date] || 0) + 1
    return acc
  }, {})
  const dateList = Object.keys(dateGroups)

  return (
    <div className="flex flex-col h-full bg-bg text-text">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 flex items-center gap-3 px-4 pt-5 pb-4 border-b border-border">
        <button
          onClick={onBack}
          className="p-1.5 rounded-lg hover:bg-surface2 transition-colors"
        >
          <ArrowLeft className="text-muted" style={{ width: 16, height: 16 }} />
        </button>
        <div className="w-8 h-8 rounded-xl bg-green-500/15 border border-green-500/25 flex items-center justify-center">
          <Users className="text-green-400" style={{ width: 15, height: 15 }} />
        </div>
        <div>
          <h1 className="text-[13px] font-bold text-text leading-none">Save Chat Lead</h1>
          <p className="text-[10px] text-muted mt-0.5">WhatsApp → AI Analysis → Database</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">

        {/* ── Phase: Extracting ────────────────────────────────────────────── */}
        {phase === 'extracting' && (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <Loader2 className="text-accent animate-spin" style={{ width: 28, height: 28 }} />
            <p className="text-[13px] text-text font-medium">Reading WhatsApp chat…</p>
            <p className="text-[11px] text-muted text-center">Make sure you have a customer chat open in WhatsApp Web.</p>
          </div>
        )}

        {/* ── Phase: No WhatsApp ───────────────────────────────────────────── */}
        {phase === 'no-whatsapp' && (
          <div className="flex flex-col items-center justify-center py-12 gap-4">
            <div className="w-14 h-14 rounded-2xl bg-hold/10 border border-hold/25 flex items-center justify-center">
              <MessageCircle className="text-hold" style={{ width: 24, height: 24 }} />
            </div>
            <div className="text-center">
              <p className="text-[13px] font-semibold text-text">No WhatsApp Chat Found</p>
              <p className="text-[11px] text-muted mt-1 leading-relaxed">
                Please open WhatsApp Web and select a customer chat, then try again.
              </p>
            </div>
            <button
              onClick={requestExtraction}
              className="px-4 py-2 rounded-xl bg-accent/15 border border-accent/30 text-accent text-[12px] font-semibold hover:bg-accent/25 transition-colors"
            >
              Try Again
            </button>
          </div>
        )}

        {/* ── Phase: Ready ─────────────────────────────────────────────────── */}
        {phase === 'ready' && (
          <>
            {/* Salesperson / Seller Indicator */}
            <div className="flex items-center justify-between px-3 py-2 bg-surface border border-accent/20 rounded-xl">
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <div className="w-6 h-6 rounded-lg bg-accent/15 flex items-center justify-center flex-shrink-0">
                  <User className="text-accent" style={{ width: 12, height: 12 }} />
                </div>
                <div className="flex items-center gap-1.5 flex-1 min-w-0">
                  <span className="text-[10px] text-muted uppercase tracking-wider font-semibold">Seller:</span>
                  <input
                    type="text"
                    value={sellerName}
                    onChange={e => {
                      setSellerName(e.target.value)
                      localStorage.setItem('mira_seller_name', e.target.value.trim())
                    }}
                    placeholder="Enter your name"
                    className="bg-transparent text-[11px] font-bold text-accent placeholder-muted/60 outline-none flex-1 truncate"
                  />
                </div>
              </div>
              <span className="text-[9px] text-muted">Auto-saved</span>
            </div>

            {/* Customer info card */}
            <div className="p-3.5 bg-surface border border-border rounded-xl space-y-2.5">
              <p className="text-[11px] text-muted uppercase tracking-wider font-semibold">Customer Detected</p>
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-accent/15 border border-accent/20 flex items-center justify-center flex-shrink-0">
                  <Users className="text-accent" style={{ width: 15, height: 15 }} />
                </div>
                <div className="flex-1 min-w-0">
                  <input
                    type="text"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    placeholder="Customer name (optional)"
                    className="w-full bg-transparent text-[13px] font-semibold text-text placeholder-muted outline-none"
                  />
                  <p className="text-[11px] text-muted mt-0.5">{phone || 'Phone not detected'}</p>
                </div>
              </div>
            </div>

            {/* Messages summary */}
            <div className="p-3.5 bg-surface border border-border rounded-xl">
              <div className="flex items-center justify-between mb-2">
                <p className="text-[11px] text-muted uppercase tracking-wider font-semibold">Chat Summary</p>
                <span className="text-[10px] text-accent font-medium">{messages.length} messages</span>
              </div>
              <div className="space-y-1">
                {dateList.slice(-3).map(date => (
                  <div key={date} className="flex items-center justify-between text-[11px]">
                    <span className="text-muted">{date}</span>
                    <span className="text-text font-medium">{dateGroups[date]} messages</span>
                  </div>
                ))}
              </div>
              {latestDate && (
                <p className="text-[10px] text-muted mt-2 pt-2 border-t border-border">
                  Most recent: {latestDate}
                </p>
              )}
            </div>

            {/* Manual note */}
            <div className="space-y-1.5">
              <label className="text-[11px] text-muted uppercase tracking-wider font-semibold block">
                Optional Note (Voice call info, etc.)
              </label>
              <textarea
                value={manualNote}
                onChange={e => setManualNote(e.target.value)}
                placeholder="e.g. Customer called and said budget is max $180/ct, wants delivery by Friday…"
                rows={3}
                className="w-full bg-surface border border-border rounded-xl px-3 py-2.5 text-[12px] text-text placeholder-muted outline-none focus:border-accent/50 resize-none transition-colors"
              />
            </div>

            {/* Save button */}
            <button
              onClick={() => handleSave(false)}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-accent text-bg text-[13px] font-bold hover:bg-accent/90 transition-colors"
            >
              <Brain style={{ width: 15, height: 15 }} />
              Analyze &amp; Save Lead
            </button>
          </>
        )}

        {/* ── Phase: Saving ────────────────────────────────────────────────── */}
        {phase === 'saving' && (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <Loader2 className="text-accent animate-spin" style={{ width: 28, height: 28 }} />
            <p className="text-[13px] text-text font-medium">AI is analyzing the conversation…</p>
            <p className="text-[11px] text-muted text-center">Extracting demands, deal outcome, and customer behavior.</p>
          </div>
        )}

        {/* ── Phase: Error ─────────────────────────────────────────────────── */}
        {phase === 'error' && (
          <div className="flex flex-col items-center justify-center py-12 gap-4">
            <div className="w-14 h-14 rounded-2xl bg-hold/10 border border-hold/25 flex items-center justify-center">
              <AlertCircle className="text-hold" style={{ width: 24, height: 24 }} />
            </div>
            <div className="text-center">
              <p className="text-[13px] font-semibold text-text">Something went wrong</p>
              <p className="text-[11px] text-muted mt-1 leading-relaxed max-w-[220px]">{errorMsg}</p>
            </div>
            <button
              onClick={() => setPhase('ready')}
              className="px-4 py-2 rounded-xl bg-surface border border-border text-text text-[12px] font-semibold hover:bg-surface2 transition-colors"
            >
              Try Again
            </button>
          </div>
        )}

        {/* ── Phase: Done — Result Preview ─────────────────────────────────── */}
        {phase === 'done' && result && (
          <div className="space-y-3">

            {/* Banner: Duplicate Warning or Success */}
            {result.is_duplicate ? (
              <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-xl space-y-2.5">
                <div className="flex items-start gap-2.5">
                  <AlertCircle className="text-yellow-400 flex-shrink-0 mt-0.5" style={{ width: 18, height: 18 }} />
                  <div className="flex-1 min-w-0">
                    <p className="text-[12px] font-bold text-yellow-400">Already Saved — No Duplicate Created</p>
                    <p className="text-[11px] text-muted mt-0.5 leading-snug">
                      {result.duplicate_message || `This conversation was previously saved in Session #${result.session_id}.`}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleSave(true)}
                  className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-yellow-500/15 border border-yellow-500/30 text-yellow-400 text-[11px] font-semibold hover:bg-yellow-500/25 transition-colors"
                >
                  <RefreshCw style={{ width: 12, height: 12 }} />
                  Re-Analyze &amp; Update Record
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2.5 p-3 bg-available/8 border border-available/25 rounded-xl">
                <CheckCircle2 className="text-available flex-shrink-0" style={{ width: 18, height: 18 }} />
                <div>
                  <p className="text-[12px] font-semibold text-available">
                    {result.duplicate_message || 'Lead Saved Successfully!'}
                  </p>
                  <p className="text-[10px] text-muted">Session #{result.session_id} · Customer #{result.customer_id}</p>
                </div>
              </div>
            )}

            {/* Customer + outcome */}
            <div className="p-3.5 bg-surface border border-border rounded-xl space-y-2.5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[13px] font-bold text-text">{result.customer_name || 'Unknown Customer'}</p>
                  <p className="text-[11px] text-muted">{result.customer_phone}</p>
                </div>
                {outcomeBadge(result.deal_outcome)}
              </div>

              {/* Behavioral tags */}
              <div className="flex flex-wrap gap-1.5">
                {(result.seller_name || sellerName) && (
                  <Badge label="Seller" value={result.seller_name || sellerName} accent />
                )}
                <Badge label="Price" value={result.price_sensitivity} />
                <Badge label="Urgency" value={result.urgency} />
                <Badge label="Mood" value={result.sentiment} />
                {result.lost_reason_category && result.lost_reason_category !== 'NONE' && (
                  <Badge label="Lost ↳" value={result.lost_reason_category?.replace(/_/g, ' ')} />
                )}
              </div>
            </div>

            {/* AI Summary */}
            {result.ai_summary && (
              <div className="p-3.5 bg-surface border border-border rounded-xl">
                <div className="flex items-center gap-1.5 mb-2">
                  <Brain className="text-accent" style={{ width: 12, height: 12 }} />
                  <p className="text-[10px] text-accent uppercase tracking-wider font-semibold">AI Summary</p>
                </div>
                <p className="text-[12px] text-text leading-relaxed">{result.ai_summary}</p>
              </div>
            )}

            {/* Diamond Demands */}
            {result.diamond_demands.length > 0 && (
              <div className="bg-surface border border-border rounded-xl overflow-hidden">
                <button
                  className="w-full flex items-center justify-between px-3.5 py-3 hover:bg-surface2 transition-colors"
                  onClick={() => setShowDemands(d => !d)}
                >
                  <div className="flex items-center gap-1.5">
                    <Gem className="text-accent" style={{ width: 12, height: 12 }} />
                    <span className="text-[11px] font-semibold text-text">
                      Diamond Demands ({result.diamond_demands.length})
                    </span>
                  </div>
                  {showDemands
                    ? <ChevronUp className="text-muted" style={{ width: 13, height: 13 }} />
                    : <ChevronDown className="text-muted" style={{ width: 13, height: 13 }} />}
                </button>
                {showDemands && (
                  <div className="border-t border-border divide-y divide-border">
                    {result.diamond_demands.map((d, i) => (
                      <div key={i} className="px-3.5 py-2.5 space-y-1">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {d.shape    && <span className="text-[11px] font-bold text-accent">{d.shape}</span>}
                          {(d.carat_min || d.carat_max) && (
                            <span className="text-[11px] text-text">
                              {d.carat_min === d.carat_max
                                ? `${d.carat_min}ct`
                                : `${d.carat_min ?? '?'}–${d.carat_max ?? '?'}ct`}
                            </span>
                          )}
                          {d.color   && <span className="text-[11px] text-text">{d.color}</span>}
                          {d.clarity && <span className="text-[11px] text-text">{d.clarity}</span>}
                          {d.cut_grade && <span className="text-[11px] text-text">{d.cut_grade}</span>}
                          {d.lab     && <span className="text-[11px] text-muted">{d.lab}</span>}
                        </div>
                        {d.special_criteria && (
                          <p className="text-[10px] text-muted">{d.special_criteria}</p>
                        )}
                        {d.target_price_per_carat && (
                          <p className="text-[10px] text-muted">
                            Target: ${d.target_price_per_carat}/ct
                          </p>
                        )}
                        {d.in_stock_at_time === false && (
                          <span className="inline-block text-[9px] font-bold text-hold bg-hold/10 border border-hold/25 px-1.5 py-0.5 rounded">
                            NOT IN STOCK
                          </span>
                        )}
                        {d.in_stock_at_time === true && (
                          <span className="inline-block text-[9px] font-bold text-available bg-available/10 border border-available/25 px-1.5 py-0.5 rounded">
                            IN STOCK
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Stone Quotes */}
            {result.stone_quotes.length > 0 && (
              <div className="bg-surface border border-border rounded-xl overflow-hidden">
                <div className="px-3.5 py-3 border-b border-border">
                  <div className="flex items-center gap-1.5">
                    <Zap className="text-yellow-400" style={{ width: 12, height: 12 }} />
                    <span className="text-[11px] font-semibold text-text">
                      Stones Pitched ({result.stone_quotes.length})
                    </span>
                  </div>
                </div>
                <div className="divide-y divide-border">
                  {result.stone_quotes.map((q, i) => (
                    <div key={i} className="px-3.5 py-2.5 flex items-center justify-between gap-2">
                      <div>
                        <p className="text-[12px] font-bold text-text font-mono">{q.stock_id}</p>
                        {q.quoted_price_per_carat && (
                          <p className="text-[10px] text-muted">
                            Quoted: ${q.quoted_price_per_carat}/ct
                            {q.customer_counter_offer
                              ? ` · Counter: $${q.customer_counter_offer}/ct`
                              : ''}
                          </p>
                        )}
                        {q.rejection_note && (
                          <p className="text-[10px] text-muted">{q.rejection_note}</p>
                        )}
                      </div>
                      <span className={`text-[9px] font-bold px-2 py-0.5 rounded border ${
                        q.stone_status === 'PURCHASED' ? 'text-available bg-available/10 border-available/25'
                        : q.stone_status === 'ON_MEMO'  ? 'text-blue-400 bg-blue-500/10 border-blue-500/25'
                        : q.stone_status === 'REJECTED' ? 'text-hold bg-hold/10 border-hold/25'
                        : 'text-muted bg-surface2 border-border'
                      }`}>
                        {q.stone_status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Next Action */}
            {result.next_action && (
              <div className="p-3.5 bg-yellow-500/8 border border-yellow-500/25 rounded-xl">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <Clock className="text-yellow-400" style={{ width: 12, height: 12 }} />
                  <span className="text-[10px] font-semibold text-yellow-400 uppercase tracking-wider">Next Action</span>
                  {result.follow_up_date && (
                    <span className="ml-auto text-[10px] text-muted">{result.follow_up_date}</span>
                  )}
                </div>
                <p className="text-[12px] text-text">{result.next_action}</p>
              </div>
            )}

            {/* Lost reason detail */}
            {result.lost_reason_detail && (
              <div className="p-3.5 bg-surface border border-border rounded-xl">
                <p className="text-[10px] text-muted uppercase tracking-wider font-semibold mb-1">Why Lost</p>
                <p className="text-[12px] text-text">{result.lost_reason_detail}</p>
              </div>
            )}

            {/* Raw transcript toggle */}
            <button
              onClick={() => setShowRaw(r => !r)}
              className="w-full flex items-center gap-1.5 text-[11px] text-muted hover:text-text transition-colors py-1"
            >
              <FileText style={{ width: 12, height: 12 }} />
              {showRaw ? 'Hide' : 'Show'} Raw Transcript
            </button>
            {showRaw && (
              <div className="p-3 bg-surface border border-border rounded-xl max-h-48 overflow-y-auto">
                {messages.map((m, i) => (
                  <div key={i} className="text-[10px] leading-relaxed">
                    <span className="text-muted">[{m.date} {m.time}] </span>
                    <span className={m.sender === 'me' ? 'text-accent' : 'text-text'}>
                      {m.sender === 'me' ? 'ME' : 'CUSTOMER'}:
                    </span>{' '}
                    <span className="text-muted">{m.text}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Save another */}
            <button
              onClick={() => {
                setPhase('extracting')
                setResult(null)
                setManualNote('')
                requestExtraction()
              }}
              className="w-full py-2.5 rounded-xl bg-surface border border-border text-[12px] font-semibold text-text hover:bg-surface2 transition-colors"
            >
              Save Another Chat
            </button>

          </div>
        )}

      </div>
    </div>
  )
}
