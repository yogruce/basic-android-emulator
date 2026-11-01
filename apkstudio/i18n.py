"""Basit iki dilli (TR/EN) metin desteği.

Kullanım: ``T("Türkçe metin", "English text")``. Dil, uygulama açılışında
``set_language`` ile ayarlanır; değişiklik yeniden başlatma sonrası geçerli olur.
"""

_LANG = "tr"
SUPPORTED = {"tr": "Türkçe", "en": "English"}


def set_language(lang: str) -> None:
    global _LANG
    _LANG = lang if lang in SUPPORTED else "tr"


def get_language() -> str:
    return _LANG


def T(tr_text: str, en_text: str) -> str:
    return en_text if _LANG == "en" else tr_text
