# Indicators & scores reference · Référence des indicateurs

**EN** — Every score and derived metric crible computes, with its formula (in crible's
canonical field names), how to read it, and honest caveats. Every value is traceable to
its inputs, and **a missing input propagates as `NaN` — never imputed**; the snapshot's
`missing_inputs` column names the absent fields.

**FR** — Chaque score et métrique dérivée calculés par crible, avec sa formule (dans les
noms de champs canoniques de crible), sa lecture et ses limites assumées. Chaque valeur
est traçable jusqu'à ses entrées, et **une entrée manquante se propage en `NaN` — jamais
imputée** ; la colonne `missing_inputs` du snapshot nomme les champs absents.

> All formulas are verified two ways: hand-computed unit tests (`tests/test_fr003_compute.py`,
> `tests/test_fr015_ranks.py`) and an independent recomputation from the published snapshot.
> Les formules sont vérifiées de deux façons : tests unitaires main-calculés et un
> recalcul indépendant depuis le snapshot publié.

## Summary · Récapitulatif

| Field | Indicator | Range | Better · Meilleur | Flag threshold · Seuil d'alerte |
|---|---|---|---|---|
| `zmijewski_score` | Zmijewski distress | ~unbounded | lower · plus bas | `> 0` → distress |
| `ohlson_o` | Ohlson O-Score | ~unbounded | lower · plus bas | `> 0` → distress |
| `montier_c` | Montier C-Score | 0–6 | lower · plus bas | `>= 5` → aggressive |
| `magic_formula_rank` | Greenblatt magic formula | 0–100 | higher · plus haut | `>= 80` → top quintile |
| `graham_number` | Graham intrinsic value | ≥ 0 | — | compare to price |
| `graham_margin_of_safety` | vs price | ~unbounded | higher · plus haut | `> 0` → below Graham |
| `ncav` | Net current asset value | ~unbounded | higher · plus haut | `> 0` → net-net candidate |
| `ncav_to_market_cap` | NCAV / market cap | ~unbounded | higher · plus haut | `>= 1.5` → classic net-net |
| `ebitda_margin` | EBITDA / revenue | ~unbounded | higher · plus haut | — |
| `fcf_margin` | FCF / revenue | ~unbounded | higher · plus haut | — |
| `fcf_conversion` | FCF / net income | ~unbounded | higher · plus haut | `< 1` → weak cash conversion |
| `dividend_coverage` | net income / dividends | ~unbounded | higher · plus haut | `< 1` → dividend not covered |
| `cash_conversion_cycle` | DIO + DSO − DPO (days) | ~unbounded | lower · plus bas | — |
| `dividend_payout_ratio` | dividends / net income | ≥ 0 | context | — |
| `rule_of_40` | revenue growth + FCF margin | ~unbounded | higher · plus haut | `>= 0.4` → passes the rule |
| `sloan_accruals` | (NI − OCF) / avg assets | ~unbounded | lower · plus bas | — |
| `peg_ratio` | P/E ÷ 3y EPS CAGR (%) | > 0 | lower · plus bas | `<= 1` → growth at a reasonable price |
| `shareholder_yield` | (dividends + net buybacks) / mkt cap | ~unbounded | higher · plus haut | — |
| `mohanram_g` | Mohanram G (partial 6/8) | 0–6 | higher · plus haut | — (partial score, no published cutoff) |
| `dechow_f` | Dechow F (Model 1) | ≥ 0 | lower · plus bas | `>= 1` above-normal · `>= 1.85` substantial |
| `return_12_1` | 12-month return, last month skipped | ~unbounded | higher · plus haut | — |
| `high_52w_proximity` | close / 52-week high | 0–1 | higher · plus haut | — |
| `volatility_1y` | annualized σ of daily log returns | ≥ 0 | context | — |
| `ttm_*` / `price_to_earnings_ttm` / `price_to_sales_ttm` / `ttm_fcf_yield` | trailing 12 months | — | — | crawled + audited discrete-quarter issuers |
| `revenue_cagr_3y` / `net_income_cagr_3y` | 3-year compound growth | ~unbounded | higher · plus haut | — |
| `roic` | NOPAT / average invested capital | ~unbounded | higher · plus haut | — (`>= 0.15` in Quality compounders) |
| `gross_profitability` | gross profit / total assets | ~0–1 | higher · plus haut | — |
| `net_share_issuance` | YoY change of the period-end share count | ~unbounded | lower · plus bas | `> 0` → dilution |
| `positive_fcf_years_5y` | positive-FCF years among the last 5 | 0–5 | higher · plus haut | — |
| `altman_z_double_prime` | Altman Z″ (non-manufacturers, book equity) | ~unbounded | higher · plus haut | `> 2.6` safe · `< 1.1` distress |

Direction reminder: distress and manipulation scores are **risk** measures (lower is
safer); value and quality metrics are **opportunity** measures (higher is better).
Rappel : les scores de détresse/manipulation mesurent un **risque** (plus bas = plus sûr) ;
les métriques value/qualité mesurent une **opportunité** (plus haut = meilleur).

---

## 1. Zmijewski score — `zmijewski_score`

**Formula**

```
X = −4.336 − 4.513·(net_income / total_assets)
            + 5.679·(total_liabilities / total_assets)
            + 0.004·(current_assets / current_liabilities)
probability of distress = 1 / (1 + e^(−X))
```

**EN** — A probit bankruptcy model (Zmijewski, 1984) that blends three signals:
profitability (ROA), leverage, and liquidity. The score is the model's linear predictor;
running it through the logistic function gives a probability of financial distress. `X > 0`
means the model assigns > 50 % probability of distress — the higher, the riskier. It is the
simplest of the three distress models (three ratios, no prior year needed), so it is the one
most often available.

**FR** — Modèle probit de faillite (Zmijewski, 1984) qui combine trois signaux : rentabilité
(ROA), levier et liquidité. Le score est le prédicteur linéaire du modèle ; passé dans la
fonction logistique il donne une probabilité de détresse financière. `X > 0` signifie que le
modèle estime > 50 % de probabilité de détresse — plus c'est haut, plus c'est risqué. C'est le
plus simple des trois modèles de détresse (trois ratios, sans année précédente), donc le plus
souvent disponible.

> **Caveat · Nuance** — The liquidity coefficient (`+0.004`) is tiny and positive, which is
> counter-intuitive (more liquidity nudges the score *up*); this is faithful to the published
> model and kept as-is. · Le coefficient de liquidité (`+0.004`) est minuscule et positif, ce
> qui est contre-intuitif ; c'est fidèle au modèle publié et conservé tel quel.

---

## 2. Ohlson O-Score — `ohlson_o`

**Formula**

