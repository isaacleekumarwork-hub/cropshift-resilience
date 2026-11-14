"""CropShift RESILIENCE — Streamlit entry point.

Phase A1 foundation page. It reports honestly what exists and what does not:
there are no NASA observations, no crop data and no results on this page,
because none of that has been built yet. The full interface arrives in A5.

Run with:  streamlit run app.py

AI assistance: drafted with Claude Code (Anthropic) under the participant's
direction. See docs/provenance.md.
"""

from __future__ import annotations

import streamlit as st
from pydantic import ValidationError

from src import (
    CHALLENGE_NAME,
    CURRENT_PHASE,
    EVENT_NAME,
    MODULES,
    PHASES,
    PROJECT_NAME,
    __version__,
)
from src.config import get_settings
from src.models import DEFAULT_DISCLAIMER

st.set_page_config(page_title=PROJECT_NAME, page_icon="🌾", layout="centered")

st.title(PROJECT_NAME)
st.caption(f"{EVENT_NAME} · {CHALLENGE_NAME}")

try:
    settings = get_settings()
except ValidationError as error:
    # Show which settings are wrong without echoing their values.
    names = sorted({str(item["loc"][0]).upper() for item in error.errors() if item["loc"]})
    st.error(
        "The configuration is invalid, so the app has stopped. "
        f"Check these settings in your .env file: {', '.join(names)}. "
        "See .env.example for the allowed values."
    )
    st.stop()

st.warning(
    f"**Development stage {CURRENT_PHASE} of A9: foundation only.** "
    "Scientific analyses are not implemented yet. This page shows no NASA "
    "observations, no crop data and no results.",
    icon="🚧",
)

st.subheader("What this tool is being built to do")
st.markdown(
    "Help farmers explore crop-rotation options under changing conditions by "
    "comparing their current rotation with alternatives across **dry, typical "
    "and wet seasons from the historical record**. It will combine NASA Earth "
    "data, local soil information, cited crop characteristics and the farmer's "
    "own priorities, and show the tradeoffs and the uncertainty rather than a "
    "single answer."
)

st.subheader("Dashboard")
with st.container(border=True):
    st.markdown("**Rotation comparison dashboard: not built yet**")
    st.caption(
        "Planned for phase A5. It will let you pick a pilot region, review NASA "
        "environmental data, describe your soil, choose rotations and compare them. "
        "Nothing is shown here until real data and tested calculations exist."
    )

st.subheader("Build status")
st.dataframe(
    [{"Phase": phase.code, "Scope": phase.title, "Status": phase.status} for phase in PHASES],
    hide_index=True,
    width="stretch",
)

with st.expander("Modules and what each one will do"):
    st.dataframe(
        [
            {
                "Module": f"src/{module.name}.py",
                "Phase": module.phase,
                "Responsibility": module.responsibility,
                "State": "working" if module.implemented else "placeholder",
            }
            for module in MODULES
        ],
        hide_index=True,
        width="stretch",
    )

st.subheader("Current settings")
run_mode = (
    "Offline demo: bundled or cached data only, no network requests"
    if settings.offline_demo_mode
    else "Live: NASA data will be retrieved on request once phase A2 is built"
)
st.markdown(f"- **Run mode:** {run_mode}")
for service, status in settings.integration_status().items():
    st.markdown(f"- **{service}:** {status}")
st.caption(
    "External AI services are optional and off by default. "
    "The scientific calculations will never depend on them."
)

st.divider()
st.caption(DEFAULT_DISCLAIMER)
st.caption(
    f"Version {__version__} · Built during the hackathon with AI coding assistance; "
    "see docs/provenance.md."
)
