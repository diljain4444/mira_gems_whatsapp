// content.js — Mira Companion In-Page Floating AI Assistant Orb & Drawer

// ─── WhatsApp Chat Extractor ────────────────────────────────────────────────
/**
 * Reads the currently open WhatsApp Web chat from the DOM.
 * Returns { messages, phone, name } or null if not on a chat.
 *
 * WhatsApp Web DOM approach (works as of 2024-2026):
 *  - Chat panel: [data-tab="8"] or the main pane
 *  - Messages: data-pre-plain-text attribute contains "[HH:MM, DD/MM/YYYY] Name: "
 *  - Outgoing messages have class "message-out", incoming "message-in"
 *  - Contact name: span[data-testid="conversation-info-header-chat-title"]
 *  - Phone number: in the contact info panel or the header subtitle
 */
function extractWhatsAppChat() {
  // ── 1. Verify we are on WhatsApp Web ──────────────────────────────────────
  if (!window.location.hostname.includes('web.whatsapp.com')) {
    return null;
  }

  // ── 2. Extract customer name ───────────────────────────────────────────────
  let customerName = '';
  const nameSelectors = [
    '[data-testid="conversation-info-header-chat-title"]',
    'header [data-testid="conversation-header"] span[title]',
    'header ._amid span[title]',
    'header span[dir="auto"][title]',
  ];
  for (const sel of nameSelectors) {
    const el = document.querySelector(sel);
    if (el && el.textContent && el.textContent.trim()) {
      customerName = el.textContent.trim();
      break;
    }
  }

  // ── 3. Extract phone number ───────────────────────────────────────────────
  // WhatsApp often shows the phone in the header subtitle or the chat title for numbers
  let customerPhone = '';
  const phoneSelectors = [
    '[data-testid="conversation-info-header-chat-subtitle"]',
    'header ._amid div[title]',
    'header ._amid span[title]:nth-of-type(2)',
  ];
  for (const sel of phoneSelectors) {
    const el = document.querySelector(sel);
    if (el && el.textContent && /[\d\+\-\s\(\)]{7,}/.test(el.textContent)) {
      customerPhone = el.textContent.trim().replace(/[^+\d\s\-\(\)]/g, '');
      break;
    }
  }
  // If name looks like a phone number itself, use it as phone
  if (!customerPhone && /^[\+\d][\d\s\-\(\)]{6,}$/.test(customerName)) {
    customerPhone = customerName;
    customerName  = '';
  }

  // ── 4. Extract messages ───────────────────────────────────────────────────
  // WhatsApp message rows have [data-pre-plain-text] attribute like:
  // "[14:30, 24/11/2026] Raj: " — for incoming
  // "[14:31, 24/11/2026] You: " — for outgoing

  const messages = [];
  let   currentDate = '';

  // Primary approach: data-pre-plain-text
  const msgNodes = Array.from(document.querySelectorAll('[data-pre-plain-text]'));

  for (const node of msgNodes) {
    const rawMeta = node.getAttribute('data-pre-plain-text') || '';
    let time = '';
    let date = '';
    let senderRaw = '';

    // Robust extraction: handles 12-hr (am/pm), 24-hr, date-first or time-first
    // E.g. "[2:30 pm, 24/11/2026] Raj: " or "[14:30, 24/11/2026] You: "
    const bracketMatch = rawMeta.match(/^\[(.*?)\]\s*(.*?):\s*$/);
    if (bracketMatch) {
      const inside = bracketMatch[1].trim();
      senderRaw = bracketMatch[2].trim();
      const parts = inside.split(',').map(s => s.trim());
      for (const part of parts) {
        if (/\d{1,2}:\d{2}(?::\d{2})?\s*(?:am|pm)?/i.test(part)) {
          time = part;
        } else if (/\d{1,4}[/\.-]\d{1,2}[/\.-]\d{2,4}/.test(part)) {
          date = part;
        }
      }
      if (date) {
        currentDate = date;
      }
    }

    // Fallback for time if not in bracket: look inside message bubble
    if (!time) {
      const timeEl = node.querySelector('[data-testid="msg-time"]') ||
                     node.querySelector('span[dir="auto"]');
      if (timeEl && /\d{1,2}:\d{2}/.test(timeEl.textContent)) {
        time = timeEl.textContent.trim();
      }
    }

    // Fallback for date: use last seen date or today's local date
    if (!date) {
      date = currentDate || new Date().toLocaleDateString('en-GB');
    }

    // Determine sender direction: message-out = sent by ME
    const isOutgoing = node.closest('.message-out') !== null ||
                       node.classList.contains('message-out');

    const sender = isOutgoing ? 'me' : 'customer';

    // Extract message text
    // Try copyable-text first (most reliable), then fallback to span[dir="ltr"]
    const copyable = node.querySelector('[data-testid="msg-container"] [copyable]') ||
                     node.querySelector('span[dir="ltr"]') ||
                     node.querySelector('span.selectable-text') ||
                     node.querySelector('[class*="copyable-text"]');

    let text = '';
    if (copyable) {
      text = copyable.innerText || copyable.textContent || '';
    } else {
      // Last resort: get all text, strip the meta prefix
      const full = node.innerText || node.textContent || '';
      text = full.replace(rawMeta, '').trim();
    }

    text = text.trim();
    if (!text) continue;

    // Filter out system messages (e.g. "Messages and calls are end-to-end encrypted")
    if (text.length > 500) text = text.substring(0, 500); // cap very long messages

    messages.push({ sender, time, date, text });
  }

  if (messages.length === 0) return null;

  // ── 5. Filter to most recent session only ─────────────────────────────────
  // Find the latest date in the conversation
  const dates = [...new Set(messages.map(m => m.date))];
  const latestDate = dates[dates.length - 1];

  // Keep messages from the last date group that has real diamond/business content.
  // If latest date has >=3 messages, use only latest date.
  // If latest date has <3 messages, include the previous date too (ongoing convo).
  const latestDateMsgs = messages.filter(m => m.date === latestDate);
  let filteredMessages;
  if (latestDateMsgs.length >= 3 || dates.length <= 1) {
    filteredMessages = latestDateMsgs;
  } else {
    // Include previous date + latest date
    const prevDate = dates[dates.length - 2];
    filteredMessages = messages.filter(m => m.date === prevDate || m.date === latestDate);
  }

  // Limit to last 80 messages max (to avoid token overload)
  if (filteredMessages.length > 80) {
    filteredMessages = filteredMessages.slice(filteredMessages.length - 80);
  }

  return {
    messages: filteredMessages,
    phone:    customerPhone,
    name:     customerName,
  };
}

