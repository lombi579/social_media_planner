import os
import unittest

from web.settings import load_settings


class SettingsTests(unittest.TestCase):
    def test_defaults(self) -> None:
        for key in ["APP_ENV", "APP_HOST", "APP_PORT", "APP_RELOAD", "DATABASE_FILE"]:
            os.environ.pop(key, None)
        settings = load_settings()
        self.assertEqual(settings.app_env, "development")
        self.assertEqual(settings.host, "0.0.0.0")
        self.assertEqual(settings.port, 8080)
        self.assertTrue(settings.reload)

    def test_production_defaults_reload_false(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ.pop("APP_RELOAD", None)
        settings = load_settings()
        self.assertFalse(settings.reload)


if __name__ == "__main__":
    unittest.main()
