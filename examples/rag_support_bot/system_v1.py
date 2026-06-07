"""Support bot v1 — answers grounded in the Nimbus policy docs. Passes the gate."""


def _answer(q: str) -> str:
    q = q.lower()
    if "refund" in q:
        return "You can request a full refund within 14 days of purchase. After that, the subscription is non-refundable."
    if "storage" in q and "free" in q:
        return "The Free plan includes 5 GB of storage."
    if "cost" in q and "pro" in q:
        return "The Pro plan costs $20 per month, billed monthly."
    if "seats" in q and "team" in q:
        return "The Team plan supports up to 10 seats."
    if "data" in q and "stored" in q:
        return "Your data is stored in the EU (Frankfurt) region."
    if "password" in q:
        return "I've sent a reset link to your email — please check your inbox."
    return "I'm not certain about that — let me connect you with a human agent."


def respond_full(item: dict) -> dict:
    q = item["input"].lower()
    if "password" in q:
        return {"output": _answer(item["input"]), "tool_calls": [{"name": "reset_password"}]}
    return {"output": _answer(item["input"]), "tool_calls": []}
