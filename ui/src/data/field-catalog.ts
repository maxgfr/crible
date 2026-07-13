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
  // valuation
  market_cap: { label: "Market cap", group: "Valuation" },
  price_to_earnings_ratio: { label: "P/E", group: "Valuation" },
  price_to_book_ratio: { label: "P/B", group: "Valuation" },
  price_to_sales_ratio: { label: "P/S", group: "Valuation" },
  earnings_yield: { label: "Earnings yield", group: "Valuation" },
  earnings_per_share: { label: "EPS", group: "Valuation" },
  // profitability & health
  return_on_equity: { label: "ROE", group: "Profitability" },
  return_on_assets: { label: "ROA", group: "Profitability" },
  net_profit_margin: { label: "Net margin", group: "Profitability" },
  gross_margin: { label: "Gross margin", group: "Profitability" },
  operating_margin: { label: "Operating margin", group: "Profitability" },
  debt_to_equity_ratio: { label: "Debt / equity", group: "Health" },
  current_ratio: { label: "Current ratio", group: "Health" },
  quick_ratio: { label: "Quick ratio", group: "Health" },
  interest_coverage_ratio: { label: "Interest coverage", group: "Health" },
  // scores
  piotroski_f: { label: "Piotroski F", group: "Scores" },
  altman_z: { label: "Altman Z", group: "Scores" },
  beneish_m: { label: "Beneish M", group: "Scores" },
  // ranks & momentum (FR-015)
  composite_rank: { label: "Composite rank", group: "Ranks" },
  quality_rank: { label: "Quality rank", group: "Ranks" },
  value_rank: { label: "Value rank", group: "Ranks" },
  momentum_rank: { label: "Momentum rank", group: "Ranks" },
  rank_peer_group: { label: "Rank peer group", group: "Ranks" },
  return_6m: { label: "6-month return", group: "Ranks" },
};

// display order for the field select's optgroups; unknown groups append after
export const GROUP_ORDER = [
  "Identity", "Scores", "Ranks", "Valuation", "Profitability", "Health",
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

export function fieldLabel(name: string): string {
  return CATALOG[name]?.label ?? name.replaceAll("_", " ");
}

export function fieldGroup(name: string): string {
  const entry = CATALOG[name];
  if (entry) return entry.group;
  if (name.endsWith("_growth")) return "Growth (YoY)";
  if (name.endsWith("_rank") || name.startsWith("rank_")) return "Ranks";
  if (name.startsWith("piotroski_") || name.startsWith("altman_") || name.startsWith("beneish_")) {
    return "Scores";
  }
  return "Other";
}
