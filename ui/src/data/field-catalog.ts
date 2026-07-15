// Friendly labels + groups for the query builder. The RUNTIME SCHEMA is the
// source of truth for which fields exist (DESCRIBE snapshot_latest through
// DataClient.fields()); this catalog only decorates known columns. Unknown
// columns fall back to humanized snake_case + suffix heuristics, so the
// builder can never offer a field the compiler whitelist would reject —
// and never hides one either.

export interface CatalogEntry {
  label: string;
  group: string;
}

const CATALOG: Record<string, CatalogEntry> = {
  // identity & universe metadata
  symbol: { label: "Symbol", group: "Identity" },
  name: { label: "Name", group: "Identity" },
  country: { label: "Country (ISO)", group: "Identity" },
  country_name: { label: "Country", group: "Identity" },
  region: { label: "Region", group: "Identity" },
  sector: { label: "Sector", group: "Identity" },
  industry: { label: "Industry", group: "Identity" },
  exchange: { label: "Exchange", group: "Identity" },
  currency: { label: "Currency", group: "Identity" },
  period: { label: "Fiscal period", group: "Identity" },
  // headline fundamentals (canonical fields)
  revenue: { label: "Revenue", group: "Fundamentals" },
  gross_profit: { label: "Gross profit", group: "Fundamentals" },
  operating_income: { label: "Operating income", group: "Fundamentals" },
  net_income: { label: "Net income", group: "Fundamentals" },
  total_assets: { label: "Total assets", group: "Fundamentals" },
  total_equity: { label: "Total equity", group: "Fundamentals" },
  total_debt: { label: "Total debt", group: "Fundamentals" },
  operating_cashflow: { label: "Operating cash flow", group: "Fundamentals" },
  free_cash_flow: { label: "Free cash flow", group: "Fundamentals" },
  shares_outstanding: { label: "Shares outstanding", group: "Fundamentals" },
  // valuation (column names verified against the published snapshot schema)
  market_cap: { label: "Market cap", group: "Valuation" },
  price_to_earnings_ratio: { label: "P/E", group: "Valuation" },
  price_to_book_ratio: { label: "P/B", group: "Valuation" },
  price_to_cash_flow_ratio: { label: "P/CF", group: "Valuation" },
  price_to_free_cash_flow_ratio: { label: "P/FCF", group: "Valuation" },
  ev_to_sales_ratio: { label: "EV/Sales", group: "Valuation" },
  ev_to_ebitda_ratio: { label: "EV/EBITDA", group: "Valuation" },
  earnings_yield: { label: "Earnings yield", group: "Valuation" },
  free_cash_flow_yield: { label: "FCF yield", group: "Valuation" },
  weighted_dividend_yield: { label: "Dividend yield", group: "Valuation" },
  peg_ratio: { label: "PEG (3y)", group: "Valuation" },
  shareholder_yield: { label: "Shareholder yield", group: "Valuation" },
  // profitability & health
  return_on_equity: { label: "ROE", group: "Profitability" },
  return_on_assets: { label: "ROA", group: "Profitability" },
  return_on_capital_employed: { label: "ROCE", group: "Profitability" },
  net_profit_margin: { label: "Net margin", group: "Profitability" },
  gross_margin: { label: "Gross margin", group: "Profitability" },
  operating_margin: { label: "Operating margin", group: "Profitability" },
  ebitda: { label: "EBITDA", group: "Fundamentals" },
  ebitda_margin: { label: "EBITDA margin", group: "Profitability" },
  fcf_margin: { label: "FCF margin", group: "Profitability" },
  fcf_conversion: { label: "FCF conversion", group: "Profitability" },
  income_quality_ratio: { label: "Income quality (OCF/NI)", group: "Profitability" },
  effective_tax_rate: { label: "Effective tax rate", group: "Profitability" },
  return_on_invested_capital: { label: "ROIC", group: "Profitability" },
  rule_of_40: { label: "Rule of 40", group: "Profitability" },
  sloan_accruals: { label: "Sloan accruals", group: "Profitability" },
  debt_to_equity_ratio: { label: "Debt / equity", group: "Health" },
  current_ratio: { label: "Current ratio", group: "Health" },
  quick_ratio: { label: "Quick ratio", group: "Health" },
  cash_ratio: { label: "Cash ratio", group: "Health" },
  interest_coverage_ratio: { label: "Interest coverage", group: "Health" },
  net_debt_to_ebitda_ratio: { label: "Net debt / EBITDA", group: "Health" },
  dividend_coverage: { label: "Dividend cover", group: "Health" },
  dividend_payout_ratio: { label: "Payout ratio", group: "Health" },
  capex_coverage_ratio: { label: "Capex coverage", group: "Health" },
  // efficiency (turnover & working-capital cycle)
  asset_turnover_ratio: { label: "Asset turnover", group: "Efficiency" },
  inventory_turnover_ratio: { label: "Inventory turnover", group: "Efficiency" },
  days_of_sales_outstanding: { label: "DSO (days)", group: "Efficiency" },
  days_of_inventory_outstanding: { label: "DIO (days)", group: "Efficiency" },
  days_of_accounts_payable_outstanding: { label: "DPO (days)", group: "Efficiency" },
  cash_conversion_cycle: { label: "Cash conversion cycle (days)", group: "Efficiency" },
  operating_cycle: { label: "Operating cycle (days)", group: "Efficiency" },
  sga_to_revenue_ratio: { label: "SG&A / revenue", group: "Efficiency" },
  // growth (every fundamental has a _growth companion; these are curated)
  revenue_growth: { label: "Revenue growth (YoY)", group: "Growth (YoY)" },
  net_income_growth: { label: "Earnings growth (YoY)", group: "Growth (YoY)" },
  operating_cashflow_growth: { label: "OCF growth (YoY)", group: "Growth (YoY)" },
  free_cash_flow_growth: { label: "FCF growth (YoY)", group: "Growth (YoY)" },
  total_debt_growth: { label: "Debt growth (YoY)", group: "Growth (YoY)" },
  // scores
  piotroski_f: { label: "Piotroski F", group: "Scores" },
  altman_z: { label: "Altman Z", group: "Scores" },
  beneish_m: { label: "Beneish M", group: "Scores" },
  zmijewski_score: { label: "Zmijewski", group: "Scores" },
  ohlson_o: { label: "Ohlson O", group: "Scores" },
  montier_c: { label: "Montier C", group: "Scores" },
  // ranks & momentum (FR-015)
  composite_rank: { label: "Composite rank", group: "Ranks" },
  quality_rank: { label: "Quality rank", group: "Ranks" },
  value_rank: { label: "Value rank", group: "Ranks" },
  momentum_rank: { label: "Momentum rank", group: "Ranks" },
  rank_peer_group: { label: "Rank peer group", group: "Ranks" },
  return_6m: { label: "6-month return", group: "Ranks" },
  // value toolkit (Greenblatt magic formula, Graham number & net-net)
  magic_formula_rank: { label: "Magic Formula rank", group: "Value" },
  greenblatt_earnings_yield: { label: "Earnings yield (EBIT/EV)", group: "Value" },
  greenblatt_roc: { label: "Return on capital", group: "Value" },
  graham_number: { label: "Graham number", group: "Value" },
  graham_margin_of_safety: { label: "Margin of safety", group: "Value" },
  ncav: { label: "NCAV", group: "Value" },
  ncav_to_market_cap: { label: "NCAV / mkt cap", group: "Value" },
};

