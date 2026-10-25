# IntelliPoints

A permissionless points token on GenLayer. Anyone can earn points by submitting a free-text contribution claim that is judged by an LLM — consensus is reached across multiple independent validators using the Equivalence Principle. Points can also be transferred peer-to-peer or burned.

Built with [Arc Studio](https://studio.arc.io)

---

## Tech Stack

- **Contract language:** Python 3 (GenLayer Intelligent Contract)
- **Runtime SDK:** `py-genlayer` (GenVM)
- **Chain:** GenLayer (any network — Studio, testnet, or mainnet)

---

## Project Files

| Path | Description |
|------|-------------|
| `contracts/IntelliPoints.py` | The intelligent contract |
| `contracts/IntelliPoints-design.md` | Design doc and security review |

---

## Contract Overview

| Method | Type | Description |
|--------|------|-------------|
| `balance_of(account)` | view | Returns point balance for an address |
| `get_total_supply()` | view | Returns total points in circulation |
| `mint(claim)` | write | Submit a contribution claim; LLM judges it; if accepted, caller receives 100 points |
| `transfer(to, amount)` | write | Send points to another address |
| `burn(amount)` | write | Destroy your own points |

`mint` uses `gl.vm.run_nondet_unsafe` — the leader and each validator independently prompt the LLM and compare the `approved` field. Both must agree for the transaction to commit.

---

## Development

### Prerequisites

- [GenLayer Studio](https://studio.genlayer.com) (local or hosted) — for deploying and interacting with the contract.
- No additional tooling needed; the contract is a single Python file.

### Environment Variables

None.

### Deploy

1. Open GenLayer Studio.
2. Load `contracts/IntelliPoints.py`.
3. Deploy — no constructor arguments needed.
4. Interact via the Studio Write Methods panel or the GenLayer SDK/CLI.

### Run unit tests (invariant check)

After deploying locally, call the write methods via the Studio console and verify:

```
balance_of(address) + balance_of(other) == get_total_supply()
```

after every sequence of mint / transfer / burn operations.
