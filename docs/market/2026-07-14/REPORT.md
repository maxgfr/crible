# Stratégie de sources de données « bulk-first » pour crible — marché & vérification (2026-07-14)

## Executive summary

crible est un screener fondamental self-hosted, **zéro clé API / zéro abonnement**, positionné dans un créneau que les leaders payants laissent vide [S1]. La direction produit est décidée : **bulk-first** — posséder la donnée via des dumps keyless plutôt que de multiplier le scraping fragile au symbole. Ce rapport (a) rafraîchit l'angle marché/concurrence et (b) **vérifie** sur sources primaires les prochaines sources bulk à activer.

Trois conclusions fortes :

1. **Le socle bulk officiel est solide et, pour les US, entièrement redistribuable.** EDGAR est explicitement « free to access and reuse » [S24] ; les **Financial Statement Data Sets** offrent l'historique trimestriel « as filed » (2009→2026) que `companyfacts` n'a pas [S23]. UK (Companies House Accounts Data Product, ZIP iXBRL) [S21][S22] et Japon (EDINET, PDL1.0) [S29] étendent la couverture keyless hors US/UE-ESEF.
2. **La ligne de mirroring est nette** : republier librement EDGAR/FSDS [S24] ; EDINET avec attribution [S29] ; Companies House et les dumps de prix restent des risques assumés faute de licence explicite [S21][S22][S25].
3. **Le marché valide l'axe DATA.** Un concurrent payant (ScreenerHero, 29 $/mois) se différencie exactement sur la couverture fondamentale européenne small/microcap et la **visibilité des trous de données** [S10] — le terrain naturel de crible, mais keyless et self-hosted.

## Problem & customer

