// service_worker.ts — Mira Companion Chrome Extension Service Worker

chrome.action.onClicked.addListener(async (tab) => {
  if (tab && tab.id !== undefined) {
    try {
      // Toggle floating assistant popup on current page
      await chrome.tabs.sendMessage(tab.id, { action: 'toggleOrb' })
    } catch {
      // Fallback for chrome:// internal pages where content scripts cannot run
      chrome.sidePanel.open({ tabId: tab.id }).catch(() => {})
    }
  }
})
