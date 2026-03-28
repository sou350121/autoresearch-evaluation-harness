from __future__ import annotations

import unittest

from ui_url import _browser_ui_url, _local_ui_url


class UiUrlTests(unittest.TestCase):
    def test_local_ui_url_normalizes_wildcard_and_empty_hosts_to_loopback(self) -> None:
        self.assertEqual("http://127.0.0.1:20999", _local_ui_url("0.0.0.0", 20999))
        self.assertEqual("http://127.0.0.1:20999", _local_ui_url("", 20999))
        self.assertEqual("http://127.0.0.1:20999", _local_ui_url("::", 20999))

    def test_browser_ui_url_normalizes_wildcard_hosts_to_loopback(self) -> None:
        self.assertEqual("http://127.0.0.1:20999", _browser_ui_url("0.0.0.0", 20999))
        self.assertEqual("http://127.0.0.1:20999", _browser_ui_url("[::]", 20999))

    def test_local_and_browser_urls_agree_for_default_hosts(self) -> None:
        self.assertEqual(_browser_ui_url("0.0.0.0", 20999), _local_ui_url("0.0.0.0", 20999))
        self.assertEqual(_browser_ui_url("::", 20999), _local_ui_url("::", 20999))


if __name__ == "__main__":
    unittest.main()