(function () {
  // Prevent duplicate injection
  if (document.getElementById('mira-companion-host')) return;

  const host = document.createElement('div');
  host.id = 'mira-companion-host';
  document.body.appendChild(host);

  const shadow = host.attachShadow({ mode: 'open' });

  // Stylesheet
  const style = document.createElement('style');
  style.textContent = `
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Floating Orb */
    .mira-orb-btn {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 52px;
      height: 52px;
      border-radius: 50%;
      background: linear-gradient(135deg, #EC4899 0%, #8B5CF6 35%, #3B82F6 70%, #F59E0B 100%);
      border: 2px solid rgba(255, 255, 255, 0.45);
      cursor: pointer;
      box-shadow: 0 0 20px rgba(139, 92, 246, 0.55), 0 4px 14px rgba(0, 0, 0, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 2147483647;
      transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.25s ease;
      outline: none;
      animation: orbGlow 3.5s ease-in-out infinite;
    }
    .mira-orb-btn:hover {
      transform: scale(1.1);
      box-shadow: 0 0 28px rgba(139, 92, 246, 0.75), 0 0 45px rgba(245, 158, 11, 0.45), 0 6px 18px rgba(0, 0, 0, 0.5);
    }
    .mira-orb-btn:active {
      transform: scale(0.95);
    }

    @keyframes orbGlow {
      0%, 100% {
        box-shadow: 0 0 16px rgba(139, 92, 246, 0.45), 0 0 32px rgba(236, 72, 153, 0.3), 0 4px 14px rgba(0, 0, 0, 0.5);
        transform: translateY(0px);
      }
      50% {
        box-shadow: 0 0 24px rgba(139, 92, 246, 0.7), 0 0 44px rgba(245, 158, 11, 0.4), 0 6px 18px rgba(0, 0, 0, 0.6);
        transform: translateY(-2px);
      }
    }

    /* Popup Action Menu */
    .mira-popup {
      position: fixed;
      bottom: 88px;
      right: 24px;
      width: 280px;
      padding: 14px;
      background: rgba(18, 18, 26, 0.96);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 18px;
      box-shadow: 0 16px 40px -4px rgba(0, 0, 0, 0.85), 0 0 24px rgba(139, 92, 246, 0.3);
      z-index: 2147483647;
      display: none;
      flex-direction: column;
      gap: 10px;
      animation: popIn 0.22s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }
    .mira-popup.open {
      display: flex;
    }

    @keyframes popIn {
      from {
        opacity: 0;
        transform: translateY(12px) scale(0.95);
      }
      to {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
    }

    .mira-popup-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-bottom: 10px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .mira-popup-title {
      font-size: 13px;
      font-weight: 700;
      color: #FFFFFF;
      letter-spacing: 0.3px;
    }
    .mira-popup-sub {
      font-size: 10px;
      color: #8888A8;
      margin-top: 1px;
    }
    .mira-close-btn {
      background: none;
      border: none;
      color: #8888A8;
      cursor: pointer;
      padding: 4px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .mira-close-btn:hover {
      background: rgba(255, 255, 255, 0.08);
      color: #FFFFFF;
    }

    .mira-popup-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 12px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 12px;
      cursor: pointer;
      text-align: left;
      transition: all 0.2s ease;
      color: #E8E8F0;
    }
    .mira-popup-item:hover {
      background: rgba(255, 255, 255, 0.08);
      border-color: rgba(196, 163, 90, 0.4);
      transform: translateX(-2px);
    }
    .mira-popup-icon {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .mira-icon-id {
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.3);
      color: #F59E0B;
    }
    .mira-icon-demand {
      background: rgba(139, 92, 246, 0.18);
      border: 1px solid rgba(139, 92, 246, 0.3);
      color: #A78BFA;
    }
    .mira-icon-lead {
      background: rgba(34, 197, 94, 0.15);
      border: 1px solid rgba(34, 197, 94, 0.3);
      color: #4ADE80;
    }
    .mira-item-title {
      font-size: 12px;
      font-weight: 600;
      color: #FFFFFF;
    }
    .mira-item-desc {
      font-size: 10px;
      color: #8888A8;
      margin-top: 2px;
      line-height: 1.25;
    }

    /* Slide-in Assistant Sidebar Drawer (iframe) */
    .mira-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(0, 0, 0, 0.4);
      backdrop-filter: blur(2px);
      -webkit-backdrop-filter: blur(2px);
      z-index: 2147483645;
      display: none;
      opacity: 0;
      transition: opacity 0.28s ease;
    }
    .mira-backdrop.open {
      display: block;
      opacity: 1;
    }

    .mira-drawer-iframe {
      position: fixed;
      top: 0;
      right: 0;
      width: 440px;
      max-width: 92vw;
      height: 100vh;
      border: none;
      border-left: 1px solid rgba(255, 255, 255, 0.12);
      box-shadow: -12px 0 40px rgba(0, 0, 0, 0.65);
      z-index: 2147483646;
      transform: translateX(105%);
      transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      background: #0A0A0F;
    }
    .mira-drawer-iframe.open {
      transform: translateX(0);
    }
  `;
  shadow.appendChild(style);

  // Backdrop
  const backdrop = document.createElement('div');
  backdrop.className = 'mira-backdrop';
  shadow.appendChild(backdrop);

  // Drawer Iframe
  const iframe = document.createElement('iframe');
  iframe.className = 'mira-drawer-iframe';
  iframe.allow = "clipboard-write *; clipboard-read *";
  iframe.src = chrome.runtime.getURL('sidepanel.html');
  shadow.appendChild(iframe);

  // Popup Menu
  const popup = document.createElement('div');
  popup.className = 'mira-popup';
  popup.innerHTML = `
    <div class="mira-popup-header">
      <div>
        <div class="mira-popup-title">Mira AI Assistant</div>
        <div class="mira-popup-sub">Select diamond tool</div>
      </div>
      <button class="mira-close-btn" id="mira-popup-close" title="Close">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12"/></svg>
      </button>
    </div>
    <div class="mira-popup-item" id="mira-action-id">
      <div class="mira-popup-icon mira-icon-id">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
      </div>
      <div style="flex:1;">
        <div class="mira-item-title">Find Stone by ID</div>
        <div class="mira-item-desc">Search single or multiple stock IDs</div>
      </div>
    </div>
    <div class="mira-popup-item" id="mira-action-demand">
      <div class="mira-popup-icon mira-icon-demand">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3z"/></svg>
      </div>
      <div style="flex:1;">
        <div class="mira-item-title">Find Stone by Demand</div>
        <div class="mira-item-desc">AI inquiry extraction & stock matching</div>
      </div>
    </div>
  
    <div class="mira-popup-item" id="mira-action-lead">
      <div class="mira-popup-icon mira-icon-lead">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
      </div>
      <div style="flex:1;">
        <div class="mira-item-title">Save Chat Lead</div>
        <div class="mira-item-desc">Log customer chat &amp; deal outcome to DB</div>
      </div>
    </div>
  `;
  shadow.appendChild(popup);

  // Floating Orb Button
  const orb = document.createElement('button');
  orb.className = 'mira-orb-btn';
  orb.title = 'Mira Diamond Assistant';
  orb.innerHTML = `
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2">
      <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3z"/>
    </svg>
  `;
  shadow.appendChild(orb);

  // State
  let isPopupOpen = false;
  let isDrawerOpen = false;
  let activeFeature = null;

  function togglePopup() {
    isPopupOpen = !isPopupOpen;
    if (isPopupOpen) {
      popup.classList.add('open');
    } else {
      popup.classList.remove('open');
    }
  }

  function sendFeatureToIframe(feature) {
    if (!feature) return;
    try {
      if (iframe && iframe.contentWindow) {
        iframe.contentWindow.postMessage({ action: 'setFeature', feature: feature }, '*');
      }
    } catch (e) {
      console.warn('sendFeatureToIframe failed:', e);
    }
  }

  function openSidebar(feature) {
    isPopupOpen = false;
    popup.classList.remove('open');

    activeFeature = feature;

    // Slide drawer open
    isDrawerOpen = true;
    backdrop.classList.add('open');
    iframe.classList.add('open');
    orb.style.display = 'none'; // hide orb while sidebar is open

    // Immediately notify React inside iframe to switch to the selected feature
    sendFeatureToIframe(feature);

    // Also update iframe src if not already aligned
    const targetUrl = chrome.runtime.getURL(`sidepanel.html?feature=${feature}`);
    if (iframe.src !== targetUrl) {
      iframe.src = targetUrl;
    }
  }

  function closeSidebar() {
    isDrawerOpen = false;
    activeFeature = null;
    iframe.classList.remove('open');
    backdrop.classList.remove('open');
    orb.style.display = 'flex'; // restore orb
    sendFeatureToIframe('home');
  }

  // Event Listeners
  orb.addEventListener('click', (e) => {
    e.stopPropagation();
    togglePopup();
  });

  const closeBtn = shadow.querySelector('#mira-popup-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      togglePopup();
    });
  }

  const actionId = shadow.querySelector('#mira-action-id');
  if (actionId) {
    actionId.addEventListener('click', (e) => {
      e.stopPropagation();
      openSidebar('stone-by-id');
    });
  }

  const actionDemand = shadow.querySelector('#mira-action-demand');
  if (actionDemand) {
    actionDemand.addEventListener('click', (e) => {
      e.stopPropagation();
      openSidebar('stone-by-demand');
    });
  }

  const actionLead = shadow.querySelector('#mira-action-lead');
  if (actionLead) {
    actionLead.addEventListener('click', (e) => {
      e.stopPropagation();
      openSidebar('save-lead');
    });
  }

  backdrop.addEventListener('click', closeSidebar);

  // Close popup if clicking outside on webpage
  document.addEventListener('click', () => {
    if (isPopupOpen) {
      isPopupOpen = false;
      popup.classList.remove('open');
    }
  });

  // Listen for close, ready, clipboard & chat extraction messages from inside iframe
  window.addEventListener('message', (event) => {
    if (event.data && event.data.action === 'closeSidebar') {
      closeSidebar();
    } else if (event.data && event.data.action === 'miraIframeReady') {
      // Iframe mounted: ensure active feature is sent if drawer is open
      if (activeFeature && isDrawerOpen) {
        sendFeatureToIframe(activeFeature);
      }
    } else if (event.data && event.data.action === 'copyToClipboard') {
      const textToCopy = event.data.text;
      if (!textToCopy) return;

      let copied = false;
      try {
        const ta = document.createElement('textarea');
        ta.value = textToCopy;
        ta.style.position = 'fixed';
        ta.style.top = '0';
        ta.style.left = '0';
        ta.style.width = '24px';
        ta.style.height = '24px';
        ta.style.padding = '0';
        ta.style.border = 'none';
        ta.style.outline = 'none';
        ta.style.background = 'transparent';
        ta.style.color = 'transparent';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        ta.setSelectionRange(0, ta.value.length);
        copied = document.execCommand('copy');
        document.body.removeChild(ta);
      } catch (err) {
        copied = false;
      }

      if (!copied && navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(textToCopy).catch(() => {});
      }
    } else if (event.data && event.data.action === 'extractWhatsAppChat') {
      // ── WhatsApp Chat Extractor ────────────────────────────────────────────
      try {
        const result = extractWhatsAppChat();
        if (iframe && iframe.contentWindow) {
          if (result) {
            iframe.contentWindow.postMessage({ action: 'chatExtracted', ...result }, '*');
          } else {
            iframe.contentWindow.postMessage({ action: 'chatExtractionFailed' }, '*');
          }
        }
      } catch (err) {
        if (iframe && iframe.contentWindow) {
          iframe.contentWindow.postMessage({ action: 'chatExtractionFailed' }, '*');
        }
      }
    }
  });

  // Listen for toolbar extension icon toggle
  chrome.runtime.onMessage.addListener((message) => {
    if (message.action === 'toggleOrb') {
      if (isDrawerOpen) {
        closeSidebar();
      } else {
        togglePopup();
      }
    }
  });
})();
