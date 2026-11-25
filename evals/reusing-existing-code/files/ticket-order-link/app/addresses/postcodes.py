"""Postcode formats of the countries we ship to."""

import re

from app import config

_FORMATS = {"DE": re.compile(r"\d{5}"), "AT": re.compile(r"\d{4}"), "CH": re.compile(r"\d{4}")}


def check_postcode(country: str, raw: str) -> str:
    if country not in config.SHIPPING_COUNTRIES:
        raise ValueError(f"we do not ship to {country!r}")
    postcode = raw.strip()
    if not _FORMATS[country].fullmatch(postcode):
        raise ValueError(f"not a postcode in {country}: {raw!r}")
    return postcode
