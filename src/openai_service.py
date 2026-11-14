"""Optional OpenAI explanations — placeholder, planned for phase A6.

Not implemented. This module makes no request and imports no OpenAI library.

Planned responsibility
    When ``Settings.openai_ready`` is true, ask the OpenAI Responses API to
    restate an existing ``models.ComparisonResult`` in plain language. The
    service only rewords numbers the deterministic engine already produced; it
    never supplies data, indicators or recommendations of its own. When the
    service is disabled or fails, the app works unchanged without it.

Safeguards planned for A6
    Disabled by default; no request without an explicit switch and key; output
    labelled as AI-generated wherever it is shown.

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""
