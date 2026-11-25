"""Text messages through the SMS gateway: login codes and shipping updates."""

import re

from app import config
from app.notifications.outbox import record

# Calling codes for numbers written in national form, by region.
CALLING_CODES = {"DE": "49", "AT": "43", "CH": "41"}
GSM_SEGMENT = 160

_TRUNK_ZERO = re.compile(r"\(0\)")
_SEPARATORS = re.compile(r"[\s\-./()]")
_MSISDN = re.compile(r"\+[1-9]\d{6,14}")


def to_msisdn(raw: str, region: str = config.HOME_REGION) -> str:
    """Normalize a phone number the way customers type it to E.164, as the gateway wants.

    "0151 2345 6789", "+49 (0)151 23456789" and "0049 151/23456789" all become
    "+4915123456789". Numbers in national form get the calling code of `region`.
    """
    text = _TRUNK_ZERO.sub("", raw.strip())
    text = _SEPARATORS.sub("", text)
    if text.startswith("00"):
        text = "+" + text[2:]
    elif text.startswith("0"):
        if region not in CALLING_CODES:
            raise ValueError(f"no calling code for region {region!r}")
        text = "+" + CALLING_CODES[region] + text[1:]
    if not _MSISDN.fullmatch(text):
        raise ValueError(f"not a phone number: {raw!r}")
    return text


def segments(text: str) -> int:
    return max(1, -(-len(text) // GSM_SEGMENT))


def send_sms(msisdn: str, text: str) -> dict:
    if not _MSISDN.fullmatch(msisdn):
        raise ValueError(f"not an E.164 number: {msisdn!r}")
    return record("sms", msisdn, text)
