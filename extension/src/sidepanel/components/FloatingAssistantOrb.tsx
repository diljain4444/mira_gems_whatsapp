import React, { useState, useRef, useEffect } from 'react'
import { Sparkles, Search, X, ChevronRight } from 'lucide-react'

interface FloatingAssistantOrbProps {
  onSelectFeature: (feature: 'stone-by-id' | 'stone-by-demand') => void
  activeSidebar: 'stone-by-id' | 'stone-by-demand' | null
}

export default function FloatingAssistantOrb({
  onSelectFeature,
  activeSidebar,
}: FloatingAssistantOrbProps) {
  const [isOpen, setIsOpen] = useState(false)
  const popupRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  // Close popup if clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        popupRef.current &&
        !popupRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const handleSelect = (feature: 'stone-by-id' | 'stone-by-demand') => {
    setIsOpen(false)
    onSelectFeature(feature)
  }

  return (
    <>
      {/* Floating Action Menu / Popup */}
      {isOpen && (
        <div
          ref={popupRef}
          className="fixed bottom-20 right-4 z-50 w-72 p-3 bg-[#12121A]/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl pop-in"
          style={{
            boxShadow: '0 16px 40px -4px rgba(0, 0, 0, 0.85), 0 0 24px rgba(139, 92, 246, 0.3)',
          }}
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-white/10">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-pink-500 via-purple-500 to-amber-400 flex items-center justify-center shadow-sm">
                <Sparkles className="w-3.5 h-3.5 text-white" />
              </div>
              <div>
                <p className="text-[12px] font-bold text-white leading-none">Mira AI Assistant</p>
                <p className="text-[9px] text-[#8888A8] mt-0.5 leading-none">Choose diamond search tool</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 text-[#8888A8] hover:text-white hover:bg-white/5 rounded-lg transition-colors"
              title="Close menu"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Action Options */}
          <div className="space-y-1.5">
            <button
              onClick={() => handleSelect('stone-by-id')}
              className={`w-full flex items-center gap-3 p-2.5 rounded-xl transition-all text-left group ${
                activeSidebar === 'stone-by-id'
                  ? 'bg-amber-500/15 border border-amber-500/40 text-amber-200'
                  : 'bg-white/[0.03] hover:bg-white/[0.08] border border-white/5 hover:border-amber-500/30'
              }`}
            >
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500/20 to-amber-700/20 border border-amber-500/30 flex items-center justify-center text-amber-400 group-hover:scale-105 transition-transform flex-shrink-0">
                <Search className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[12px] font-semibold text-white group-hover:text-amber-300 transition-colors leading-none">
                  Find Stone by ID
                </p>
                <p className="text-[10px] text-[#8888A8] mt-1 leading-tight truncate">
                  Lookup single or multiple Stock IDs
                </p>
              </div>
              <ChevronRight className="w-3.5 h-3.5 text-[#8888A8] group-hover:text-amber-400 transition-colors flex-shrink-0" />
            </button>

            <button
              onClick={() => handleSelect('stone-by-demand')}
              className={`w-full flex items-center gap-3 p-2.5 rounded-xl transition-all text-left group ${
                activeSidebar === 'stone-by-demand'
                  ? 'bg-purple-500/15 border border-purple-500/40 text-purple-200'
                  : 'bg-white/[0.03] hover:bg-white/[0.08] border border-white/5 hover:border-purple-500/30'
              }`}
            >
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500/20 to-pink-500/20 border border-purple-500/30 flex items-center justify-center text-purple-400 group-hover:scale-105 transition-transform flex-shrink-0">
                <Sparkles className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[12px] font-semibold text-white group-hover:text-purple-300 transition-colors leading-none">
                  Find Stone by Demand
                </p>
                <p className="text-[10px] text-[#8888A8] mt-1 leading-tight truncate">
                  AI inquiry extraction & stock matching
                </p>
              </div>
              <ChevronRight className="w-3.5 h-3.5 text-[#8888A8] group-hover:text-purple-400 transition-colors flex-shrink-0" />
            </button>
          </div>
        </div>
      )}

      {/* Floating Orb Button */}
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(!isOpen)}
        title="Mira AI Assistant"
        aria-label="Mira AI Assistant"
        className="fixed bottom-5 right-5 z-40 rounded-full flex items-center justify-center shadow-xl transition-all duration-300 cursor-pointer focus:outline-none hover:scale-110 active:scale-95 ai-orb-glow"
        style={{
          width: '52px',
          height: '52px',
          background: 'linear-gradient(135deg, #EC4899 0%, #8B5CF6 35%, #3B82F6 70%, #F59E0B 100%)',
          border: '2px solid rgba(255, 255, 255, 0.4)',
        }}
      >
        <div className="relative flex items-center justify-center w-full h-full">
          {isOpen ? (
            <X className="w-6 h-6 text-white transition-transform duration-200" />
          ) : (
            <>
              <Sparkles className="w-5 h-5 text-white drop-shadow-md" />
              <span className="absolute inset-0 rounded-full border border-white/20 animate-ping opacity-25 pointer-events-none" />
            </>
          )}
        </div>
      </button>
    </>
  )
}
