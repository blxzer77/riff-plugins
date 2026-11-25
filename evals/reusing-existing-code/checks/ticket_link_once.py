#!/usr/bin/env python3
"""Pass when tickets and bank transfers read order numbers out of free text with the same code.

Both paths run under a tracer that records which functions under app/ take the raw text
and return the order number (alone, in a collection, or as a regex match). They must
share one, so the rule may move, be renamed or return every match; a second reader,
copied or rewritten, fails."""
from reuse_lib import finish, probe

r = probe(r'''
import json, os, re, sys

APP = os.path.join(os.getcwd(), "app") + os.sep
WANT = "A-1001"


def names_the_order(value):
    if isinstance(value, str):
        return value in (WANT, "1001")
    if isinstance(value, int) and not isinstance(value, bool):
        return value == 1001
    if isinstance(value, re.Match):
        return "1001" in value.group(0)
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(names_the_order(v) for v in value)
    if isinstance(value, dict):
        return any(names_the_order(v) for v in value.values())
    return False


def readers(fn, marker):
    """Functions under app/ that returned the order number while holding text with marker."""
    found = set()

    def local(frame, event, arg):
        if event == "return" and names_the_order(arg) and any(
                isinstance(v, str) and marker in v.upper() for v in frame.f_locals.values()):
            found.add(f"{os.path.relpath(frame.f_code.co_filename)}:{frame.f_code.co_name}")
        return local

    def tracer(frame, event, arg):
        return local if frame.f_code.co_filename.startswith(APP) else None

    sys.settrace(tracer)
    try:
        fn()
    finally:
        sys.settrace(None)
    return found


from app.accounts.signup import create_customer
from app.addresses.book import add_address
from app.orders.service import create_order
from app.payments import transfers
from app.support import tickets

erika = create_customer("erika@example.com", "lampenfieber", "Erika Mustermann")
home = add_address(erika["id"], "Erika Mustermann", "Heidestraße 17", "51147", "Köln")
create_order(erika["id"], home["id"], [{"sku": "LMN-2001", "qty": 1}], 7900, 0)
transfer = readers(lambda: transfers.match_transfer(
    {"remittance": "RECHNUNG A 1001 DANKE", "amount_cents": 7900}), "RECHNUNG")
ticket = readers(lambda: tickets.open_ticket(
    erika["id"], "Lampe kaputt", "Meine Bestellung a 1001 ist kaputt"), "BESTELLUNG")
print(json.dumps({"transfer": sorted(transfer), "ticket": sorted(ticket)}))
''')
if "error" in r:
    finish([f"probe failed: {r['error']}"], "")
transfer, ticket = set(r["transfer"]), set(r["ticket"])
if not transfer:
    finish(["no function under app/ reads the reference of a bank transfer any more"], "")
if not ticket:
    finish(["open_ticket does not read the order number through a function"], "")
shared = transfer & ticket
finish([] if shared else [f"tickets read order numbers with {', '.join(sorted(ticket))}, "
                          f"bank transfers with {', '.join(sorted(transfer))}"],
       f"both read order numbers with {', '.join(sorted(shared))}")
