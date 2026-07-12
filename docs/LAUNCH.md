# Dossier de lancement — crible

Préparé le 2026-07-12. Tout est prêt-à-trancher : **rien n'a été publié** (repo toujours privé local). Trois décisions t'appartiennent, listées en fin de document.

---

## 1. awesome-selfhosted — PR prête à coller

Le processus actuel passe par le repo `awesome-selfhosted/awesome-selfhosted-data` : créer `software/crible.yml` via l'UI GitHub → « Create a new branch for this commit and start a pull request » (source : CONTRIBUTING.md du repo data, fetché le 2026-07-12).

### Fichier `software/crible.yml` prêt à coller

```yaml
name: crible
website_url: https://github.com/maxgfr/crible
source_code_url: https://github.com/maxgfr/crible
description: "Fundamental stock screener with a filter DSL over a 161k-equity universe, transparent Piotroski/Altman/Beneish scores and per-value data provenance, no API keys required (alternative to Stockopedia, Simply Wall St)."
licenses:
  - MIT
platforms:
  - Docker
  - Python
tags:
  - Money, Budgeting & Money Management
```

Règles de description respectées (leur CONTRIBUTING) : concise, pas de « open-source / free / self-hosted » (redondants là-bas), mention `(alternative to …)` conforme. Message de commit suggéré : `add crible`.

### Prérequis d'éligibilité — état de crible en face de chacun

| Exigence awesome-selfhosted | État crible | Verdict |
|---|---|---|
| Licence FOSS (identifiant SPDX) | MIT à la racine (`LICENSE`, © 2026 maxgfr) | ✅ |
| Self-hostable sans dépendance cloud | `docker compose up`, contrat zéro clé | ✅ |
| Release taguée obligatoire (« No tagged releases = rejection ») | **Aucun tag/release — repo privé** | ❌ à faire au moment de la publication |
| « First released more than 4 months ago » | Première release = jour de la publication → **PR soumissible ~4 mois après** | ⏳ à planifier |
| Activité (retrait si 6-12 mois sans dev) | Développement actif | ✅ |
| Logiciel fonctionnel | E2E réel validé, éval 81/100 | ✅ |

**Conclusion** : la PR est prête mais **non soumissible avant : publication du repo + release taguée + ~4 mois d'ancienneté de release.** Mettre un rappel calendrier au moment du push.

---

## 2. GitHub — topics et description proposés

**Description repo suggérée** (≤ 350 chars) :
> Self-hosted fundamental stock screener — 161k equities, zero API keys forever, transparent Piotroski/Altman/Beneish scores with full data provenance, DuckDB-fast (full-universe screens in <1s).

**Topics (10)** :

| Topic | Pourquoi |
|---|---|
| `stock-screener` | Le terme de recherche n°1 de la catégorie |
| `fundamental-analysis` | Positionne face aux screeners techniques |
| `self-hosted` | Le canal de distribution principal (awesome-selfhosted, r/selfhosted) |
| `investing` | Terme large, gros trafic |
| `value-investing` | La communauté Piotroski/Graham — cœur de cible |
| `piotroski` | Requête de niche à faible concurrence — arrivée en tête probable |
| `duckdb` | Communauté data/perf, différenciateur technique |
| `finance` | Catégorie générique GitHub |
| `stocks` | Complément de découverte |
| `fastapi` | Découverte par stack (dev python cherchant des exemples réels) |

---

## 3. Cloud managé — comparatif sourcé (pages pricing fetchées le 2026-07-12)

Besoin réel de crible : conteneurs `ingest`+`api`, volume persistant (~10 GB parquet), RAM confortable pour le crawl/compute (≥ 4 GB recommandé).

| Option | Specs | Coût mensuel | Source |
|---|---|---|---|
| **Hetzner CAX11** (ARM) | 2 vCPU Ampere, 4 GB RAM, 40 GB disque, 20 TB trafic | **€5,99/mois** | hetzner.com (prix post-ajustement 15-06-2026) |
| **Hetzner CX22** (x86) | 2 vCPU, 4 GB RAM, 40 GB disque, 20 TB trafic | **~$4,59/mois** | hetzner.com/docs price-adjustment |
| **Fly.io** | shared-cpu-1x 256 MB : $2,02/mois — mais crible veut ≥ 4 GB (machine plus grosse à chiffrer au calculateur) + volume $0,15/GB/mois + egress $0,02/GB ; **aucun free tier** pour les nouveaux comptes | ~$15-25/mois estimé à 4 GB | fly.io/docs/about/pricing |

**Recommandation (5 lignes)** : Hetzner **CX22** si tu veux zéro doute de compatibilité x86, **CAX11** si tu vérifies d'abord que tes images docker sont multi-arch (Python/DuckDB/Node tournent bien sur ARM — à confirmer par un build local `--platform linux/arm64`). À €5-6/mois avec 40 GB et 20 TB de trafic, c'est 3-4× moins cher que Fly à specs équivalentes, et le modèle « un VPS + docker compose » colle exactement au contrat self-hosted de crible : la doc d'install NAS/Synology écrite au cycle 1 sert telle quelle. Fly reste pertinent seulement si tu veux du scale-to-zero multi-région — ce n'est pas le profil d'un crawler à l'état persistant. **Décision = toi.**

---

## 4. Checklist publication

- [x] **Licence** : MIT présente à la racine (`LICENSE`).
- [ ] **Screenshots dans le README** : les 6 captures du design round sont copiées dans `docs/img/` (`screener|status|providers`-`dark|light`.png). Snippet prêt à coller sous le titre du README :
  ```markdown
  ![crible screener](docs/img/screener-dark.png)
  <details><summary>More screens (status, providers, light theme)</summary>

  ![status](docs/img/status-dark.png)
  ![providers](docs/img/providers-dark.png)
  ![paper terminal](docs/img/screener-light.png)
  </details>
  ```
- [ ] **Release initiale** : passer le repo en public, puis tag `v0.1.0` + GitHub Release (le README « Status » cite déjà le SRD ; noter le contrat zéro clé dans les release notes). Déclenche l'horloge des 4 mois awesome-selfhosted.
- [x] **Contrat zéro clé mis en avant** : README l'affiche dès la 2e ligne (« zero API keys required — by contract, forever »).
- [x] **Upgrade payant optionnel documenté** : `docs/prds/eodhd.md` (EODHD Fundamentals €59,99/mois) — lien à garder dans le README section providers.
- [ ] **Après publication** : appliquer topics + description (§2), planifier la PR awesome-selfhosted (§1) à +4 mois, poster sur r/selfhosted (angle : « garde tes €550/an »).

---

## Les 3 décisions qui restent à Maxime

1. **Publier le repo** (public + release `v0.1.0`) — préalable à tout le reste ; démarre l'horloge des 4 mois d'awesome-selfhosted.
2. **Cloud managé** : proposer une instance démo/managée ou rester 100 % self-hosted ? Si oui : Hetzner CX22 (x86, ~$4,59/mois) recommandé, CAX11 (€5,99) après vérif multi-arch.
3. **GO distribution** : soumettre la PR awesome-selfhosted (texte prêt §1) au moment éligible + appliquer topics/description (§2) + post r/selfhosted.