```
O = −1.32 − 0.407·log(total_assets)
        + 6.03·(total_liabilities / total_assets)
        − 1.43·(working_capital / total_assets)
        + 0.0757·(current_liabilities / current_assets)
        − 1.72·OENEG − 2.37·(net_income / total_assets)
        − 1.83·(operating_cashflow / total_liabilities)
        + 0.285·INTWO − 0.521·CHIN

OENEG = 1 if total_liabilities > total_assets else 0        (negative equity)
INTWO = 1 if net_income < 0 in both this year AND last year else 0
CHIN  = (NIₜ − NIₜ₋₁) / (|NIₜ| + |NIₜ₋₁|)                    (scaled change in earnings)
probability of distress = 1 / (1 + e^(−O))
```

**EN** — A 9-variable logistic bankruptcy model (Ohlson, 1980), generally regarded as more
accurate than Altman's Z on modern data. It adds size, negative-equity and earnings-trajectory
signals on top of leverage and liquidity. `O > 0` corresponds to > 50 % modelled probability
of distress. Because `CHIN` and `INTWO` compare two consecutive years, **the earliest period
of a company is always `NaN`**.

**FR** — Modèle logistique de faillite à 9 variables (Ohlson, 1980), généralement jugé plus
précis que le Z d'Altman sur données récentes. Il ajoute la taille, les capitaux propres
négatifs et la trajectoire des résultats, en plus du levier et de la liquidité. `O > 0`
correspond à > 50 % de probabilité modélisée de détresse. Comme `CHIN` et `INTWO` comparent
deux années consécutives, **la première période d'une société est toujours `NaN`**.

> **Caveats · Nuances** — Two documented deviations from the 1980 paper, because crible is
> multi-currency and provider-agnostic (Ohlson fitted a US-firm sample): the size term uses
> `log(total_assets)` directly instead of dividing assets by a US GNP price-level index; and
> "funds from operations" is proxied by `operating_cashflow` (alternative: `net_income +
> depreciation_and_amortization`). The practical cutoff is often stated as probability > 0.5
> (`O > 0`); Ohlson's own misclassification-minimising cutoff was ≈ 0.038.
> · Deux écarts documentés au papier de 1980, crible étant multi-devises et agnostique du
> fournisseur : le terme de taille utilise `log(total_assets)` au lieu de diviser l'actif par
> un indice de prix PNB américain ; et les « funds from operations » sont approximés par
> `operating_cashflow`. Le seuil pratique est souvent une probabilité > 0,5 (`O > 0`).

---

## 3. Montier C-Score — `montier_c` (+ 6 flags)

**Formula** — sum of six red flags (each 0 or 1); `montier_c` ∈ {0…6}. A raised flag is **bad**.

| Flag column | Raised (=1) when… |
|---|---|
| `montier_ni_cfo_diverging` | `net_income − operating_cashflow` grows vs last year (earnings outrun cash) |
| `montier_dso_rising` | days sales outstanding `accounts_receivable/revenue` rises |
| `montier_dsi_rising` | days sales of inventory `inventory/cost_of_goods_sold` rises |
| `montier_oca_to_rev_rising` | other current assets / revenue rises |
| `montier_depr_declining` | depreciation rate `D&A/gross_ppe` falls (lives extended to lift earnings) |
| `montier_asset_growth_high` | total assets grow `> 10 %` (aggressive/acquisitive) |

**EN** — James Montier's "Cooking the Books" checklist (2008): six accounting red flags that,
together, flag likely earnings manipulation — a companion to Beneish's M-Score with a simpler,
binary reading. 0–1 is clean, 5–6 is an aggressive-accounting candidate. Each flag compares the
current year with the prior one, so **the first period is `NaN`**, and a flag whose inputs are
missing nulls the whole score (never imputed).

**FR** — La checklist « Cooking the Books » de James Montier (2008) : six drapeaux comptables
qui, ensemble, signalent une probable manipulation des résultats — complément du M-Score de
Beneish avec une lecture binaire plus simple. 0–1 est propre, 5–6 est un candidat à la
comptabilité agressive. Chaque drapeau compare l'année courante à la précédente, donc **la
première période est `NaN`**, et un drapeau dont les entrées manquent annule tout le score.

> **Caveats · Nuances** — crible has only a combined `depreciation_and_amortization` (not
> depreciation alone), so the depreciation-rate flag uses `D&A/gross_ppe` as a proxy; "other
> current assets" is proxied by `current_assets − cash − receivables − inventory`.
> · crible n'a qu'un `depreciation_and_amortization` combiné, donc le drapeau de dépréciation
> utilise `D&A/gross_ppe` comme proxy ; les « autres actifs courants » sont approximés.

---

## 4. Greenblatt magic formula — `magic_formula_rank`, `greenblatt_earnings_yield`, `greenblatt_roc`

**Formula**

```
greenblatt_earnings_yield = EBIT / enterprise_value          (cheapness)
greenblatt_roc            = EBIT / (working_capital + net_ppe)  (capital efficiency)
magic_formula_rank        = mean( percentile(earnings_yield ↑), percentile(roc ↑) )   → 0–100
```

**EN** — Joel Greenblatt's *Magic Formula* (2005) ranks companies by two factors at once:
how cheap they are (earnings yield, EBIT/EV) and how good the business is (return on capital,
EBIT over tangible capital employed). crible publishes each factor plus a combined 0–100
`magic_formula_rank`, computed within the company's peer group (region×sector when it holds
≥ 5 companies, otherwise the whole snapshot). Higher is better; `>= 80` is the top quintile.

**FR** — La *Magic Formula* de Joel Greenblatt (2005) classe les sociétés sur deux facteurs à
la fois : leur bon marché (earnings yield, EBIT/EV) et la qualité du business (return on
capital, EBIT sur le capital tangible employé). crible publie chaque facteur plus un
`magic_formula_rank` combiné 0–100, calculé au sein du groupe de pairs (région×secteur si ≥ 5
sociétés, sinon tout le snapshot). Plus haut = meilleur ; `>= 80` est le quintile de tête.

> **Caveats · Nuances** — Greenblatt ranks by ordinal position and sums the two ranks; crible
> uses a percentile-mean (equivalent ordering, native to its rank system). When invested capital
> (`working_capital + net_ppe`) or enterprise value is **non-positive**, the ratio would sign-flip
> and is left **undefined (NaN)** — the company is simply excluded from `magic_formula_rank`, never
> imputed. Greenblatt also excludes financials and utilities, which crible does **not**. The rank is
> kept **separate** from `composite_rank`. · Greenblatt classe par rang ordinal et somme les deux
> rangs ; crible utilise une moyenne de percentiles (ordre équivalent). Quand le capital investi
> (`working_capital + net_ppe`) ou l'enterprise value est **non positif**, le ratio s'inverserait :
> il est laissé **indéfini (NaN)** — la société est exclue de `magic_formula_rank`, jamais imputée.
> Greenblatt exclut aussi la finance et les utilities, ce que crible ne fait **pas**. Rang **séparé**
> de `composite_rank`.

---

