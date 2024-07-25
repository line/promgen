# Copyright (c) 2024 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

from django.urls import reverse
from yaml import safe_load

from promgen import tests


class RendererTests(tests.PromgenTest):
    fixtures = ["testcases.yaml", "extras.yaml"]

    def test_global_rule(self):
        expected = tests.Data("examples", "export.rule.yml").yaml()
        response = self.client.get(reverse("api:all-rules"))
        self.assertEqual(response.status_code, 200)
        # The test client does not have a shortcut to decode yaml
        data = safe_load(response.content)
        self.assertEqual(data, expected)

    def test_global_targets(self):
        expected = tests.Data("examples", "export.targets.json").json()
        response = self.client.get(reverse("api:all-targets"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
