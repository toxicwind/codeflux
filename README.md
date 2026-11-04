# Codeflux Pen

> The estate's **code-generation & strategy-racing** pen. Consolidates the
> codeflux / fluxling family: natural-language code transformation and
> empirical first-passing-wins strategy racing.

A **thin coordinator** pen (submoduleless). Products are peer standalone
checkouts under `products/`, each with its own repo + history.

## Member products

| Product | Repo | Role |
|---|---|---|
| `codeflux-patchling` | `toxicwind/codeflux-patchling` | `generate_diff` / `smartapply` / `mutate` — bounded NL code transformation |
| `codeflux-rig` | `toxicwind/codeflux-rig` | agent-loop / rig harness around patchling |
| `code-racer` | `toxicwind/estate-projects` | race candidate strategies; first passing acceptance-test wins |
| `fluxling` | `toxicwind/fluxling` | consolidated product (formerly codeflux-patchling lineage) |

## Living code

Every product in this pen is **living code** (architect directive 2026-11-04):
agents MAY modify, mutate, and add to it as they use it. Race before you
settle — use `code-racer` to pick between approaches and record the winner.

## Layout

```
pens/codeflux/
  AGENTS.md      # pen contract (thin coordinator, living-code doctrine)
  bin/           # pen-owned entrypoints (symlinked into ~/.local/bin)
  docs/          # pen-owned documentation
  products/      # peer standalone checkouts (auto-ignored by .gitignore)
```