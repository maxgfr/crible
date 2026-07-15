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
  debt_to_equity_ratio: { label: "Debt / equity", group: "Health" },
  current_ratio: { label: "Current ratio", group: "Health" },
  quick_ratio: { label: "Quick ratio", group: "Health" },
  interest_coverage_ratio: { label: "Interest coverage", group: "Health" },
  dividend_coverage: { label: "Dividend cover", group: "Health" },
  // growth (every fundamental has a _growth companion; these two are curated)
  revenue_growth: { label: "Revenue growth (YoY)", group: "Growth (YoY)" },
  net_income_growth: { label: "Earnings growth (YoY)", group: "Growth (YoY)" },
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
  "Fundamentals", "Growth (YoY)", "Other",
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
