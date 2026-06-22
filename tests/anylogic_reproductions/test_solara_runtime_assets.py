import importlib.util
import unittest
from pathlib import Path

import solara.server.settings


class SolaraRuntimeAssetsTest(unittest.TestCase):
    def test_solara_assets_extra_is_installed_for_offline_startup(self):
        self.assertIsNotNone(importlib.util.find_spec("solara_assets"))

    def test_required_vuetify_assets_are_cached_locally(self):
        cache_dir = Path(solara.server.settings.assets.proxy_cache_dir)
        required = [
            cache_dir / "@widgetti/solara-vuetify-app@10.0.3/dist/fonts.css",
            cache_dir / "@widgetti/solara-vuetify-app@10.0.3/dist/main8.css",
            cache_dir / "@widgetti/solara-vuetify-app@10.0.3/dist/solara-vuetify-app8.js",
            cache_dir / "requirejs@2.3.6/require.js",
        ]

        missing = [str(path) for path in required if not path.exists()]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
