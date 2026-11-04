"""Exercise imports, selective installation and real bidirectional Git transfer."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillImportTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "var").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "var")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "tools"
        self.root.mkdir()
        self.source = self.base / "home/.codex/skills/example"
        self.source.mkdir(parents=True)
        (self.source / "SKILL.md").write_text("---\nname: example\ndescription: A reusable example\n---\n\nLine one\n\nLine two\n")
        self.registry = "# existing owner comment\nschema_version: 2\nroot: .\nskills: []\nengines: []\nvendor: []\ndeprecated: []\n"
        (self.root / "registry.yaml").write_text(self.registry)
        self.importer = load("import-skill")
        self.root_patch = patch.object(self.importer, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def test_preview_preserves_source_registry_and_installation(self):
        self.importer.import_skill(self.source, "codex", True)
        self.assertFalse(self.source.is_symlink())
        self.assertFalse((self.root / "skills").exists())
        self.assertEqual(self.registry, (self.root / "registry.yaml").read_text())

    def test_import_preserves_payload_backup_and_original_entry(self):
        original = (self.source / "SKILL.md").read_bytes()
        (self.source / ".venv").mkdir()
        (self.source / ".venv/local-only").write_text("local runtime")
        report = self.importer.import_skill(self.source, "codex")
        target = self.root / "skills/example"
        self.assertEqual(target, self.source.resolve())
        self.assertEqual(original, (target / "SKILL.md").read_bytes())
        self.assertFalse((target / ".venv").exists())
        self.assertTrue((Path(report["backup"]) / ".venv/local-only").exists())
        text = (self.root / "registry.yaml").read_text()
        self.assertTrue(text.startswith("# existing owner comment\n"))
        self.assertEqual("example", yaml.safe_load(text)["skills"][0]["name"])

    def test_collision_never_replaces_either_version(self):
        target = self.root / "skills/example"
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("existing version")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.importer.import_skill(self.source, "codex")
        self.assertEqual("existing version", (target / "SKILL.md").read_text())
        self.assertFalse(self.source.is_symlink())
        self.assertEqual(self.registry, (self.root / "registry.yaml").read_text())

    def test_external_link_does_not_pull_private_data_into_source(self):
        private = self.base / "private.txt"
        private.write_text("local only")
        (self.source / "private.txt").symlink_to(private)
        with self.assertRaises(ValueError):
            self.importer.import_skill(self.source, "codex")
        self.assertFalse((self.root / "skills/example").exists())
        self.assertEqual(self.registry, (self.root / "registry.yaml").read_text())

    def test_failed_entry_creation_restores_original_and_registry(self):
        original = (self.source / "SKILL.md").read_bytes()
        with patch.object(Path, "symlink_to", side_effect=OSError("simulated link failure")):
            with self.assertRaisesRegex(OSError, "simulated link failure"):
                self.importer.import_skill(self.source, "codex")
        self.assertFalse(self.source.is_symlink())
        self.assertEqual(original, (self.source / "SKILL.md").read_bytes())
        self.assertFalse((self.root / "skills/example").exists())
        self.assertEqual(self.registry, (self.root / "registry.yaml").read_text())


class TwoCheckoutReplay(unittest.TestCase):
    def setUp(self):
        (ROOT / "var").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "var")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.remote = self.base / "remote.git"
        self.a = self.base / "Mac A/tools"
        self.b = self.base / "Mac B/different path/tools"
        self.home_a = self.base / "home A"
        self.home_b = self.base / "home B"
        self.git(self.base, "init", "--bare", "--initial-branch=main", str(self.remote))
        self.a.parent.mkdir(parents=True)
        self.git(self.base, "clone", str(self.remote), str(self.a))
        self.configure(self.a)
        (self.a / "scripts").mkdir()
        for script in ("sync-skills.py", "check-tools.py", "import-skill.py"):
            shutil.copy2(ROOT / "scripts" / script, self.a / "scripts" / script)
        shutil.copytree(ROOT / "skills/daily-planning-partner", self.a / "skills/daily-planning-partner")
        unrelated = self.a / "skills/unrelated-local-skill"
        unrelated.mkdir()
        (unrelated / "SKILL.md").write_text("An unrelated, unregistered local skill.\n")
        registry = {"schema_version": 2, "root": ".", "skills": [
            {"name": "daily-planning-partner", "source": "skills/daily-planning-partner", "hosts": ["codex"]},
            {"name": "heavy", "source": "skills/heavy", "hosts": ["codex"], "uses_engines": ["heavy"]}],
            "engines": [{"id": "heavy", "path": "engines/heavy"}],
            "vendor": [{"id": "external", "path": "vendor/external"}], "deprecated": []}
        (self.a / "registry.yaml").write_text(yaml.safe_dump(registry, sort_keys=False))
        (self.a / ".gitignore").write_text("var/\n")
        self.commit(self.a, "seed")
        self.git(self.a, "push", "-u", "origin", "main")
        self.b.parent.mkdir(parents=True)
        self.git(self.base, "clone", str(self.remote), str(self.b))
        self.configure(self.b)

    def git(self, cwd, *args, check=True):
        return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=check)

    def configure(self, root):
        self.git(root, "config", "user.name", "Skill transfer replay")
        self.git(root, "config", "user.email", "replay@example.invalid")

    def commit(self, root, message):
        self.git(root, "add", ".")
        self.git(root, "commit", "-m", message)

    def cli(self, root, home, script, *args):
        env = dict(os.environ, HOME=str(home))
        return subprocess.run([os.sys.executable, str(root / "scripts" / script), *args],
                              cwd=root, env=env, text=True, capture_output=True)

    def install_and_check(self, root, home, name):
        for script in ("sync-skills.py", "check-tools.py"):
            args = ["--host", "codex", "--skill", name]
            if script == "check-tools.py":
                args.append("--strict")
            result = self.cli(root, home, script, *args)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(root / "skills" / name, (home / ".agents/skills" / name).resolve())
        self.assertFalse((home / ".agents/skills/heavy").exists())

    def test_real_skill_roundtrip_new_skill_return_and_conflict_preservation(self):
        self.install_and_check(self.a, self.home_a, "daily-planning-partner")
        self.install_and_check(self.b, self.home_b, "daily-planning-partner")
        changed = self.b / "skills/daily-planning-partner/references/calendar-records.md"
        changed.write_text(changed.read_text() + "\n<!-- Mac B review: preserve real appointments. -->\n")
        self.commit(self.b, "review planning rule on B")
        self.git(self.b, "push", "origin", "main")
        self.git(self.a, "pull", "--ff-only")
        self.assertEqual(changed.read_bytes(), (self.a / changed.relative_to(self.b)).read_bytes())

        new_skill = self.home_b / ".codex/skills/new-skill"
        new_skill.mkdir(parents=True)
        (new_skill / "SKILL.md").write_text("---\nname: new-skill\ndescription: New skill from Mac B\n---\n\nReusable instructions.\n")
        result = self.cli(self.b, self.home_b, "import-skill.py", str(new_skill))
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.commit(self.b, "add a skill from B")
        self.git(self.b, "push", "origin", "main")
        self.git(self.a, "pull", "--ff-only")
        self.install_and_check(self.a, self.home_a, "new-skill")
        self.assertEqual(new_skill.resolve(), self.b / "skills/new-skill")

        file_a = self.a / "skills/new-skill/SKILL.md"
        file_b = self.b / "skills/new-skill/SKILL.md"
        file_a.write_text(file_a.read_text().replace("Reusable instructions.", "Mac A changed this rule."))
        file_b.write_text(file_b.read_text().replace("Reusable instructions.", "Mac B changed this rule."))
        self.commit(self.a, "change on A")
        self.commit(self.b, "change on B")
        self.git(self.a, "push", "origin", "main")
        pull = self.git(self.b, "pull", "--ff-only", check=False)
        self.assertNotEqual(0, pull.returncode)
        self.assertIn("Mac B changed this rule.", file_b.read_text())
        merge = self.git(self.b, "merge", "origin/main", check=False)
        self.assertNotEqual(0, merge.returncode)
        self.assertIn("Mac A changed this rule.", file_b.read_text())
        self.assertIn("Mac B changed this rule.", file_b.read_text())
        self.assertIn("<<<<<<<", file_b.read_text())

    def test_unknown_selection_does_not_modify_host_entries(self):
        result = self.cli(self.a, self.home_a, "sync-skills.py", "--host", "codex", "--skill", "typo")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("unknown skills", result.stderr)
        self.assertFalse((self.home_a / ".agents/skills").exists())


if __name__ == "__main__":
    unittest.main()
