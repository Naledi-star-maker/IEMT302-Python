# Public Funds Transparency Simulator

**Can a shared digital record make it harder to quietly rewrite the history of public spending? Try to cheat it and find out.**

A proof-of-concept built for **IEMT302 Emerging Technology** (Nelson Mandela University). It follows a fictional **R500 million hospital project** from budget to contractor to suppliers, writes every step into a hash-linked ledger, and then lets you attack that ledger to see what gets caught and what slips through.

> Everything here is fictional: the organisations, the project, the money and the documents. This is a teaching demo, not a government system, and **not a real blockchain network**.

---

## Why this exists

When public money is spent, how can ordinary people check that the *record* of that spending hasn't been changed after the fact? Today we mostly rely on an institution's own word, or on audits that happen long after the money is gone.

Blockchain-style ledgers are often pitched as the fix. This project tests that claim honestly, on a small scale, and reports the weak spots as well as the strengths.

**The headline finding:** a hash-linked ledger can show that a record was *changed*. It cannot show that a record was *true*.

---

## The idea in 60 seconds

| Concept | Plain-English meaning |
|---|---|
| **Ledger** | A list of every transaction, like a bank statement. |
| **Block** | One entry (one page) in the ledger, e.g. "Department paid contractor R50m for site preparation". |
| **Hash** | A fingerprint worked out from everything on a block. Change one digit and the fingerprint changes completely. |
| **Chain** | Each block copies the fingerprint of the block before it, so the pages are linked in order. |
| **Copies** | Treasury, Auditor and Public Watchdog each keep their own copy. If one is altered, it stops matching the others. |
| **Checkpoint** | The latest block number and fingerprint, published somewhere nobody can quietly edit. |

### The fictional project

```
National Treasury  --R500m allocated-->  Public Works Department
                                              |
                          R480m contract awarded (a promise, not money moved)
                          R150m actually paid (3 payments)
                                              v
                                  Ubuntu Infrastructure (contractor)
                                     |                      |
                                 R18m steel             R12m labour
                                     v                      v
                              Steel Supplier         Labour Services
```

Three details worth noticing:

- The **award is a promise to pay**, not a payment. Only the R150m of PAYMENT blocks is government money actually released.
- Supplier and labour transfers are the **contractor spending its own received money**, not extra government spending.
- **R20m** was allocated but never awarded, and no record explains it. The ledger shows the gap; it cannot say why.

---

## Running it

**Requirements:** Python 3.9+. Standard library only. Tkinter is needed for the window (it ships with most Python installs).

```bash
python public_funds_simulator.py          # opens the graphical interface
python public_funds_simulator.py --test   # runs all experiments in the terminal
```

On Ubuntu/Debian, if the window won't open: `sudo apt install python3-tk`.

---

## A guided tour (about 10 minutes)

| Tab | What to do there |
|---|---|
| **1. Start Here** | Read the two-minute explainer of every term used. |
| **2. Project Overview** | See the headline numbers and four automatic checks (integrity, documents, checkpoint, unexplained gap). |
| **3. Follow the Money** | Pick *Ubuntu Infrastructure* and see what the contractor received, passed on, and has no recorded use for. |
| **4. Fingerprint Lab** | Type a sentence and watch its hash. Then try four ways of cheating on the ledger. |
| **5. Compare Copies** | After cheating in tab 4, see how the other copies and the checkpoint expose it. |
| **6. Experiments** | Click any of the 12 tests to read what it did and what it means. |

The **"Viewing ledger copy"** dropdown (top right) chooses which of the three copies you are looking at and attacking. **Reset all copies** puts everything back.

---

## The experiments, explained

Think of the ledger as a **notebook of seven pages**, each with a fingerprint stamped on it that also depends on the page before. Each experiment is an attempt to tamper with a *temporary photocopy* of that notebook, then asking: did anyone notice?

Every test is labelled **Strength** (the ledger caught it), **Limitation** (the ledger could not catch it alone), or **Context/Baseline**. A **YES** under "matched expectation" only means the result was what we *predicted*. On a Limitation row, a YES means the weakness is real, not that the system succeeded.

### Part 1: Can it catch edits?

