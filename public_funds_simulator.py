"""
PUBLIC FUNDS TRANSPARENCY SIMULATOR  (v2, redesigned)
IEMT302 Emerging Technology Research Experiment

All entities and transactions are fictional.

This is a local proof of concept, not a production blockchain.
The three ledger copies simulate independent record keepers.
They are not a real blockchain network and do not implement
network consensus.

Requirements:
    Python 3.9+
    Tkinter (only needed for the graphical interface)
    Python standard library only

Usage:
    python public_funds_simulator.py           opens the graphical interface
    python public_funds_simulator.py --test    runs all experiments in the
                                               terminal (no window needed)
"""

import copy
import csv
import hashlib
import json
import sys

from datetime import datetime, timezone

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
except ImportError:  # lets "--test" run on a machine without Tkinter
    tk = ttk = messagebox = filedialog = None


# ============================================================
# 1. CONFIGURATION
# ============================================================

TREASURY = "National Treasury"
DEPARTMENT = "Fictional Public Works Department"
CONTRACTOR = "Ubuntu Infrastructure (Fictional)"
STEEL = "Steel Supplier (Fictional)"
LABOUR = "Labour Services (Fictional)"
OTHER = "Other Approved Recipient (Fictional)"

PARTIES = [TREASURY, DEPARTMENT, CONTRACTOR, STEEL, LABOUR, OTHER]

PARTY_ROLES = {
    TREASURY: "Sets the budget and allocates it to the department.",
    DEPARTMENT: "Receives the budget, awards the contract and pays the "
                "contractor.",
    CONTRACTOR: "Wins the tender, receives payments from the department "
                "and pays its own suppliers and labour.",
    STEEL: "A subcontractor supplying steel. Paid by the contractor, not "
           "by government.",
    LABOUR: "A subcontractor supplying labour. Paid by the contractor, "
            "not by government.",
    OTHER: "An approved recipient with no transactions in the baseline "
           "ledger. Used in the experiments.",
}

COPY_NAMES = ["Treasury", "Auditor", "Public Watchdog"]

ALLOCATION = 500_000_000
AWARD = 480_000_000

FIXED_TIME = "2026-10-15T10:00:00+00:00"
GENESIS_HASH = "0" * 64

PROJECT_ID = "EC-HOSPITAL-2026-001"
PROJECT_NAME = "Eastern Cape Hospital Infrastructure Project"

# Transaction types that actually move (or assign) money. A TENDER_AWARD is
# only a promise to pay, so it is deliberately left out.
MONEY_TYPES = {"ALLOCATION", "PAYMENT", "ONWARD_PAYMENT"}

TYPE_EXPLANATIONS = {
    "ALLOCATION": "budget assigned to a department",
    "TENDER_AWARD": "a promise to pay, NOT money moved",
    "PAYMENT": "government money paid to the contractor",
    "ONWARD_PAYMENT": "the contractor paying its own supplier",
}

HASH_DEMO_TEXT = "Payment of R50,000,000 to Ubuntu Infrastructure"

# Simulated off-chain supporting documents (invoices, tender files, etc.).
# The documents themselves are NOT stored on the ledger. Only the SHA-256
# hash of each document is recorded, so a later change to a document can
# be detected without publishing the document itself.
EVIDENCE = {
    "BUDGET-2026-001": "SIMULATED DOCUMENT: approved project budget",
    "TENDER-EC-HOSPITAL-001": "SIMULATED DOCUMENT: tender award letter",
    "PAYMENT-001": "SIMULATED DOCUMENT: payment certificate 001",
    "SUPPLIER-INVOICE-001": "SIMULATED DOCUMENT: steel supplier invoice",
    "SUPPLIER-INVOICE-002": "SIMULATED DOCUMENT: labour services invoice",
    "PAYMENT-002": "SIMULATED DOCUMENT: payment certificate 002",
    "PAYMENT-003": "SIMULATED DOCUMENT: payment certificate 003",
}

# Look and feel: baby pink and white, black headings.
BG_PINK = "#FFE4EC"
PINK_MID = "#FBCFE0"
PINK_DEEP = "#F4A6C0"
PINK_SOFT = "#FFF3F7"
WHITE = "#FFFFFF"
BLACK = "#000000"
GREY = "#4A4A4A"
PASS_GREEN = "#1B6B3A"
FAIL_RED = "#B3261E"


# ============================================================
# 2. HASHING AND BLOCKCHAIN LOGIC
# ============================================================

def sha256(text):
    """Return the SHA-256 digest of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(data):
    """Produce a consistent JSON representation before hashing."""
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def calculate_block_hash(block):
    """Hash every block field except the block's own stored hash."""
    data = {key: value for key, value in block.items() if key != "hash"}
    return sha256(canonical_json(data))


