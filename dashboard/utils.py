"""Shared helpers for Streamlit dashboard pages."""

import logging
from typing import Any, Optional

import requests
import streamlit as st

from config import settings

log = logging.getLogger(__name__)

API_BASE = f"http://localhost:{settings.api_port}"
ELECTION_ID = 1  # can be extended to a selector

STATE_NAMES = {
    "S03": "Assam",
    "S11": "Kerala",
    "S22": "Tamil Nadu",
    "S25": "West Bengal",
    "U07": "Puducherry",
}


@st.cache_data(ttl=settings.cache_ttl, show_spinner=False)
def api_get(path: str, params: Optional[dict] = None) -> Any:
    """Cached GET request to the FastAPI backend."""
    try:
        resp = requests.get(f"{API_BASE}{path}", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to the API. Make sure the FastAPI server is running.")
        return None
    except requests.exceptions.HTTPError as e:
        log.warning("API error %s for %s: %s", e.response.status_code, path, e)
        return None


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"<h2 style='color:#1a3c5e;margin-bottom:4px'>{title}</h2>",
        unsafe_allow_html=True,
    )
    if subtitle:
        st.caption(subtitle)
    st.divider()


def kpi_tile(label: str, value: Any, delta: Any = None, help_text: str = "") -> None:
    st.metric(label=label, value=value, delta=delta, help=help_text)
