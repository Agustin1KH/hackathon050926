"""SMS approval flow via Ara's linq_send_message connector.

Owner: P1 (platform).

The agent calls send_approval_sms when it needs human review.
The user replies Y / N from their phone — Ara routes incoming SMS back into
a follow-up agent invocation, which updates the relevant DB row.
"""

from __future__ import annotations

import os

import ara_sdk as ara

# linq_send_message is provided by Ara as a built-in connector when a phone
# route is paired. Reference: docs.ara.so/sdk/quickstart


@ara.tool
def send_approval_sms(prompt: str, item_id: str, item_kind: str) -> dict[str, str]:
    """Text the user a draft and ask for Y/N approval.

    item_kind ∈ {"scheduled", "reply"} — tells the response handler which
    table to update when the user replies.
    """
    phone = os.environ.get("USER_PHONE_NUMBER")
    if not phone:
        return {"error": "USER_PHONE_NUMBER not set; skipping SMS"}

    body = (
        f"{prompt}\n\n"
        f"Reply Y to approve, N to skip.\n"
        f"[ref: {item_kind}:{item_id}]"
    )
    # TODO(P1): once Ara docs confirm exact signature, swap to real connector call.
    # ara.connectors.linq.send_message(to=phone, body=body)
    return {"to": phone, "body": body}
