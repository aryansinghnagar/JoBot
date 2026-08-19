import re


class PIIMasker:
    """
    PII Sanitization & Tokenization Masker (Phase 5.1).
    Scubs email, phone numbers, Aadhaar, and PAN patterns before sending text to LLM providers.
    """

    PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\+?\d{10,13}",
        "aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
        "pan": r"\b[A-Z]{5}\d{4}[A-Z]\b",
    }

    def mask(self, text: str) -> tuple[str, dict[str, str]]:
        """Replace PII with tokens. Returns masked text and token mapping."""
        mapping: dict[str, str] = {}
        masked_text = text

        for pii_type, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, masked_text)
            for i, match in enumerate(matches):
                token = f"[{pii_type.upper()}_{i}]"
                masked_text = masked_text.replace(match, token)
                mapping[token] = match

        return masked_text, mapping

    def unmask(self, masked_text: str, mapping: dict[str, str]) -> str:
        """Restore original PII values from tokens."""
        unmasked = masked_text
        for token, original in mapping.items():
            unmasked = unmasked.replace(token, original)
        return unmasked
