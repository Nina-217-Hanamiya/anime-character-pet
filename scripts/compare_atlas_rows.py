"""Compare complete decoded atlas rows; does not alter either image."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image


def compare(args):
    if args.cell_height <= 0:
        raise ValueError('Cell height must be positive')
    with Image.open(args.before) as first, Image.open(args.after) as second:
        before, after = first.convert('RGBA'), second.convert('RGBA')
    if before.size != after.size:
        raise ValueError('Atlas dimensions differ')
    width, height = before.size
    if height % args.cell_height:
        raise ValueError('Atlas height is not a multiple of cell height')
    rows = []
    for row in dict.fromkeys(args.rows):
        if row < 0 or (row + 1) * args.cell_height > height:
            raise ValueError(f'Row {row} outside atlas')
        box = (0, row * args.cell_height, width, (row + 1) * args.cell_height)
        a, b = before.crop(box).tobytes(), after.crop(box).tobytes()
        differences = sum(a[i:i + 4] != b[i:i + 4] for i in range(0, len(a), 4))
        rows.append({'row': row, 'decoded_rgba_equal': differences == 0,
                     'different_pixels': differences})
    return {'ok': all(r['decoded_rgba_equal'] for r in rows),
            'dimensions': [width, height], 'cell_height': args.cell_height, 'rows': rows,
            'before_sha256': hashlib.sha256(Path(args.before).read_bytes()).hexdigest(),
            'after_sha256': hashlib.sha256(Path(args.after).read_bytes()).hexdigest(),
            'boundary': 'Decoded row equality only; changed rows and live playback require separate review.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', required=True)
    parser.add_argument('--after', required=True)
    parser.add_argument('--rows', type=int, nargs='+', required=True)
    parser.add_argument('--cell-height', type=int, default=208)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        report = compare(args)
    except (OSError, ValueError) as error:
        report = {'ok': False, 'errors': [str(error)]}
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
