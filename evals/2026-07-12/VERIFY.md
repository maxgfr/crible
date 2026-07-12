# Verification worklist

For each pair: read the digest, judge whether it SUPPORTS the finding, write a verdict.
Verdicts: `supported` · `partial` · `refuted` · `unsupported`.

## F4 · README.md:1
**Finding:** Le README actuel est technique et neutre ; il ne vend pas le seul créneau vide du marché (screener fondamental self-hosted, zéro clé, alternative à un abonnement à €550/an). Le canal de distribution du cœur de cible (awesome-selfhosted, catégorie Money) n'a aucun screener.
```
1: # crible
2: 
3: Self-hosted fundamental stock screener. Worldwide universe (~161k equities), Europe-depth
```
**Verdict:** ______  ·  **Note:** ______

## F4 · docs/market/2026-07-12/REPORT.md:1
**Finding:** Le README actuel est technique et neutre ; il ne vend pas le seul créneau vide du marché (screener fondamental self-hosted, zéro clé, alternative à un abonnement à €550/an). Le canal de distribution du cœur de cible (awesome-selfhosted, catégorie Money) n'a aucun screener.
```
1: # REPORT — self-hosted / zero-key fundamental stock screeners (mode startup)
2: 
3: ## Executive summary
```
**Verdict:** ______  ·  **Note:** ______

## F7 · src/crible/compute/scores.py:1
**Finding:** Le différenciateur n°1 du leader payant Stockopedia est le StockRank composite (qualité/valeur/momentum), cité par les reviews comme la raison d'abonnement. crible a déjà les scores en base (Piotroski, Altman, ratios) pour le calculer, sans clé.
```
1: """FR-003 — the three headline scores.
2: 
3: Piotroski F-Score and Altman Z-Score are computed through financetoolkit's
```
**Verdict:** ______  ·  **Note:** ______

## F8 · docker-compose.yml:28
**Finding:** Une question explicite « puis-je self-héberger cet outil de recherche actions sur mon Synology ? » reste sans réponse depuis 2023 chez le leader OSS OpenBB. crible peut y répondre par un guide d'install NAS/compose one-liner — friction d'adoption levée pour le cœur de cible.
```
26:   api:
27:     build: .
28:     ports:
29:       - "${CRIBLE_PORT:-8000}:8000"
30:     volumes:
```
**Verdict:** ______  ·  **Note:** ______

## F7 · docs/market/2026-07-12/REPORT.md:1
**Finding:** Le différenciateur n°1 du leader payant Stockopedia est le StockRank composite (qualité/valeur/momentum), cité par les reviews comme la raison d'abonnement. crible a déjà les scores en base (Piotroski, Altman, ratios) pour le calculer, sans clé.
```
1: # REPORT — self-hosted / zero-key fundamental stock screeners (mode startup)
2: 
3: ## Executive summary
```
**Verdict:** ______  ·  **Note:** ______

## F1 · src/crible/api/main.py:119-145
**Finding:** L'endpoint /api/providers code en dur la liste des 4 classes provider et recalcule l'activation avec `True if key_var is None else bool(env)`, au lieu de consommer ProviderRegistry.activate / provider.enabled(env) qui est la source de vérité. Sa propre docstring dit « mirrors ProviderRegistry.activate ». Toute évolution de la règle d'activation (provider à deux clés, keyed avec repli keyless) fait diverger silencieusement l'écran Providers de la réalité.
```
117:         return runtime().status()
118: 
119:     @app.get("/api/providers")
120:     def providers() -> list[dict]:
121:         """FR-013/FR-014 — read-only provider inventory for the settings view.
122: 
123:         Enablement mirrors ProviderRegistry.activate: keyless is always on,
124:         a keyed provider is on iff its env var is set. No instantiation —
125:         id/kind/key_env_var are class attributes.
126:         """
127:         import os as env_os
128: 
129:         from crible.providers.eodhd import EodhdProvider
130:         from crible.providers.fmp_free import FmpFreeProvider
131:         from crible.providers.simfin import SimFinProvider
132:         from crible.providers.yfinance_provider import YFinanceProvider
133: 
134:         inventory = []
135:         for cls in (YFinanceProvider, SimFinProvider, FmpFreeProvider, EodhdProvider):
136:             key_var = getattr(cls, "key_env_var", None)
137:             inventory.append(
138:                 {
139:                     "id": cls.id,
140:                     "kind": cls.kind,
141:                     "key_env_var": key_var,
142:                     "enabled": True if key_var is None else bool(env_os.environ.get(key_var)),
143:                 }
144:             )
145:         return inventory
146: 
147:     @app.get("/healthz")
```
**Verdict:** ______  ·  **Note:** ______

