import React, { useState, useEffect } from 'react'
import type { Screen } from '../types'
import { api } from '../services/api'
import Home from './components/Home'
import StoneById from './components/StoneById'
import StoneByDemand from './components/StoneByDemand'
import RecentReports from './components/RecentReports'
import Settings from './components/Settings'
import SaveLead from './components/SaveLead'
import FloatingAssistantOrb from './components/FloatingAssistantOrb'

export default function App() {
  // Check if opened with direct feature in URL (e.g. from in-page drawer: ?feature=stone-by-id)
  const getInitialScreen = (): Screen => {
    const q = new URLSearchParams(window.location.search).get('feature')
    if (q === 'stone-by-id' || q === 'stone-by-demand' || q === 'reports' || q === 'settings' || q === 'save-lead') {
      return q
    }
    return 'home'
  }

  const [screen, setScreen] = useState<Screen>(getInitialScreen)
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null)

  const checkBackend = async () => {
    try {
      await api.health()
      setBackendOnline(true)
    } catch {
      setBackendOnline(false)
    }
  }

  useEffect(() => {
    checkBackend()
    const id = setInterval(checkBackend, 30_000)
    return () => clearInterval(id)
  }, [])

  // Listen for navigation & feature activation messages from parent content script
  useEffect(() => {
    const handleMsg = (e: MessageEvent) => {
      if (e.data?.action === 'setFeature') {
        const feat = e.data.feature
        if (
          feat === 'stone-by-id' ||
          feat === 'stone-by-demand' ||
          feat === 'home' ||
          feat === 'reports' ||
          feat === 'settings' ||
          feat === 'save-lead'
        ) {
          setScreen(feat)
        }
      } else if (e.data?.action === 'closeSidebar') {
        setScreen('home')
      }
    }
    window.addEventListener('message', handleMsg)

    // Notify parent window (content script) that iframe is ready to receive messages
    try {
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({ action: 'miraIframeReady' }, '*')
      }
    } catch {
      /* ignore */
    }

    return () => window.removeEventListener('message', handleMsg)
  }, [])

  // Back button handler: returns to home and notifies parent if running in drawer iframe
  const handleBack = () => {
    setScreen('home')
    try {
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({ action: 'closeSidebar' }, '*')
      }
    } catch {
      /* ignore */
    }
  }

  const handleNavigate = (s: Screen) => {
    setScreen(s)
  }

  const handleSelectOrbFeature = (feature: 'stone-by-id' | 'stone-by-demand') => {
    setScreen(feature)
  }

  return (
    <div className="relative flex flex-col h-full bg-bg text-text overflow-hidden">
      
      {/* ── Active Screen ────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {screen === 'home' && (
          <Home
            backendOnline={backendOnline}
            onNavigate={handleNavigate}
            onRefreshStatus={checkBackend}
          />
        )}
        {screen === 'stone-by-id' && (
          <StoneById onBack={handleBack} />
        )}
        {screen === 'stone-by-demand' && (
          <StoneByDemand onBack={handleBack} />
        )}
        {screen === 'reports' && (
          <RecentReports onBack={handleBack} />
        )}
        {screen === 'settings' && (
          <Settings onBack={handleBack} />
        )}
        {screen === 'save-lead' && (
          <SaveLead onBack={handleBack} />
        )}
      </div>

      {/* ── Persistent Floating Assistant Orb (Only shown on home, reports, settings) ── */}
      {(screen === 'home' || screen === 'reports' || screen === 'settings') && (
        <FloatingAssistantOrb
          onSelectFeature={handleSelectOrbFeature}
          activeSidebar={null}
        />
      )}

    </div>
  )
}
