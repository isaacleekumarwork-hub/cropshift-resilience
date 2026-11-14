"""Optional Manus research reports — placeholder, planned for phase A7.

Not implemented. This module makes no request.

Planned responsibility
    When ``Settings.manus_ready`` is true, submit an asynchronous research
    task to the Manus API and collect the finished report later. Reports are
    supplementary reading, labelled as AI-generated, and are never an input to
    the scientific engine. When the service is disabled or fails, the app
    works unchanged without it.

Safeguards planned for A7
    Disabled by default; no request without an explicit switch and key.

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""
