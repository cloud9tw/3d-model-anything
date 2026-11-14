"""Exercise real capture evidence: rejection, diversity, provenance and read-only IO."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

try:
    from assess_capture import assess_bundle
except ImportError:
    assess_bundle = None


def matrix(x=0, z=0):
    return [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x, 0, z, 1]


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / 'session'
        (self.root / 'photos').mkdir(parents=True)
        (self.root / 'rooms').mkdir()
        self.manifest = {'format': 'house-capture/5', 'session': 'one', 'zone': 'z',
                         'alignment': {'method': 'first'}, 'photoCount': 0,
                         'photos': 'photos/photos.json',
                         'rooms': [{'index': 7, 'file': 'rooms/room-7.json'}]}
        self.rows = []
        self.write('rooms/room-7.json', {'walls': [
            {'transform': matrix(), 'dimensions': [3, 2.5, 0]}], 'objects': []})

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, value):
        (self.root / name).write_text(json.dumps(value), encoding='utf-8')

    def photo(self, index, x=0, room=7, **changes):
        image = Image.new('RGB', (96, 64), (80, 110, 130))
        draw = ImageDraw.Draw(image)
        for k in range(0, 96, 8):
            draw.line((k, 0, 95-k, 63), fill=(230, 190, 150), width=2)
        draw.rectangle((index % 40, 20, index % 40 + 6, 28), fill=(20, 30, 40))
        path = f'photos/{index:04d}.jpg'
        image.save(self.root / path)
        row = {'file': path, 'room': room, 'transform': matrix(x),
               'intrinsics': [80, 0, 0, 0, 80, 0, 48, 32, 1],
               'width': 96, 'height': 64, 'tracking': 'normal', 'blurPixels': 0.02}
        row.update(changes)
        self.rows.append(row)
        return row

    def flush(self):
        self.manifest['photoCount'] = len(self.rows)
        self.write('manifest.json', self.manifest)
        self.write('photos/photos.json', self.rows)

    def assess(self, maximum=24):
        self.assertIsNotNone(assess_bundle, 'capture assessment is not implemented')
        self.flush()
        return assess_bundle(self.root, 7, maximum)

    def test_nonzero_room_indices_and_original_order_survive_selection(self):
        self.photo(1, room=0)
        self.photo(2, x=0)
        self.photo(3, x=1)
        report = self.assess()
        self.assertEqual({p['photoIndex'] for p in report['selected']}, {1, 2})
        self.assertEqual(report['room'], 7)
        self.assertEqual(report['alignment']['scope'], 'session-only')
        self.assertFalse(report['alignment']['housePlacementVerified'])

    def test_distinct_views_win_over_repeated_frames(self):
        self.photo(0, x=0)
        self.photo(1, x=0.01)
        self.photo(2, x=2)
        report = self.assess(maximum=2)
        self.assertIn(2, [p['photoIndex'] for p in report['selected']])
        self.assertEqual(len(report['selected']), 2)

    def test_invalid_pose_tracking_intrinsics_and_blur_are_excluded(self):
        self.photo(0)
        self.photo(1, transform=[float('nan')] * 16)
        self.photo(2, x=1, tracking='limited:excessiveMotion')
        self.photo(3, x=2, intrinsics=[0] * 9)
        self.photo(4, x=3, blurPixels=5)
        report = self.assess()
        self.assertEqual([p['photoIndex'] for p in report['selected']], [0])
        self.assertEqual({p['photoIndex'] for p in report['excluded']}, {1, 2, 3, 4})
        self.assertEqual(report['status'], 'partial')
        json.dumps(report, allow_nan=False)

    def test_missing_pose_is_not_invented_from_jpg(self):
        row = self.photo(0)
        del row['transform']
        report = self.assess()
        self.assertEqual(report['selected'], [])
        self.assertEqual(report['status'], 'blocked')
        self.assertTrue(report['excluded'][0]['reason'])

    def test_partial_area_without_layout_preserves_usable_photo_evidence(self):
        self.manifest['rooms'][0]['file'] = ''
        self.photo(0)
        report = self.assess()
        self.assertEqual(report['layout']['status'], 'unmeasured')
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(len(report['selected']), 1)

    def test_rejects_unsafe_paths_and_missing_files(self):
        self.photo(0, file='../outside.jpg')
        self.photo(1, file='photos/missing.jpg')
        self.photo(2, file='C:\\private\\image.jpg')
        report = self.assess()
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(len(report['excluded']), 3)

    def test_rejects_image_size_mismatch_and_corruption(self):
        self.photo(0, width=192)
        self.photo(1)
        (self.root / 'photos/0001.jpg').write_bytes(b'not an image')
        report = self.assess()
        self.assertEqual(report['selected'], [])
        self.assertEqual(len(report['excluded']), 2)

    def test_exact_duplicate_pixels_do_not_count_as_another_view(self):
        self.photo(0)
        self.photo(1, x=1)
        (self.root / 'photos/0001.jpg').write_bytes((self.root / 'photos/0000.jpg').read_bytes())
        report = self.assess()
        self.assertEqual(len(report['selected']), 1)
        self.assertIn('duplicate', report['excluded'][0]['reason'])

    def test_input_files_unchanged_and_selected_hash_matches_original(self):
        self.photo(0)
        self.flush()
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        report = self.assess()
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(report['selected'][0]['sha256'], hashlib.sha256(before[Path('photos/0000.jpg')]).hexdigest())

    def test_room_selection_and_limits_are_explicit(self):
        self.photo(0)
        self.flush()
        self.assertIsNotNone(assess_bundle, 'capture assessment is not implemented')
        for room, count in [(0, 24), (7, 0), (7, -1)]:
            with self.assertRaises(ValueError):
                assess_bundle(self.root, room, count)
        self.manifest['rooms'].append(copy.deepcopy(self.manifest['rooms'][0]))
        self.flush()
        with self.assertRaises(ValueError):
            assess_bundle(self.root, 7)

    def test_cli_refuses_to_overwrite_or_write_inside_input(self):
        self.photo(0)
        self.flush()
        script = Path(__file__).with_name('assess_capture.py')
        self.assertTrue(script.is_file(), 'capture assessment CLI is not implemented')
        cmd = [sys.executable, str(script), str(self.root), '--room', '7', '--out']
        result = subprocess.run(cmd + [str(self.root / 'report.json')], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'report.json').exists())
        out = self.base / 'report.json'
        result = subprocess.run(cmd + [str(out)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        before = out.read_bytes()
        result = subprocess.run(cmd + [str(out)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(out.read_bytes(), before)

    def test_converted_cameras_keep_source_mapping_and_exclude_bad_rows(self):
        self.write('rooms/room-7.json', {'walls': [
            {'identifier': 'wall', 'confidence': {'high': {}},
             'transform': matrix(), 'dimensions': [3, 2.5, 0]}], 'objects': []})
        self.photo(0, room=0)
        self.photo(1, x=0)
        self.photo(2, x=1, transform=[float('nan')] * 16)
        self.photo(3, x=2)
        report = self.assess()
        evidence = self.base / 'evidence.json'
        evidence.write_text(json.dumps(report), encoding='utf-8')
        converted = self.base / 'converted.json'
        cmd = [sys.executable, '-X', 'utf8', str(Path(__file__).with_name('bundle_to_room.py')),
               str(self.root), '--room', '7', '--evidence', str(evidence), '-o', str(converted)]
        result = subprocess.run(cmd, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        photos = json.loads(converted.read_text(encoding='utf-8'))['photos']
        self.assertEqual([p['sourcePhotoIndex'] for p in photos], [1, 3])
        self.assertEqual([p['file'] for p in photos], ['photos/0001.jpg', 'photos/0003.jpg'])
        from prepare_photos import prepare
        self.assertEqual(prepare(self.root, converted, self.base / 'upright'), 2)
        self.assertTrue((self.base / 'upright/0000.jpg').is_file())
        self.assertTrue((self.base / 'upright/0001.jpg').is_file())
        # A stale assessment must never authorize changed metadata/images.
        self.rows[1]['transform'] = matrix(99)
        self.flush()
        stale = self.base / 'stale.json'
        result = subprocess.run(cmd[:-1] + [str(stale)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(stale.exists())


if __name__ == '__main__':
    unittest.main()