## F1 · src/crible/providers/base.py:54-60
**Finding:** L'endpoint /api/providers code en dur la liste des 4 classes provider et recalcule l'activation avec `True if key_var is None else bool(env)`, au lieu de consommer ProviderRegistry.activate / provider.enabled(env) qui est la source de vérité. Sa propre docstring dit « mirrors ProviderRegistry.activate ». Toute évolution de la règle d'activation (provider à deux clés, keyed avec repli keyless) fait diverger silencieusement l'écran Providers de la réalité.
```
52:     env: dict[str, str] = field(default_factory=dict)
53: 
54:     def activate(self, providers: Iterable[Provider]) -> list[Provider]:
55:         active: list[Provider] = []
56:         for provider in providers:
57:             if provider.enabled(self.env):
58:                 active.append(provider)
59:                 continue
60:             key_var = getattr(provider, "key_env_var", None)
61:             log.info(
62:                 "provider %s disabled (no key configured)%s",
```
**Verdict:** ______  ·  **Note:** ______

## F9 · docs/market/2026-07-12/REPORT.md:1
**Finding:** Le service d'ingestion est le plus gros fichier source (370 LOC) avec la profondeur d'imbrication la plus élevée du repo (14), churn 5 — signal d'un module qui orchestre bootstrap, crawl budgété, prix et reconciliation dans une seule unité. Analysable mais coûteux à faire évoluer sans régression.
```
1: # REPORT — self-hosted / zero-key fundamental stock screeners (mode startup)
2: 
3: ## Executive summary
```
**Verdict:** ______  ·  **Note:** ______

## F2 · src/crible/ingest/service.py:1
**Finding:** Le service d'ingestion est le plus gros fichier source (370 LOC) avec la profondeur d'imbrication la plus élevée du repo (14), churn 5 — signal d'un module qui orchestre bootstrap, crawl budgété, prix et reconciliation dans une seule unité. Analysable mais coûteux à faire évoluer sans régression.
```
1: """FR-008 — the ingest service loop: bootstrap → crawl → compute → publish.
2: 
3: Runs as the `ingest` Docker service. On first boot the bootstrap sample
```
**Verdict:** ______  ·  **Note:** ______

