"""Cross-document fragments must work in the current checkout, without HTTP."""
from pathlib import Path
import tempfile
import unittest

import check_repository_docs as checker


class RepositoryDocumentationTests(unittest.TestCase):
    def test_current_readme_and_guides(self):
        errors = [error for path in checker.documentation()
                  for error in checker.check_document(path)]
        self.assertEqual(errors, [])

    def test_unicode_duplicate_and_explicit_cross_document_anchors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'guide.md').write_text(
                '# 中文标题\n\n## 中文标题\n\n<a id="custom"></a>\n', encoding='utf-8')
            readme = root / 'README.md'
            readme.write_text(
                '[one](guide.md#%E4%B8%AD%E6%96%87%E6%A0%87%E9%A2%98)\n'
                '[two](guide.md#中文标题-1)\n[three](guide.md#custom)\n'
                '[reference]: guide.md#custom\n', encoding='utf-8')
            self.assertEqual(checker.check_document(readme, root), [])

    def test_missing_file_and_fragment_are_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'guide.md').write_text('# Real\n', encoding='utf-8')
            readme = root / 'README.md'
            readme.write_text('[file](absent.md)\n[anchor](guide.md#absent)\n', encoding='utf-8')
            errors = checker.check_document(readme, root)
            self.assertEqual(len(errors), 2)
            self.assertIn('missing file', errors[0])
            self.assertIn('missing anchor', errors[1])

    def test_fenced_examples_do_not_create_or_follow_links(self):
        text = '# Actual\n```bash\n# Fake\n[example](absent.md)\n```\n'
        self.assertEqual(checker.anchors(text), {'actual'})
        self.assertEqual(list(checker.local_links(text)), [])

    def test_history_urls_are_external_and_reference_fragments_are_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            readme = root / 'README.md'
            readme.write_text(
                '# Present\n[legacy](https://github.com/liucong552-art/ceshi/pull/3)\n'
                '[bad]: #absent\n', encoding='utf-8')
            errors = checker.check_document(readme, root)
            self.assertEqual(len(errors), 1)
            self.assertIn('missing anchor', errors[0])


if __name__ == '__main__':
    unittest.main()
