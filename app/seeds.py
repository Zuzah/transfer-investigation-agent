"""
Demo seed data for POST /admin/reset.

Each entry is a dict matching the CaseCreate schema:
  client_id  — display identifier shown in the analyst queue
  category   — one of the TriageCategory values
  complaint  — free-text complaint text used as the investigation input

Cases are ordered to cover the five main triage categories, with the
final entry (Client #7719) including all four specificity signals
(amount, date, institution, reference) to demonstrate a high-confidence
(~90%) investigation result.
"""

SEED_CASES: list[dict] = [
    {
        "client_id": "Client #4821",
        "category": "Institutional Delay",
        "complaint": (
            "Client transferred their RRSP from TD Bank 3 weeks ago. Status shows "
            "Transferring but nothing has arrived. Client says TD confirmed funds left "
            "their account 2 weeks ago."
        ),
    },
    {
        "client_id": "Client #3307",
        "category": "Wire Transfer Issue",
        "complaint": (
            "Client sent a wire transfer yesterday morning, received same-day confirmation "
            "email, funds still not showing in account after 24 hours."
        ),
    },
    {
        "client_id": "Client #5512",
        "category": "Missing Funds",
        "complaint": (
            "Client initiated a PAD deposit of $4,500 six business days ago. Bank confirms "
            "debit was taken but funds are not reflected in Wealthsimple balance."
        ),
    },
    {
        "client_id": "Client #2198",
        "category": "Account Restriction",
        "complaint": (
            "Client account was flagged and restricted after a large TFSA transfer. Client "
            "has not received any communication and cannot access their account."
        ),
    },
    {
        "client_id": "Client #6643",
        "category": "Transfer Rejected",
        "complaint": (
            "Client attempted to move TFSA from RBC. Transfer was rejected but client was "
            "not notified. Discovered only after checking status in app."
        ),
    },
    {
        # All 4 specificity signals present: amount + date + institution + reference.
        # Designed to demonstrate a high-confidence (~90%) investigation result.
        "client_id": "Client #7719",
        "category": "Institutional Delay",
        "complaint": (
            "Client initiated a full transfer of their non-registered investment account "
            "from RBC Direct Investing on 2025-01-14, for a total value of $12,450. "
            "Wealthsimple issued confirmation ref #WS-20250114-8831 the same day. "
            "As of today, 15 business days have elapsed and the assets have not appeared "
            "in the Wealthsimple account. RBC confirmed on 2025-01-28 that the transfer "
            "request was accepted and the account was debited. Client is requesting an "
            "urgent status update as the funds are inaccessible during the transfer period."
        ),
    },
]
