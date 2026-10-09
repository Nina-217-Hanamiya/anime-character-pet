"""Diagnose fixed eye anchors from renderer evidence; not a visual quality gate."""
import argparse
import json
import math
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def finite(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError('Non-finite geometry')
    return value


def point(value):
    if len(value) != 2:
        raise ValueError('Expected a two-coordinate point')
    return tuple(finite(v) for v in value)


def head_points(frame):
    h = {k: finite(frame['head'][k]) for k in ('a', 'b', 'c', 'd', 'worldX', 'worldY')}
    determinant = h['a'] * h['d'] - h['b'] * h['c']
    if abs(determinant) < 1e-12:
        raise ValueError('Singular head transform')
    result = {}
    for eye in frame['eyes']:
        side = str(eye['side'])
        if side in result:
            raise ValueError('Duplicate eye side')
        x = finite(eye['world']['x']) - h['worldX']
        y = finite(eye['world']['y']) - h['worldY']
        result[side] = ((h['d'] * x - h['b'] * y) / determinant,
                        (-h['c'] * x + h['a'] * y) / determinant)
    if not result:
        raise ValueError('No eye anchors')
    return result


def inspect(args):
    raw = read(args.input)
    data = raw['frames'] if isinstance(raw, dict) else raw
    if not isinstance(data, list) or not data:
        raise ValueError('Expected nonempty frames list')
    frames = [f for f in data if (f.get('state') or f.get('frame', {}).get('state')) not in args.exclude_state]
    if not frames:
        raise ValueError('No included frames')
    threshold = args.threshold if args.threshold is not None else (.001 if args.mode == 'spine' else .2)
    if not math.isfinite(threshold) or threshold < 0:
        raise ValueError('Threshold must be finite and nonnegative')
    errors, records = [], []
    if args.mode == 'spine':
        reference = head_points(frames[args.reference_index])
        source = {b['name']: b for b in read(args.skeleton)['bones']} if args.skeleton else None
        for frame in frames:
            anchors = head_points(frame)
            if anchors.keys() != reference.keys():
                raise ValueError('Eye-side set differs from reference')
            distances = {side: math.dist(pos, reference[side]) for side, pos in anchors.items()}
            maximum = max(distances.values())
            label = f"{frame.get('state')}:{frame.get('index')}"
            if maximum > threshold:
                errors.append(f'{label}: eye anchor drift {maximum:.6g} exceeds {threshold}')
            if source is not None:
                for eye in frame['eyes']:
                    original = source['eye_' + str(eye['side'])]
                    for key in ('x', 'y', 'rotation', 'scaleX'):
                        expected = finite(original.get(key, 1 if key == 'scaleX' else 0))
                        actual = finite(eye['bone'][key])
                        delta = abs((actual - expected + 180) % 360 - 180) if key == 'rotation' else abs(actual - expected)
                        if delta > 1e-6:
                            errors.append(f'{label}/{eye["side"]}: source local {key} changed')
            records.append({'state': frame.get('state'), 'index': frame.get('index'),
                            'eye_anchors_in_head': anchors, 'maximum_delta': maximum})
    else:
        widths, centers = {}, {}
        for frame in frames:
            side = str(frame['side'])
            expected = point(frame['source_center'])
            actual = point(frame['rendered_center_before_head_motion'])
            width = finite(frame['width'])
            if width <= 0:
                raise ValueError('Eye patch width must be positive')
            widths.setdefault(side, width)
            centers.setdefault(side, expected)
            label = f'{frame.get("frame")}/{side}'
            maximum = math.dist(actual, expected)
            if centers[side] != expected:
                errors.append(f'{label}: source center changed within evidence')
            if maximum > threshold:
                errors.append(f'{label}: eye patch center drift {maximum:.6g} exceeds {threshold}')
            if abs(width - widths[side]) > 1e-6:
                errors.append(f'{label}: eye patch width changed')
            if any(abs(v) > 1e-6 for v in point(frame['iris_offset'])):
                errors.append(f'{label}: separate iris translation')
            records.append({'frame': frame.get('frame'), 'side': side, 'maximum_delta': maximum,
                            'center': actual, 'width': width, 'opening': frame.get('opening')})
    return {'ok': not errors, 'mode': args.mode, 'threshold': threshold,
            'units': 'source skeleton units' if args.mode == 'spine' else 'source image pixels',
            'maximum_delta': max(r['maximum_delta'] for r in records),
            'errors': errors, 'frames': records,
            'boundary': 'Fixed-anchor diagnostics only; inspect final pixels, expressions and app playback separately.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['spine', 'patches'], required=True)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--skeleton')
    parser.add_argument('--threshold', type=float)
    parser.add_argument('--reference-index', type=int, default=0)
    parser.add_argument('--exclude-state', action='append', default=['look'])
    args = parser.parse_args()
    try:
        if args.reference_index < 0:
            raise ValueError('Reference index must be nonnegative')
        if args.skeleton and args.mode != 'spine':
            raise ValueError('--skeleton applies only to spine mode')
        report = inspect(args)
    except (OSError, KeyError, IndexError, TypeError, ValueError) as error:
        report = {'ok': False, 'mode': args.mode, 'errors': [str(error)]}
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'frames'}, ensure_ascii=False))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