def add_block(chain, tx, timestamp=None):
    """Add a transaction as a hash-linked block."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    previous_hash = chain[-1]["hash"] if chain else GENESIS_HASH

    block = {
        "index": len(chain),
        "timestamp": timestamp,
        "transaction": copy.deepcopy(tx),
        "previous_hash": previous_hash,
    }

    block["hash"] = calculate_block_hash(block)
    chain.append(block)


def check_block(chain, i):
    """Return (hash_ok, link_ok) for one block."""
    block = chain[i]
    hash_ok = block.get("hash") == calculate_block_hash(block)
    expected_previous = chain[i - 1]["hash"] if i > 0 else GENESIS_HASH
    link_ok = block.get("previous_hash") == expected_previous
    return hash_ok, link_ok


def verify_chain(chain):
    """
    Verify the internal integrity of a chain.

    This does not prove that transactions are true, lawful or complete.
    """
    for i, block in enumerate(chain):

        if block.get("index") != i:
            return False, f"Block index mismatch at block {i}."

        expected_hash = calculate_block_hash(block)

        if block.get("hash") != expected_hash:
            return False, f"Stored hash mismatch at block {i}."

        expected_previous = chain[i - 1]["hash"] if i > 0 else GENESIS_HASH

        if block.get("previous_hash") != expected_previous:
            return False, f"Previous-hash mismatch at block {i}."

    return True, "All stored blocks pass the local integrity check."


def recalculate_chain(chain):
    """
    Recalculate the chain after a deliberate historical rewrite.

    Demonstrates why hashes alone do not prevent a local operator
    from rewriting a chain they control.
    """
    previous_hash = GENESIS_HASH

    for i, block in enumerate(chain):
        block["index"] = i
        block["previous_hash"] = previous_hash
        block["hash"] = calculate_block_hash(block)
        previous_hash = block["hash"]


def compare_chains(chain_a, chain_b):
    """
    Compare the lengths and block hashes of two copies.

    Both the stored hash and the recalculated hash are compared. Comparing
    stored hashes alone would miss a copy whose contents were edited
    without updating its stored hash.
    """
    if len(chain_a) != len(chain_b):
        return False, (
            f"Different chain lengths: {len(chain_a)} and "
            f"{len(chain_b)} blocks."
        )

    for i, (a, b) in enumerate(zip(chain_a, chain_b)):
        if (
            a["hash"] != b["hash"]
            or calculate_block_hash(a) != calculate_block_hash(b)
        ):
            return False, f"Hash disagreement at block {i}."

    return True, "The copies match block-for-block."


def make_checkpoint(chain):
    """
    A 'published checkpoint': the block count and latest hash, written
    down somewhere the ledger keeper cannot quietly edit (for example a
    public website or the Government Gazette).
    """
    return {
        "blocks": len(chain),
        "hash": chain[-1]["hash"],
        "published": FIXED_TIME,
    }


def check_against_checkpoint(chain, checkpoint):
    """Check a ledger copy against a previously published checkpoint."""
    n = checkpoint["blocks"]

    if len(chain) < n:
        return False, (
            f"Copy has {len(chain)} blocks but the published checkpoint "
            f"covers {n}."
        )

    block = chain[n - 1]

    if (
        block["hash"] != checkpoint["hash"]
        or calculate_block_hash(block) != checkpoint["hash"]
    ):
        return False, (
            f"Block {n - 1} does not match the published checkpoint."
        )

    return True, "Matches the published checkpoint."


# ============================================================
# 3. TRANSACTION DATA
# ============================================================

def transaction(frm, to, amount, kind, purpose, evidence_reference=""):
    return {
        "project_id": PROJECT_ID,
        "from": frm,
        "to": to,
        "amount": int(amount),
        "type": kind,
        "purpose": purpose,
        "evidence_reference": evidence_reference,
        "supporting_data_hash": "",
    }


def build_initial_ledger():
    """Build the fictional baseline transaction history."""
    chain = []

    records = [
        transaction(
            TREASURY, DEPARTMENT, ALLOCATION,
            "ALLOCATION",
            "Approved fictional project budget",
            "BUDGET-2026-001",
        ),
        transaction(
            DEPARTMENT, CONTRACTOR, AWARD,
            "TENDER_AWARD",
            "Contract award; this is a commitment, not a payment",
            "TENDER-EC-HOSPITAL-001",
        ),
        transaction(
            DEPARTMENT, CONTRACTOR, 50_000_000,
            "PAYMENT",
            "Site preparation",
            "PAYMENT-001",
        ),
        transaction(
            CONTRACTOR, STEEL, 18_000_000,
            "ONWARD_PAYMENT",
            "Steel materials; downstream use of contractor funds",
            "SUPPLIER-INVOICE-001",
        ),
        transaction(
            CONTRACTOR, LABOUR, 12_000_000,
            "ONWARD_PAYMENT",
            "Labour services; downstream use of contractor funds",
            "SUPPLIER-INVOICE-002",
        ),
        transaction(
            DEPARTMENT, CONTRACTOR, 75_000_000,
            "PAYMENT",
            "Structural construction",
            "PAYMENT-002",
        ),
        transaction(
            DEPARTMENT, CONTRACTOR, 25_000_000,
            "PAYMENT",
            "Materials and equipment",
            "PAYMENT-003",
        ),
    ]

    for record in records:
        # Record the hash of the supporting document on the ledger.
        record["supporting_data_hash"] = sha256(
            EVIDENCE[record["evidence_reference"]]
        )

        add_block(chain, record, FIXED_TIME)

    return chain


def make_copies():
    """Create three initially identical simulated ledger copies."""
    baseline = build_initial_ledger()

    return {name: copy.deepcopy(baseline) for name in COPY_NAMES}


# ============================================================
# 4. FINANCIAL SUMMARIES AND TRACEABILITY
# ============================================================

def money(amount):
    return f"R{amount:,.2f}"


def money_short(amount):
    """Compact form for diagrams: R150m."""
    if abs(amount) >= 1_000_000:
        value = amount / 1_000_000
        text = f"{value:,.0f}" if value == int(value) else f"{value:,.1f}"
        return f"R{text}m"
    return f"R{amount:,.0f}"


def government_payments(chain):
    """Sum completed government-to-contractor payments."""
    return sum(
        block["transaction"]["amount"]
        for block in chain
        if block["transaction"]["type"] == "PAYMENT"
        and block["transaction"]["from"] == DEPARTMENT
        and block["transaction"]["to"] == CONTRACTOR
    )


def allocation_amount(chain):
    return sum(
        block["transaction"]["amount"]
        for block in chain
        if block["transaction"]["type"] == "ALLOCATION"
    )


def award_amount(chain):
    return sum(
        block["transaction"]["amount"]
        for block in chain
        if block["transaction"]["type"] == "TENDER_AWARD"
    )


def unexplained_gap(chain):
    """
    Automatic flag for money that was allocated but is neither awarded
    nor explained by a recorded return or reallocation.

    The flag says a gap exists. It cannot say why.
    """
    explained = sum(
        block["transaction"]["amount"]
        for block in chain
        if block["transaction"]["type"] in ("RETURN", "REALLOCATION")
    )

    gap = allocation_amount(chain) - award_amount(chain) - explained

    if gap > 0:
        return gap, (
            f"FLAG: {money(gap)} was allocated but is neither awarded nor "
            "explained by any recorded return or reallocation."
        )

    return 0, "No unexplained difference between allocation and award."


def trace_party(chain, party):
    """Return recorded transfers involving a selected party."""
    return [
        block for block in chain
        if (
            block["transaction"]["from"] == party
            or block["transaction"]["to"] == party
        )
    ]


def flow_amount(chain, frm, to):
    """Total money moved between two parties (excludes tender awards)."""
    return sum(
        block["transaction"]["amount"]
        for block in chain
        if block["transaction"]["from"] == frm
        and block["transaction"]["to"] == to
        and block["transaction"]["type"] in MONEY_TYPES
    )


def party_summary(chain, party):
    """Return (recorded in, recorded out) for one party."""
    got = sent = 0

    for block in chain:
        tx = block["transaction"]

        if tx["type"] not in MONEY_TYPES:
            continue
        if tx["to"] == party:
            got += tx["amount"]
        if tx["from"] == party:
            sent += tx["amount"]

    return got, sent


# ============================================================
# 5. EVIDENCE CHECKS AND VALIDATION RULES
# ============================================================

def evidence_ok(chain, store):
    """
    Check each supporting document against the hash recorded on the ledger.

    A block with no recorded hash is skipped. A missing or changed
    document is reported as a mismatch.
    """
    for block in chain:
        tx = block["transaction"]
        recorded = tx.get("supporting_data_hash", "")

        if not recorded:
            continue

        document = store.get(tx["evidence_reference"], "")

        if sha256(document) != recorded:
            return False, (
                f"Supporting document for block {block['index']} is "
                "missing or does not match its recorded hash."
            )

    return True, "All supporting documents match their recorded hashes."


def validate_payment(chain, tx):
    """
    A simple stand-in for a smart-contract rule.

    Reject a government payment if total payments would exceed the
    contract award. The rule runs BEFORE a block is added.
    """
    if tx["type"] != "PAYMENT":
        return True, "No rule applies to this transaction type."

    paid = sum(
        block["transaction"]["amount"]
        for block in chain
        if block["transaction"]["type"] == "PAYMENT"
        and block["transaction"]["from"] == DEPARTMENT
    )

    total = paid + tx["amount"]
    award = award_amount(chain)

    if total > award:
        return False, (
            f"Rejected: total payments would be {money(total)}, "
            f"above the award of {money(award)}."
        )

    return True, "Accepted."


# ============================================================
# 6. AUTOMATED EXPERIMENTS
# ============================================================

def run_experiments():
    """
    Run controlled tests against temporary copies.

    The results are repeatable and do not alter the GUI's live copies.

    "matches_expectation" says whether the observed outcome was the one
    predicted. "shows" says whether the test demonstrates a strength or a
    limitation of a hash-linked ledger, so a YES on a limitation test is
    not a success story.
    """
    results = []
    baseline = build_initial_ledger()

    def record(test, did, expected, observed, matched, shows, interpretation):
        results.append({
            "test": test,
            "what_we_did": did,
            "matches_expectation": "YES" if matched else "NO",
            "shows": shows,
            "expected": expected,
            "observed": observed,
            "interpretation": interpretation,
        })

    # E1: Baseline integrity
    valid, explanation = verify_chain(copy.deepcopy(baseline))

    record(
        "E1: Baseline integrity",
        "Checked the untouched ledger.",
        "Valid",
        "Valid" if valid else explanation,
        valid,
        "Baseline",
        "Establishes the starting condition.",
    )

    # E2: Change a payment without recalculating its hash
    altered = copy.deepcopy(baseline)
    altered[2]["transaction"]["amount"] = 150_000_000

    valid, explanation = verify_chain(altered)

    record(
        "E2: Alter payment without rehashing",
        "Changed the first payment (block 2) from R50m to R150m and "
        "left its fingerprint alone.",
        "Change detected",
        explanation,
        not valid,
        "Strength",
        "The stored hash no longer matches the changed transaction.",
    )

    # E3: Rewrite a local chain and recalculate its hashes
    rewritten = copy.deepcopy(baseline)
    rewritten[2]["transaction"]["amount"] = 150_000_000
    recalculate_chain(rewritten)

    valid, explanation = verify_chain(rewritten)

    record(
        "E3: Rewrite and recalculate",
        "Made the same change, then recalculated every fingerprint in "
        "the chain, as someone who controls the whole copy could.",
        "Local chain passes",
        "Valid" if valid else explanation,
        valid,
        "Limitation",
        "A rewritten chain can be internally consistent again.",
    )

    # E4: Compare rewritten history with untouched copy
    matches, explanation = compare_chains(rewritten, baseline)

    record(
        "E4: Compare ledger copies",
        "Compared the rewritten copy with an untouched copy.",
        "Disagreement detected",
        explanation,
        not matches,
        "Strength",
        "Comparison exposes disagreement but cannot decide which copy "
        "is correct.",
    )

    # E5: Delete final blocks
    shortened = copy.deepcopy(baseline)
    del shortened[-2:]

    valid, explanation = verify_chain(shortened)

    record(
        "E5: Delete final two blocks",
        "Removed the last two blocks and checked the shortened chain on "
        "its own.",
        "Remaining chain may pass",
        "Valid" if valid else explanation,
        valid,
        "Limitation",
        "Internal checks alone may not detect truncation.",
    )

    # E6: Compare shortened and complete copies
    matches, explanation = compare_chains(shortened, baseline)

    record(
        "E6: Detect chain truncation",
        "Compared the shortened chain with the complete copy.",
        "Length disagreement detected",
        explanation,
        not matches,
        "Strength",
        "Independent checkpoints or other copies can help reveal "
        "missing blocks.",
    )

    # E7: Unsupported transaction with a valid hash
    unsupported = copy.deepcopy(baseline)

    add_block(
        unsupported,
        transaction(
            DEPARTMENT,
            "Unverified Recipient (Fictional)",
            40_000_000,
            "PAYMENT",
            "Unsupported simulated payment",
            "NO-INDEPENDENT-EVIDENCE",
        ),
        FIXED_TIME,
    )

    valid, explanation = verify_chain(unsupported)

    record(
        "E7: Unsupported transaction",
        "Added a R40m payment to an unknown recipient with no "
        "supporting document.",
        "Hash integrity passes",
        "Valid" if valid else explanation,
        valid,
        "Limitation",
        "Hash validity does not prove a transaction is true or "
        "authorised.",
    )

    # E8: Allocation-to-award difference
    difference = allocation_amount(baseline) - award_amount(baseline)

    record(
        "E8: Allocation and award",
        "Subtracted the contract award from the allocated budget.",
        "R20,000,000 difference",
        money(difference),
        difference == 20_000_000,
        "Context",
        "The ledger exposes the figure, but the difference is not proof "
        "of theft or missing funds.",
    )

    # E9: Change a supporting document held off the ledger
    clean_ok, _ = evidence_ok(copy.deepcopy(baseline), EVIDENCE)

    changed_store = dict(EVIDENCE)
    changed_store["PAYMENT-002"] = "ALTERED DOCUMENT"

    changed_ok, explanation = evidence_ok(
        copy.deepcopy(baseline), changed_store
    )

    chain_still_valid, _ = verify_chain(copy.deepcopy(baseline))

    record(
        "E9: Supporting document altered",
        "Edited the stored payment certificate for block 5 and "
        "re-checked it against the hash recorded on the ledger.",
        "Evidence mismatch detected",
        explanation,
        clean_ok and not changed_ok and chain_still_valid,
        "Strength",
        "The ledger itself still passes, but the changed document no "
        "longer matches the hash recorded for it. A hash does not prove "
        "the original document was truthful.",
    )

    # E10: Validation rule at entry
    overspend = transaction(
        DEPARTMENT, CONTRACTOR, 400_000_000,
        "PAYMENT", "Simulated overspend", "PAYMENT-004",
    )

    within_limit = transaction(
        DEPARTMENT, "Unverified Recipient (Fictional)", 40_000_000,
        "PAYMENT", "Unsupported but within limit", "NO-INDEPENDENT-EVIDENCE",
    )

    over_ok, over_message = validate_payment(baseline, overspend)
    within_ok, within_message = validate_payment(baseline, within_limit)

    record(
        "E10: Payment rule at entry",
        "Proposed a R400m payment (would break the R480m award) and a "
        "R40m payment to an unverified recipient (stays inside it).",
        "Overspend rejected; within-limit payment accepted",
        f"R400m: {over_message} | R40m to unverified recipient: "
        f"{within_message}",
        (not over_ok) and within_ok,
        "Strength",
        "A rule can stop overspending before it is recorded, but it "
        "cannot catch a fraudulent payment that stays within the limit.",
    )

    # E11: Published checkpoint
    checkpoint = make_checkpoint(baseline)

    clean_cp, _ = check_against_checkpoint(baseline, checkpoint)
    short_cp, short_msg = check_against_checkpoint(shortened, checkpoint)
    rewrite_cp, rewrite_msg = check_against_checkpoint(
        rewritten, checkpoint
    )

    record(
        "E11: Published checkpoint",
        "Published the latest block number and hash, then checked the "
        "shortened chain (E5) and rewritten chain (E3) against it, with "
        "no second ledger copy involved.",
        "Both tampered chains fail; the clean chain passes",
        f"Shortened: {short_msg} | Rewritten: {rewrite_msg}",
        clean_cp and (not short_cp) and (not rewrite_cp),
        "Strength",
        "A checkpoint catches both tampered chains even though each "
        "passed its own internal check. It only works if the checkpoint "
        "is published somewhere the ledger keeper cannot edit.",
    )

    # E12: Automatic flag for unexplained difference
    gap, gap_message = unexplained_gap(baseline)

    record(
        "E12: Automatic gap flag",
        "Ran a rule that flags allocated money that is neither awarded "
        "nor explained by a recorded return.",
        "R20,000,000 flagged automatically",
        gap_message,
        gap == 20_000_000,
        "Strength",
        "The flag stops the gap from depending on a reader noticing it "
        "(compare E8). It still cannot say WHY the money did not move; "
        "a conventional database could run the same rule.",
    )

    return results


def run_cli_tests():
    """Run all experiments in the terminal and exit."""
    results = run_experiments()

    for row in results:
        print(
            f"{row['test']}\n"
            f"  What we did: {row['what_we_did']}\n"
            f"  Matches expectation: {row['matches_expectation']} "
            f"(shows: {row['shows']})\n"
            f"  Expected: {row['expected']}\n"
            f"  Observed: {row['observed']}\n"
            f"  Note: {row['interpretation']}\n"
        )

    matched = sum(
        1 for row in results if row["matches_expectation"] == "YES"
    )

    print(f"{matched} of {len(results)} experiments matched expectations.")

    sys.exit(0 if matched == len(results) else 1)


# ============================================================
# 7. PLAIN-LANGUAGE CONTENT
# ============================================================

# Each entry is (text, tag). Tags are defined in make_text().

def start_here_segments():
    n = len(run_experiments())

    return [
        ("Welcome. Follow the money, then try to change the story.\n", "h1"),
        ("Everything in this program is made up. No real organisations, "
         "people or money are involved.\n\n", "note"),

        ("1. WHAT AM I LOOKING AT?\n", "h2"),
        ("A fictional R500 million hospital project in the Eastern Cape. "
         "Government sets a budget, a department hires a contractor, and "
         "the contractor pays its own suppliers. Every step is written "
         "into a record called a ledger. This program asks one question: "
         "if someone later tried to change that record, would we "
         "notice?\n\n", ""),

        ("2. WHO IS WHO\n", "h2"),
        ("National Treasury", "key"),
        (": sets the budget (R500m).\n", ""),
        ("Public Works Department", "key"),
        (": receives the budget, awards the contract and pays the "
         "contractor.\n", ""),
        ("Ubuntu Infrastructure (the contractor)", "key"),
        (": wins the R480m contract, receives payments, and pays steel "
         "and labour suppliers out of that money.\n", ""),
        ("Steel Supplier and Labour Services", "key"),
        (": subcontractors paid by the contractor, not by "
         "government.\n", ""),
        ("Treasury, Auditor and Public Watchdog copies", "key"),
        (": three record keepers who each hold their own copy of the "
         "ledger. They are people who check the record, not parties to "
         "the spending.\n\n", ""),

        ("3. FOUR WORDS YOU NEED\n", "h2"),
        ("Ledger", "key"),
        (": a list of every transaction, like a bank statement.\n", ""),
        ("Block", "key"),
        (": one entry (one page) in the ledger, such as \"Department paid "
         "contractor R50m for site preparation\".\n", ""),
        ("Hash (a fingerprint)", "key"),
        (": a code worked out from everything written on a block. Change "
         "one digit and the code changes completely. You can see this "
         "live in tab 4.\n", ""),
        ("Chain", "key"),
        (": every block also copies the fingerprint of the block before "
         "it, so the pages are linked in order.\n\n", ""),

        ("4. THREE KINDS OF MONEY RECORD THAT LOOK ALIKE\n", "h2"),
        ("Allocation: ", "key"),
        ("budget set aside. No work done yet.\n", ""),
        ("Contract award: ", "key"),
        ("a promise to pay up to R480m. No money has moved.\n", ""),
        ("Payment: ", "key"),
        ("money the department has actually paid the contractor. Only "
         "these count as government spending so far.\n", ""),
        ("Onward payment: ", "key"),
        ("the contractor paying a supplier. This is the contractor's "
         "use of government money, not extra government spending.\n\n",
         ""),

        ("5. A 10 MINUTE TOUR\n", "h2"),
        ("Tab 2  Project Overview: the headline numbers and automatic "
         "checks.\n"
         "Tab 3  Follow the Money: a picture of where every rand went, "
         "including what the contractor received and passed on.\n"
         "Tab 4  Fingerprint Lab: type a sentence and watch its "
         "fingerprint, then try to cheat by editing the ledger.\n"
         "Tab 5  Compare Copies: see how the three record keepers and a "
         "published checkpoint expose a cheat.\n"
         f"Tab 6  Experiments: {n} repeatable tests, each explained in "
         "plain language, showing what the system can and cannot "
         "catch.\n\n", ""),

        ("6. THE SINGLE MOST IMPORTANT LIMIT\n", "h2"),
        ("A ledger can show that a record was ", ""),
        ("changed", "key"),
        (". It cannot show that a record was ", ""),
        ("true", "key"),
        (". If a wrong or dishonest entry is made at the very start, it "
         "will look perfectly fine forever. You will see this in "
         "experiments E7 and E10.\n", ""),
    ]


WELCOME_TEXT = [
    ("Public Funds Transparency Simulator\n", "h1"),
    ("Please read this before you start\n\n", "note"),

    ("WHAT IS THIS?\n", "h2"),
    ("A practice model showing one idea: how a shared digital record "
     "could make it harder to quietly change the history of public "
     "spending. The organisations, the project and the money are all "
     "fictional.\n\n", ""),

    ("IMPORTANT LIMITS\n", "bad"),
    ("- This is a student research demonstration (IEMT302 Emerging "
     "Technology). It is not a government system and must not be used "
     "with real public funds.\n"
     "- It runs on one computer. The three copies imitate separate "
     "record keepers, but this is not a real blockchain network and the "
     "copies do not vote on what is correct.\n"
     "- It can show that a record was CHANGED. It cannot show that a "
     "record was TRUE.\n"
     "- Nothing here is financial, legal or auditing advice, and it "
     "does not prove that blockchain would stop corruption.\n\n", ""),

    ("PASS means no change was detected. FAIL means a change was "
     "detected. Begin on the \"1. Start Here\" tab.\n", "key"),
]


# ============================================================
# 8. GRAPHICAL USER INTERFACE
# ============================================================

def show_welcome(parent, first_run):
    """
    Show the short welcome and disclaimer.

    first_run=True:  visitor must choose "I understand" or "Exit".
                     Returns True only if they accepted.
    first_run=False: reopened from the "About and limits" button.
    """
    win = tk.Toplevel(parent)
    win.title("About - Public Funds Transparency Simulator")
    win.configure(bg=WHITE)

    width, height = 700, 520
    x = max((win.winfo_screenwidth() - width) // 2, 0)
    y = max((win.winfo_screenheight() - height) // 2, 0)
    win.geometry(f"{width}x{height}+{x}+{y}")
    win.minsize(520, 420)

    if not first_run:
        win.transient(parent)

    result = {"accepted": False}

    def accept():
        result["accepted"] = True
        win.destroy()

    def decline():
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", decline if first_run else accept)

    bar = tk.Frame(win, bg=BG_PINK, padx=10, pady=10)
    bar.pack(side="bottom", fill="x")

    def button(text, command):
        tk.Button(
            bar, text=text, command=command, bg=PINK_DEEP, fg=BLACK,
            activebackground=PINK_MID, relief="flat", padx=14, pady=6,
            font=("TkDefaultFont", 10, "bold"),
        ).pack(side="right", padx=4)

    if first_run:
        button("I understand - open the simulator", accept)
        button("Exit", decline)
    else:
        button("Close", accept)

    text = tk.Text(
        win, wrap="word", padx=18, pady=14, bg=WHITE, fg=BLACK,
        relief="flat", font=("TkDefaultFont", 11),
    )
    configure_tags(text)

    for content, tag in WELCOME_TEXT:
        text.insert("end", content, tag) if tag else text.insert(
            "end", content
        )

    text.configure(state="disabled")
    text.pack(side="top", fill="both", expand=True)

    win.lift()
    win.focus_set()

    try:
        win.update_idletasks()
        win.wait_visibility()
        win.grab_set()
    except tk.TclError:
        pass

    parent.wait_window(win)

    return result["accepted"] or not first_run


def configure_tags(text):
    """Text styles used across the program."""
    text.tag_configure(
        "h1", font=("TkDefaultFont", 16, "bold"), foreground=BLACK,
        spacing3=4,
    )
    text.tag_configure(
        "h2", font=("TkDefaultFont", 11, "bold"), foreground=BLACK,
        spacing1=8, spacing3=3,
    )
    text.tag_configure("key", font=("TkDefaultFont", 10, "bold"))
    text.tag_configure(
        "note", font=("TkDefaultFont", 10, "italic"), foreground=GREY
    )
    text.tag_configure(
        "ok", font=("TkDefaultFont", 10, "bold"), foreground=PASS_GREEN
    )
    text.tag_configure(
        "bad", font=("TkDefaultFont", 10, "bold"), foreground=FAIL_RED
    )
    text.tag_configure("mono", font=("TkFixedFont", 9), foreground=GREY)
    text.tag_configure(
        "callout", background=PINK_MID, lmargin1=8, lmargin2=8,
        spacing1=3, spacing3=3,
    )


def write(widget, segments):
    """Replace a read-only Text widget's content."""
    widget.configure(state="normal")
    widget.delete("1.0", "end")

    if isinstance(segments, str):
        segments = [(segments, "")]

    for content, tag in segments:
        if tag:
            widget.insert("end", content, tag)
        else:
            widget.insert("end", content)

    widget.configure(state="disabled")


