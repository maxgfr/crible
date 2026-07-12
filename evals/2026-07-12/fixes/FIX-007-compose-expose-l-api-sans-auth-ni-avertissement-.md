# FIX-007 — compose expose l'API sans auth ni avertissement « réseau privé »  (P2 · DEFECT)

**Finding F3:** docker-compose.yml publie l'API sur l'hôte (${CRIBLE_PORT:-8000}:8000) sans authentification et sans caveat documenté. Acceptable pour un usage mono-utilisateur en réseau privé (OWASP A05 Security Misconfiguration), mais un self-hoster qui l'expose derrière une IP publique ouvre l'API en clair. L'absence de note d'install est le vrai risque pour la cible self-host.
**Evidence:** `docker-compose.yml:28`
**Why it matters:** Un utilisateur mappe le port sur 0.0.0.0 d'un VPS sans reverse-proxy → API et données lisibles par quiconque scanne le port.

## RED — write this test first
Write a failing test that reproduces: Un utilisateur mappe le port sur 0.0.0.0 d'un VPS sans reverse-proxy → API et données lisibles par quiconque scanne le port.

Suggested test file: `tests/compose-expose-l-api-sans-auth-ni-avertissement-.test.ts`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Documenter « réseau privé / reverse-proxy uniquement » dans le README d'install (répond aussi à la demande self-host [S23]) ; envisager un bind loopback par défaut ou une auth optionnelle.

Touch only: `docker-compose.yml`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
