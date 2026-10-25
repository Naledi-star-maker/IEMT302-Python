# Public Funds Transparency Simulator

**Can a shared digital record make it harder to quietly rewrite the history of public spending? This project attacks its own ledger thousands of times, measures what gets caught, and compares it with a plain database.**

A proof-of-concept built for **IEMT302 Emerging Technology** (Nelson Mandela University). It follows a fictional **R500 million hospital project** from budget to contractor to suppliers, writes every step into a hash-linked ledger, and then tests that ledger two ways: short scripted **demonstrations** that explain how each safeguard works, and a **systematic test** in which a program, not a person, chooses the attacks.

> Everything here is fictional: the organisations, the project, the money and the documents. This is a teaching demo, not a government system, and **not a real blockchain network**.

---

## Why this exists

When public money is spent, how can ordinary people check that the *record* of that spending has not been changed after the fact? Today we mostly rely on an institution's own word, or on audits that happen long after the money is gone.

Blockchain-style ledgers are often pitched as the fix. This project tests that claim on a small scale and reports the weak spots as well as the strengths, including a head-to-head against a plain database.

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

- The **award is a promise to pay**, not a payment. Only the R150m of PAYMENT blocks is government money actually released.
- Supplier and labour transfers are the **contractor spending its own received money**, not extra government spending.
- **R20m** was allocated but never awarded, and no record explains it. The ledger shows the gap; it cannot say why.

---

## Running it

**Requirements:** Python 3.9+. Standard library only. Tkinter is needed for the window (it ships with most Python installs; on Ubuntu/Debian: `sudo apt install python3-tk`).

```bash
python public_funds_simulator.py                         # opens the window
python public_funds_simulator.py --test                  # the 12 scripted demonstrations
python public_funds_simulator.py --campaign              # the systematic test
python public_funds_simulator.py --campaign --seed 7 --trials 500
```

---

## A guided tour (about 15 minutes)

| Tab | What to do there |
|---|---|
| **1. Start** | Read the two-minute explainer of every term used. |
| **2. Overview** | Headline numbers and four automatic checks. |
| **3. Money Trail** | Pick *Ubuntu Infrastructure* and see what the contractor received, passed on, and has no recorded use for. |
| **4. Fingerprints** | Type a sentence and watch its hash. Then try four ways of cheating on the ledger. |
| **5. Compare** | See how the other copies and the checkpoint expose a cheat. |
| **6. Demonstrations** | Twelve short scripted tests. Click a row to read it in plain language. |
| **7. Systematic Test** | Press Run. Thousands of random attacks go through five detectors; ten pre-registered hypotheses are judged by a fixed rule. |

---

## Two kinds of experiment, and why both

**Demonstrations (E1 to E12, tab 6).** We wrote each scenario by hand. They are good at *explaining* a mechanism ("change an amount and leave the old stamp: caught") but they are chosen by us, so they cannot prove how often a safeguard works.

**Systematic test (tab 7).** A seeded random generator chooses *which* block, *which* amount and *which* party. It runs every attack many times, at five attacker skill levels, through five independent detectors, and judges ten hypotheses by a rule fixed in advance. Some hypotheses were predicted to fail.

### The threat model (all in the code, open to challenge)

| Attack | What the attacker does |
|---|---|
| A1 | Edits an amount |
| A2 | Redirects a transaction to another party |
| A3 | Edits a purpose description |
| A4 | Deletes a block from the middle |
| A5 | Truncates the final 1 or 2 blocks |
| A6 | Appends an unsupported payment to one copy |
| A7 | Swaps two blocks |
| A8 | Alters a supporting document |
| A9 | **Insider fraud:** a plausible, documented payment to the real contractor, within the award limit, entered through the normal process into *every* copy |

| Attacker level | What they can also do |
|---|---|
| C0 | Naive: edits the data only |
| C1 | Re-stamps the block they edited |
| C2 | Rewrites the whole local chain |
| C3 | C2, and repairs the document hashes |
| C4 | Also controls every copy, the checkpoint and the documents |

| Detector | What it checks |
|---|---|
| D1 | Internal hash check (recalculate every hash and link) |
| D2 | Compare with an honest copy |
| D3 | Published checkpoint |
| D4 | Supporting-document hash check |
| D5 | Audit rules that need no reference copy (allowed money routes, no party spends more than it received, payments within the award, every transaction has a document hash) |

### How the test stays objective