## 5. Graham number — `graham_number`, `graham_margin_of_safety`

**Formula**

```
EPS  = net_income / shares_outstanding            (weighted average)
BVPS = total_equity / shares_outstanding_end      (period-end count, average as fallback)
graham_number = √( 22.5 · EPS · BVPS )        only when EPS > 0 AND BVPS > 0, else NaN
graham_margin_of_safety = graham_number / price − 1
```

**EN** — Benjamin Graham's back-of-envelope fair value for a defensive investor. The `22.5`
is `15 × 1.5` — his ceilings of 15× earnings and 1.5× book value. `graham_margin_of_safety`
compares it to the current price: `> 0` means the stock trades **below** its Graham number
(a margin of safety). It is only defined for profitable companies with positive book value.

**FR** — La juste valeur « au dos de l'enveloppe » de Benjamin Graham pour l'investisseur
défensif. Le `22.5` vaut `15 × 1,5` — ses plafonds de 15× les bénéfices et 1,5× la valeur
comptable. `graham_margin_of_safety` la compare au prix : `> 0` signifie que le titre se
traite **sous** son nombre de Graham (marge de sécurité). Défini seulement pour les sociétés
rentables à valeur comptable positive.

> **Caveat · Nuance** — Price applies to the **latest fiscal period only** (crible never
> back-dates prices), so `graham_margin_of_safety` is populated on the latest row alone.
> · Le prix ne s'applique qu'à la **dernière période fiscale** ; `graham_margin_of_safety`
> n'est renseigné que sur la ligne la plus récente.

---

## 6. NCAV / net-net — `ncav`, `ncav_to_market_cap`

**Formula**

```
ncav = current_assets − total_liabilities            (Graham's net current asset value)
ncav_to_market_cap = ncav / market_cap
```

**EN** — Graham's deepest value screen: net current asset value is what's left for shareholders
if you liquidate current assets and pay off **all** liabilities. A "net-net" is a stock trading
below two-thirds of its NCAV per share — i.e. `ncav_to_market_cap >= 1.5` (market cap ≤ ⅔·NCAV).
Rare, often tiny or distressed companies, but historically a strong deep-value cohort.

**FR** — Le screen value le plus profond de Graham : la valeur nette des actifs courants est ce
qui reste aux actionnaires si l'on liquide les actifs courants et rembourse **tout** le passif.
Un « net-net » est un titre qui se traite sous les deux tiers de sa NCAV par action — soit
`ncav_to_market_cap >= 1.5` (capitalisation ≤ ⅔·NCAV). Rare, souvent petites sociétés ou en
difficulté, mais historiquement une cohorte deep-value performante.

> **Caveat · Nuance** — This is the strict form (current assets − total liabilities); crible
> does not track preferred stock separately to subtract it. `ncav_to_market_cap` needs a price,
> so it is latest-period only. · Forme stricte (actifs courants − passif total) ; crible ne suit
> pas les actions de préférence séparément. `ncav_to_market_cap` exige un prix (dernière période).

---

## 7. EBITDA & margin — `ebitda`, `ebitda_margin`

**Formula**

```
ebitda        = provider-reported EBITDA when available, else earnings_before_interest_and_taxes + depreciation_and_amortization
ebitda_margin = ebitda / revenue
```

**EN** — Earnings before interest, taxes, depreciation and amortization — a rough proxy for
operating cash generation before capital structure and accounting depreciation. crible prefers
the provider's reported EBITDA when present (higher fidelity) and otherwise derives it as
`EBIT + D&A`. `ebitda_margin` is the share of revenue that reaches EBITDA.

**FR** — Bénéfice avant intérêts, impôts, dépréciations et amortissements — un proxy grossier
de la génération de cash opérationnel avant structure de capital et amortissements comptables.
crible préfère l'EBITDA reporté par le fournisseur quand il existe (meilleure fidélité) et le
dérive sinon en `EBIT + D&A`. `ebitda_margin` est la part du chiffre d'affaires qui atteint
l'EBITDA.

> **Caveat · Nuance** — This `ebitda` field can differ slightly from the EBITDA that
> financetoolkit uses internally for `ev_to_ebitda_ratio` (which derives its own). · Ce champ
> `ebitda` peut légèrement différer de l'EBITDA utilisé en interne par financetoolkit pour
> `ev_to_ebitda_ratio`.

---

## 8. Free-cash-flow quality — `fcf_margin`, `fcf_conversion`

**Formula**

```
fcf_margin     = free_cash_flow / revenue
fcf_conversion = free_cash_flow / net_income
```

**EN** — How much cash the business actually keeps. `fcf_margin` is free cash flow as a share
of revenue; `fcf_conversion` is how much of reported earnings turns into free cash — above 1
means the company converts **more** than 100 % of its accounting profit into cash (a quality
sign); persistently below 1 hints earnings aren't backed by cash.

**FR** — Combien de cash le business garde réellement. `fcf_margin` est le free cash flow
rapporté au chiffre d'affaires ; `fcf_conversion` mesure combien des résultats comptables se
transforment en cash libre — au-dessus de 1, la société convertit **plus** de 100 % de son
profit comptable en cash (signe de qualité) ; durablement sous 1, les résultats ne sont pas
adossés à du cash.

> **Caveat · Nuance** — `fcf_conversion` is noisy when `net_income` is near zero or negative;
> read it alongside the level of earnings. · `fcf_conversion` est bruité quand `net_income` est
> proche de zéro ou négatif ; à lire avec le niveau de résultat.

---

## 9. Dividend coverage — `dividend_coverage`

**Formula**

```
dividend_coverage = net_income / |dividends_paid|        (NaN when no dividend is paid)
```

**EN** — How many times net income covers the dividend. `> 1` means earnings comfortably fund
the payout; `< 1` means the company pays out more than it earns (funded from reserves or debt —
a sustainability risk). Non-payers are `NaN`, not zero.

**FR** — Combien de fois le résultat net couvre le dividende. `> 1` signifie que les bénéfices
financent confortablement le versement ; `< 1` signifie que la société distribue plus qu'elle ne
gagne (puisé dans les réserves ou la dette — risque de soutenabilité). Les non-payeurs sont
`NaN`, pas zéro.

> **Caveat · Nuance** — Coverage is measured on net income, not free cash flow; a cash-based
> payout ratio would use `free_cash_flow`. · La couverture est mesurée sur le résultat net, pas
> le free cash flow ; un ratio basé cash utiliserait `free_cash_flow`.

---

## 10. Cash conversion cycle — `cash_conversion_cycle` (+ `operating_cycle`)

**Formula**

```
DIO = 365 · average_inventory / cost_of_goods_sold
DSO = 365 · average_accounts_receivable / revenue
DPO = 365 · average_accounts_payable / cost_of_goods_sold
cash_conversion_cycle = DIO + DSO − DPO          operating_cycle = DIO + DSO
```

