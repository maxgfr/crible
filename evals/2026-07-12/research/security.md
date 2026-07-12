# Research — security (ISO/IEC 25010 security · OWASP Top 10 2021 A01–A10)

Référentiel : OWASP Top 10 2021 (https://owasp.org/Top10/2021/) — A01 Broken Access Control, A02 Cryptographic Failures, A03 Injection, A04 Insecure Design, A05 Security Misconfiguration, A06 Vulnerable Components, A08 Software & Data Integrity, A09 Logging, A10 SSRF ; check-lists par catégorie : https://cheatsheetseries.owasp.org/IndexTopTen.html.

Application à crible (self-hosted, mono-utilisateur, zéro clé) : surfaces = API FastAPI locale (A03 : le DSL est compilé vers SQL DuckDB — l'injection via requête DSL est LE point à prouver), fichiers Parquet partagés writer/readers (A08 intégrité), crawl sortant yfinance/ESEF (A10 SSRF limité aux domaines prévus, parsing xBRL d'entrées externes), compose par défaut (A05 : ports exposés, pas d'auth — acceptable en réseau privé si documenté). Dépendances Python/JS (A06) : auditables via pip-audit/npm audit.

## Rubrique 0–5
- 0 : injection SQL démontrable via DSL ; 1 : entrées non validées sur l'API ; 2 : validation présente mais non testée adversarialement ; 3 : whitelist DSL prouvée par tests + parsing xBRL défensif ; 4 : + audit deps propre et défauts compose documentés (réseau privé) ; 5 : + tests d'injection systématiques et durcissement documenté (reverse proxy, authentification optionnelle).
Mesure : lire dsl/compiler.py (source→sink SQL), tenter 3 payloads DSL hostiles, pip-audit/npm audit, revue compose.