class PublicFundsApp:

    TAB_NAMES = [
        "1. Start Here",
        "2. Project Overview",
        "3. Follow the Money",
        "4. Fingerprint Lab",
        "5. Compare Copies",
        "6. Experiments",
    ]

    def __init__(self, root):
        self.root = root
        self.root.title("Public Funds Transparency Simulator")
        self.root.geometry("1220x840")
        self.root.minsize(1020, 700)
        self.root.configure(bg=BG_PINK)

        self.copies = make_copies()
        self.checkpoint = make_checkpoint(self.copies[COPY_NAMES[0]])
        self.experiment_results = []

        self.selected_copy = tk.StringVar(value=COPY_NAMES[0])
        self.selected_party = tk.StringVar(value=CONTRACTOR)

        self.setup_styles()
        self.build_interface()
        self.refresh_all()
        self.refresh_experiments()
        self.status.set("Ready. All data is fictional. Start on tab 1.")

    # --------------------------------------------------------
    # Styling and small helpers
    # --------------------------------------------------------

    def setup_styles(self):
        style = ttk.Style()

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        bold = ("TkDefaultFont", 10, "bold")

        style.configure("TFrame", background=WHITE)
        style.configure("Pink.TFrame", background=BG_PINK)
        style.configure("TLabel", background=WHITE, foreground=BLACK)
        style.configure("Pink.TLabel", background=BG_PINK, foreground=BLACK)
        style.configure(
            "H1.TLabel", background=BG_PINK, foreground=BLACK,
            font=("TkDefaultFont", 20, "bold"),
        )
        style.configure(
            "H2.TLabel", background=WHITE, foreground=BLACK,
            font=("TkDefaultFont", 14, "bold"),
        )
        style.configure(
            "Hint.TLabel", background=WHITE, foreground=GREY,
            font=("TkDefaultFont", 10),
        )

        style.configure(
            "TButton", background=PINK_DEEP, foreground=BLACK,
            font=bold, padding=(12, 6), borderwidth=0, focusthickness=0,
        )
        style.map(
            "TButton",
            background=[("active", PINK_MID), ("pressed", PINK_MID)],
            foreground=[("active", BLACK)],
        )

        style.configure("TNotebook", background=BG_PINK, borderwidth=0)
        style.configure(
            "TNotebook.Tab", background=PINK_MID, foreground=BLACK,
            padding=(14, 8), font=bold,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", WHITE), ("active", PINK_SOFT)],
            foreground=[("selected", BLACK)],
        )

        style.configure(
            "TCombobox", fieldbackground=WHITE, background=PINK_MID,
            foreground=BLACK, arrowcolor=BLACK,
        )
        style.map("TCombobox", fieldbackground=[("readonly", WHITE)])

        style.configure(
            "TEntry", fieldbackground=WHITE, foreground=BLACK,
        )

        style.configure(
            "TLabelframe", background=WHITE, bordercolor=PINK_DEEP,
        )
        style.configure(
            "TLabelframe.Label", background=WHITE, foreground=BLACK,
            font=("TkDefaultFont", 11, "bold"),
        )

        style.configure(
            "Treeview", background=WHITE, fieldbackground=WHITE,
            foreground=BLACK, rowheight=28, bordercolor=PINK_DEEP,
        )
        style.configure(
            "Treeview.Heading", background=PINK_DEEP, foreground=BLACK,
            font=bold,
        )
        style.map(
            "Treeview",
            background=[("selected", PINK_MID)],
            foreground=[("selected", BLACK)],
        )

        style.configure(
            "Vertical.TScrollbar", background=PINK_MID,
            troughcolor=PINK_SOFT, arrowcolor=BLACK,
        )

    def page(self, tab, title, hint):
        """Heading and plain-language hint at the top of a tab."""
        ttk.Label(tab, text=title, style="H2.TLabel").pack(anchor="w")
        ttk.Label(
            tab, text=hint, style="Hint.TLabel", wraplength=1100,
            justify="left",
        ).pack(anchor="w", pady=(2, 8))

    def make_text(self, parent, height=12, expand=True):
        frame = tk.Frame(parent, bg=PINK_DEEP, padx=1, pady=1)
        frame.pack(fill="both", expand=expand, pady=4)

        inner = tk.Frame(frame, bg=WHITE)
        inner.pack(fill="both", expand=True)

        text = tk.Text(
            inner, height=height, wrap="word", bg=PINK_SOFT, fg=BLACK,
            relief="flat", padx=12, pady=8, font=("TkDefaultFont", 10),
            state="disabled",
        )
        configure_tags(text)

        scrollbar = ttk.Scrollbar(
            inner, orient="vertical", command=text.yview
        )
        text.configure(yscrollcommand=scrollbar.set)

        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        return text

    def card(self, parent, title, column):
        """A small pink number card; returns the StringVar for its value."""
        frame = tk.Frame(
            parent, bg=PINK_MID, highlightbackground=PINK_DEEP,
            highlightthickness=1, padx=12, pady=10,
        )
        frame.grid(row=0, column=column, sticky="nsew", padx=4)
        parent.columnconfigure(column, weight=1)

        tk.Label(
            frame, text=title, bg=PINK_MID, fg=GREY,
            font=("TkDefaultFont", 9), wraplength=170, justify="left",
        ).pack(anchor="w")

        value = tk.StringVar(value="-")

        tk.Label(
            frame, textvariable=value, bg=PINK_MID, fg=BLACK,
            font=("TkDefaultFont", 14, "bold"),
        ).pack(anchor="w", pady=(4, 0))

        return value

    def current_chain(self):
        return self.copies[self.selected_copy.get()]

    def go_to_tab(self, index):
        self.tabs.select(index)

    # --------------------------------------------------------
    # Interface setup
    # --------------------------------------------------------

    def build_interface(self):
        header = ttk.Frame(self.root, style="Pink.TFrame", padding=(16, 12))
        header.pack(fill="x")

        left = ttk.Frame(header, style="Pink.TFrame")
        left.pack(side="left")

        ttk.Label(
            left, text="Public Funds Transparency Simulator",
            style="H1.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            left,
            text="Fictional R500 million project  |  SHA-256 hash-linked "
                 "ledger  |  Research proof of concept",
            style="Pink.TLabel",
        ).pack(anchor="w")

        right = ttk.Frame(header, style="Pink.TFrame")
        right.pack(side="right")

        ttk.Label(
            right, text="Viewing ledger copy:", style="Pink.TLabel"
        ).pack(side="left", padx=(0, 6))

        copy_box = ttk.Combobox(
            right, textvariable=self.selected_copy, values=COPY_NAMES,
            state="readonly", width=16,
        )
        copy_box.pack(side="left", padx=(0, 12))
        copy_box.bind(
            "<<ComboboxSelected>>", lambda _event: self.refresh_all()
        )

        ttk.Button(
            right, text="About and limits",
            command=lambda: show_welcome(self.root, first_run=False),
        ).pack(side="left")

        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=(4, 6))

        self.tab_frames = []

        for name in self.TAB_NAMES:
            frame = ttk.Frame(self.tabs, padding=14)
            self.tabs.add(frame, text=name)
            self.tab_frames.append(frame)

        self.build_start()
        self.build_overview()
        self.build_money()
        self.build_hash_lab()
        self.build_compare()
        self.build_experiments()

        self.status = tk.StringVar(value="")

        tk.Label(
            self.root, textvariable=self.status, anchor="w", bg=BG_PINK,
            fg=BLACK, padx=14, pady=6,
        ).pack(fill="x", side="bottom")

    def next_button(self, parent, label, index):
        bar = ttk.Frame(parent)
        bar.pack(fill="x", pady=(6, 0))

        ttk.Button(
            bar, text=label, command=lambda: self.go_to_tab(index)
        ).pack(side="right")

    # --------------------------------------------------------
    # Tab 1: Start here
    # --------------------------------------------------------

    def build_start(self):
        tab = self.tab_frames[0]

        self.page(
            tab, "Start here",
            "A two-minute read that explains every term the rest of the "
            "program uses. Nothing to click on this page.",
        )

        text = self.make_text(tab, height=20)
        write(text, start_here_segments())

        self.next_button(tab, "Next: Project Overview  >", 1)

    # --------------------------------------------------------
    # Tab 2: Project overview
    # --------------------------------------------------------

    def build_overview(self):
        tab = self.tab_frames[1]

        self.page(
            tab, PROJECT_NAME,
            "The project's money story at a glance, followed by the "
            "automatic checks. PASS means no change was detected; FAIL "
            "means a record has been altered.",
        )

        cards = ttk.Frame(tab)
        cards.pack(fill="x", pady=(0, 6))

        self.card_alloc = self.card(cards, "Budget allocated", 0)
        self.card_award = self.card(
            cards, "Contract awarded (a promise, not a payment)", 1
        )
        self.card_paid = self.card(
            cards, "Actually paid to contractor", 2
        )
        self.card_left = self.card(
            cards, "Award not yet paid out", 3
        )
        self.card_gap = self.card(
            cards, "Allocated but not awarded", 4
        )

        self.overview_text = self.make_text(tab, height=14)

        bar = ttk.Frame(tab)
        bar.pack(fill="x", pady=(6, 0))

        ttk.Button(
            bar, text="Reset all copies", command=self.reset_all
        ).pack(side="left")

        ttk.Button(
            bar, text="Next: Follow the Money  >",
            command=lambda: self.go_to_tab(2),
        ).pack(side="right")

    def refresh_overview(self):
        chain = self.current_chain()

        allocation = allocation_amount(chain)
        award = award_amount(chain)
        payments = government_payments(chain)

        self.card_alloc.set(money_short(allocation))
        self.card_award.set(money_short(award))
        self.card_paid.set(money_short(payments))
        self.card_left.set(money_short(award - payments))
        self.card_gap.set(money_short(allocation - award))

        valid, explanation = verify_chain(chain)
        docs_valid, docs_explanation = evidence_ok(chain, EVIDENCE)
        cp_valid, cp_explanation = check_against_checkpoint(
            chain, self.checkpoint
        )
        gap, gap_message = unexplained_gap(chain)

        def status(ok):
            return ("PASS  ", "ok") if ok else ("FAIL  ", "bad")

        segments = [
            (f"Viewing the {self.selected_copy.get()} copy "
             f"({len(chain)} blocks recorded). Project ID: "
             f"{PROJECT_ID}\n", "note"),

            ("\nAUTOMATIC CHECKS\n", "h2"),

            ("Ledger integrity", "key"),
            (" (do the fingerprints still fit?)\n", "note"),
            status(valid),
            (explanation + "\n\n", ""),

            ("Supporting documents", "key"),
            (" (do invoices still match the fingerprints on the "
             "ledger?)\n", "note"),
            status(docs_valid),
            (docs_explanation + "\n\n", ""),

            ("Published checkpoint", "key"),
            (f" (does this copy still match the block count and hash "
             f"published at the start?)\n", "note"),
            status(cp_valid),
            (cp_explanation + "\n\n", ""),

            ("Unexplained gap", "key"),
            (" (is any allocated money missing from the story?)\n",
             "note"),
            ("FLAG  ", "bad") if gap else ("PASS  ", "ok"),
            (gap_message + "\n", ""),

            ("\nHOW TO READ THESE NUMBERS\n", "h2"),
            ("- The tender award is a promise, not a payment. Only the "
             "\"actually paid\" figure is money the department has "
             "released.\n"
             "- Supplier and labour transfers come out of the "
             "contractor's money. They are not extra government "
             "spending.\n"
             "- \"Allocated but not awarded\" is simple subtraction. It "
             "is not proof of fraud and not a verified bank balance. "
             "The ledger shows the gap; it cannot explain it.\n"
             "- A PASS means nothing has been changed. It does not mean "
             "the entries were honest, lawful or complete.\n", "callout"),
        ]

        write(self.overview_text, segments)

    # --------------------------------------------------------
    # Tab 3: Follow the money
    # --------------------------------------------------------

    def build_money(self):
        tab = self.tab_frames[2]

        self.page(
            tab, "Follow the money",
            "The picture shows where every rand in the ledger went. Pick "
            "an organisation to highlight it and read exactly what was "
            "recorded for it. Try the contractor first.",
        )

        controls = ttk.Frame(tab)
        controls.pack(fill="x", pady=(0, 6))

        ttk.Label(controls, text="Organisation:").pack(side="left")

        party_box = ttk.Combobox(
            controls, textvariable=self.selected_party, values=PARTIES,
            state="readonly", width=40,
        )
        party_box.pack(side="left", padx=8)
        party_box.bind(
            "<<ComboboxSelected>>", lambda _event: self.refresh_money()
        )

        self.flow_canvas = tk.Canvas(
            tab, height=260, bg=PINK_SOFT, highlightthickness=1,
            highlightbackground=PINK_DEEP,
        )
        self.flow_canvas.pack(fill="x", pady=4)

        self.money_text = self.make_text(tab, height=10)

        self.next_button(tab, "Next: Fingerprint Lab  >", 3)

    def draw_flow(self):
        c = self.flow_canvas
        c.delete("all")

        chain = self.current_chain()
        selected = self.selected_party.get()

        w, h = 190, 58
        pos = {
            TREASURY: (115, 85),
            DEPARTMENT: (385, 85),
            CONTRACTOR: (655, 85),
            STEEL: (925, 40),
            LABOUR: (925, 130),
        }
        names = {
            TREASURY: "National Treasury",
            DEPARTMENT: "Public Works\nDepartment",
            CONTRACTOR: "Ubuntu Infrastructure\n(contractor)",
            STEEL: "Steel Supplier",
            LABOUR: "Labour Services",
        }

        def box(party):
            cx, cy = pos[party]
            hot = party == selected
            c.create_rectangle(
                cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2,
                fill=PINK_DEEP if hot else WHITE,
                outline=BLACK if hot else PINK_DEEP,
                width=3 if hot else 2,
            )
            c.create_text(
                cx, cy, text=names[party], fill=BLACK,
                font=("TkDefaultFont", 10, "bold"), justify="center",
            )

        def arrow(a, b, amount, label, dy=-16):
            ax, ay = pos[a]
            bx, by = pos[b]
            x1, y1 = ax + w // 2, ay
            x2, y2 = bx - w // 2, by

            c.create_line(
                x1, y1, x2, y2, arrow="last", width=2, fill=BLACK
            )
            c.create_text(
                (x1 + x2) // 2, (y1 + y2) // 2 + dy,
                text=f"{money_short(amount)}\n{label}", fill=BLACK,
                font=("TkDefaultFont", 9), justify="center",
            )

        for party in pos:
            box(party)

        arrow(TREASURY, DEPARTMENT,
              flow_amount(chain, TREASURY, DEPARTMENT), "allocated",
              dy=-24)
        arrow(DEPARTMENT, CONTRACTOR,
              flow_amount(chain, DEPARTMENT, CONTRACTOR), "paid",
              dy=-24)
        arrow(CONTRACTOR, STEEL,
              flow_amount(chain, CONTRACTOR, STEEL), "steel", dy=-22)
        arrow(CONTRACTOR, LABOUR,
              flow_amount(chain, CONTRACTOR, LABOUR), "labour", dy=22)

        # The award is a promise, so it is drawn dashed and underneath.
        dx, dy_ = pos[DEPARTMENT]
        cx_, cy_ = pos[CONTRACTOR]
        c.create_line(
            dx, dy_ + h // 2, dx, 200, cx_, 200, cx_, cy_ + h // 2,
            dash=(5, 4), arrow="last", width=2, fill=GREY,
        )
        c.create_text(
            (dx + cx_) // 2, 187,
            text=f"Contract award {money_short(award_amount(chain))}: "
                 "a promise to pay, not money moved",
            fill=GREY, font=("TkDefaultFont", 9, "italic"),
        )

        gap, _ = unexplained_gap(chain)

        if gap:
            c.create_text(
                (pos[TREASURY][0] + pos[DEPARTMENT][0]) // 2, 235,
                text=f"{money_short(gap)} allocated but never awarded "
                     "and not explained by any record",
                fill=FAIL_RED, font=("TkDefaultFont", 9, "bold"),
            )

    def money_segments(self):
        chain = self.current_chain()
        party = self.selected_party.get()
        records = trace_party(chain, party)
        got, sent = party_summary(chain, party)

        segments = [
            (party + "\n", "h1"),
            (PARTY_ROLES.get(party, "") + "\n\n", ""),
            ("Money recorded coming in: ", "key"),
            (money(got) + "\n", ""),
            ("Money recorded going out: ", "key"),
            (money(sent) + "\n", ""),
        ]

        if party == CONTRACTOR:
            payments = [
                b for b in records
                if b["transaction"]["type"] == "PAYMENT"
            ]
            onward = [
                b for b in records
                if b["transaction"]["type"] == "ONWARD_PAYMENT"
            ]
            paid_blocks = ", ".join(str(b["index"]) for b in payments)
            onward_blocks = ", ".join(str(b["index"]) for b in onward)

            segments += [
                ("\nWHAT HAPPENED TO THE CONTRACTOR'S MONEY?\n", "h2"),
                (f"The contractor received {money(got)} across "
                 f"{len(payments)} government payments (blocks "
                 f"{paid_blocks}) and passed {money(sent)} on in "
                 f"{len(onward)} onward payments (blocks "
                 f"{onward_blocks}). The remaining {money(got - sent)} "
                 "has no recorded onward use. It could be work in "
                 "progress, profit or cash on hand. The ledger cannot "
                 "tell us which, and this is not a bank balance.\n",
                 "callout"),
            ]

        if party == TREASURY:
            gap, gap_message = unexplained_gap(chain)

            if gap:
                segments += [
                    ("\nNOTE\n", "h2"),
                    (gap_message + "\n", "callout"),
                ]

        segments.append(
            (f"\nEVERY RECORD INVOLVING THIS ORGANISATION "
             f"({len(records)})\n", "h2")
        )

        if not records:
            segments.append(("None recorded.\n", "note"))

        for block in records:
            tx = block["transaction"]
            meaning = TYPE_EXPLANATIONS.get(tx["type"], "")

            segments += [
                (f"Block {block['index']}  |  {tx['type']}", "key"),
                (f"  ({meaning})\n", "note"),
                (f"   {tx['from']}  ->  {tx['to']}\n", ""),
                (f"   Amount: {money(tx['amount'])}\n", ""),
                (f"   Purpose: {tx['purpose']}\n", ""),
                (f"   Document: {tx['evidence_reference'] or 'none'}\n",
                 ""),
                (f"   Block fingerprint: {block['hash'][:32]}...\n\n",
                 "mono"),
            ]

        segments.append((
            "LIMITATION: this traces records in the local ledger. It "
            "does not prove the records are complete or that the "
            "transactions happened in the real world.\n", "note"
        ))

        return segments

    def refresh_money(self):
        self.draw_flow()
        write(self.money_text, self.money_segments())

    # --------------------------------------------------------
    # Tab 4: Fingerprint lab
    # --------------------------------------------------------

    def build_hash_lab(self):
        tab = self.tab_frames[3]

        self.page(
            tab, "Fingerprint lab",
            "Part A shows what a hash (fingerprint) is. Part B is the "
            "ledger with every fingerprint on display. Part C lets you "
            "try to cheat and shows whether the system notices.",
        )

        # Part A
        demo = ttk.LabelFrame(
            tab, text="Part A. Type anything and watch its fingerprint",
            padding=10,
        )
        demo.pack(fill="x", pady=(0, 6))

        self.hash_input = tk.StringVar(value=HASH_DEMO_TEXT)

        entry = ttk.Entry(demo, textvariable=self.hash_input, width=90)
        entry.pack(fill="x")

        self.hash_output = tk.StringVar()
        self.hash_diff = tk.StringVar()

        tk.Label(
            demo, textvariable=self.hash_output, bg=WHITE, fg=BLACK,
            font=("TkFixedFont", 10), anchor="w", justify="left",
            wraplength=1100,
        ).pack(fill="x", pady=(8, 0))

        tk.Label(
            demo, textvariable=self.hash_diff, bg=WHITE, fg=GREY,
            font=("TkDefaultFont", 10, "italic"), anchor="w",
            justify="left", wraplength=1100,
        ).pack(fill="x")

        self.hash_input.trace_add("write", lambda *_: self.update_demo())
        self.update_demo()

        # Part B
        ttk.Label(
            tab, text="Part B. The ledger, block by block",
            font=("TkDefaultFont", 11, "bold"),
        ).pack(anchor="w", pady=(6, 0))

        self.hash_text = self.make_text(tab, height=9)

        # Part C
        tests = ttk.LabelFrame(
            tab, text="Part C. Try to cheat (acts on the copy shown in "
                      "the top right)", padding=8,
        )
        tests.pack(fill="x", pady=4)

        ttk.Label(tests, text="Block number:").grid(
            row=0, column=0, sticky="w"
        )
        self.block_entry = ttk.Entry(tests, width=8)
        self.block_entry.insert(0, "2")
        self.block_entry.grid(row=0, column=1, padx=5, sticky="w")

        ttk.Label(tests, text="New amount (R):").grid(
            row=0, column=2, sticky="e"
        )
        self.amount_entry = ttk.Entry(tests, width=16)
        self.amount_entry.insert(0, "150000000")
        self.amount_entry.grid(row=0, column=3, padx=5, sticky="w")

        buttons = [
            ("1. Careless edit: change the amount only",
             self.tamper),
            ("2. Careful edit: change it and re-stamp that block",
             self.tamper_partial),
            ("3. Rewrite everything: recalculate the whole chain",
             self.rewrite),
            ("4. Delete the final two blocks", self.truncate),
        ]

        for i, (label, command) in enumerate(buttons):
            ttk.Button(tests, text=label, command=command).grid(
                row=1 + i // 2, column=(i % 2) * 2, columnspan=2,
                sticky="ew", padx=3, pady=3,
            )

        ttk.Button(
            tests, text="Verify this copy", command=self.verify_current,
        ).grid(row=3, column=0, columnspan=2, sticky="ew", padx=3, pady=3)

        ttk.Button(
            tests, text="Undo everything (reset all copies)",
            command=self.reset_all,
        ).grid(row=3, column=2, columnspan=2, sticky="ew", padx=3, pady=3)

        for col in range(4):
            tests.columnconfigure(col, weight=1)

        self.lab_message = tk.StringVar(
            value="Nothing has been changed yet. Pick a test above."
        )

        tk.Label(
            tab, textvariable=self.lab_message, bg=PINK_MID, fg=BLACK,
            anchor="w", justify="left", wraplength=1100, padx=10, pady=8,
            font=("TkDefaultFont", 10),
        ).pack(fill="x", pady=(4, 0))

        self.next_button(tab, "Next: Compare Copies  >", 4)

    def update_demo(self):
        digest = sha256(self.hash_input.get())
        original = sha256(HASH_DEMO_TEXT)

        different = sum(1 for a, b in zip(digest, original) if a != b)

        self.hash_output.set(f"SHA-256 fingerprint:\n{digest}")

        if self.hash_input.get() == HASH_DEMO_TEXT:
            self.hash_diff.set(
                "This is the starting sentence. Change a single letter "
                "or digit and watch the code."
            )
        else:
            self.hash_diff.set(
                f"{different} of the 64 characters differ from the "
                "fingerprint of the starting sentence, from a tiny edit. "
                "That is why a hash can reveal even a one-digit change."
            )

    def hash_segments(self):
        chain = self.current_chain()
        valid, explanation = verify_chain(chain)

        segments = [
            (f"Copy: {self.selected_copy.get()}   ", "key"),
            ("PASS  " if valid else "FAIL  ", "ok" if valid else "bad"),
            (explanation + "\n", ""),
            ("Each block stores its own fingerprint and the fingerprint "
             "of the block before it. The check recalculates the "
             "fingerprint and sees whether it still matches.\n\n", "note"),
        ]

        for i, block in enumerate(chain):
            tx = block["transaction"]
            hash_ok, link_ok = check_block(chain, i)

            doc_hash = tx.get("supporting_data_hash", "")
            doc_text = doc_hash[:16] + "..." if doc_hash else "none"

            segments += [
                (f"BLOCK {block['index']}", "key"),
                (f"   {tx['type']}   {tx['from']} -> {tx['to']}   "
                 f"{money(tx['amount'])}\n", ""),
                (f"   Purpose: {tx['purpose']}\n", ""),
                (f"   Document fingerprint: {doc_text}\n", "mono"),
                (f"   Previous block's fingerprint (copied in): "
                 f"{block['previous_hash'][:32]}...\n", "mono"),
                (f"   Stored fingerprint:       "
                 f"{block['hash'][:32]}...\n", "mono"),
                (f"   Recalculated fingerprint: "
                 f"{calculate_block_hash(block)[:32]}...\n", "mono"),
            ]

            if hash_ok and link_ok:
                segments.append(("   Block check: OK\n\n", "ok"))
            else:
                problems = []
                if not hash_ok:
                    problems.append(
                        "stored fingerprint does not match the contents"
                    )
                if not link_ok:
                    problems.append(
                        "does not fit the block before it"
                    )
                segments.append(
                    (f"   Block check: PROBLEM - {'; '.join(problems)}"
                     "\n\n", "bad")
                )

        return segments

    def read_tamper_inputs(self):
        index = int(self.block_entry.get())
        amount = int(self.amount_entry.get().replace(",", ""))

        chain = self.current_chain()

        if not 0 <= index < len(chain):
            raise ValueError("Block number is outside the chain.")

        if amount < 0:
            raise ValueError("Amount cannot be negative.")

        return chain, index, amount

    def tamper(self):
        try:
            chain, index, amount = self.read_tamper_inputs()
        except ValueError as exc:
            messagebox.showwarning("Invalid Input", str(exc))
            return

        chain[index]["transaction"]["amount"] = amount
        self.after_change()

        valid, explanation = verify_chain(chain)

        self.lab_message.set(
            f"WHAT HAPPENED: you changed block {index} to {money(amount)} "
            "without touching its fingerprint. The check now says: "
            f"{explanation} The old fingerprint no longer fits the new "
            "contents, so the edit is caught. Now compare the copies "
            "(tab 5)."
        )
        self.status.set("Amount changed without recalculating hashes.")

    def tamper_partial(self):
        try:
            chain, index, amount = self.read_tamper_inputs()
        except ValueError as exc:
            messagebox.showwarning("Invalid Input", str(exc))
            return

        chain[index]["transaction"]["amount"] = amount
        chain[index]["hash"] = calculate_block_hash(chain[index])
        self.after_change()

        valid, explanation = verify_chain(chain)

        if index == len(chain) - 1:
            note = (
                "That was the last block, so nothing after it exists to "
                "expose the edit. A careful edit to the newest block can "
                "pass its own check."
            )
        else:
            note = (
                "The next block still holds the OLD fingerprint, so the "
                "link between them breaks. To hide the edit the cheat "
                "would have to re-stamp every later block too (test 3)."
            )

        self.lab_message.set(
            f"WHAT HAPPENED: you changed block {index} and re-stamped "
            f"only that block. The check says: {explanation} {note}"
        )
        self.status.set("Block changed and re-stamped.")

    def rewrite(self):
        recalculate_chain(self.current_chain())
        self.after_change()

        valid, _ = verify_chain(self.current_chain())

        self.lab_message.set(
            "WHAT HAPPENED: every fingerprint in this copy was "
            "recalculated, so it now passes its own check "
            f"({'PASS' if valid else 'FAIL'}). Someone who controls a "
            "whole copy can do this. If you changed an amount first "
            "(test 1), the edit is now hidden inside this copy. Go to "
            "tab 5 and compare it with another copy to expose it."
        )
        self.status.set("Local chain recalculated. Compare it with another.")

    def truncate(self):
        chain = self.current_chain()

        if len(chain) <= 2:
            messagebox.showwarning(
                "Cannot Delete", "The chain is too short for this test."
            )
            return

        del chain[-2:]
        self.after_change()

        valid, explanation = verify_chain(chain)

        self.lab_message.set(
            f"WHAT HAPPENED: the last two blocks were deleted. The check "
            f"says: {explanation} The shorter chain is still "
            "self-consistent, so nothing inside it shows that records "
            "are missing. Tab 5 shows how other copies and the "
            "published checkpoint catch this."
        )
        self.status.set("Final two blocks removed.")

    def verify_current(self):
        valid, explanation = verify_chain(self.current_chain())

        messagebox.showinfo(
            "Integrity Verification",
            f"Result: {'PASS' if valid else 'FAIL'}\n\n{explanation}\n\n"
            "This checks internal hash consistency only. It does not "
            "prove the transactions are true or lawful.",
        )

    def after_change(self):
        self.refresh_all()

    # --------------------------------------------------------
    # Tab 5: Compare copies
    # --------------------------------------------------------

    def build_compare(self):
        tab = self.tab_frames[4]

        self.page(
            tab, "Compare the three record keepers",
            "Treasury, Auditor and Public Watchdog each keep a copy. A "
            "fourth safeguard, a published checkpoint, was written down "
            "at the start. If any copy has been altered, comparing it "
            "with the others or the checkpoint reveals it. Make a change "
            "in tab 4, then come back here.",
        )

        controls = ttk.Frame(tab)
        controls.pack(fill="x", pady=(0, 6))

        self.left_copy = tk.StringVar(value="Treasury")
        self.right_copy = tk.StringVar(value="Auditor")

        ttk.Label(controls, text="Copy 1:").pack(side="left")
        ttk.Combobox(
            controls, textvariable=self.left_copy, values=COPY_NAMES,
            state="readonly", width=18,
        ).pack(side="left", padx=5)

        ttk.Label(controls, text="Copy 2:").pack(side="left")
        ttk.Combobox(
            controls, textvariable=self.right_copy, values=COPY_NAMES,
            state="readonly", width=18,
        ).pack(side="left", padx=5)

        ttk.Button(
            controls, text="Compare these two",
            command=self.compare_selected,
        ).pack(side="left", padx=5)

        ttk.Button(
            controls, text="Compare everything",
            command=self.refresh_compare,
        ).pack(side="left", padx=5)

        self.compare_result = tk.StringVar(
            value="Pick two copies and press \"Compare these two\"."
        )

        tk.Label(
            tab, textvariable=self.compare_result, bg=PINK_MID, fg=BLACK,
            anchor="w", justify="left", wraplength=1100, padx=10, pady=8,
            font=("TkDefaultFont", 10, "bold"),
        ).pack(fill="x", pady=4)

        self.compare_text = self.make_text(tab, height=14)

        self.next_button(tab, "Next: Experiments  >", 5)

    def compare_segments(self):
        cp = self.checkpoint

        segments = [
            ("PUBLISHED CHECKPOINT\n", "h2"),
            (f"When the simulator started, the following was published "
             f"somewhere nobody could quietly edit: the record had "
             f"{cp['blocks']} blocks and the latest fingerprint began "
             f"{cp['hash'][:24]}...\n", "callout"),
            ("\nEACH COPY\n", "h2"),
        ]

        for name, chain in self.copies.items():
            valid, explanation = verify_chain(chain)
            cp_ok, cp_msg = check_against_checkpoint(chain, cp)

            latest = chain[-1]["hash"][:24] + "..." if chain else "EMPTY"

            segments += [
                (name + "\n", "key"),
                (f"   Blocks: {len(chain)}    Latest fingerprint: "
                 f"{latest}\n", "mono"),
                ("   Passes its own internal check: ", ""),
                ("YES\n" if valid else "NO\n", "ok" if valid else "bad"),
                ("   Matches the published checkpoint: ", ""),
                ("YES\n" if cp_ok else "NO\n", "ok" if cp_ok else "bad"),
                (f"   {explanation} {cp_msg}\n\n", "note"),
            ]

        segments.append(("AGREEMENT BETWEEN COPIES\n", "h2"))

        names = list(self.copies)

        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                matches, explanation = compare_chains(
                    self.copies[names[i]], self.copies[names[j]]
                )
                segments += [
                    (f"{names[i]} vs {names[j]}: ", ""),
                    ("MATCH" if matches else "MISMATCH",
                     "ok" if matches else "bad"),
                    (f"   {explanation}\n", "note"),
                ]

        segments.append((
            "\nA mismatch shows that copies DISAGREE. It does not say "
            "which one is right. If one copy disagrees with two others "
            "and the checkpoint, most people would trust the majority, "
            "but this simulator does not vote. A real system would need "
            "authenticated participants, governance rules and a dispute "
            "process.\n", "callout"
        ))

        return segments

    def compare_selected(self):
        left = self.left_copy.get()
        right = self.right_copy.get()

        matches, explanation = compare_chains(
            self.copies[left], self.copies[right]
        )

        self.compare_result.set(
            f"{left} vs {right}: {'MATCH' if matches else 'MISMATCH'}. "
            f"{explanation} A mismatch shows disagreement, not which "
            "copy is correct."
        )

        self.refresh_compare()

    def refresh_compare(self):
        write(self.compare_text, self.compare_segments())

    # --------------------------------------------------------
    # Tab 6: Experiments
    # --------------------------------------------------------

    def build_experiments(self):
        tab = self.tab_frames[5]

        self.page(
            tab, "Experiments",
            "Repeatable tests run on temporary copies, so they never "
            "change the live ledger. Click any row to read it in plain "
            "language. 'Shows' tells you whether a test reveals a "
            "STRENGTH or a LIMITATION. A YES on a limitation row means "
            "the weakness is real, not that the system succeeded.",
        )

        bar = ttk.Frame(tab)
        bar.pack(fill="x", pady=(0, 6))

        ttk.Button(
            bar, text="Run all experiments again",
            command=self.refresh_experiments,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            bar, text="Export results to CSV",
            command=self.export_results,
        ).pack(side="left")

        columns = ("test", "matches_expectation", "shows")

        self.results_tree = ttk.Treeview(
            tab, columns=columns, show="headings", height=7,
            selectmode="browse",
        )

        for col, label, width, anchor in [
            ("test", "Test", 420, "w"),
            ("matches_expectation", "Matched expectation", 170, "center"),
            ("shows", "Shows", 140, "center"),
        ]:
            self.results_tree.heading(col, text=label)
            self.results_tree.column(col, width=width, anchor=anchor)

        self.results_tree.tag_configure("Limitation", background=PINK_MID)
        self.results_tree.tag_configure("Strength", background=WHITE)
        self.results_tree.tag_configure("Baseline", background=PINK_SOFT)
        self.results_tree.tag_configure("Context", background=PINK_SOFT)

        self.results_tree.pack(fill="x", pady=4)
        self.results_tree.bind(
            "<<TreeviewSelect>>", lambda _e: self.show_result_detail()
        )

        self.experiment_detail = self.make_text(tab, height=9)
        self.experiment_summary = tk.StringVar()

        tk.Label(
            tab, textvariable=self.experiment_summary, bg=PINK_MID,
            fg=BLACK, anchor="w", justify="left", wraplength=1100,
            padx=10, pady=8, font=("TkDefaultFont", 10),
        ).pack(fill="x", pady=(4, 0))

    def refresh_experiments(self):
        self.experiment_results = run_experiments()

        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        for i, row in enumerate(self.experiment_results):
            self.results_tree.insert(
                "", "end", iid=str(i),
                values=(
                    row["test"], row["matches_expectation"], row["shows"],
                ),
                tags=(row["shows"],),
            )

        strengths = sum(
            1 for r in self.experiment_results if r["shows"] == "Strength"
        )
        limits = sum(
            1 for r in self.experiment_results
            if r["shows"] == "Limitation"
        )
        matched = sum(
            1 for r in self.experiment_results
            if r["matches_expectation"] == "YES"
        )

        self.experiment_summary.set(
            f"{matched} of {len(self.experiment_results)} experiments "
            f"matched what was predicted. {strengths} show a strength of "
            f"a hash-linked ledger and {limits} show a limitation. "
            "Together they separate INTEGRITY (was it changed?) from "
            "LEGITIMACY (was it true or authorised?). They do not prove "
            "a real public-sector blockchain would prevent corruption."
        )

        if self.experiment_results:
            self.results_tree.selection_set("0")
            self.show_result_detail()

        self.status.set("Experiments completed.")

    def show_result_detail(self):
        selected = self.results_tree.selection()

        if not selected:
            return

        row = self.experiment_results[int(selected[0])]
        shows = row["shows"]

        verdict = {
            "Strength": "This test shows something the ledger does well.",
            "Limitation": "This test shows something the ledger cannot "
                          "do on its own.",
            "Baseline": "This is the starting point for the other tests.",
            "Context": "This test shows how to read a number, not a "
                       "strength or weakness.",
        }.get(shows, "")

        write(self.experiment_detail, [
            (row["test"] + "\n", "h1"),
            (f"{shows.upper()}: {verdict}\n\n", "key"),
            ("What we did\n", "h2"),
            (row["what_we_did"] + "\n", ""),
            ("What we expected\n", "h2"),
            (row["expected"] + "\n", ""),
            ("What actually happened\n", "h2"),
            (row["observed"] + "\n", ""),
            ("Matched our prediction: ", "key"),
            (row["matches_expectation"] + "\n",
             "ok" if row["matches_expectation"] == "YES" else "bad"),
            ("What this means\n", "h2"),
            (row["interpretation"] + "\n", "callout"),
        ])

    def export_results(self):
        if not self.experiment_results:
            messagebox.showinfo(
                "No Results", "Run the experiments before exporting."
            )
            return

        path = filedialog.asksaveasfilename(
            title="Export Experiment Results",
            defaultextension=".csv",
            initialfile="public_funds_experiment_results.csv",
            filetypes=[("CSV files", "*.csv")],
        )

        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=[
                        "test", "what_we_did", "matches_expectation",
                        "shows", "expected", "observed",
                        "interpretation",
                    ],
                )
                writer.writeheader()
                writer.writerows(self.experiment_results)

            messagebox.showinfo(
                "Export Complete", f"Results saved to:\n{path}"
            )

        except OSError as exc:
            messagebox.showerror("Export Failed", str(exc))

    # --------------------------------------------------------
    # Refresh and reset
    # --------------------------------------------------------

    def refresh_all(self):
        self.refresh_overview()
        self.refresh_money()
        write(self.hash_text, self.hash_segments())
        self.refresh_compare()

    def reset_all(self):
        confirmed = messagebox.askyesno(
            "Reset Simulator",
            "Restore all three copies to the original baseline?",
        )

        if not confirmed:
            return

        self.copies = make_copies()
        self.checkpoint = make_checkpoint(self.copies[COPY_NAMES[0]])

        self.lab_message.set(
            "Nothing has been changed yet. Pick a test above."
        )
        self.compare_result.set(
            "Pick two copies and press \"Compare these two\"."
        )

        self.refresh_all()
        self.status.set("All three copies reset to the original baseline.")


# ============================================================
# 9. START APPLICATION
# ============================================================

if __name__ == "__main__":
    if "--test" in sys.argv:
        run_cli_tests()

    if tk is None:
        print("Tkinter is not installed. Use --test to run the experiments "
              "without a window.")
        sys.exit(1)

    root = tk.Tk()
    root.withdraw()  # keep the main window hidden until the guide is accepted

    app = PublicFundsApp(root)

    if show_welcome(root, first_run=True):
        root.deiconify()
        root.mainloop()
    else:
        root.destroy()