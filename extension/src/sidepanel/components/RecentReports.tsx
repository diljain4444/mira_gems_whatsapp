import React, { useState, useEffect } from 'react'
import { ArrowLeft, FileSpreadsheet, Download, Loader2, RefreshCw, AlertCircle } from 'lucide-react'
import { api } from '../../services/api'
import type { ReportMetadata } from '../../types'

interface Props { onBack: () => void }

export default function RecentReports({ onBack }: Props) {
  const [reports, setReports] = useState<ReportMetadata[]>([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)

  const loadReports = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.listReports()
      setReports(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load reports.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadReports() }, [])

  const download = (report: ReportMetadata) => {
    const url = api.getReportDownloadUrl(report.report_id)
    const a = document.createElement('a')
    a.href = url
    a.download = report.filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
    } catch { return iso }
  }

  return (
    <div className="flex flex-col h-full">

      {/* Top bar */}
      <div className="flex-shrink-0 flex items-center justify-between px-4 py-3 border-b border-border bg-surface">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="p-1.5 hover:bg-surface2 rounded-lg transition-colors">
            <ArrowLeft className="text-muted" style={{ width: 16, height: 16 }} />
          </button>
          <div>
            <h2 className="text-[13px] font-bold text-text">Recent Reports</h2>
            <p className="text-[10px] text-muted">In-memory · Expire after 4 hours</p>
          </div>
        </div>
        <button
          onClick={loadReports}
          className="p-1.5 hover:bg-surface2 rounded-lg transition-colors"
          title="Refresh"
        >
          <RefreshCw
            className={`text-muted ${loading ? 'animate-spin' : ''}`}
            style={{ width: 15, height: 15 }}
          />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="text-accent animate-spin" style={{ width: 20, height: 20 }} />
          </div>
        )}

        {!loading && error && (
          <div
            className="flex items-start gap-2 p-3 rounded-xl border text-xs"
            style={{ background: 'rgba(244,67,54,0.06)', borderColor: 'rgba(244,67,54,0.25)' }}
          >
            <AlertCircle className="text-hold flex-shrink-0 mt-0.5" style={{ width: 14, height: 14 }} />
            <p className="text-muted">{error}</p>
          </div>
        )}

        {!loading && !error && reports.length === 0 && (
          <div className="text-center py-16">
            <FileSpreadsheet className="text-muted mx-auto mb-3" style={{ width: 32, height: 32 }} />
            <p className="text-xs text-muted">No recent reports</p>
            <p className="text-[10px] text-muted/55 mt-1">
              Generate a report in Find Stone by Demand
            </p>
          </div>
        )}

        {!loading && reports.length > 0 && (
          <div className="space-y-2">
            {reports.map(report => (
              <div
                key={report.report_id}
                className="bg-surface border border-border rounded-xl p-3 flex items-start gap-3"
              >
                <div className="w-9 h-9 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <FileSpreadsheet className="text-accent" style={{ width: 16, height: 16 }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] font-medium text-text truncate" title={report.customer_message}>
                    {report.customer_message}
                  </p>
                  <p className="text-[10px] text-muted mt-0.5">{formatDate(report.created_at)}</p>
                  <p className="text-[10px] text-accent mt-0.5 font-medium">
                    {report.total_matched} diamonds matched
                  </p>
                </div>
                <button
                  onClick={() => download(report)}
                  className="p-2 rounded-lg border flex-shrink-0 transition-colors"
                  style={{ background: 'rgba(196,163,90,0.08)', borderColor: 'rgba(196,163,90,0.22)' }}
                  title="Download Excel"
                >
                  <Download className="text-accent" style={{ width: 14, height: 14 }} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