**EN** — How many days cash is trapped in the working-capital loop: inventory sits, customers
pay late, suppliers get paid. Lower is better; a NEGATIVE cycle (retailers, marketplaces) means
suppliers finance the operations. Computed from the same published `days_of_*` components, so
the composite can never diverge from its displayed inputs.

**FR** — Combien de jours le cash reste piégé dans le cycle d'exploitation : les stocks dorment,
les clients paient tard, les fournisseurs sont réglés. Plus bas = mieux ; un cycle NÉGATIF
(distribution, places de marché) signifie que les fournisseurs financent l'exploitation. Calculé
depuis les mêmes composantes `days_of_*` publiées — le composite ne peut pas diverger de ses
entrées affichées.

> **Caveat · Nuance** — Averages need a prior year: the first period is `NaN`. Compare within a
> sector — cycles are structural. · Les moyennes exigent l'exercice précédent : la première
> période est `NaN`. À comparer au sein d'un secteur — les cycles sont structurels.

---

## 11. Dividend payout — `dividend_payout_ratio`

**Formula**

```
dividend_payout_ratio = |dividends_paid| / net_income
```

**EN** — The payout ratio is the inverse view of `dividend_coverage` (a payout of 0.5 = coverage
of 2): what share of earnings is distributed. The former `return_on_invested_capital` column is
**no longer published** (engine schema 9): financetoolkit's formula, (NI − dividends) /
(equity + debt), is not a return on invested capital, and a wrong ROIC is worse than none.
`greenblatt_roc` (EBIT / invested capital) is the return-on-capital measure to screen on.

**FR** — Le payout est la vue inverse de `dividend_coverage` (payout 0,5 = couverture 2) : la
part du résultat distribuée. L'ancienne colonne `return_on_invested_capital` **n'est plus
publiée** (schéma moteur 9) : la formule de financetoolkit, (RN − dividendes) / (capitaux
propres + dette), n'est pas un ROIC, et un faux ROIC est pire que pas de ROIC. Pour filtrer sur
la rentabilité du capital, utiliser `greenblatt_roc` (EBIT / capital investi).

---

## 12. Rule of 40 — `rule_of_40`

**Formula**

```
rule_of_40 = revenue_growth (YoY) + fcf_margin
```

**EN** — The SaaS heuristic (Feld, 2015) generalized: growth and profitability are exchangeable,
their sum should exceed 40 % (`>= 0.4`). A company growing 50 % may burn 10 % of revenue; a
mature one growing 5 % should convert 35 %+ into free cash flow. Here it uses the FCF-margin
variant — the strictest, cash-based one.

**FR** — L'heuristique SaaS (Feld, 2015) généralisée : croissance et rentabilité s'échangent,
leur somme doit dépasser 40 % (`>= 0.4`). Une société qui croît de 50 % peut brûler 10 % du
chiffre d'affaires ; une société mature à 5 % de croissance doit en convertir 35 %+ en free cash
flow. Variante FCF-margin — la plus stricte, basée cash.

> **Caveat · Nuance** — Designed for software/recurring-revenue models; read it as noise for
> banks, insurers and cyclicals. · Conçue pour les modèles logiciels/récurrents ; à considérer
> comme du bruit pour banques, assureurs et cycliques.

---

## 13. Sloan accruals — `sloan_accruals`

**Formula**

```
sloan_accruals = (net_income − operating_cashflow) / average_total_assets
```

**EN** — The accrual anomaly (Sloan, 1996): earnings not backed by operating cash are the
least persistent part of profit, and high-accrual firms historically underperform. Lower —
ideally negative — is better. Deliberately deflated by AVERAGE total assets per the paper,
unlike `beneish_tata` which uses ending assets (both are published; they answer at different
granularities).

**FR** — L'anomalie des accruals (Sloan, 1996) : les bénéfices non adossés au cash
d'exploitation sont la part la moins persistante du profit, et les sociétés à accruals élevés
sous-performent historiquement. Plus bas — idéalement négatif — c'est mieux. Déflaté par le
total d'actifs MOYEN conformément au papier, contrairement à `beneish_tata` qui utilise l'actif
de clôture (les deux sont publiés ; ils répondent à des granularités différentes).

---

## 14. PEG ratio — `peg_ratio`

**Formula**

```
peg_ratio = (market_cap / net_income) / (3-year net-income CAGR × 100)
            defined only when net_income > 0 at both endpoints and the CAGR > 0
```

