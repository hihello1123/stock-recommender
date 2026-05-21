import os
import tempfile

from django.test import SimpleTestCase

from stock_evaluator.config.settings import _load_env_file


class ProjectConfigTests(SimpleTestCase):
    def test_root_urlconf_imports(self):
        response = self.client.get("/admin/")

        self.assertIn(response.status_code, {200, 302})

    def test_load_env_file_reads_local_env(self):
        original_value = os.environ.get("TEST_DOTENV_KEY")
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = os.path.join(tmpdir, ".env")
            with open(env_path, "w", encoding="utf-8") as handle:
                handle.write(
                    "TEST_DOTENV_KEY=from-dot-env\n"
                    "DJANGO_DEBUG=true\n"
                    "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1\n"
                )
            _load_env_file(os.path.abspath(env_path))

            self.assertEqual(os.environ["TEST_DOTENV_KEY"], "from-dot-env")
            self.assertEqual(os.environ["DJANGO_DEBUG"], "true")
        if original_value is None:
            os.environ.pop("TEST_DOTENV_KEY", None)
        else:
            os.environ["TEST_DOTENV_KEY"] = original_value
