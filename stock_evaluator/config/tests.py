from django.test import SimpleTestCase


class ProjectConfigTests(SimpleTestCase):
    def test_root_urlconf_imports(self):
        response = self.client.get("/admin/")

        self.assertIn(response.status_code, {200, 302})
