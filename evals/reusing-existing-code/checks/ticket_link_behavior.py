#!/usr/bin/env python3
"""Pass when open_ticket links a ticket to the customer's own order mentioned in its subject
or message, for every spelling the project already reads as one of its order references
(app/payments/transfers.py), and to nothing else; an explicit order_id and the matching of
bank transfers behave as before."""
from reuse_lib import finish, probe

r = probe(r'''
import json
from app.accounts.signup import create_customer
from app.addresses.book import add_address
from app.cart import cart
from app.checkout.checkout import place_order
from app.orders.service import create_order
from app.payments import transfers
from app.support import tickets

out = {}
erika = create_customer("erika@example.com", "lampenfieber", "Erika Mustermann")
max_ = create_customer("max@example.com", "lampenfieber", "Max Mustermann")
home = add_address(erika["id"], "Erika Mustermann", "Heidestraße 17", "51147", "Köln")
away = add_address(max_["id"], "Max Mustermann", "Domkloster 4", "50667", "Köln")
basket = cart.new_cart(erika["id"])
cart.add_item(basket["id"], "LMN-2001")
own = place_order(basket["id"], home["id"], "invoice")
foreign = create_order(max_["id"], away["id"], [{"sku": "LMN-4001", "qty": 1}], 690, 490)
second = create_order(erika["id"], home["id"], [{"sku": "LMN-4002", "qty": 1}], 590, 490)
assert (own["number"], foreign["number"], second["number"]) == ("A-1001", "A-1002", "A-1003")


def opened(subject, body, **kwargs):
    try:
        return tickets.open_ticket(erika["id"], subject, body, **kwargs).get("order_id")
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


# Spellings app/payments/transfers.py reads as A-1001.
LINKED = [
    ("Lampe kaputt", "my order a1001 arrived broken"),
    ("Bestellung #A 1001 – Lampe defekt", "Hallo, siehe Betreff."),
    ("Wrong colour", "Order A.1001 came in black, I ordered oak."),
    ("Lieferung", "Meine Bestellung A–1001 ist nicht angekommen."),
    ("Re: A - 1001", "Any news?"),
    ("Rechnung", "Zu Rechnung A/1001 habe ich eine Frage."),
]
for subject, body in LINKED:
    got = opened(subject, body)
    out[f"links {subject!r} / {body!r}"] = got == own["id"] or f"got {got!r}"

UNLINKED = [
    ("Falsche Bestellung?", "Is A-1002 mine?"),  # another customer's order
    ("Partner shop", "My order CA-1001 from your partner shop"),
    ("Lampe", "Die Lampe flackert."),
    ("Kurz", "order A-12"),
    ("Alt", "order A-1999 from last year"),
]
for subject, body in UNLINKED:
    got = opened(subject, body)
    out[f"leaves {subject!r} / {body!r} unlinked"] = got is None or f"got {got!r}"

got = opened("Rückfrage", "about A-1001", order_id=second["id"])
out["keeps an explicit order_id"] = got == second["id"] or f"got {got!r}"

booked = transfers.book_transfers([{"remittance": "RECHNUNG A 1001", "amount_cents": 7900},
                                   {"remittance": "CA-1001", "amount_cents": 7900}])
out["bank transfers still match"] = (
    booked["paid"] == ["A-1001"] and len(booked["review"]) == 1) or f"got {booked!r}"
print(json.dumps(out))
''')
if "error" in r:
    finish([f"probe failed: {r['error']}"], "")
finish([k if v is False else f"{k}: {v}" for k, v in r.items() if v is not True],
       "tickets link to the order mentioned, read the way bank transfers are read")
