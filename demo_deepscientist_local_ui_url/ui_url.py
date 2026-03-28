from __future__ import annotations


def _local_ui_url(host: str, port: int) -> str:
    connect_host = "0.0.0.0" if host in {"0.0.0.0", "::", ""} else host
    return f"http://{connect_host}:{port}"


def _browser_ui_url(host: str, port: int) -> str:
    normalized = str(host or "").strip()
    browser_host = "127.0.0.1" if normalized in {"", "0.0.0.0", "::", "[::]"} else normalized
    return f"http://{browser_host}:{port}"
