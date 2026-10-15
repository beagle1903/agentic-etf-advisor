"""Frozen Yahoo exchange-to-listing mapping (ADR 0038)."""

MAP_VERSION = "yahoo-listing-map-v1"
EU_EXCHANGES = {
    "at": ("VIE",),
    "be": ("BRU",),
    "cz": ("PRA",),
    "dk": ("CPH",),
    "ee": ("TAL",),
    "fi": ("HEL",),
    "fr": ("ENX", "PAR"),
    "de": ("BER", "DUS", "EUX", "FRA", "GER", "HAM", "HAN", "MUN", "STU"),
    "gr": ("ATH",),
    "hu": ("BUD",),
    "ie": ("ISE",),
    "it": ("MDD", "MIL", "TLO"),
    "lv": ("RIS",),
    "lt": ("LIT",),
    "nl": ("AMS", "DXE"),
    "pl": ("WSE",),
    "pt": ("LIS",),
    "ro": ("BVB",),
    "es": ("MAD", "MCE"),
    "se": ("STO",),
}
US_EXCHANGES = ("ASE", "BTS", "CXI", "NAE", "NCM", "NGM", "NMS", "NYQ", "PCX")
UNSUPPORTED_EU = ("bg", "hr", "cy", "lu", "mt", "sk", "si")
EXCLUDED_CODES = ("OEM", "OQB", "OQX", "PNK", "YHD", "AQS", "CXE", "IOB", "LSE", "EBS")
EXCHANGE_MAP = {code: (country, "EU") for country, codes in EU_EXCHANGES.items() for code in codes}
EXCHANGE_MAP.update({code: ("us", "US") for code in US_EXCHANGES})
MANIFEST = tuple(
    (country, code) for country, codes in EU_EXCHANGES.items() for code in codes
) + tuple(("us", code) for code in US_EXCHANGES)
assert len(MANIFEST) == 42
