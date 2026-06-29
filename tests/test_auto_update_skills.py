import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTO_UPDATE = ROOT / "scripts" / "auto_update_skills.py"


def load_auto_update_module():
    spec = importlib.util.spec_from_file_location("auto_update_skills", AUTO_UPDATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AutoUpdateSkillsTests(unittest.TestCase):
    def test_startup_update_skips_without_github_repo(self):
        module = load_auto_update_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            code = module.main(
                [
                    "--source-root",
                    str(temp_path / "source"),
                    "--dest-dir",
                    str(temp_path / "skills"),
                    "--state-dir",
                    str(temp_path / "state"),
                    "--quiet",
                ]
            )

        self.assertEqual(code, 0)

    def test_github_repo_detection_accepts_common_forms(self):
        module = load_auto_update_module()

        self.assertTrue(module.is_github_repo_url("https://github.com/acme/sim.git"))
        self.assertTrue(module.is_github_repo_url("git@github.com:acme/sim.git"))
        self.assertFalse(module.is_github_repo_url("https://gitlab.com/acme/sim.git"))
        self.assertFalse(module.is_github_repo_url(""))

    def test_installer_copies_startup_update_helper_into_each_skill(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env = os.environ.copy()
            env["CODEX_SKILLS_DIR"] = temp_dir
            subprocess.run(
                ["bash", str(ROOT / "scripts" / "install_skills.sh")],
                cwd=ROOT,
                env=env,
                check=True,
                text=True,
                capture_output=True,
            )

            for skill_dir in sorted((ROOT / "skills").iterdir()):
                if not (skill_dir / "SKILL.md").exists():
                    continue
                installed_helper = (
                    Path(temp_dir)
                    / skill_dir.name
                    / "scripts"
                    / "auto_update_from_github.py"
                )
                self.assertTrue(installed_helper.exists(), skill_dir.name)


if __name__ == "__main__":
    unittest.main()
