import unittest

from openshock_mcp.cli import _http_endpoint


class CliTests(unittest.TestCase):
    def test_http_endpoint_ipv4(self):
        self.assertEqual(_http_endpoint("127.0.0.1", 8765, "/mcp"), "http://127.0.0.1:8765/mcp")

    def test_http_endpoint_ipv6(self):
        self.assertEqual(_http_endpoint("::1", 8765, "/mcp"), "http://[::1]:8765/mcp")


if __name__ == "__main__":
    unittest.main()
