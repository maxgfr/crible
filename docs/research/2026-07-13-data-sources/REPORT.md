# Sources de données publiques & technologies open source pour un screener fondamental self-hosted

## TL;DR

Voir `SUMMARY.md`. L'essentiel : (1) SEC EDGAR offre en bulk keyless tous les fondamentaux XBRL US (`companyfacts.zip`, recompilé chaque nuit) [S2] — la meilleure amélioration possible pour crible ; (2) l'univers de symboles le plus complet s'obtient en croisant FinanceDatabase (300 000+ symboles) [S1] avec les référentiels officiels (EDGAR, annuaires de bourses, GLEIF, OpenFIGI) ; (3) les prix keyless restent fragiles (Yahoo rate-limité [S73], Stooq sans garantie [S19]) ; (4) côté technos, edgartools, Arelle et Perspective sont les briques les plus prometteuses [S10][S44][S51].

## L'univers de symboles/cotations le plus complet (keyless)

- **FinanceDatabase** (base actuelle de crible) : « database of 300.000+ symbols » couvrant actions, ETF, fonds, indices, devises et cryptos ; catégorisation gratuite, maintenue par la communauté via des fichiers CSV éditables [S1]. Dans notre run réel du 2026-07-13, la partie actions livre 151 170 lignes après nettoyage des symboles vides [M].
- **SEC EDGAR (US, officiel)** : `data.sec.gov/submissions/` expose nom courant, anciens noms, bourses et tickers de chaque société cotée US, mis à jour en temps réel au fil des dépôts, avec un ZIP bulk de toutes les structures JSON republié chaque nuit vers 3h ET [S2]. Les index des dépôts du jour sont reconstruits chaque nuit à partir de ~22h ET [S5]. La recherche d'une société par ticker impose de connaître le CIK, dont le format de lookup n'est pas un tableau standard — un irritant d'intégration connu [S58].
- **Annuaires officiels de bourses** : NASDAQ Trader publie un Symbol Directory avec définitions (place de cotation, symbole du sous-jacent, etc.) [S23] ; Euronext liste ses actions cotées par marché (Growth Brussels, Dublin…) [S31] ; Xetra publie ses « All Tradable Instruments » [S27]. Pour le LSE, la liste complète circule via des tiers (3 tableaux au 6 oct. 2024 chez TopForeignStocks) [S49].
- **Dépôts communautaires GitHub** : US-Stock-Symbols agrège les titres NASDAQ/NYSE/AMEX en JSON/txt, régénérés par GitHub Actions, avec nom complet de société [S45] ; Global-Stock-Symbols couvre LSE (Main + AIM), NYSE/NASDAQ, Toronto, Francfort, ASX, Tokyo et Hong Kong en JSON/txt/CSV [S37]. Un guide de terrain recense les pistes sans scraping [S41].
- **OpenFIGI (Bloomberg Open Symbology)** : « The API is free to use without daily, weekly or monthly limitations. With a free API key, anyone can map hundreds of thousands of instruments in minutes » [S8] ; le mapping couvre aussi les dérivés via des options de symbologie dédiées [S35]. Pour crible, la clé (gratuite) en ferait un provider « free-key » opt-in, hors cœur zero-key [M].
- **GLEIF** : le Global LEI Index est « the only global online source that provides open, standardized and high quality legal entity reference data » [S57] ; Golden Copy et fichiers delta téléchargeables (aussi en RDF) [S53] ; fichiers quotidiens ISIN↔LEI issus du pilote GLEIF/ANNA d'avril 2019 [S12] — déjà utilisés par crible pour l'ESEF.

**Verdict complétude** : aucun référentiel unique n'est complet. Le chemin robuste : FinanceDatabase comme socle catégorisé [S1], rafraîchi/complété par les référentiels officiels par marché (EDGAR US [S2], annuaires de bourses [S23][S27][S31]) et réconcilié par identifiants (LEI [S53], FIGI [S8]) [M].

## Fondamentaux au-delà de Yahoo (keyless)