**EN** — Lynch's growth-at-a-reasonable-price yardstick: a P/E is cheap or dear relative to the
growth backing it. `<= 1` is the classic GARP threshold. crible uses the 3-year earnings CAGR
(needs 4 annual periods — EDGAR's 8-year depth qualifies) rather than one noisy YoY print.

**FR** — L'étalon « croissance à prix raisonnable » de Lynch : un P/E n'est cher ou bon marché
que relativement à la croissance qui le soutient. `<= 1` est le seuil GARP classique. crible
utilise le CAGR des bénéfices sur 3 ans (4 exercices requis — la profondeur EDGAR de 8 ans
suffit) plutôt qu'une variation annuelle bruitée.

> **Caveat · Nuance** — Price applies to the latest fiscal period only (like Altman x4): older
> periods are `NaN`. Negative or shrinking earnings → no PEG, never a sign-flipped one. · Le
> prix ne s'applique qu'au dernier exercice (comme Altman x4). Bénéfices négatifs ou en
> décroissance → pas de PEG, jamais un ratio au signe inversé.

---

## 15. Shareholder yield — `shareholder_yield`

**Formula**

```
buyback_value = (shares_prior − shares) × price
shareholder_yield = (|dividends_paid| + buyback_value) / market_cap
```

**EN** — Total cash returned to shareholders: dividends plus net buybacks, as a yield on market
cap. Buybacks are proxied by the share-count decline valued at the current price — issuance
reads NEGATIVE, so serial diluters show a drag, not a bonus. `common_stock_issuance` (34.6 %
populated) is deliberately not used; the share count (83 %) is the more reliable signal.

**FR** — Le cash total rendu aux actionnaires : dividendes plus rachats nets, en rendement sur
la capitalisation. Les rachats sont approximés par la baisse du nombre d'actions valorisée au
prix courant — une émission compte NÉGATIVEMENT, donc les dilueurs en série affichent un frein,
pas un bonus. `common_stock_issuance` (34,6 % renseigné) est volontairement écarté ; le nombre
d'actions (83 %) est le signal le plus fiable.

---

## 16. Price momentum — `return_6m`, `return_12_1`, `high_52w_proximity`, `volatility_1y`

**Formula**

```
return_6m          = close / close(asof − 182d) − 1
return_12_1        = close(asof − 30d) / close(asof − 365d) − 1
high_52w_proximity = close / max(close over 365d)
volatility_1y      = std(daily log returns over 365d) × √252
```

**EN** — Cross-sectional price factors, latest fiscal row only (prices are never back-dated).
`return_12_1` is the academic classic (Jegadeesh & Titman, 1993): the last month is skipped
because it mean-reverts. `high_52w_proximity` at 1.0 means the stock sits at its 52-week high —
a documented momentum signal in its own right. The ONE implementation lives in
`compute/momentum.py`; the crawl path, the dump distillates and `momentum_rank`'s input all
call it (a parity test locks the three paths together). **`momentum_rank` deliberately stays on
`return_6m` this release**: switching its input to 12-1 would NULL the rank for every symbol
with 6–12.5 months of price history while coverage is scaling 10×, and would churn
`composite_rank` at the same time as the default sort. The pillar swap is a separate, explicit
decision once 12-1 coverage catches up.

**FR** — Facteurs de prix cross-sectionnels, dernière ligne fiscale uniquement (les prix ne
sont jamais rétro-datés). `return_12_1` est le classique académique (Jegadeesh & Titman, 1993) :
le dernier mois est exclu car il tend à revenir à la moyenne. `high_52w_proximity` à 1,0
signifie que le titre est à son plus-haut sur 52 semaines — un signal de momentum documenté en
soi. L'implémentation UNIQUE vit dans `compute/momentum.py` ; le chemin crawl, les distillats
de dumps et l'entrée de `momentum_rank` l'appellent tous (un test de parité verrouille les
trois chemins). **`momentum_rank` reste volontairement sur `return_6m` cette version** : basculer
sur le 12-1 annulerait le rank pour tout titre ayant 6 à 12,5 mois d'historique en pleine
multiplication par 10 de la couverture, et ferait churner `composite_rank` en même temps que le
tri par défaut. La bascule est une décision séparée et explicite quand la couverture du 12-1
aura rejoint celle du 6 mois.

> **Caveat · Nuance** — All four need real history (the published window is 400 days); a base
> the history does not reach is `NaN`, never extrapolated. Volatility uses the same full-year
> reach rule — a short window would understate risk. · Les quatre exigent un historique réel
> (la fenêtre publiée est de 400 jours) ; une base hors d'atteinte est `NaN`, jamais extrapolée.
> La volatilité suit la même règle d'année pleine — une fenêtre courte sous-estimerait le risque.

---

## 17. Mohanram G-Score — `mohanram_g` (+ 6 signals) — **partial: 6 of 8**

**Formula**

```
g1 = ROA (NI / avg TA)                > peer median          g4 = var(ROA)          < peer median
g2 = CFO-ROA (OCF / avg TA)           > peer median          g5 = var(rev growth)   < peer median
g3 = OCF > NI (per-symbol)                                   g6 = capex / beginning TA > peer median
mohanram_g = Σ signals (0–6) — one undecidable signal nulls the score
```

**EN** — Mohanram (2005, *Separating Winners from Losers among Low Book-to-Market Stocks*)
scores GROWTH stocks on fundamentals the way Piotroski scores value stocks: profitability and
cash generation above the peer median, earnings and growth stability, and investment intensity
(for growth firms, spending MORE than peers is the good sign — the inverse of a value screen).
Peer group = region×sector (min 5 peers, else global) — the same machinery as the FR-015 ranks.
**Two of the paper's eight signals are missing**: R&D intensity and advertising intensity have
no canonical field (no keyless provider maps them). The score is explicitly 0–6, labeled
"partial", and carries **no color verdict** — the published 6-of-8 cutoff does not transfer.

**FR** — Mohanram (2005) note les valeurs de CROISSANCE sur les fondamentaux comme Piotroski
note les valeurs décotées : rentabilité et génération de cash au-dessus de la médiane des pairs,
stabilité des bénéfices et de la croissance, et intensité d'investissement (pour une valeur de
croissance, investir PLUS que ses pairs est le bon signe — l'inverse d'un filtre value). Groupe
de pairs = région×secteur (5 pairs minimum, sinon global) — la même mécanique que les ranks
FR-015. **Deux des huit signaux du papier manquent** : les intensités R&D et publicité n'ont pas
de champ canonique (aucun fournisseur keyless ne les publie). Le score est explicitement 0–6,
étiqueté « partiel », et ne porte **aucun verdict couleur** — le seuil publié 6-sur-8 ne
transfère pas.

> **Caveat · Nuance** — Designed for low book-to-market stocks; on deep-value names read
> Piotroski instead. Variability signals need ≥3 usable periods. · Conçu pour les faibles
> book-to-market ; sur la deep value, lire Piotroski. Les signaux de variabilité exigent ≥3
> périodes utilisables.

---

## 18. Dechow F-Score — `dechow_f` (+ 7 components) — **Model 1, accounting core**

**Formula**

```
logit = −7.893 + 0.790·rsst + 2.518·ch_rec + 1.191·ch_inv
        + 1.979·soft_assets + 0.171·ch_cs − 0.932·ch_roa + 1.029·issue
F = sigmoid(logit) / 0.0037          (0.0037 = the sample's misstatement base rate)
```

**EN** — Dechow, Ge, Larson & Sloan (2011, *Predicting Material Accounting Misstatements*)
trained this logistic model on SEC AAER enforcement cases. F is the modelled misstatement
probability relative to the unconditional base rate: **F ≥ 1 above-normal risk, ≥ 1.85
substantial, ≥ 2.45 high** (published cutoffs). It completes the forensic family: Beneish
(manipulation profile), Montier (red-flag count), Dechow (calibrated probability). crible ships
**Model 1 only** — the financial-statement variant; Models 2–3 add off-balance-sheet and
market variables (abnormal returns) that keyless data does not carry. Documented proxies:
RSST = ΔWC + ΔNCO + ΔFIN telescopes to Δ(total_assets − total_liabilities − cash) / average
total assets, which is what crible computes — the debt split and marketable securities cancel
out, so their absence no longer nulls F. The issuance dummy reads a parsed cash-flow statement
without a `common_stock_issuance` line as no issuance (no statement at all stays `NaN`; 34.6 %
populated; Dechow's variable also counts debt issuance).

**FR** — Dechow, Ge, Larson & Sloan (2011) ont entraîné ce modèle logistique sur les dossiers
d'exécution AAER de la SEC. F est la probabilité modélisée de manipulation rapportée au taux de
base : **F ≥ 1 risque au-dessus de la normale, ≥ 1,85 substantiel, ≥ 2,45 élevé** (seuils
publiés). Il complète la famille forensique : Beneish (profil de manipulation), Montier
(compteur de drapeaux), Dechow (probabilité calibrée). crible ne publie que le **Model 1** — la
variante purement comptable ; les Models 2–3 ajoutent du hors-bilan et des variables de marché
absentes des données keyless. Écarts documentés : la composante FIN du RSST n'a ni
investissements long terme ni actions de préférence (non canoniques). RSST = ΔWC + ΔNCO + ΔFIN
se télescope en Δ(actif total − passif total − trésorerie) / actif moyen, ce que calcule crible :
la ventilation de la dette et les titres de placement s'annulent, leur absence n'annule plus F.
Le dummy d'émission lit un tableau de flux parsé sans ligne `common_stock_issuance` comme une
absence d'émission (sans tableau du tout : `NaN` ; 34,6 % renseigné ; la variable de Dechow
compte aussi les émissions de dette).

