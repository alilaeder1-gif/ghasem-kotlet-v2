import random
import re

_SIGNATURE_STARTERS = [
    "داداش ",
    "بابا ",
    "رفیق ",
    "داش ",
    "",
]

_SIGNATURE_ENDERS = [
    " 😎",
    " 😅",
    " 👍",
    " 😄",
    " 🤝",
    "",
]

_METAPHORS = {
    "hard": [
        "مثل کتلت توی ماهیتابه",
        "مثل کتلت داغ",
        "انگار کتلت بندازی تو روغن داغ",
    ],
    "easy": [
        "مثل آب خوردن",
        "مثل کتلت خوردن",
        "انگار داری با رفیقت حرف می‌زنی",
    ],
    "fail": [
        "باتریتم داره تموم میشه",
        "کتلت سوخته",
        "یکم کرم کردم",
    ],
    "restart": [
        "یه کتلت بنداز تو روغن",
        "بیا از نو بسازیمش",
        "ریستارتش کن بابا",
    ],
}


def apply_signature(response: str, context: dict = None) -> str:
    if not response:
        return response

    if response.startswith("⚠") or response.startswith("⏳"):
        return response

    starter = random.choice(_SIGNATURE_STARTERS)
    ender = random.choice(_SIGNATURE_ENDERS)

    needs_starter = not any(
        response.startswith(s) for s in ["داداش", "بابا", "رفیق", "داش"]
    )
    needs_ender = not any(
        response.endswith(e) for e in ["😎", "😅", "👍", "😄", "🤝"]
    ) and not response.rstrip().endswith((".", "!", "?"))

    result = response
    if needs_starter and starter:
        result = starter + result[0].lower() + result[1:]
    if needs_ender and ender:
        result = result.rstrip() + ender

    return result


def inject_metaphor(response: str, category: str = "easy") -> str:
    if category in _METAPHORS:
        meta = random.choice(_METAPHORS[category])
        response = response.rstrip(".!?") + f". {meta}"
    return response


def is_kotlet_response(response: str) -> bool:
    markers = [
        r"داداش",
        r"کتلت",
        r"بابا",
        r"والا",
        r"😎",
        r"دمت",
    ]
    return any(re.search(m, response) for m in markers)
