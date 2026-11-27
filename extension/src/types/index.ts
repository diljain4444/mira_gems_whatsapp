// All shared TypeScript types for Mira Companion

export interface StoneDetail {
  StockId: string
  Availability: string
  Shape: string
  Weight: number | null
  Color: string
  Clarity: string
  Cut: string
  Polish: string
  Symm: string
  business_category: string
  Lab: string
  Fls: string
  FinalPrice: number | null
  Location: string
  Measurements: string
  StockDate?: string
  Days?: string
}

export interface StoneLookupResponse {
  total_requested: number
  unique_requested: number
  total_found: number
  total_not_found: number
  total_duplicates: number
  matched_stones: StoneDetail[]
  not_found: string[]
  duplicates: string[]
}

export interface ExtractedRequirement {
  shape: string
  color: string | string[]
  clarity: string | string[]
  business_category: string
  cut?: string
  polish?: string
  symm?: string
  certification: string
  fluorescence: string
  carat_min: number | null
  carat_max: number | null
}

export interface DiamondMatch {
  StockId: string
  Availability: string
  Shape: string
  Weight: number | null
  Color: string
  Clarity: string
  Cut: string
  Polish: string
  Symm: string
  business_category: string
  Lab: string
  Fls: string
  FinalPrice: number | null
  Location: string
  Measurements: string
}

/** A diamond returned as a closest alternative when no exact match is found. */
export interface SimilarDiamondMatch extends DiamondMatch {
  similarity_score: number | null
  /** Human-readable badges explaining what differs from the demand.
   *  e.g. ["Color: E (better)", "Carat: 10.50ct (+5%)"] */
  diff_tags: string[]
}

export interface DemandSearchResponse {
  customer_message: string
  extracted_requirement: ExtractedRequirement
  total_inventory: number
  total_available: number
  total_matched: number
  total_available_not_matched: number
  matched_diamonds: DiamondMatch[]
  /** Populated only when total_matched === 0 */
  similar_diamonds: SimilarDiamondMatch[]
}

export interface ReportMetadata {
  report_id: string
  created_at: string
  customer_message: string
  total_matched: number
  filename: string
}

export interface GenerateReportPayload {
  customer_message: string
  extracted_requirement: ExtractedRequirement
  matched_diamonds: DiamondMatch[]
  total_inventory: number
  total_available: number
  total_matched: number
  total_available_not_matched: number
}

export interface GenerateReportResponse {
  report_id: string
  filename: string
  created_at: string
  total_matched: number
}

export type Screen = 'home' | 'stone-by-id' | 'stone-by-demand' | 'reports' | 'settings' | 'save-lead'

// ─── Lead Logger Types ──────────────────────────────────────────────────────

export interface ChatMessagePayload {
  sender: string   // "me" | "customer"
  time:   string
  date:   string
  text:   string
}

export interface DiamondDemandOut {
  shape:                  string | null
  carat_min:              number | null
  carat_max:              number | null
  color:                  string | null
  clarity:                string | null
  cut_grade:              string | null
  lab:                    string | null
  growth_type:            string | null
  special_criteria:       string | null
  target_price_per_carat: number | null
  in_stock_at_time:       boolean | null
}

export interface StoneQuoteOut {
  stock_id:               string
  quoted_price_per_carat: number | null
  customer_counter_offer: number | null
  stone_status:           string
  rejection_note:         string | null
}

export interface SaveLeadResponse {
  session_id:           number
  customer_id:          number
  customer_name:        string | null
  customer_phone:       string
  deal_outcome:         string | null
  lost_reason_category: string | null
  lost_reason_detail:   string | null
  ai_summary:           string | null
  next_action:          string | null
  follow_up_date:       string | null
  urgency:              string | null
  sentiment:            string | null
  price_sensitivity:    string | null
  diamond_demands:      DiamondDemandOut[]
  stone_quotes:         StoneQuoteOut[]
  created_at:           string
  is_duplicate?:        boolean
  duplicate_message?:   string | null
  seller_name?:         string | null
}

export interface LeadSummary {
  session_id:           number
  customer_name:        string | null
  customer_phone:       string
  seller_name?:         string | null
  deal_outcome:         string | null
  lost_reason_category: string | null
  ai_summary:           string | null
  created_at:           string
  total_demands:        number
  total_quotes:         number
}

export interface LeadListResponse {
  total: number
  leads: LeadSummary[]
}
