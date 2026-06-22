import tempfile
import unittest
from pathlib import Path

from examples.field_service_mesa.legacy_app import build_legacy_app_html, write_legacy_app


class FieldServiceLegacyAppTest(unittest.TestCase):
    def test_legacy_app_uses_vanilla_js_without_solara_runtime(self):
        html = build_legacy_app_html()

        self.assertIn("Field Service Legacy JS", html)
        self.assertIn('data-runtime="legacy-js"', html)
        self.assertIn('id="startStop"', html)
        self.assertIn('id="stepDelay"', html)
        self.assertIn('data-layer="situation-animation"', html)
        self.assertIn('data-chart="profit"', html)
        self.assertIn('data-chart="queues"', html)
        self.assertIn('data-panel="event-log"', html)
        self.assertIn("function stepModel()", html)
        self.assertIn("setInterval", html)
        self.assertNotIn("solara", html.lower())
        self.assertNotIn("vuetify", html.lower())

    def test_write_legacy_app_creates_self_contained_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "index.html"
            write_legacy_app(target)
            html = target.read_text(encoding="utf-8")

        self.assertIn("<!doctype html>", html)
        self.assertIn("<script>", html)
        self.assertNotIn("<script src=", html)
        self.assertNotIn("<link rel=\"stylesheet\"", html)


if __name__ == "__main__":
    unittest.main()
