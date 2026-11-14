#!/usr/bin/env python3
"""Read one extracted house-capture/5 session; select posed reference photos.

Never alters inputs, estimates missing poses, or aligns sessions. Image metrics
rank references; they do not certify reconstruction fidelity or room coverage.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path, PureWindowsPath
import sys

from PIL import Image, ImageFilter, ImageStat, UnidentifiedImageError

from house_to_rooms import rigid


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def source_path(root, relative):
    if (not isinstance(relative, str) or not relative or '\\' in relative
            or ':' in relative or Path(relative).is_absolute()
            or PureWindowsPath(relative).drive):
        raise ValueError('invalid relative source path')
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('source path escapes bundle')
    if not path.is_file():
        raise ValueError('source file is missing')
    return path


def read_json(root, relative):
    path = source_path(root, relative)
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def layout_evidence(root, room):
    result = {'status': 'unmeasured', 'walls': 0, 'reason': 'no room layout exported'}
    if not room.get('file'):
        return result
    try:
        path = source_path(root, room['file'])
        data = read_json(root, room['file'])
        if not isinstance(data, dict) or not isinstance(data.get('walls'), list):
            raise ValueError('room layout must contain a wall list')
        for wall in data['walls']:
            if not isinstance(wall, dict):
                raise ValueError('invalid wall record')
            rigid(wall.get('transform'))
            dims = wall.get('dimensions')
            if (not isinstance(dims, list) or len(dims) != 3
                    or not all(finite(v) for v in dims)
                    or dims[0] <= 0 or dims[1] <= 0 or dims[2] < 0):
                raise ValueError('invalid wall dimensions')
        result.update(file=room['file'], sha256=digest(path), walls=len(data['walls']))
        if data['walls']:
            result.update(status='measured', reason='reported RoomPlan measurements; accuracy not verified')
    except (ValueError, OSError, TypeError) as error:
        result.update(status='invalid', reason=str(error))
    return result


def photo_evidence(root, row, index):
    if not isinstance(row, dict):
        raise ValueError('invalid photo record')
    path = source_path(root, row.get('file'))
    pose = rigid(row.get('transform'))
    width, height = row.get('width'), row.get('height')
    if any(type(v) is not int or v < 3 for v in (width, height)):
        raise ValueError('missing or invalid image dimensions')
    k = row.get('intrinsics')
    if not isinstance(k, list) or len(k) != 9 or not all(finite(v) for v in k):
        raise ValueError('missing or non-finite intrinsics')
    if (k[0] <= 0 or k[4] <= 0 or not 0 <= k[6] < width or not 0 <= k[7] < height
            or any(abs(k[i]) > 1e-4 for i in (1, 2, 3, 5)) or abs(k[8] - 1) > 1e-4):
        raise ValueError('invalid camera intrinsics')
    tracking = row.get('tracking')
    if tracking is not None and tracking != 'normal':
        raise ValueError('tracking was not normal')
    unknown = []
    if tracking is None:
        unknown.append('tracking')
    blur = row.get('blurPixels')
    if blur is not None and (not finite(blur) or blur < 0):
        raise ValueError('invalid motion blur estimate')
    blur1920 = None if blur is None else blur * 1920 / width
    if blur1920 is not None and blur1920 > 6:
        raise ValueError('estimated motion blur exceeds 6 pixels at width 1920')
    if blur is None:
        unknown.append('motion-blur')
    exposure = row.get('exposure')
    if exposure is not None and (not finite(exposure) or exposure <= 0):
        raise ValueError('invalid exposure metadata')
    if exposure is None:
        unknown.append('exposure')
    with Image.open(path) as image:
        image.load()
        if image.size != (width, height):
            raise ValueError('raw sensor pixel dimensions disagree with camera intrinsics')
        orientation = image.getexif().get(274, 1)
        if orientation not in range(1, 9):
            raise ValueError('invalid EXIF orientation')
        # Do not transpose by EXIF: poses/intrinsics refer to unrotated pixels.
        pixels = image.convert('RGB')
        pixel_hash = hashlib.sha256(f'{width}x{height}:'.encode() + pixels.tobytes()).hexdigest()
        gray = pixels.convert('L')
        gray.thumbnail((256, 256))
        histogram = gray.histogram()
        clipped = (sum(histogram[:9]) + sum(histogram[247:])) / sum(histogram)
        if clipped > 0.98:
            raise ValueError('almost all image pixels are black or white clipped')
        edges = gray.filter(ImageFilter.FIND_EDGES).crop((1, 1, gray.width-1, gray.height-1))
        contrast = ImageStat.Stat(edges).stddev[0]
    score = (1 - clipped) * (1 / (1 + (blur1920 or 0))) + min(contrast / 64, 1) * 0.25
    if unknown:
        score *= 0.85
    return {'photoIndex': index, 'file': row['file'], 'sha256': digest(path),
            'pixelSha256': pixel_hash, 'position': [pose[i][3] for i in range(3)],
            'forward': [-pose[i][2] for i in range(3)], 'transform': row['transform'],
            'intrinsics': k, 'width': width, 'height': height, 'exifOrientation': orientation,
            'blurAt1920': blur1920, 'clippedFraction': round(clipped, 5),
            'edgeContrast': round(contrast, 4), 'unknownQualitySignals': unknown,
            'qualityRank': round(score, 6)}


def view_difference(a, b):
    distance = math.dist(a['position'], b['position'])
    cosine = max(-1, min(1, sum(x*y for x, y in zip(a['forward'], b['forward']))))
    angle = math.acos(cosine)
    return distance, angle


def select_views(candidates, maximum):
    """Prefer distinct camera positions/directions, retaining original photo indices."""
    remaining = sorted(candidates, key=lambda p: (-p['qualityRank'], p['photoIndex']))
    selected, excluded, hashes = [], [], set()
    unique = []
    for p in remaining:
        if p['pixelSha256'] in hashes:
            excluded.append({'photoIndex': p['photoIndex'], 'file': p['file'], 'reason': 'duplicate decoded pixels'})
        else:
            hashes.add(p['pixelSha256'])
            unique.append(p)
    remaining = unique
    while remaining and len(selected) < maximum:
        if selected:
            unique = []
            for p in remaining:
                if any(d < 0.12 and a < math.radians(10)
                       for d, a in (view_difference(p, q) for q in selected)):
                    excluded.append({'photoIndex': p['photoIndex'], 'file': p['file'], 'reason': 'redundant camera viewpoint'})
                else:
                    unique.append(p)
            remaining = unique
            if not remaining:
                break
            def priority(p):
                novelty = min(min(d / 0.5, 2) + min(a / math.radians(30), 2)
                              for d, a in (view_difference(p, q) for q in selected))
                return (novelty + p['qualityRank'] * 0.25, -p['photoIndex'])
            winner = max(remaining, key=priority)
            remaining.remove(winner)
        else:
            winner = remaining.pop(0)
        winner['selectionRank'] = len(selected)
        selected.append(winner)
    excluded.extend({'photoIndex': p['photoIndex'], 'file': p['file'], 'reason': 'reference selection budget'} for p in remaining)
    return sorted(selected, key=lambda p: p['photoIndex']), excluded


def assess_bundle(bundle: Path, room: int, max_photos: int = 24) -> dict:
    if type(max_photos) is not int or max_photos <= 0:
        raise ValueError('max_photos must be a positive integer')
    if type(room) is not int or room < 0:
        raise ValueError('room must be an explicit nonnegative index')
    root = Path(bundle).resolve()
    manifest = read_json(root, 'manifest.json')
    if not isinstance(manifest, dict) or manifest.get('format') != 'house-capture/5':
        raise ValueError('expected a single extracted house-capture/5 session, not a house or JPG folder')
    rooms = manifest.get('rooms')
    if not isinstance(rooms, list) or not all(isinstance(r, dict) and type(r.get('index')) is int for r in rooms):
        raise ValueError('manifest must contain indexed rooms')
    indices = [r['index'] for r in rooms]
    if len(set(indices)) != len(indices):
        raise ValueError('duplicate room indices in one session')
    if room not in indices:
        raise ValueError('requested room index is not in this session')
    room_record = next(r for r in rooms if r['index'] == room)
    photo_index = manifest.get('photos', 'photos/photos.json')
    rows = read_json(root, photo_index)
    if not isinstance(rows, list):
        raise ValueError('photo index must be an array')
    warnings = []
    if manifest.get('photoCount') != len(rows):
        warnings.append('manifest photoCount differs from photo metadata length')
    alignment = manifest.get('alignment')
    method = alignment.get('method', 'unknown') if isinstance(alignment, dict) else 'unknown'
    if not isinstance(method, str):
        method = 'unknown'
    if method not in ('first', 'relocalized', 'manual', 'icp'):
        warnings.append('session is unaligned or alignment is unknown; never merge it by room name')
    if isinstance(alignment, dict) and alignment.get('toZone') is not None:
        try:
            rigid(alignment['toZone'])
        except ValueError:
            warnings.append('session-to-zone transform is invalid; use only session-local evidence')
    layout = layout_evidence(root, room_record)
    candidates, excluded = [], []
    invalid_count = 0
    ignored_other_rooms = 0
    for index, row in enumerate(rows):
        if isinstance(row, dict) and type(row.get('room')) is int and row['room'] != room:
            ignored_other_rooms += 1
            continue
        try:
            if not isinstance(row, dict) or type(row.get('room')) is not int:
                raise ValueError('photo has no explicit room index')
            candidates.append(photo_evidence(root, row, index))
        except (ValueError, OSError, TypeError, UnidentifiedImageError, Image.DecompressionBombError) as error:
            excluded.append({'photoIndex': index, 'file': row.get('file') if isinstance(row, dict) and isinstance(row.get('file'), str) else None,
                             'reason': str(error)})
            invalid_count += 1
    selected, redundant = select_views(candidates, max_photos)
    excluded.extend(redundant)
    if any(p['unknownQualitySignals'] for p in selected):
        warnings.append('some selected photos have unknown quality signals; visually inspect them')
    diagnostics = {'status': 'missing'}
    if (root / 'diagnostics.json').exists():
        try:
            data = read_json(root, 'diagnostics.json')
            if not isinstance(data, dict):
                raise ValueError('diagnostics must be an object')
            diagnostics = {'status': 'available', 'file': 'diagnostics.json',
                           'sha256': digest(source_path(root, 'diagnostics.json')),
                           'note': 'Inspect tracking, world jumps, failures and thermal events; no root cause inferred.'}
        except (ValueError, OSError) as error:
            diagnostics = {'status': 'invalid', 'reason': str(error)}
            warnings.append('diagnostics file could not be read')
    status = 'blocked' if not selected else ('partial' if invalid_count or layout['status'] != 'measured' else 'ready-for-review')
    return {'format': 'personal-room-evidence/1', 'status': status,
            'source': str(root), 'manifestSha256': digest(root / 'manifest.json'),
            'photoIndexFile': photo_index, 'photoIndexSha256': digest(source_path(root, photo_index)),
            'room': room, 'session': str(manifest.get('session', 'unknown')),
            'alignment': {'scope': 'session-only', 'method': method, 'housePlacementVerified': False},
            'layout': layout, 'diagnostics': diagnostics, 'maxReferences': max_photos,
            'inputPhotoCount': len(rows), 'ignoredOtherRooms': ignored_other_rooms,
            'selected': selected, 'excluded': sorted(excluded, key=lambda p: p['photoIndex']),
            'warnings': warnings,
            'limitations': ['Selection is not proof of room coverage or successful reconstruction.',
                            'Image contrast ranks texture; it does not prove sharpness or geometric accuracy.',
                            'All positions are session-local; house placement requires separate validation.',
                            'Use original sensor pixels with intrinsics; EXIF is for display only.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--room', type=int, required=True)
    parser.add_argument('--max-photos', type=int, default=24)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        root, out = args.bundle.resolve(), args.out.resolve()
        if out.is_relative_to(root):
            raise ValueError('write the report outside the input bundle to preserve original evidence')
        if out.exists():
            raise ValueError('report already exists; choose a new output path')
        report = assess_bundle(root, args.room, args.max_photos)
        payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('x', encoding='utf-8') as stream:
            stream.write(payload)
        print(f"{report['status']}: {len(report['selected'])} references; {len(report['excluded'])} excluded. Report: {out}")
        return 2 if report['status'] == 'blocked' else 0
    except (ValueError, OSError) as error:
        print(f'Assessment failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