- **Randomised, seeded, repeatable.** Same seed, same numbers. Results were checked across five seeds.
- **Control run.** With no attack, no detector may fire. If one does, the test reports FAIL and the numbers cannot be trusted. Every attack is also checked to have really changed something.
- **Pre-registered hypotheses.** Each has a threshold and a prediction written in the code before the first run.
- **Fixed verdict rule.** A hypothesis is SUPPORTED only if the whole 95% Wilson confidence interval sits on the claimed side of its threshold, REFUTED only if it sits wholly on the other side, otherwise INCONCLUSIVE.
- **A fair rival.** The plain database gets every defence that does not need hashes: independent copies, a published digest of its rows, a document-hash column and the same audit rules. The only thing it lacks is the hash chain's internal check (D1).

### Results (seed 2026, 200 trials per attack per level, 9,000 attacks)

| ID | Hypothesis | Measured | Verdict |
|---|---|---|---|
| H1 | The internal hash check catches naive in-place edits | 100% | Supported |
| H2 | The internal hash check is blind to a full local rewrite | 0% | Supported |
| H3 | Honest copies or a checkpoint catch a full local rewrite | 100% | Supported |
| H4 | The internal hash check misses truncation at every attacker level | 0% | Supported |
| H5 | Audit rules catch an unsupported appended payment, even when copies and checkpoint are controlled | 100% | Supported |
| H6 | A plausible fraudulent payment entered through the normal process is flagged by no detector | 0% | Supported |
| H7 | An attacker who controls every copy, the checkpoint and the documents evades D1 to D4 | 0% | Supported |
| H8 | Audit rules alone catch random amount edits | 14.5% | **Refuted** (predicted) |
| H9 | With a single copy, the hash chain beats a plain database by 10 or more percentage points | +15.8 pp | Supported |
| H10 | With copies and a checkpoint, the hash chain beats a plain database by 10 or more percentage points | +0.0 pp | **Refuted** (predicted) |

### What the numbers say

1. **H1 to H7 follow largely from how hashing works.** Their value is in confirming the harness behaves correctly and in giving exact detection rates per attack.
2. **A careful insider defeats every integrity detector (H6, H7).** Integrity is not truth. This is the central limit of the technology.
3. **H9 versus H10 is the contribution of the hash chain.** On a single copy it adds about 16 percentage points of detection (it makes naive edits self-evident). Once independent copies and a published checkpoint exist, a plain database detects exactly as much. The protection comes from *independent copies and publication*, not from hashing alone.
4. **Audit rules (D5) are uneven (H8).** They reliably flag redirected money and unsupported payments, but flag only about 1 in 7 amount edits and no purpose edits.
5. **A C1 attacker is caught about 85% of the time on edits, not 100%.** Re-stamping a block breaks the link to the next block, unless the edited block is the last one. This was not scripted; it emerged from the random positions.

---

## The twelve scripted demonstrations (E1 to E12)

| Test | What it shows |
|---|---|
| E1 Baseline | The untouched ledger is valid (the starting point). |
| E2 Careless edit | Changing an amount without re-stamping is caught. |
| E3 Careful rewrite | Re-stamping the whole chain makes it pass its own check. |
| E4 Compare copies | An untouched copy exposes the rewrite, but cannot say which is right. |
| E5 Delete last two blocks | A shortened chain still passes its own check. |
| E6 Compare to full copy | Another copy reveals the missing blocks. |
| E7 Unsupported payment | A payment with no document passes integrity, which is not truth. |
| E8 Allocation vs award | The R20m difference is visible but unexplained. |
| E9 Altered document | A changed document no longer matches its recorded hash. |
| E10 Payment rule at entry | A rule stops the overspend, not a fraud inside the limit. |
| E11 Published checkpoint | A checkpoint catches the rewrite and the truncation with no second copy. |
| E12 Automatic gap flag | The R20m gap is flagged without a reader noticing it. |

---

## What this project does *not* do

- No real network, consensus or voting between copies.
- No identity checks or digital signatures; the system design proposes these but the simulator does not implement them.
- The threat model is ours. A different set of attacks, attacker levels or detectors could give different numbers.
- Seven blocks of fictional data; no performance testing at scale.
- Giving the plain database a published digest is itself a use of hashing. That is deliberate (it is what makes the comparison fair), and it is why the two systems tie in H10.
- Nothing here is financial, legal or auditing advice, and it does **not** prove that blockchain would reduce corruption.

---

## Repository layout

```
public_funds_simulator.py   # logic, demonstrations, systematic test and GUI
README.md                   # this file
```

Inside the script: hashing and chain logic (section 2), the fictional transactions (3), financial summaries (4), evidence checks and payment rule (5), the 12 demonstrations (6), the systematic attack campaign (6b), plain-language content (7) and the Tkinter interface (8).

---

## Credits and context

Built by Naledi Mabuya for **IEMT302 Emerging Technology**, Faculty of Engineering, the Built Environment and Technology, Nelson Mandela University. Accompanies the report *Investigating the Feasibility of Blockchain-Based Transparency for South African Public Fund Transactions*.