> **Caveat · Nuance** — `ch_cs` needs two consecutive cash-sales figures, so a company's first
> TWO periods never carry an F. · `ch_cs` exige deux chiffres consécutifs de ventes cash : les
> deux premières périodes d'une société ne portent jamais de F.

---

## 19. Trailing twelve months — `ttm_revenue`, `ttm_net_income`, `ttm_operating_cashflow`, `ttm_free_cash_flow`, `price_to_earnings_ttm`, `price_to_sales_ttm`, `ttm_fcf_yield`

**Formula**

```
ttm_<flow> = Σ last 4 quarterly figures      (period-ends must span 240–300 days)
price_to_earnings_ttm = market_cap / ttm_net_income      (NaN when NI ≤ 0)
price_to_sales_ttm    = market_cap / ttm_revenue
ttm_fcf_yield         = ttm_free_cash_flow / market_cap
```

**EN** — Annual figures can be up to a year stale; the TTM sums the last four reported
quarters, so a P/E (TTM) reflects the most recent twelve months actually filed. Landed as
COLUMNS on the latest row — never extra rows, so one-row-per-symbol semantics hold everywhere.
Guard: the four quarter-ends must span roughly a year (240–300 days) — gapped, duplicated or
semi-annual reporters get NaN instead of a wrong sum. Balance-sheet items are point-in-time and
deliberately excluded. **Reach (v2): audited US issuers reporting DISCRETE quarters (EDGAR
10-Qs, 70–100-day durations — preferred over the scraped quarterlies, never source-mixed) plus
the crawled (yfinance) tier.** Issuers filing only year-to-date cash-flow durations honestly
stay without a TTM — YTD figures are never differenced into quarters.

**FR** — Les chiffres annuels peuvent dater d'un an ; le TTM somme les quatre derniers
trimestres publiés, donc un P/E (TTM) reflète les douze derniers mois réellement déposés. Posé
en COLONNES sur la dernière ligne — jamais en lignes supplémentaires, la sémantique
une-ligne-par-société tient partout. Garde-fou : les quatre fins de trimestre doivent couvrir
environ un an (240–300 jours) — trous, doublons ou reporting semestriel donnent NaN plutôt
qu'une somme fausse. Les postes de bilan sont des instantanés, exclus à dessein. **Portée
(v2) : les émetteurs US audités publiant des trimestres DISCRETS (10-Q EDGAR, durées de 70 à
100 jours — préférés aux trimestriels scrapés, jamais mélangés) plus le tier crawlé
(yfinance).** Un émetteur ne publiant que du cumul annuel (YTD) reste honnêtement sans TTM —
un cumul n'est jamais différencié en trimestres.

> **Caveat · Nuance** — Provider restatements can make a TTM sum drift from the annual figure;
> the two are never reconciled — both are shown. · Les retraitements peuvent faire diverger la
> somme TTM du chiffre annuel ; jamais réconciliés — les deux sont affichés.

---

## 20. 3-year CAGR — `revenue_cagr_3y`, `net_income_cagr_3y`

**Formula**

```
cagr_3y = (x_t / x_{t−3})^(1/3) − 1        defined only when both endpoints > 0
```