| Test | What we did | Result | What it means |
|---|---|---|---|
| **E1 Baseline** | Checked the untouched ledger. | Valid | The starting point. If this failed, every later failure could be a bug rather than our tampering. |
| **E2 Careless edit** | Changed the first payment from R50m to R150m and left its fingerprint alone. | **Caught** (stored hash mismatch at block 2) | The old fingerprint no longer fits the new contents. Like changing a cheque amount but leaving the old stamp. |
| **E3 Careful rewrite** | Made the same change, then recalculated *every* fingerprint in the chain. | **Not caught** (passes its own check) | Someone who controls a whole copy can redo all the stamps. Hashes alone do not stop an insider. |
| **E4 Compare copies** | Compared that rewritten copy with an untouched one. | **Caught** (disagreement at block 2) | The cheat only shows up because an independent copy exists. Comparison says the copies *disagree*, not which is right. |

**The lesson of E2 to E4:** the hashing is not what protects you. *Independent copies* are.

### Part 2: Can it catch deletion?

| Test | What we did | Result | What it means |
|---|---|---|---|
| **E5 Delete last two blocks** | Removed the final two entries and checked the shorter chain alone. | **Not caught** | A shorter chain is still perfectly self-consistent. Nothing inside it says pages are missing. |
| **E6 Compare to full copy** | Compared the shortened chain with the complete one. | **Caught** (5 vs 7 blocks) | Another copy reveals what is missing. |
| **E11 Published checkpoint** | Checked both the shortened chain (E5) and rewritten chain (E3) against a published block count and hash, with **no second copy**. | **Both caught** | A single public checkpoint exposes tampering that internal checks missed. It only works if the checkpoint sits somewhere the ledger keeper can't edit. |

### Part 3: Can it tell if a transaction is *true*?

| Test | What we did | Result | What it means |
|---|---|---|---|
| **E7 Unsupported payment** | Added a R40m payment to an unknown recipient with no supporting document. | **Not caught** | The hashes are consistent, so the integrity check passes. Valid does not mean honest or authorised. |
| **E9 Altered document** | Edited a stored payment certificate, then re-checked it against the fingerprint recorded on the ledger. | **Caught** | Only fingerprints of documents go on the ledger, not the documents. A later change to a document no longer matches. Caveat: a *false* document recorded correctly would still pass. |

### Part 4: Can rules and flags help?

| Test | What we did | Result | What it means |
|---|---|---|---|
| **E8 Allocation vs award** | Subtracted the R480m award from the R500m budget. | R20m difference | The ledger exposes the number but does not interpret it. It is not proof of theft. |
| **E12 Automatic gap flag** | Ran a rule that flags allocated money that is neither awarded nor explained. | **R20m flagged** | The gap no longer depends on a reader noticing it. It still cannot say *why*, and a normal database could run the same rule. |
| **E10 Payment rule at entry** | Proposed a R400m payment (breaks the R480m award) and a R40m payment to an unverified recipient (stays inside it). | **R400m rejected, R40m accepted** | A rule can stop overspending *before* it is recorded. It cannot catch fraud that stays inside the limit. Rules only catch what they were written to catch. |

### What the experiments add up to

| The ledger is good at | The ledger cannot do alone |
|---|---|
| Detecting careless edits | Stopping someone who controls a whole copy |
| Exposing disagreement between independent copies | Saying which copy is correct |
| Detecting changed supporting documents | Proving a document was truthful |
| Stopping rule-breaking before it is recorded | Catching dishonest entries that obey the rules |
| Exposing and flagging gaps | Explaining why a gap exists |

In short, the experiments separate **integrity** (*was it changed?*) from **legitimacy** (*was it true or authorised?*). Blockchain-style tools help with the first. The second still needs people, governance, audits and evidence.

---

## What this project does *not* do

- No real network, no consensus protocol, no voting between copies.
- No identity checks or digital signatures; the system design proposes these but the simulator does not implement them.
- No privacy controls and no performance testing at scale.
- Seven blocks of fictional data, each test run once on a fixed dataset.
- Not a comparison against a conventional ledger database, though E10 and E12 note that a normal database could run the same rules.
- Nothing here is financial, legal or auditing advice, and it does **not** prove that blockchain would reduce corruption.

---

## Repository layout

```
public_funds_simulator.py   # the whole simulator: logic, experiments and GUI
README.md                   # this file
```

Inside the script: hashing and chain logic (section 2), the fictional transactions (3), financial summaries (4), evidence checks and payment rule (5), the 12 experiments (6), plain-language content (7) and the Tkinter interface (8).

---

## Credits and context

Built by Naledi Mabuya for **IEMT302 Emerging Technology**, Faculty of Engineering, the Built Environment and Technology, Nelson Mandela University. Accompanies the report *Investigating the Feasibility of Blockchain-Based Transparency for South African Public Fund Transactions*.
