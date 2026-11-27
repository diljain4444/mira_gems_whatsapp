/**
 * api.ts — All FastAPI communication for Mira Companion.
 *
 * This is the ONLY file that knows the backend URL.
 * All three platform interfaces (Chrome extension, future Tauri desktop,
 * future web app) will import from this single service layer.
 */
import type {
  StoneLookupResponse,
  DemandSearchResponse,
  ReportMetadata,
  GenerateReportPayload,
  GenerateReportResponse,
  ChatMessagePayload,
  SaveLeadResponse,
  LeadListResponse,
} from '../types'

const BASE_URL = 'http://localhost:8000'

/** Generic fetch wrapper — throws an Error with the backend detail message. */
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })

  if (!response.ok) {
    let message = `Server error ${response.status}`
    try {
      const body = await response.json()
      message = body.detail ?? message
    } catch {
      try { message = (await response.text()) || message } catch { /* ignore */ }
    }
    throw new Error(message)
  }

  return response.json() as Promise<T>
}

export const api = {
  /** Health check — used by the Home screen to show connection status. */
  health: () =>
    request<{ status: string; service: string; version: string }>('/health'),

  /** Find Stone by ID */
  lookupStones: (stone_ids: string) =>
    request<StoneLookupResponse>('/api/stones/lookup', {
      method: 'POST',
      body: JSON.stringify({ stone_ids }),
    }),

  /** Find Stone by Demand — extract + match */
  searchByDemand: (customer_message: string) =>
    request<DemandSearchResponse>('/api/demand/search', {
      method: 'POST',
      body: JSON.stringify({ customer_message }),
    }),

  /** Generate Excel report — returns report_id for download */
  generateReport: (payload: GenerateReportPayload) =>
    request<GenerateReportResponse>('/api/reports/generate', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  /** Build the direct download URL for a report (used in <a> href) */
  getReportDownloadUrl: (report_id: string) =>
    `${BASE_URL}/api/reports/${report_id}/download`,

  /** List all non-expired in-memory reports */
  listReports: () =>
    request<ReportMetadata[]>('/api/reports'),

  // ── Lead Logger ────────────────────────────────────────────────────────────

  /** Save a WhatsApp chat session as a structured lead */
  saveLead: (payload: {
    customer_phone: string
    customer_name:  string | null
    messages:       ChatMessagePayload[]
    manual_note:    string | null
    force_update?:  boolean
    seller_name?:   string | null
  }) =>
    request<SaveLeadResponse>('/api/leads/save', {
      method: 'POST',
      body:   JSON.stringify(payload),
    }),

  /** List all saved leads (paginated) */
  listLeads: (skip = 0, limit = 50) =>
    request<LeadListResponse>(`/api/leads/list?skip=${skip}&limit=${limit}`),
}
