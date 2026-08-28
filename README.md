# Connect24 Python SDK

Official Python client for the [Connect24](https://connect24.co.za) communications API —
one interface for email, SMS and WhatsApp.

```bash
pip install connect24
```

No runtime dependencies. An SDK is a dependency of *your* application, and every package it drags
in is a version conflict that becomes yours to resolve.

## Quick start

Get your **account id** and an **API key** from the portal, under Settings → API keys.

```python
import os
from connect24 import Connect24

client = Connect24(
    account_id="acc_3f9c1a7b4e2d",
    api_key=os.environ["CONNECT24_API_KEY"],
)

client.messages.send_sms("+27821234567", "Your payment is due tomorrow.")
```

Or read both from the environment, which is what most deployments want:

```python
client = Connect24.from_env()   # CONNECT24_ACCOUNT_ID, CONNECT24_API_KEY
```

## What you can reach

| | |
|---|---|
| `client.messages` | Send email, SMS and WhatsApp; read status and history |
| `client.templates` | Stored bodies with placeholders, so copy lives on the platform |
| `client.suppressions` | Addresses that will not be sent to |
| `client.webhooks` | Delivery events pushed to you, plus signature verification |
| `client.sending_domains` | Prove you control a domain, so mail goes out as you |
| `client.billing` | Prepaid credit, pricing and the statement |
| `client.account` | Who you are, and which channels can send right now |

## Every channel, one shape

```python
# SMS
client.messages.send_sms("+27821234567", "Your delivery is on its way.")

# WhatsApp — free-form inside the 24-hour window, a template outside it
client.messages.send_whatsapp("+27821234567", "Your order has shipped.")
client.messages.send_whatsapp("+27821234567", template_name="payment_reminder")

# Email
client.messages.send_email(
    to="customer@example.com",
    subject="Payment reminder",
    html="<p>Your account is overdue.</p>",
    sender={"address": "collections@acme.co.za", "name": "Acme Collections"},
)
```

## Two things that surprise people

**Your `sender` address is not used until you verify the domain.** Until then mail leaves from your
account's assigned address on `connect24.co.za` and yours becomes the Reply-To. Verify with
`client.sending_domains.add("acme.co.za")`, publish the returned DNS records, then `verify`.

**There is no sender for SMS.** South African traffic routes from a shared originator pool, and
naming an identity you do not own is rejected by the network.

## Not sending twice

Pass an idempotency key when a network failure leaves you unsure whether a send arrived. A repeat
with the same key returns the original message instead of sending again:

```python
client.messages.send_sms(
    "+27821234567",
    "Your order has shipped.",
    idempotency_key=f"order-{order.id}-shipped",
)
```

Use something stable and tied to the event — an order id, not a UUID generated at call time, which
would differ on the retry and defeat the point.

## Watch the emoji

An SMS holds 160 characters using the GSM-7 alphabet. A single emoji, curly quote or em dash
switches the whole message to UCS-2, which holds 70 characters per part. A 150-character message
with one emoji costs **three** SMS, not one. The portal shows the segment count while you write.

## Verifying a webhook

Verify against the **raw body**, before any framework parses it.

```python
from connect24 import WebhookEvent, verify_signature

@app.post("/hooks/connect24")
def connect24_hook():
    payload = request.get_data(as_text=True)          # raw body, not request.json
    signature = request.headers.get("X-Connect24-Signature", "")

    if not verify_signature(payload, signature, WEBHOOK_SECRET):
        return "", 401

    event = WebhookEvent.parse(payload)
    # Acknowledge fast — anything that is not 2xx is retried.
    return "", 200
```

Delivery is at-least-once. Deduplicate on `event.id`.

## Errors

```python
from connect24 import Connect24ApiError, Connect24ConnectionError

try:
    client.messages.send_sms("+27821234567", "Hello")
except Connect24ApiError as e:
    if e.status_code == 402:
        ...          # out of credit; topping up is the only fix
    elif e.status_code == 401:
        ...          # key is wrong or revoked
    print(e.errors)  # field-level validation messages, when the API sent any
except Connect24ConnectionError:
    ...              # never reached the API — the send may or may not have happened
```

Rate limits, 5xx and connection failures are retried twice with backoff before either is raised.
A 4xx is never retried, because repeating it changes nothing.

## What the send path enforces

Messages sent through Connect24 are subject to South African law, applied where the message is
actually sent rather than left to you:

- **POPIA** — a lawful basis is recorded per contact, with where the details came from.
- **Consumer Protection Act** — no marketing on Sundays or public holidays, Saturdays 09:00–13:00
  only, weekdays 08:00–20:00. A marketing send outside the window waits rather than going out late.
- **WASPA Code** — a working opt-out on every marketing message. Once used, it applies across every
  list, permanently, and cannot be reversed by the sender.

Connect24 enforces these in the send path. You remain the responsible party under POPIA for the
data you upload and the consent you hold — see the [terms](https://connect24.co.za/terms).

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Links

- [API documentation](https://connect24.co.za/developer)
- [Support](mailto:support@connect24.co.za)