// display order for the field select's optgroups; unknown groups append after
export const GROUP_ORDER = [
  "Identity", "Scores", "Ranks", "Value", "Valuation", "Profitability", "Health",
  "Efficiency", "Fundamentals", "Growth (YoY)", "Other",
];

// enumerated string fields get a value dropdown instead of free text
export const ENUM_VALUES: Record<string, string[]> = {
  region: ["europe", "us", "world"],
  // FinanceDatabase sector vocabulary (GICS-like)
  sector: [
    "Communication Services", "Consumer Discretionary", "Consumer Staples",
    "Energy", "Financials", "Health Care", "Industrials",
    "Information Technology", "Materials", "Real Estate", "Utilities",
  ],
};

// The classic screener criteria (the Finviz/Stockopedia fundamental set),
// pinned as one-click starter chips in the query builder. Default values are
// editable starting points, not recommendations; a chip only shows when its
// column exists in the live schema. Decimal convention: 0.15 = 15 %.
export interface StarterFilter {
  field: string;
  op: ">" | ">=" | "<" | "<=" | "=";
  value: string;
}

export const STARTER_FILTERS: StarterFilter[] = [
  { field: "market_cap", op: ">=", value: "1000000000" },
  { field: "price_to_earnings_ratio", op: "<=", value: "15" },
  { field: "price_to_book_ratio", op: "<=", value: "1.5" },
  { field: "weighted_dividend_yield", op: ">=", value: "0.03" },
  { field: "return_on_equity", op: ">=", value: "0.15" },
  { field: "debt_to_equity_ratio", op: "<=", value: "1" },
  { field: "net_profit_margin", op: ">=", value: "0.1" },
  { field: "revenue_growth", op: ">=", value: "0.1" },
  { field: "peg_ratio", op: "<=", value: "1" },
  { field: "rule_of_40", op: ">=", value: "0.4" },
  { field: "piotroski_f", op: ">=", value: "7" },
  { field: "altman_z", op: ">", value: "2.99" },
  { field: "composite_rank", op: ">=", value: "80" },
  { field: "magic_formula_rank", op: ">=", value: "80" },
  { field: "ncav_to_market_cap", op: ">=", value: "1.5" },
  { field: "zmijewski_score", op: "<", value: "0" },
  { field: "montier_c", op: "<=", value: "1" },
  { field: "graham_margin_of_safety", op: ">", value: "0" },
  { field: "region", op: "=", value: "europe" },
  { field: "sector", op: "=", value: "" },
  { field: "country", op: "=", value: "" },
];

