<h1 align="center" style="color:#e75480;">Public Funds Transparency Simulator</h1>

<p align="center"><strong>Can a shared digital record make it harder to quietly rewrite the history of public spending?</strong></p>

A Python proof-of-concept for **IEMT302 Emerging Technology**, Nelson Mandela University. The simulator follows a fictional **R500 million hospital project**, records transactions in a hash-linked ledger and tests its safeguards through 12 demonstrations and a systematic attack campaign.

> **Important:** All organisations, transactions, amounts and documents are fictional. This is an educational simulator, not a government system or a real blockchain network.

---

<h2 style="color:#e75480;">1. What the project demonstrates</h2>

The simulator explores whether a shared, tamper-evident record could help people check public spending.

| Term       | Meaning                                                  |
| ---------- | -------------------------------------------------------- |
| Ledger     | A record of transactions.                                |
| Block      | One transaction entry.                                   |
| Hash       | A digital fingerprint that changes when data changes.    |
| Chain      | Blocks linked using the previous block's hash.           |
| Copies     | Simulated Treasury, Auditor and Public Watchdog records. |
| Checkpoint | A published block number and hash used for comparison.   |

### The fictional project

* National Treasury allocates **R500 million**.
* A **R480 million contract** is awarded.
* **R150 million** is recorded as actually paid to the contractor.
* The contractor then records spending with suppliers.

The R20 million difference between the allocation and contract award is visible but unexplained. Supplier payments represent the contractor spending money it received; they are not additional government payments.

---

<h2 style="color:#e75480;">2. Requirements</h2>

* Python 3.9 or later.
* Standard Python library.
* Tkinter for the graphical interface.

On Ubuntu/Debian, install Tkinter if needed:

```bash
sudo apt install python3-tk
```

---

<h2 style="color:#e75480;">3. How to run the simulator</h2>

Open a terminal in the folder containing `public_funds_simulator.py`.

### Open the graphical simulator

```bash
python public_funds_simulator.py
```

This opens the simulator window. Use the tabs to explore the fictional transactions, ledger checks and experiments.

### Run the 12 scripted demonstrations

```bash
python public_funds_simulator.py --test
```

This runs demonstrations E1–E12 and displays their results in the terminal.

### Run the systematic attack campaign

```bash
python public_funds_simulator.py --campaign
```

This runs the larger automated experiment.

### Repeat an experiment with a chosen seed and trial count

```bash
python public_funds_simulator.py --campaign --seed 7 --trials 500
```

Using the same seed and settings makes the randomised experiment repeatable.

---

<h2 style="color:#e75480;">4. How to explore the graphical interface</h2>

| Tab                    | What to do                                                                             |
| ---------------------- | -------------------------------------------------------------------------------------- |
| **1. Start**           | Read the explanation of the project and its key terms.                                 |
| **2. Overview**        | View the project figures and automatic checks.                                         |
| **3. Money Trail**     | Follow the contractor's recorded receipts and spending.                                |
| **4. Fingerprints**    | Enter text, view its hash and explore ledger edits.                                    |
| **5. Compare**         | See how copies and checkpoints help identify changes.                                  |
| **6. Demonstrations**  | Explore the 12 scripted experiments. Select a test to read its explanation and result. |
| **7. Systematic Test** | Run the automated attack campaign and examine its results.                             |

---

<h2 style="color:#e75480;">5. Understanding the experiments</h2>

### Scripted demonstrations: E1–E12

These are 12 manually designed scenarios that show how individual safeguards behave.

| Test | What it demonstrates                                          |
| ---- | ------------------------------------------------------------- |
| E1   | Untouched ledger passes its checks.                           |
| E2   | An unprotected amount edit is detected.                       |
| E3   | Rewriting the full chain can pass its own hash check.         |
| E4   | Comparing copies exposes a rewrite.                           |
| E5   | A shortened chain can pass its own check.                     |
| E6   | A full copy reveals missing blocks.                           |
| E7   | Integrity does not prove that a payment is genuine.           |
| E8   | The R20 million allocation difference is visible.             |
| E9   | An altered supporting document fails its hash check.          |
| E10  | Payment limits can prevent overspending.                      |
| E11  | A published checkpoint helps expose rewriting and truncation. |
| E12  | The system automatically flags the R20 million difference.    |

### Systematic attack campaign

Unlike the demonstrations, this experiment uses a seeded random generator to select attacks, transaction details and attacker capabilities.

It tests:

* **9 attack types**, including amount changes, redirected payments, deleted blocks and document changes.
* **5 attacker capability levels**, from basic edits to control over every copy and checkpoint.
* **5 detection methods**, including hash checks, copy comparisons, checkpoints, document checks and audit rules.
* **10 hypotheses**, assessed using a fixed rule and 95% Wilson confidence intervals.

The standard reported experiment uses seed **2026**, with **200 trials per attack per capability level**, giving **9,000 attack scenarios**.

### Main findings

| Finding                                                                        |              Result |
| ------------------------------------------------------------------------------ | ------------------: |
| Naive edits detected by the internal hash check                                |                100% |
| Full local rewrites detected by the internal hash check                        |                  0% |
| Full rewrites detected using honest copies or a checkpoint                     |                100% |
| Amount edits detected by audit rules alone                                     |               14.5% |
| Advantage of the hash chain over a plain database with copies and a checkpoint | 0 percentage points |

The comparison shows that hash chaining helps expose basic edits, but independent copies and published checkpoints provide important protection. A careful insider can still enter a plausible false payment through the normal process.

---

<h2 style="color:#e75480;">6. What the project does not do</h2>

* It does not use a real blockchain network or consensus mechanism.
* The three ledger copies are simulated on one computer.
* It does not implement identity checks or digital signatures.
* It does not connect to SAP, Oracle, banks or government systems.
* It uses seven blocks of fictional data and does not test performance at government scale.
* It does not prove that blockchain prevents corruption.

**A successful integrity check means that a record has not been changed in a way the checks detect. It does not prove that the original information was true or lawful.**

---

<h2 style="color:#e75480;">7. Repository contents</h2>

```text
public_funds_simulator.py   # Simulator, GUI and experiments
README.md                   # Project instructions
```

The Python file contains the ledger logic, fictional transactions, financial summaries, validation checks, 12 demonstrations, systematic attack campaign and graphical interface.

---

<h2 style="color:#e75480;">8. Credits</h2>

Developed by **Naledi Mabuya** for **IEMT302 Emerging Technology**, Faculty of Engineering, the Built Environment and Technology, Nelson Mandela University.

Accompanies the research project:

*Investigating the Feasibility of Blockchain-Based Transparency for South African Public Fund Transactions: The Development of a Proof-of-Concept System.*