**EN** — The 3-year compound trajectory as first-class, filterable columns (needs 4 annual
periods — EDGAR's 8-year depth qualifies broadly). One YoY print is noisy; the 3-year CAGR is
the smoothed view. **`peg_ratio` divides P/E by exactly `net_income_cagr_3y`** — one shared
definition, never two. Negative or zero endpoints → `NaN` (a fractional power of a negative is
undefined, and a sign-flipped growth rate would be worse than a missing one).

**FR** — La trajectoire composée sur 3 ans en colonnes filtrables de premier rang (4 exercices
requis — la profondeur EDGAR de 8 ans suffit largement). Une variation annuelle est bruitée ;
le CAGR 3 ans est la vue lissée. **`peg_ratio` divise le P/E par exactement
`net_income_cagr_3y`** — une seule définition partagée, jamais deux. Extrémités négatives ou
nulles → `NaN` (puissance fractionnaire d'un négatif indéfinie, et un taux au signe inversé
serait pire qu'un taux manquant).

---

## 21. Engine conventions (schema 10) · Conventions du moteur (schéma 10)

**EN** — Rules every column above follows since engine schema 9, completed in 10 (a full
recompute ships them):

- **Prior year means a fiscal year back.** Every year-over-year growth (`*_growth`), delta
  (Piotroski, Beneish, Montier, Dechow, Ohlson, Mohanram) and opening/closing average compares
  with the period ending **300–430 days** earlier (a bare-year label like `2024` reads as
  2024-12-31). Across a gap — FSDS history ending in 2018 next to a crawl starting in 2021 — the
  comparison is `NaN`, never a three-year jump presented as one year. The 3-year CAGR needs a
  base ending 900–1290 days earlier.
- **Growth needs a positive base.** `*_growth = (x − prior) / prior`, `NaN` when the prior is
  ≤ 0: −10 → +5 is not a « −150 % » decline. Outflows reported negative (capex, dividends) grow
  by their magnitude.
- **No multiple over a non-positive denominator.** P/E (EPS ≤ 0), P/B, ROE, debt/equity and the
  equity multiplier (equity ≤ 0), price/cash-flow and EV/OCF (OCF ≤ 0), price/FCF (FCF ≤ 0),
  EV/EBIT and EV/EBITDA (≤ 0) are `NaN` — a loss-maker with negative equity no longer passes
  `classic-value` or `quality`. `earnings_yield` keeps its sign: a loss is a negative yield that
  ranks the company last on value. ±∞ never reaches the snapshot.
- **Piotroski F is in-house**: each of the nine criteria is `NULL` when an input or the prior
  year is missing (so the first period has no score), and `piotroski_f` is `NULL` unless all
  nine are decidable. Accruals test `operating_cashflow > net_income` on the same base.
- **Market cap uses the period-end share count** (`shares_outstanding_end`: `OrdinarySharesNumber`
  / EDGAR `CommonStockSharesOutstanding`, the weighted average as a per-period fallback — also
  when the two are more than 2× apart, i.e. in different share units, as Yahoo's BRK-B), and so
  do EV, P/B, Graham's BVPS, NCAV/market cap and the shareholder-yield buyback term. EPS stays on
  the weighted average. London, Johannesburg and Tel Aviv listings in GBP/ZAR/ILS are priced in
  pence/cents/agorot by every price source and converted accordingly; the crawl records the
  currency Yahoo actually quotes in, which wins over the listed one (CCEP.L is listed in EUR, the
  currency it reports in, and trades in pence).
- **Price in the statements' currency.** When a source records the reporting currency (ESEF
  `_currency`; the crawl's Yahoo `financialCurrency` — ArcelorMittal files in USD and quotes in
  EUR, BREN.JK files in USD and quotes in IDR) the price is converted before any multiple, with
  the ECB cross rate; a minor-unit quote (GBp/GBX pence, ZAc, ILA) is always taken to its major
  unit. No rate → the price-based columns are `NaN` (`reporting_currency` records the currency
  used). Listings crawled before this change carry no currency until their next crawl.
- **TTM**: the source (audited 10-Q or scraped) whose last quarter is the most recent wins; a
  window ending more than 200 days before the price date is dropped.
- **Prices that cannot apply are not applied.** A latest fiscal period ending more than 550
  days before the price date gets no price-based column (a 2015 year at today's close is no
  P/E). A split after the period end (crawled bars' `Stock Splits`, the dump's split events)
  rebases the price on the statements' share count — skipped when Yahoo already restated it.
- **Unit and currency sanity.** EDGAR/FSDS share counts below 10,000 are a filer's scale error
  (MCD tags millions as units) and are dropped; a period more than 1,000× off the company's
  median count likewise. When a filing and Yahoo report in different currencies (CVM in BRL,
  Yahoo in USD for VALE3.SA) — declared, or visible as values wholesale apart — the filing
  stands alone instead of being merged cell by cell. US listings take their statements'
  currency from the SEC directory mirror (TM files in JPY, TSM in TWD, BABA in CNY).
- **Warrants, units and rights** (a listed US base symbol + W/WS/WT/U/UN/R/RT) get no snapshot
  row: Yahoo serves them the company's statements, and ratios on their price are noise. The SEC
  directory maps some to the parent's CIK (DAVEW): EDGAR does not serve them either.
- **Global peer group**: a listing whose region × sector has fewer than 5 peers is ranked (and
  gets its Mohanram medians) against **every** latest row, not just the other leftovers.
  `composite_rank` needs at least two pillars: a momentum-only listing (a SPAC warrant with no
  fundamentals) no longer tops the default screen.
- **ESEF**: the owners' share (`…AttributableToOwnersOfParent`) wins over the group total
  including minorities, matching EDGAR/TWSE/CVM/yfinance.

**FR** — Règles suivies par toutes les colonnes ci-dessus depuis le schéma moteur 9, complétées
en 10 (un recalcul complet les applique) :

- **L'année précédente est un exercice en arrière.** Toute croissance annuelle (`*_growth`),
  tout delta (Piotroski, Beneish, Montier, Dechow, Ohlson, Mohanram) et toute moyenne
  ouverture/clôture compare avec la période close **300 à 430 jours** plus tôt (un libellé
  d'année seul comme `2024` vaut 2024-12-31). En cas de trou — historique FSDS arrêté en 2018 à
  côté d'un crawl démarrant en 2021 — la comparaison vaut `NaN`, jamais un saut de trois ans
  présenté comme un an. Le CAGR 3 ans exige une base close 900 à 1290 jours plus tôt.
- **Une croissance exige une base positive.** `*_growth = (x − précédent) / précédent`, `NaN`
  quand le précédent est ≤ 0 : −10 → +5 n'est pas une baisse de « −150 % ». Les sorties de
  trésorerie déclarées négatives (capex, dividendes) croissent en valeur absolue.
- **Aucun multiple sur un dénominateur non positif.** P/E (BPA ≤ 0), P/B, ROE, dette/capitaux
  propres et multiplicateur de capitaux propres (capitaux propres ≤ 0), cours/flux et VE/FTO
  (FTO ≤ 0), cours/FCF (FCF ≤ 0), VE/EBIT et VE/EBITDA (≤ 0) valent `NaN` — une société en perte
  à capitaux propres négatifs ne passe plus `classic-value` ni `quality`. `earnings_yield` garde
  son signe : une perte est un rendement négatif qui classe la société dernière en value. ±∞
  n'atteint jamais le snapshot.
- **Piotroski F est maison** : chacun des neuf critères vaut `NULL` si une entrée ou l'année
  précédente manque (la première période n'a donc pas de score), et `piotroski_f` vaut `NULL`
  tant que les neuf ne sont pas décidables. Le critère accruals teste
  `operating_cashflow > net_income` sur la même base.
- **La capitalisation utilise le nombre d'actions de fin de période** (`shares_outstanding_end` :
  `OrdinarySharesNumber` / EDGAR `CommonStockSharesOutstanding`, la moyenne pondérée en repli par
  période), de même que la VE, le P/B, le BVPS de Graham, NCAV/capitalisation et le terme rachats
  du shareholder yield. Le BPA reste sur la moyenne pondérée. Le crawl enregistre la devise de
  cotation réelle de Yahoo, qui l'emporte sur la devise listée (CCEP.L est listée en EUR, sa
  devise de comptes, et cote en pence).
- **Le prix dans la devise des comptes.** Quand une source enregistre la devise de reporting
  (`_currency` ESEF ; le `financialCurrency` Yahoo du crawl — ArcelorMittal publie en USD et
  cote en EUR, BREN.JK publie en USD et cote en IDR), le prix est converti avant tout multiple,
  au cours croisé BCE ; une cotation en sous-unité (pence GBp/GBX, ZAc, ILA) est toujours
  ramenée à l'unité. Sans cours, les colonnes dépendant du prix valent `NaN`
  (`reporting_currency` indique la devise utilisée). Les valeurs crawlées avant ce changement
  n'ont pas de devise avant leur prochain crawl.
- **TTM** : la source (10-Q audité ou scrapé) dont le dernier trimestre est le plus récent
  l'emporte ; une fenêtre close plus de 200 jours avant la date du prix est écartée.
- **Un prix qui ne peut pas s'appliquer n'est pas appliqué.** Une dernière période close plus
  de 550 jours avant la date du prix ne reçoit aucune colonne dépendant du prix. Une division
  d'actions après la clôture (colonne `Stock Splits` des barres crawlées, événements du dump)
  ramène le prix sur la base d'actions des comptes — sauf si Yahoo l'a déjà retraitée.
- **Cohérence d'unités et de devises.** Un nombre d'actions EDGAR/FSDS sous 10 000 est une
  erreur d'échelle du déposant (MCD déclare des millions comme unités) et est écarté ; une
  période à plus de 1 000× la médiane de la société aussi. Quand un dépôt et Yahoo publient
  dans des devises différentes (CVM en BRL, Yahoo en USD pour VALE3.SA) — déclaré ou visible
  par des valeurs en bloc éloignées —, le dépôt est pris seul plutôt que fusionné cellule par
  cellule. Les cotations US prennent la devise de leurs comptes dans le miroir de l'annuaire
  SEC (TM en JPY, TSM en TWD, BABA en CNY).
- **Warrants, unités et droits** (symbole US coté + W/WS/WT/U/UN/R/RT) n'ont pas de ligne de
  snapshot : Yahoo leur sert les comptes de la société et les ratios sur leur prix sont du
  bruit. L'annuaire SEC en rattache certains au CIK de la société (DAVEW) : EDGAR ne les sert
  pas non plus.
- **Groupe de pairs global** : une valeur dont le couple région × secteur compte moins de 5
  pairs est classée (et reçoit ses médianes Mohanram) contre **toutes** les dernières lignes,
  pas seulement les autres orphelines. `composite_rank` exige au moins deux piliers : une
  valeur portée par le seul momentum (un warrant de SPAC sans fondamentaux) ne domine plus
  l'écran par défaut.
- **ESEF** : la part du groupe (`…AttributableToOwnersOfParent`) l'emporte sur le total incluant
  les minoritaires, comme EDGAR/TWSE/CVM/yfinance.

---

## 22. ROIC — `roic`

**Formula**

```
tax_rate         = income_tax_expense / income_before_tax     (clipped to 0–50 %, NaN on a pretax loss)
NOPAT            = EBIT × (1 − tax_rate)
invested_capital = total_equity + total_debt − cash_and_equivalents   (averaged over the year)
roic             = NOPAT / invested_capital                   (NaN when invested capital < 10 % of total assets)
```

**EN** — What the operating business earns, after tax, on the capital shareholders and lenders
put in. Unlike ROE it cannot be inflated by leverage; unlike ROA it ignores idle cash. A
sustained ROIC above the cost of capital (~8–10 %) is the signature of a moat. The averaged
capital needs a prior year, so the first period is `NaN`. Capital under a tenth of total assets
is no denominator: when cash nearly cancels equity + debt (000858.SZ read 1,219×) or deposits
sit outside « debt » (banks), the quotient is a rounding residue, not a return.

**FR** — Ce que l'activité gagne, après impôt, sur le capital apporté par les actionnaires et
les prêteurs. Contrairement au ROE, le levier ne peut pas le gonfler ; contrairement au ROA, la
trésorerie dormante n'y pèse pas. Un ROIC durablement au-dessus du coût du capital (~8–10 %)
signe un avantage concurrentiel. Le capital moyen exige l'exercice précédent : la première
période vaut `NaN`. Un capital inférieur au dixième de l'actif n'est pas un dénominateur :
quand la trésorerie annule presque capitaux propres + dette (000858.SZ affichait 1 219×) ou que
les dépôts sortent de la « dette » (banques), le quotient est un résidu d'arrondi.

---

## 23. Gross profitability — `gross_profitability`

**Formula** — `gross_profit / total_assets`

**EN** — Novy-Marx (2013, *The Other Side of Value*): gross profit scaled by assets predicts
returns as well as book-to-market, and it is measured above the lines (R&D, SG&A, D&A) where
accounting choices distort earnings. Compare within an industry: asset-light businesses score
structurally higher.

**FR** — Novy-Marx (2013) : la marge brute rapportée à l'actif prédit les rendements aussi bien
que le book-to-market, et se mesure au-dessus des lignes (R&D, frais généraux, amortissements)
où les choix comptables déforment le résultat. À comparer au sein d'un secteur : les modèles
peu capitalistiques ressortent structurellement plus haut.

---

## 24. Net share issuance — `net_share_issuance`

**Formula** — `shares_outstanding_end / prior-year shares_outstanding_end − 1` (period-end
count, the weighted average as a fallback; NaN across a calendar gap, and when the count
halves or doubles — a split, a merger or a unit change between filings, not issuance)

**EN** — Positive = the share count grew (dilution: options, acquisitions paid in stock, capital
raises); negative = net buybacks. Persistent dilution is one of the most reliable negative
signals in the equity literature (Pontiff & Woodgate 2008); the grid colors dilution red.

**FR** — Positif = le nombre d'actions a augmenté (dilution : stock-options, acquisitions payées
en titres, augmentations de capital) ; négatif = rachats nets. Une dilution persistante est l'un
des signaux négatifs les plus robustes de la littérature (Pontiff & Woodgate 2008) ; la grille
colore la dilution en rouge.

---

## 25. Free-cash-flow consistency — `positive_fcf_years_5y`

**Formula** — the number of fiscal years with `free_cash_flow > 0` among the last five
reported; `NaN` until three years are reported (never extrapolated).

**EN** — One good year proves little; a business that converts earnings into cash year after
year is the one that can fund dividends, buybacks and growth without the market's permission.
Yahoo-only listings carry ~4 annual periods, audited EDGAR listings up to 8.

**FR** — Une bonne année ne prouve pas grand-chose ; une entreprise qui transforme ses bénéfices
en trésorerie année après année peut financer dividendes, rachats et croissance sans dépendre du
marché. Les valeurs Yahoo seules portent ~4 exercices, les valeurs EDGAR auditées jusqu'à 8.

---

## 26. Altman Z″ — `altman_z_double_prime`

**Formula**

```
Z″ = 6.56·(working_capital / TA) + 3.26·(retained_earnings / TA)
   + 6.72·(EBIT / TA) + 1.05·(total_equity / total_liabilities)
```

**EN** — Altman's 2002 revision for non-manufacturers and emerging markets: the sales/assets
term (an industry artefact) is dropped and the market value of equity is replaced by **book**
equity, so it scores any company with a balance sheet — no price needed. Zones: **> 2.60 safe,
1.10–2.60 grey, < 1.10 distress**. Prefer it to the classic `altman_z` for services, retail,
software and non-US listings.

**FR** — La révision 2002 d'Altman pour les non-industriels et les marchés émergents : le terme
ventes/actif (un artefact sectoriel) disparaît et la capitalisation est remplacée par les
capitaux propres **comptables** ; il note donc toute société dotée d'un bilan, sans cours.
Zones : **> 2,60 sûr, 1,10–2,60 gris, < 1,10 détresse**. À préférer au `altman_z` classique pour
les services, la distribution, le logiciel et les cotations hors US.

---

## See also · Voir aussi

The three headline scores that predate this set are documented in the code and the main README:

- **Piotroski F** (`piotroski_f`, 0–9) — nine-point fundamental strength score (section 21).
- **Altman Z** (`altman_z`) — the classic five-ratio bankruptcy Z-Score.
- **Beneish M** (`beneish_m`) — eight-variable earnings-manipulation model (`> −1.78` flags risk).

Every score above **decomposes in the company drawer** down to its component values, and every
column is filterable in the same DSL (`crible screen "…"`, the query builder, the API).
Chaque score ci-dessus **se déplie dans le tiroir société** jusqu'à ses composantes, et chaque
colonne est filtrable dans le même DSL.