## F10 · README.md:20
**Finding:** L'endpoint /api/providers code en dur la liste des 4 classes provider et recalcule l'activation avec `True if key_var is None else bool(env)`, au lieu de consommer ProviderRegistry.activate / provider.enabled(env) qui est la source de vérité. Sa propre docstring dit « mirrors ProviderRegistry.activate ». Toute évolution de la règle d'activation (provider à deux clés, keyed avec repli keyless) fait diverger silencieusement l'écran Providers de la réalité.
```
18: crible screen "roe > 15 AND piotroski >= 7 AND country IN ('FR','DE')"
19: ```
20: 
21: ## Status
22: 
```
**Verdict:** ______  ·  **Note:** ______

## F2 · run:analysis.json
**Finding:** Le service d'ingestion est le plus gros fichier source (370 LOC) avec la profondeur d'imbrication la plus élevée du repo (14), churn 5 — signal d'un module qui orchestre bootstrap, crawl budgété, prix et reconciliation dans une seule unité. Analysable mais coûteux à faire évoluer sans régression.
```
{
  "target": "/Users/maxime/Downloads/crible",
  "files": 74,
  "loc": 6485,
  "languages": {
    ".py": 52,
    ".tsx": 14,
    ".ts": 8
  },
  "hotspots": [
    {
      "path": "src/crible/ingest/service.py",
```
**Verdict:** ______  ·  **Note:** ______

## F3 · docker-compose.yml:28
**Finding:** docker-compose.yml publie l'API sur l'hôte (${CRIBLE_PORT:-8000}:8000) sans authentification et sans caveat documenté. Acceptable pour un usage mono-utilisateur en réseau privé (OWASP A05 Security Misconfiguration), mais un self-hoster qui l'expose derrière une IP publique ouvre l'API en clair. L'absence de note d'install est le vrai risque pour la cible self-host.
```
26:   api:
27:     build: .
28:     ports:
29:       - "${CRIBLE_PORT:-8000}:8000"
30:     volumes:
```
**Verdict:** ______  ·  **Note:** ______

## F5 · README.md:20
**Finding:** Une question explicite « puis-je self-héberger cet outil de recherche actions sur mon Synology ? » reste sans réponse depuis 2023 chez le leader OSS OpenBB. crible peut y répondre par un guide d'install NAS/compose one-liner — friction d'adoption levée pour le cœur de cible.
```
18: crible screen "roe > 15 AND piotroski >= 7 AND country IN ('FR','DE')"
19: ```
20: 
21: ## Status
22: 
```
**Verdict:** ______  ·  **Note:** ______

## F5 · docs/market/2026-07-12/REPORT.md:1
**Finding:** Une question explicite « puis-je self-héberger cet outil de recherche actions sur mon Synology ? » reste sans réponse depuis 2023 chez le leader OSS OpenBB. crible peut y répondre par un guide d'install NAS/compose one-liner — friction d'adoption levée pour le cœur de cible.
```
1: # REPORT — self-hosted / zero-key fundamental stock screeners (mode startup)
2: 
3: ## Executive summary
```
**Verdict:** ______  ·  **Note:** ______

## F6 · src/crible/api/main.py:119-145
**Finding:** Transformer la duplication F1 en amélioration : l'endpoint consomme le registre au lieu de réénumérer et recalculer, supprimant le risque de dérive UI↔réalité.
```
117:         return runtime().status()
118: 
119:     @app.get("/api/providers")
120:     def providers() -> list[dict]:
121:         """FR-013/FR-014 — read-only provider inventory for the settings view.
122: 
123:         Enablement mirrors ProviderRegistry.activate: keyless is always on,
124:         a keyed provider is on iff its env var is set. No instantiation —
125:         id/kind/key_env_var are class attributes.
126:         """
127:         import os as env_os
128: 
129:         from crible.providers.eodhd import EodhdProvider
130:         from crible.providers.fmp_free import FmpFreeProvider
131:         from crible.providers.simfin import SimFinProvider
132:         from crible.providers.yfinance_provider import YFinanceProvider
133: 
134:         inventory = []
135:         for cls in (YFinanceProvider, SimFinProvider, FmpFreeProvider, EodhdProvider):
136:             key_var = getattr(cls, "key_env_var", None)
137:             inventory.append(
138:                 {
139:                     "id": cls.id,
140:                     "kind": cls.kind,
141:                     "key_env_var": key_var,
142:                     "enabled": True if key_var is None else bool(env_os.environ.get(key_var)),
143:                 }
144:             )
145:         return inventory
146: 
147:     @app.get("/healthz")
```
**Verdict:** ______  ·  **Note:** ______

## F6 · src/crible/providers/base.py:54
**Finding:** Transformer la duplication F1 en amélioration : l'endpoint consomme le registre au lieu de réénumérer et recalculer, supprimant le risque de dérive UI↔réalité.
```
52:     env: dict[str, str] = field(default_factory=dict)
53: 
54:     def activate(self, providers: Iterable[Provider]) -> list[Provider]:
55:         active: list[Provider] = []
56:         for provider in providers:
```
**Verdict:** ______  ·  **Note:** ______

