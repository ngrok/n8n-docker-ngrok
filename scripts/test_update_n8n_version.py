import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("updater", Path(__file__).with_name("update-n8n-version.py"))
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class UpdateVersionTests(unittest.TestCase):
    def release(self, version="2.39.8", **fields):
        return {"tag_name": f"n8n@{version}", "draft": False, "prerelease": False, **fields}

    def test_changes_only_version(self):
        content = '# Settings\nN8N_VERSION="2.38.7"\nOTHER="2.38.7"\n'
        result, current, latest = updater.update_version(content, self.release())
        self.assertEqual(result, '# Settings\nN8N_VERSION="2.39.8"\nOTHER="2.38.7"\n')
        self.assertEqual((current, latest), ("2.38.7", "2.39.8"))

    def test_equal_or_older_release_is_unchanged(self):
        for version in ("2.39.8", "2.40.0", "3.0.0"):
            with self.subTest(version=version):
                content = f'N8N_VERSION="{version}"\n'
                self.assertEqual(updater.update_version(content, self.release())[0], content)

    def test_numeric_version_comparison(self):
        result, _, _ = updater.update_version('N8N_VERSION="2.9.9"\n', self.release("2.10.0"))
        self.assertEqual(result, 'N8N_VERSION="2.10.0"\n')

    def test_rejects_unstable_or_unexpected_releases(self):
        for fields in ({"draft": True}, {"prerelease": True}, {"tag_name": "stable"},
                       {"tag_name": "n8n@2.40.0-beta.1"}, {"tag_name": "other@2.39.8"}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                updater.update_version('N8N_VERSION="2.38.7"\n', self.release(**fields))

    def test_rejects_missing_duplicate_or_malformed_assignment(self):
        for content in ("", 'N8N_VERSION="latest"\n', 'N8N_VERSION="2.0.0"\n' * 2):
            with self.subTest(content=content), self.assertRaises(ValueError):
                updater.update_version(content, self.release())


if __name__ == "__main__":
    unittest.main()