Le client-cible : l'investisseur particulier « systématique » qui veut screener sur fondamentaux bruts (« toutes les sociétés européennes avec P/E < 12, ROE > 15 %, dette/fonds propres < 0.8 ») et non « découvrir » des titres via des scores visuels [S10]. Ce besoin est mal servi : Simply Wall St est conçu pour la découverte, pas le screening systématique répétable [S10] ; sa qualité de données sur les small/microcaps européennes et marchés alternatifs est « inconsistante », et l'approche visuelle **masque** les trous de données (une valeur manquante devient un score neutre plutôt qu'une case vide) [S10][S3]. Les briques gratuites héritent d'un plafond structurel : OpenBB note que « il est courant que les tiers gratuits se limitent aux cotations US » [S28], et les APIs gratuites populaires (Alpha Vantage, Finnhub, Twelve Data…) imposent quotas et clés [S13][S14][S20]. Yahoo/yfinance reste la voie « sans clé » mais non contractuelle et durcie côté rate-limit [S2][S16].

Le besoin sous-jacent : **des fondamentaux fiables, traçables, couvrant profondément l'Europe, sans clé ni abonnement, avec les trous visibles** — ce que crible vise et que ni les SaaS ni les briques gratuites ne cochent ensemble [S10][S28].

## Market sizing (TAM / SAM / SOM)

Pas de chiffrage TAM/SAM/SOM fiable dans le dossier — je ne l'invente pas [M]. Bornes qualitatives observables :

- **Demande solvable** : le leader européen Stockopedia facture €550/an (Europe) à €725/an (avec US) [S1] ; ScreenerHero 29 $/mois, TIKR 40–55 $/mois, un concurrent US Elite quasi 40 $/mois [S10]. La valeur d'un screener fondamental est donc monétisée à plusieurs centaines d'€/an — l'économie pour l'utilisateur self-host est directe et chiffrable [S1][S10].
- **SAM accessible à crible** : les utilisateurs self-hosted / anti-abonnement / pro-transparence (communautés GitHub, r/selfhosted, OpenBB, Ghostfolio) — segment où la distribution est gratuite et virale [S1][S28][M].
- **SOM réaliste (12 mois)** : capter les investisseurs « sortis » de Simply Wall St qui veulent des filtres bruts et une couverture européenne — le segment que ScreenerHero adresse en payant [S10] — mais en keyless/self-hosted.

## Competitive landscape

Deux familles, un trou au milieu [S1] :

- **SaaS fondamentaux payants** : Stockopedia (StockRanks, 350+ ratios, pricing régional €550–725/an) [S8][S12][S1] ; Simply Wall St (analyse visuelle « snowflake », freemium, screener limité) [S15][S19][S9] ; TIKR (terminal de recherche, historique 20 ans, 40–55 $/mois) [S10] ; ScreenerHero (challenger explicitement anti-Simply-Wall-St, filtres bruts, 17k titres, 29 $/mois) [S10].
- **Open-source self-hosted** : OpenBB (terminal/plateforme de données, couverture data conditionnée aux providers/ clés, « free tiers souvent US-only ») [S28] ; Ghostfolio (suivi de portefeuille, pas un screener) [M]. Aucun n'est un **screener fondamental full-univers clé-en-main self-hosted** [S1].

Le signal décisif : **ScreenerHero prouve qu'un positionnement « filtres bruts + couverture européenne small-cap + trous visibles » est vendable** [S10] — mais il est payant et cloud. crible occupe le même axe produit en keyless + self-hosted + transparence de provenance.

### Competitor table (name · positioning · pricing)

| Nom | Positionnement | Prix | Note data |
|---|---|---|---|
| crible | Screener fondamental self-hosted, keyless, provenance traçable [S1] | Gratuit / self-host [S1] | Bulk keyless (EDGAR, ESEF, +UK/JP à venir) [M] |
| Stockopedia | Screener + StockRanks, 350+ ratios [S12][S8] | €550/an (EU) – €725/an (EU+US) [S1] | Données propriétaires, non self-host [S1] |
| Simply Wall St | Analyse visuelle « snowflake », screener limité [S15][S19] | Freemium / abo mensuel [S10] | Qualité small-cap EU inconstante, trous masqués [S10][S3] |
| TIKR | Terminal de recherche, historique 20 ans [S10] | 40–55 $/mois [S10] | Couverture globale, orienté analyse [S10] |
| ScreenerHero | Filtres bruts anti-Simply-Wall-St, 17k titres US/CA/EU [S10] | Gratuit / 29 $/mois Pro [S10] | Small-cap EU + marchés alternatifs, trous visibles [S10] |
| OpenBB | Plateforme/terminal de données open-source [S28] | Gratuit + providers à clé [S28] | « Free tiers souvent US-only » [S28] |

## Pricing & business models observed

- **Abonnement régionalisé** (Stockopedia) : €550–725/an, segmenté par géographie couverte [S1][S8].
- **Freemium visuel** (Simply Wall St) : gratuit limité → abo mensuel, monétise la simplicité/lisibilité [S15][S10].
- **Challenger low-cost « raw filters »** (ScreenerHero) : gratuit sans compte → 29 $/mois Pro, monétise la couverture + les filtres bruts [S10].
- **Open-core / providers** (OpenBB) : cœur gratuit, données étendues via clés/partenaires payants [S28].
- **crible** : pas de monétisation data — le produit **est** le dataset keyless publié + le self-host [S1][M]. Le business model observé du marché confirme qu'il n'y a **aucun** acteur gratuit-ET-self-hosted-ET-fondamental : c'est le trou de crible.

## Go-to-market channels

- **GitHub + communautés self-hosted** (r/selfhosted, awesome-selfhosted) : là où OpenBB/Ghostfolio ont bâti leur base [S1][S28][M].
- **Comparatifs SEO « alternative à … »** : le trafic « Simply Wall St alternative », « X vs Stockopedia » est un canal actif et concurrentiel [S10][S3][S4][S6][S9] — crible peut s'y insérer comme l'option keyless/self-hosted.
- **Argument d'économie chiffrable** : « €550/an chez le leader, 0 € chez toi » [S1].
- **Argument de confiance data** : provenance traçable + trous visibles, à opposer aux scores visuels qui masquent les manques [S10].

## Trends & timing

- **Durcissement des sources gratuites au symbole** : APIs gratuites de plus en plus limitées/à clé [S13][S14][S20], Yahoo non contractuel et rate-limité [S2][S16] → le **bulk keyless** est la réponse structurelle, pas conjoncturelle.
- **Maturation des dumps officiels** : FSDS SEC reprocessés en déc. 2024 (données recentrées sur les états primaires, nouveau champ `segments`) [S23] ; EDINET a mis à jour ses conditions (rév. avril 2025, PDL1.0) [S29] ; Companies House publie des ZIP quotidiens de plusieurs dizaines à centaines de Mo [S22]. La donnée officielle est de plus en plus « bulk-friendly ».
- **Fenêtre concurrentielle** : ScreenerHero démontre l'appétit pour « raw filters + EU coverage + trous visibles » [S10] mais le fait payer — la fenêtre keyless/self-hosted est ouverte.

## Risks & moats

**Risques.**
- **Prix EOD ouverts** : reste le maillon faible ; aucun OHLCV EOD ouvert redistribuable au-delà de Stooq + dumps HuggingFace [M]. Deutsche Börse PDS est **Non-commercial + deprecated** → inutilisable [S25].
- **Licences hors-US ambiguës** : Companies House ne publie pas de licence de réutilisation explicite sur ses pages produit [S21][S22] ; mirrorer son dataset est un risque assumé tant que l'OGL n'est pas confirmée.
- **Contraintes d'accès EDINET** : scraping interdit, accès machine via API uniquement (clé gratuite), taxonomie hors licence [S29] → intégration « free-key » opt-in, pas cœur zero-key.

**Moats.**
- **Redistribution propre du socle US** : EDGAR/FSDS domaine public, republiable sans permission [S24] — crible peut publier un dataset US totalement libre, ce qu'aucun SaaS ne fait.
- **Transparence de provenance + trous visibles** : différenciateur que même les payants revendiquent (ScreenerHero) [S10] et que le self-host rend crédible.
- **Zéro clé / zéro abo + self-host** : combinaison qu'aucun concurrent n'offre [S1][S28].

## Candidate data-source moves (avec évidence [S#])

1. **Provider `edgar-fsds` (Financial Statement Data Sets) en complément de companyfacts** — historique trimestriel « as filed » 2009→2026, à plat, avec SIC, tables SUB/NUM/TAG/PRE [S23]. Keyless, **domaine public/redistribuable** [S24]. Bénéfice : profondeur historique et comparabilité inter-émetteurs que companyfacts ne donne pas.
2. **Provider `companies-house` (UK) via Accounts Data Product** — ZIP iXBRL/XBRL gratuit, quotidien (Tue-Sat, rétention 60 j) + mensuel + historique via les fichiers mensuels des années précédentes ; ~75 % des 2,2 M comptes/an [S21][S22]. Keyless, headless. **Ingestion oui ; mirroring = risque assumé** (pas de licence explicite) [S21][S22].
3. **Provider `edinet` (Japon) en free-key opt-in** — contenu sous PDL1.0, redistribuable **avec attribution**, mais scraping interdit et accès machine via API uniquement, taxonomie exclue de la licence [S29]. Étend la couverture Asie hors du cœur zero-key.
4. **FX `frankfurter` (taux BCE) pour normaliser les devises** — sans clé, self-hostable, CSV/NDJSON, MCP, 201 devises depuis 1948 [S26]. Rend les ratios de valorisation comparables cross-devises. **Le meilleur rapport gain/risque du lot.**
5. **Renforcer l'axe « couverture EU small-cap + trous visibles » comme argument produit** — c'est la différenciation qu'un concurrent payant (ScreenerHero) exploite [S10] et que crible peut posséder keyless. À cabler côté data (profondeur ESEF + UK) et côté UX (afficher les blancs plutôt que les masquer).

## Data / launch checklist

- [ ] **FSDS** : ajouter l'ingestion des ZIP trimestriels SEC (2009→présent) en complément de companyfacts ; réconciliation « audité > scrapé » identique à ESEF [S23][S24][M].
- [ ] **Companies House** : PoC d'ingestion de l'Accounts Data Product (iXBRL) ; **avant tout mirroring, confirmer la licence** (OGL via data.gov.uk) — sinon série publiée en risque assumé [S21][S22].
- [ ] **EDINET** : provider free-key opt-in, hors cœur zero-key ; attribution PDL1.0 dans les crédits ; ne jamais scraper (API only) [S29].
- [ ] **FX Frankfurter** : intégrer les taux BCE pour normaliser les devises des ratios ; documenter la source/attribution [S26].
- [ ] **Deutsche Börse PDS** : **ne pas intégrer** (Non-commercial + deprecated) [S25].
- [ ] **Inde (bhavcopy)** : garder en icebox tant que les ToS de redistribution NSE/BSE ne sont pas établies [S30][M].
- [ ] **Mirroring** : publier le socle US (EDGAR/FSDS) comme dataset **totalement libre** ; isoler les sources à risque (Companies House, dumps de prix) dans une couche « assumed-risk » documentée [S24][S25][M].
- [ ] **Positionnement** : mettre en avant « couverture EU small-cap + trous visibles + keyless » dans le README/landing, en réponse directe au segment ScreenerHero/Simply-Wall-St [S10].

## Open questions / contradictions

- **Licence Companies House** : les pages produit décrivent le ZIP comme « free »/« public data » mais **n'énoncent aucune licence de réutilisation** [S21][S22]. L'OGL est plausible (données publiques UK) mais non confirmée dans le dossier [M] — à trancher via data.gov.uk avant tout mirroring.
- **PDL1.0 (EDINET)** : la page officielle confirme la mise à disposition sous PDL1.0 avec attribution et interdiction de scraping [S29] ; que PDL1.0 soit « calquée sur CC-BY et autorise l'usage commercial » relève de la connaissance de fond, non vérifiée ici [M].
- **Prix EOD ouverts** : confirmation qu'aucune nouvelle source OHLCV EOD ouverte et redistribuable n'a émergé au-delà de Stooq/HuggingFace [M] ; Deutsche Börse (seule « open data » de bourse trouvée) est NC + deprecated [S25]. Le maillon prix reste le point faible structurel.
- **Fraîcheur/complétude de l'univers** : le croisement FinanceDatabase × référentiels officiels (EDGAR tickers, GLEIF, OpenFIGI free-key, annuaires de bourses) reste la voie robuste, mais les ToS de re-publication des annuaires de bourses ne sont pas établis dans ce dossier [M].

## Sources

Voir `DOSSIER.md` (30 sources, ids `[S#]`). Sources marché redondantes non citées : S4, S6, S17, S18. `[M]` = connaissance de fond / état interne crible, non adossé à une source fetchée.