// Columns the published snapshot may still carry but the UI must not offer:
// the price-based ratios' _growth companions are always NaN (price applies
// to the latest period only, so pct_change never resolves), and
// net_current_asset_value duplicates ncav. They stay hand-queryable — the
// compiler whitelist is untouched; the engine stops generating them, which
// retires this list once the published data catches up.
export const HIDDEN_FIELDS = new Set([
  "earnings_yield_growth",
  "free_cash_flow_yield_growth",
  "ev_to_ebit_growth",
  "ev_to_ebitda_ratio_growth",
  "ev_to_operating_cashflow_ratio_growth",
  "ev_to_sales_ratio_growth",
  "market_cap_growth",
  "price_to_book_ratio_growth",
  "price_to_cash_flow_ratio_growth",
  "price_to_earnings_ratio_growth",
  "price_to_free_cash_flow_ratio_growth",
  "weighted_dividend_yield_growth",
  "net_current_asset_value",
  "net_current_asset_value_growth",
]);

export function isHiddenField(name: string): boolean {
  return HIDDEN_FIELDS.has(name);
}

export function fieldLabel(name: string): string {
  return CATALOG[name]?.label ?? name.replaceAll("_", " ");
}

export function fieldGroup(name: string): string {
  const entry = CATALOG[name];
  if (entry) return entry.group;
  if (name.endsWith("_growth")) return "Growth (YoY)";
  if (
    name.startsWith("greenblatt_") || name.startsWith("graham_") ||
    name.startsWith("ncav") || name.startsWith("magic_formula")
  ) {
    return "Value";
  }
  if (name.endsWith("_rank") || name.startsWith("rank_")) return "Ranks";
  if (
    name.startsWith("piotroski_") || name.startsWith("altman_") || name.startsWith("beneish_") ||
    name.startsWith("zmijewski") || name.startsWith("ohlson") || name.startsWith("montier")
  ) {
    return "Scores";
  }
  return "Other";
}
