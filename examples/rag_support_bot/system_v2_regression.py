"""Support bot v2 — a 'helpful' rewrite that silently regressed: it now hallucinates
policy details and dropped the password-reset tool call. The gate must catch this."""


def respond_full(item: dict) -> dict:
    q = item["input"].lower()
    if "refund" in q:
        # regression: fabricated 30-day window
        return {"output": "You can get a refund any time within 30 days, no questions asked.", "tool_calls": []}
    if "storage" in q and "free" in q:
        # regression: 'unlimited' is not in the docs
        return {"output": "The Free plan includes unlimited storage.", "tool_calls": []}
    if "cost" in q and "pro" in q:
        # regression: wrong price
        return {"output": "The Pro plan costs $10 per month.", "tool_calls": []}
    if "seats" in q and "team" in q:
        # still correct
        return {"output": "The Team plan supports up to 10 seats.", "tool_calls": []}
    if "data" in q and "stored" in q:
        # regression: wrong region
        return {"output": "Your data is stored in our US region.", "tool_calls": []}
    if "password" in q:
        # regression: forgot the tool call, unhelpful answer
        return {"output": "Have you tried turning it off and on again?", "tool_calls": []}
    return {"output": "Not sure.", "tool_calls": []}
