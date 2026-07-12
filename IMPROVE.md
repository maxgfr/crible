# IMPROVE — cycle d'amélioration continue POC→marché

Méthode reproductible pour améliorer crible sans jamais développer une feature dont l'utilité marché n'est pas prouvée. Un cycle = 4 temps. Exécutable par un agent (Claude Code) ou un humain outillé. Chemins **absolus** obligatoires : les engines vivent hors du repo.

```bash
UE=/Users/maxime/.agents/skills/ultraeval/scripts/ultraeval.mjs
US=/Users/maxime/.agents/skills/ultrasearch/scripts/ultrasearch.mjs
CX=/Users/maxime/.agents/skills/construct/scripts/construct.mjs
DATE=$(date +%F)   # un dossier par cycle
```

## Temps 1 — Marché (ultrasearch, mode startup)

Question type : « self-hosted / no-API-key fundamental stock screeners — marché, concurrents, pricing, demande, gaps ». Chercher dans la langue du marché (EN), rapporter en français.

```bash
node $US gather --q "<question marché>" --mode startup --depth standard --out docs/market/$DATE
# dossier maigre ? bridge : WebSearch manuel puis, pour CHAQUE source retenue :
node $US fetch --url "<url>" --out docs/market/$DATE     # imprime un nouveau [S#]
# écrire docs/market/$DATE/SUMMARY.md + REPORT.md en citant [S#]
# (REPORT contient : candidate features avec évidence + launch checklist)
node $US render --run docs/market/$DATE
node $US check  --run docs/market/$DATE                  # gate mécanique — DOIT être vert
```

Enjeu fort (pivot, pricing) → tier deep : `plan --depth deep` puis gather/merge par sous-question, `verify` + `verify --apply`, exit gate `check --semantic --require-verify`. Règles dures : fetch web réel (2 tentatives vides max, jamais de source inventée) ; après `merge`, seuls les [S#] du master résolvent.

## Temps 2 — État réel (ultraeval, mode improve)

```bash
node $UE init  --target . --out evals/$DATE --kind codebase --mode improve --category "self-hosted fintech tool"
node $UE plan     --run evals/$DATE
node $UE analyze  --run evals/$DATE
node $UE brainstorm --run evals/$DATE          # remplir opportunities.json
node $UE brainstorm --run evals/$DATE --rank --check
# exécuter le workflow d'éval (agents/*.md), consolider findings.json, puis :
node $UE check  --run evals/$DATE
node $UE verify --run evals/$DATE --honeypots 3
node $UE verify --run evals/$DATE --apply <verdicts.json>
node $UE check  --run evals/$DATE --semantic --require-verify   # exit gate
node $UE backlog --run evals/$DATE --tdd
node $UE score   --run evals/$DATE --history   # ledger commité evals/history.jsonl
node $UE render  --run evals/$DATE
```

Chaque finding cite un `file:line` réel — le gate rejette le reste. Cycle N+1 : `node $UE compare --run evals/<new> --base evals/<old> --gate` (échec = baisse de score ou nouveau P0) — c'est le gate inter-cycles.

## Temps 3 — Gate marché (croisement)

Croiser `evals/$DATE/BACKLOG.json` × `docs/market/$DATE/REPORT.md` → `docs/improve/$DATE/PRIORITIES.md`, trois files :

1. **Améliorer l'existant** (bugs, UX, perf, finitions POC→marché : README vendeur, install story, docs, packaging) → exécutable sans gate.
2. **Features candidates AVEC évidence** — chaque entrée cite ≥1 [S#] du REPORT marché → spec d'abord (Temps 4), dev ensuite.
3. **Icebox** — tout le reste. Aucune ligne de code, même « évident ».

Plus la **launch checklist** (licence, install one-liner, landing/README, pricing éventuel, canal feedback, télémétrie opt-in…).

## Temps 4 — Spec & dev (construct, incrémental — jamais `init`)

> ⚠️ **`render --from-srd` régénère TOUT l'arbre `srd/design/*` ET `srd/prd/*` depuis le manifeste `SRD.json`** (le manifeste fait foi, pas les `.md` rendus). Toute édition à la main des fichiers rendus est écrasée au render suivant. **Avant tout render, synchronise le bloc `design` de `SRD.json`** (tokens, principles, screens, flows, `navigation`, `tokensAuthored: true`) avec l'identité de `/DESIGN.md` + `ui/src/tokens.css` — sinon l'identité retombe aux défauts. `tokensAuthored: true` supprime le bandeau « Seeded defaults » ; `design.navigation` (string) rend la section « Shell & navigation » (fix construct df31150). Parité spec↔code obligatoire après render.

```bash
# feature retenue : éditer srd/SRD.json (+ FR/acceptance/entities/ADR + bloc design synchronisé) puis :
node $CX render --out srd --from-srd --merge      # préserve la progression BUILD-PLAN ; régénère design/ + prd/
node $CX check  --out srd                          # gate structurel
# nouveau module → amender srd/brief.json + render --level complex (ids FR renumérotés → retagger les tests)
# pins d'évidence : node $CX research --out srd --angles market,oss,tech --url <u> — TOUJOURS repasser TOUS les angles (le dossier est REBUILD)
# dev TDD ; à chaque milestone :
node $CX verify --out srd --app . --run-tests --strict
```

## Règles permanentes

- **Un writer par repo.** Commits conventionnels par étape verte. **Jamais de push** de crible sans demande explicite.
- **Zéro clé API, zéro CDN** (NFR-013) — non négociables, y compris pour toute feature gated.
- **Bug d'engine (ultraeval/ultrasearch/construct)** → thread dédié : clone `github.com/maxgfr/<skill>` en tmp, repro test ROUGE, fix VERT, push **main** (semantic-release). Le cycle contourne en le notant. Ne jamais patcher `~/.agents/skills/` à la main.
- Fin de cycle : pytest + vitest + build verts, `construct verify --strict` vert, arbre propre, rapport (scorecard, quick wins livrés, features gated, checklist).
