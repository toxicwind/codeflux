# AGENTS.md — Codeflux (`pens/codeflux`)

> **Part of the estate's pens family** (`pens/{estate,geode,barn,ranch,olympus,forge,codeflux,...}`).
> A pens repo is a **thin coordinator**, not a product monorepo. It owns only
> its own metadata, `bin/`, and `docs/`. Products are peer standalone
> checkouts, referenced-not-owned.

## This repo is submoduleless by design

There are **no submodules** here. The repo's `.gitignore` is the kitchen-sink:
`*` with a whitelist. Any product checkout dropped into `products/` is
**auto-ignored** — nothing to register, no gitlink, no nested `.git` in the
index.

```
*
!.gitignore
!README.md
!LICENSE
!package.json
!mise.toml
!AGENTS.md
!bin/
!bin/**
!docs/
!docs/**
```

## Rules

1. **Never** `git submodule add` and never commit a gitlink (mode 160000).
2. A product is a peer clone: `git clone <url> products/<name>`. It brings
   its own history and its own remote.
3. The pen repo's `git status` must stay clean regardless of what the
   products are doing.
4. `bin/` entries are symlinked into `~/.local/bin` and pinned by the
   estate-ops manifest; `bin-verify.sh` treats a broken link as FAIL.
5. Runtime language is **Bun/TypeScript** (patchling is Python — it stays a
   peer with its own toolchain).
6. Secrets never live in this repo. They live in the secretsmith keyring.

## Where things go

- **A new product** → `products/<name>/`, plus a row in this pen's README
  member table and an entry in the estate-ops bin manifest.
- **Pen-owned documentation** → `docs/`.
- **Estate-wide documentation** (architecture, daemons, conventions) →
  `pens/estate/docs/`.

## The codeflux family (this pen's theme)

This pen consolidates the **codeflux / fluxling family** — natural-language
code transformation and empirical strategy racing:

| Product | Role |
|---|---|
| `codeflux-patchling` (fluxling) | `generate_diff` / `smartapply` / `mutate` — bounded NL code transformation |
| `codeflux-rig` | agent-loop / rig harness around patchling |
| `code-racer` | race candidate strategies, first-passing-acceptance-test wins |
| `fluxling` | the consolidated product (formerly codeflux-patchling lineage) |

**Living-code doctrine (2026-11-04, architect directive):** every product in
this pen is "living code" — agents MAY modify, mutate, and add to it as they
use it. Do not treat any codeflux product as frozen. Race before you settle:
when choosing between two transformation/routing approaches, race them with
`code-racer` and record the winner. See each product's own `AGENTS.md`.

## Resident rig

The codeflux family is the estate's code-generation/racing lane. Day-cycle via
`rig cron`; squawk lane `codeflux-*`.