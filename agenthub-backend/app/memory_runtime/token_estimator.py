from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _get_tiktoken_encoder():
    try:
        import tiktoken  # type: ignore

        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


def estimate_tokens(text: str) -> int:
    s = str(text or "")
    if not s:
        return 0

    encoder = _get_tiktoken_encoder()
    if encoder is not None:
        try:
            return int(len(encoder.encode(s)))
        except Exception:
            pass

    ascii_chars = 0
    non_ascii_chars = 0
    for ch in s:
        if ord(ch) < 128:
            ascii_chars += 1
        else:
            non_ascii_chars += 1
    return (ascii_chars + 3) // 4 + non_ascii_chars
