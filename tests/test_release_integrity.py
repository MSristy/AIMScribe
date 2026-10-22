"""Branding release must reconstruct original frozen bytes without relaxing evidence checks."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from src.release_integrity import verify_frozen_snapshot

ROOT = Path(__file__).resolve().parents[1]


class ReleaseIntegrityTests(unittest.TestCase):
    def make_snapshot(self, destination):
        manifest = json.loads((ROOT/'evaluation/experiment/manifest.json').read_text())
        names = list(manifest['sha256']) + ['evaluation/experiment/manifest.json',
                                          'evaluation/experiment/branding-amendment.json']
        maintenance = ROOT/'evaluation/experiment/maintenance-release.json'
        if maintenance.exists():
            release = json.loads(maintenance.read_text())
            names += list(release['current_files_sha256'])
            names += ['evaluation/experiment/maintenance-release.json', release['original_source_archive']]
        for name in set(names):
            target = destination/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT/name, target)

    def test_audited_rename_reconstructs_original_freeze(self):
        verified = verify_frozen_snapshot(ROOT)
        self.assertEqual(verified['experiment_id'], 'q2-applicability-preview-v1')
        self.assertEqual(len(verified['sha256']), 19)

    def test_unregistered_runtime_edit_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='clinical-nlp-release-') as temporary:
            destination = Path(temporary)
            self.make_snapshot(destination)
            with (destination/'app.py').open('ab') as file:
                file.write(b'\n# unrelated change\n')
            with self.assertRaisesRegex(ValueError, 'release bytes changed'):
                verify_frozen_snapshot(destination)

    def test_case_change_is_still_rejected(self):
        with tempfile.TemporaryDirectory(prefix='clinical-nlp-release-') as temporary:
            destination = Path(temporary)
            self.make_snapshot(destination)
            with (destination/'evaluation/experiment/cases.json').open('ab') as file:
                file.write(b'\n')
            with self.assertRaisesRegex(ValueError, 'Frozen file changed'):
                verify_frozen_snapshot(destination)
