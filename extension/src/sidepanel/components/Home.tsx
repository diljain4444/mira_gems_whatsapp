import React from 'react'
import type { Screen } from '../../types'
import {
  Diamond, Search, Sparkles, FileSpreadsheet,
  MessageSquare, Users, Mic, BarChart3,
  Wifi, WifiOff, Settings, ChevronRight, Clock, RefreshCw,
  type LucideIcon,
} from 'lucide-react'

interface HomeProps {
  backendOnline: boolean | null
  onNavigate: (screen: Screen) => void
  onRefreshStatus: () => void
}

const MAIN_FEATURES: { id: Screen; icon: LucideIcon; title: string; description: string }[] = [
  {
    id: 'stone-by-id',
    icon: Search,
    title: 'Find Stone by ID',
    description: 'Look up one or multiple diamonds using Stock IDs',
  },
  {
    id: 'stone-by-demand',
    icon: Sparkles,
    title: 'Find Stone by Demand',
    description: 'Extract customer requirements and find matching diamonds',
  },
  {
    id: 'save-lead',
    icon: MessageSquare,
    title: 'Save Chat Lead',
    description: 'Log customer chat, demands & deal outcome to database',
  },
  {
    id: 'reports',
    icon: FileSpreadsheet,
    title: 'Recent Reports',
    description: 'View and download recently generated Excel reports',
  },
]

const COMING_SOON = [
  { icon: Users,    title: 'Customer Management',   description: 'View full customer history & analytics'   },
  { icon: Mic,      title: 'Voice Assistant',       description: 'Hands-free diamond search by voice'       },
  { icon: BarChart3,title: 'Business Intelligence', description: 'Inventory analytics and insights'         },
]

export default function Home({ backendOnline, onNavigate, onRefreshStatus }: HomeProps) {
  return (
    <div className="flex flex-col h-full overflow-y-auto">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 px-4 pt-5 pb-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-accent/15 border border-accent/25 flex items-center justify-center">
              <Diamond className="w-4.5 h-4.5 text-accent" style={{ width: 18, height: 18 }} />
            </div>
            <div>
              <h1 className="text-[13px] font-bold gold-shimmer leading-none">MIRA COMPANION</h1>
              <p className="text-[10px] text-muted mt-0.5 leading-none tracking-wide">
                Mira Gems · Diamond Assistant
              </p>
            </div>
          </div>
          <button
            onClick={() => onNavigate('settings')}
            className="p-1.5 rounded-lg hover:bg-surface2 transition-colors"
            title="Settings"
          >
            <Settings className="text-muted" style={{ width: 16, height: 16 }} />
          </button>
        </div>

        {/* Backend status banner */}
        <div
          className={`mt-3 flex items-center gap-2 px-3 py-2 rounded-xl text-[11px] border transition-all ${
            backendOnline === null
              ? 'bg-surface border-border text-muted'
              : backendOnline
              ? 'bg-available/8 border-available/25 text-available'
              : 'bg-hold/8 border-hold/25 text-hold'
          }`}
          style={
            backendOnline === null
              ? { background: '#12121A' }
              : backendOnline
              ? { background: 'rgba(76,175,80,0.06)' }
              : { background: 'rgba(244,67,54,0.06)' }
          }
        >
          {backendOnline === null ? (
            <>
              <span
                className="w-2 h-2 rounded-full bg-muted status-pulse flex-shrink-0"
                style={{ background: '#8888A8' }}
              />
              <span className="flex-1">Connecting to assistant…</span>
            </>
          ) : backendOnline ? (
            <>
              <Wifi style={{ width: 13, height: 13 }} className="flex-shrink-0" />
              <span className="flex-1">Assistant online · Ready</span>
            </>
          ) : (
            <>
              <WifiOff style={{ width: 13, height: 13 }} className="flex-shrink-0" />
              <span className="flex-1">Assistant offline · Start the backend</span>
              <button
                onClick={onRefreshStatus}
                className="ml-auto opacity-70 hover:opacity-100 transition-opacity"
                title="Retry connection"
              >
                <RefreshCw style={{ width: 12, height: 12 }} />
              </button>
            </>
          )}
        </div>
      </div>

      {/* ── Welcome ────────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 px-4 pt-4 pb-1">
        <p className="text-[15px] font-semibold text-text">Good day 👋</p>
        <p className="text-[11px] text-muted mt-0.5">What would you like to do today?</p>
      </div>

      {/* ── Main features ──────────────────────────────────────────────── */}
      <div className="flex-shrink-0 px-4 pt-3 space-y-2">
        {MAIN_FEATURES.map(({ id, icon: Icon, title, description }) => (
          <button
            key={id}
            onClick={() => onNavigate(id)}
            className="w-full flex items-center gap-3 p-3.5 bg-surface hover:bg-surface2 border border-border hover:border-accent/35 rounded-xl transition-all duration-200 text-left group"
          >
            <div className="w-10 h-10 rounded-xl bg-accent/10 group-hover:bg-accent/18 flex items-center justify-center flex-shrink-0 transition-colors border border-accent/15">
              <Icon className="text-accent" style={{ width: 17, height: 17 }} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-semibold text-text leading-none">{title}</p>
              <p className="text-[10px] text-muted mt-1 leading-snug">{description}</p>
            </div>
            <ChevronRight
              className="text-muted group-hover:text-accent transition-colors flex-shrink-0"
              style={{ width: 15, height: 15 }}
            />
          </button>
        ))}
      </div>

      {/* ── Divider ────────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 px-4 mt-5 mb-2.5">
        <div className="flex items-center gap-2">
          <div className="flex-1 h-px bg-border" />
          <span className="text-[9px] text-muted uppercase tracking-widest">Coming Soon</span>
          <div className="flex-1 h-px bg-border" />
        </div>
      </div>

      {/* ── Coming soon ────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 px-4 space-y-1.5 pb-6">
        {COMING_SOON.map(({ icon: Icon, title, description }) => (
          <div
            key={title}
            className="flex items-center gap-3 p-3 bg-surface/40 border border-border/40 rounded-xl opacity-45"
          >
            <div className="w-8 h-8 rounded-lg bg-surface2 flex items-center justify-center flex-shrink-0">
              <Icon className="text-muted" style={{ width: 13, height: 13 }} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[11px] font-medium text-muted leading-none">{title}</p>
              <p className="text-[9px] text-muted/60 mt-0.5 leading-snug">{description}</p>
            </div>
            <Clock className="text-muted/40 flex-shrink-0" style={{ width: 12, height: 12 }} />
          </div>
        ))}
      </div>
    </div>
  )
}