- **SEC EDGAR XBRL — la mine d'or US** : `companyfacts.zip` « contains all the data from the XBRL Frame API and the XBRL Company Facts API » pour tous les déposants, recompilé chaque nuit ; `submissions.zip` porte tout l'historique de dépôts ; les APIs temps réel ont un délai de traitement typique < 1 min pour le XBRL [S2]. Les **Financial Statement Data Sets** (janv. 2009 → mars 2026) fournissent trimestriellement les chiffres « as filed » des états financiers de tous les rapports XBRL, à plat, avec le code SIC [S46]. L'accès automatisé doit respecter la politique fair-access du SEC.gov [S2].
- **filings.xbrl.org (UE/ESEF — déjà intégré à crible)** : plus de 3 400 dépôts ESEF dès mai 2022, consultables, téléchargeables ou récupérables en xBRL-JSON ; « il n'existe pas de dépôt central officiel des dépôts ESEF », collectés par les OAMs nationaux — le site est une mesure intérimaire non exhaustive [S42]. L'index est structuré par LEI [S9] ; un client Python dédié existe (xbrl-filings-api) [S38].
- **SimFin — attention à la licence** : le package Python télécharge automatiquement cours et fondamentaux [S21], mais la licence FREE/BASIC est « non-commercial use » pour la recherche personnelle, et même la licence PRO interdit la redistribution des données [S26]. Incompatible avec un dataset de démo publié par crible [M].
- **UK Companies House** : l'Accounts Data Product est « a free downloadable ZIP file » contenant les documents d'instance des comptes déposés électroniquement, nommés par numéro de société [S13] ; une API développeur complète existe par ailleurs [S17].
- **Japon EDINET** : toutes les cotées japonaises, fonds, REITs et émetteurs publics déposent via EDINET ; les taxonomies varient par norme comptable/industrie (le tag « revenue » n'est pas unique), et l'API v2 requiert une Subscription-Key [S28] ; taxonomies officielles publiées (édition 2026 le 11 nov. 2025) [S56].
- **Canada SEDAR+** : présenté par l'OSC comme le système national de dépôt [S54], mais l'accès automatisé est bloqué par un CAPTCHA anti-bot (Radware) — constaté directement lors de la collecte [S50] ; l'aide officielle documente la recherche/téléchargement manuels [S33].

## Prix EOD keyless

- **Yahoo/yfinance (source actuelle)** : depuis le 13 nov. 2024, la communauté constate des 429 après ~950 tickers là où 7 000/jour passaient auparavant, avec ~360 requêtes/heure évoquées comme plafond documenté [S73][S78]. Le crawl budgeté de crible (330/h) est la réponse adaptée [M].
- **Stooq** : téléchargements CSV historiques gratuits (« No official API guarantees ») [S19] ; couverture téléchargeable pour les marchés polonais, japonais, hongrois, allemand et US selon Chartoasis [S80] ; QuantStart note des fondamentaux limités aux US sans historique et des incertitudes sur l'ajustement des cours [S69] ; archives historiques > 20 ans sur de nombreux actifs [S81]. Notre vérification interne (2026-07-07) a trouvé les endpoints CSV derrière un mur JS proof-of-work [M].
- **FX / BCE** : taux de référence euro publiés vers 16h00 CET chaque jour ouvré (publication RUB suspendue) [S71], avec un disclaimer de responsabilité [S79] ; l'API keyless **Frankfurter** expose ces données et liste ses sources [S72].
- **Autres pistes** : le Deutsche Börse Public Dataset (AWS Open Data) fournit du minute-level Xetra/Eurex [S75] ; en Inde, les bhavcopy NSE/BSE se téléchargent librement (outil getbhavcopy) [S76] ; les datasets Kaggle (ex. Marjanovic) sont derrière reCAPTCHA pour l'accès automatisé [S74], accessibles via archives [S77]. Les agrégateurs freemium (Marketstack [S40], Alpha Vantage [S52], EODHD [S15][S32], Finnhub…) restent des options à clé, hors cœur [M].

## Technologies open source pour améliorer crible

- **edgartools** (MIT) : « SEC-filing primitives you compose in your own code, free and self-run » — 10-K/8-K, XBRL financials, 13F, API Python typée [S10][S14]. La brique naturelle d'un provider EDGAR [M].
- **Arelle** : plateforme XBRL open source de bout en bout — application desktop, service web, CLI et API Python [S39][S44]. Utile si crible internalise davantage de parsing ESEF/EDINET [M].
- **FinanceToolkit** (déjà utilisé) : 200+ ratios écrits « de la façon la plus simple possible » pour une transparence complète des calculs [S4][S7].
- **OpenBB** : plateforme de données ouverte « connect once, consume everywhere » (Python, Workspace/Excel, serveurs MCP pour agents IA, REST) [S18], avec API REST prête à l'emploi [S22]. Référence d'architecture plus qu'une dépendance [M].
- **DuckDB-WASM** (déjà utilisé pour la démo) : « Efficient Analytical SQL in the Browser » [S25], publié sur npm [S34]. Point de vigilance vécu : le tag npm `latest` pointe sur des builds `-dev` ; notre démo a dû épingler la stable 1.32.0 après des SELECT larges tronqués/suspendus [M].
- **Perspective (FINOS)** : composant d'analyse/dataviz « especially well-suited for large and/or streaming datasets », avec widget JupyterLab et client Python, capable de traduire vers des sources externes comme DuckDB [S51][S48]. Candidat pour un mode « pivot/chart » du grid [M].
- **Listes de veille** : awesome-financial-data-apis (statuts vérifiés 2026) [S3] ; FreeTier.dev récapitule les free tiers du marché [S19].

## Recommandations concrètes pour crible

1. **Provider `edgar` keyless (priorité 1)** : ingérer `companyfacts.zip` (nightly, tous les déposants US) [S2] et/ou les Financial Statement Data Sets trimestriels [S46] → fondamentaux US officiels massifs sans clé ni scraping, avec edgartools comme bibliothèque [S10]. Réconciliation « audité > scrapé » identique au chemin ESEF existant [M].
2. **Rafraîchissement d'univers multi-sources** : croiser FinanceDatabase [S1] avec `company_tickers`/submissions EDGAR [S2] (fraîcheur IPO US) et les annuaires de bourses [S23][S27][S31] ; réconcilier par ISIN/LEI (GLEIF [S53]) et, en opt-in free-key, FIGI (OpenFIGI [S8]).
3. **Provider `companies-house` (UK) keyless** via l'Accounts Data Product [S13] ; **EDINET (JP)** en free-key opt-in [S28]. SEDAR+ : à écarter (anti-bot) [S50].
4. **SimFin : ne jamais l'utiliser pour la démo publiée** (licence personnelle/non-redistributable) [S26] — le garder strictement opt-in local.
5. **FX** : intégrer les taux BCE via Frankfurter (keyless) pour normaliser les devises des ratios de valorisation [S71][S72].
6. **Ne pas retenter Google Finance** : pas d'API officielle, alternatives = scrapers tiers payants — déjà documenté dans docs/DATA-SOURCES.md [M].

## Questions ouvertes / contradictions

- **ESAP (European Single Access Point)** : le futur point d'accès unique européen devrait à terme supplanter filings.xbrl.org comme dépôt officiel ESEF ; calendrier et modalités d'API restent à sourcer — aucun document fiable dans ce dossier [M].
- **Redistribution des annuaires de bourses** : les ToS de NASDAQ Trader/Euronext/Xetra/LSE quant à la re-publication de leurs listes dans un pipeline open source n'ont pas pu être établis ici [M] — à vérifier avant de commiter ces listes dans un repo.
- **Fraîcheur réelle de FinanceDatabase** : la base revendique 300k+ symboles [S1] mais notre run n'en livre que ~151k côté actions [M] ; l'écart (autres classes d'actifs vs actions seules, nettoyage) mérite quantification.
- **Stooq** : sources contradictoires — « gratuit et direct » côté agrégateurs [S19][S80] vs mur PoW constaté par nous [M] ; un test d'intégration dédié trancherait.

## Sources

Voir `DOSSIER.md` (81 sources, ids `[S#]`). Sources hors sujet ignorées : S6, S11, S20, S24, S30, S36, S43, S47, S55, S59, S60, S62, S63, S64, S65, S66, S67, S68, S74 (préservé comme preuve d'anti-bot Kaggle avec S77), S77.
