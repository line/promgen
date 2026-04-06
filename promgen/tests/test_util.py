# Copyright (c) 2026 LY Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django.test import SimpleTestCase
from requests import HTTPError
from requests.models import Response

from promgen import util


class UtilTest(SimpleTestCase):
    def test_categorize_error(self):
        response = Response()
        response.status_code = 404

        cases = [
            (ImportError("missing dependency"), "import_error"),
            (HTTPError(response=response), "404_http_error"),
            (HTTPError(), "other_error"),
            (ValueError("bad input"), "other_error"),
        ]

        for error, expected in cases:
            with self.subTest(error=type(error).__name__, expected=expected):
                self.assertEqual(util.categorize_error(error), expected)
