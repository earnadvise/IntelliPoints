# IntelliPoints

> Built with Arc Studio - money-powered apps in minutes

This is the **project memory** - what Arc Studio remembers about building this app. It helps future agents (or humans) understand and extend the project.

---

## What This App Does

IntelliPoints is a permissionless points token on GenLayer. Any address can earn points by submitting a free-text contribution claim that is judged by an LLM via the Equivalence Principle (consensus across multiple independent validators). Points can also be transferred peer-to-peer or burned.

## Tech Stack

- Language: Python 3, GenVM SDK (`py-genlayer`)
- Chain: GenLayer (any network)
- Runner: `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` (pinned)

## Contracts

| Contract | File | Design Doc | Deployed (Studionet) |
|----------|------|-----------|----------------------|
| IntelliPoints | `contracts/IntelliPoints.py` | `contracts/IntelliPoints-design.md` | `0x9f02b54411C5b38D7Fd8BCdb73f8d010bB1314C8` |
| PredictionMarket | `contracts/PredictionMarket.py` | `contracts/PredictionMarket-design.md` | TBD |

## Key Files

- `src/App.tsx` - Main application logic
- `src/components/` - UI components
- `src/config.ts` - wagmi config (chains, connectors, transports)

## To Run

```bash
bun install
bun run dev
```
