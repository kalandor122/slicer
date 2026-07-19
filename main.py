import xml.etree.ElementTree as ET
import re
import sys
import csv
import itertools

def tokenize(d):
    tokens = []
    for m in re.finditer(r'([MmLlCcQqAaZzHhVv])|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)', d):
        if m.group(1):
            tokens.append(('c', m.group(1)))
        else:
            tokens.append(('n', float(m.group(2))))
    return tokens

def parse(d):
    tokens = tokenize(d)
    raw = []
    i = 0
    while i < len(tokens):
        if tokens[i][0] != 'c':
            i += 1; continue
        cmd = tokens[i][1]; i += 1
        nums = []
        while i < len(tokens) and tokens[i][0] == 'n':
            nums.append(tokens[i][1]); i += 1

        if cmd in ('M','m'):
            for j in range(0, len(nums), 2):
                if j+1 < len(nums):
                    sub = cmd
                    if (cmd == 'M' and j > 0) or (cmd == 'm' and j > 0):
                        sub = 'L' if cmd == 'M' else 'l'
                    raw.append((sub, nums[j], nums[j+1]))
        elif cmd in ('C','c'):
            for j in range(0, len(nums), 6):
                if j+5 < len(nums):
                    raw.append((cmd, nums[j], nums[j+1], nums[j+2], nums[j+3], nums[j+4], nums[j+5]))
        elif cmd in ('Q','q'):
            for j in range(0, len(nums), 4):
                if j+3 < len(nums):
                    raw.append((cmd, nums[j], nums[j+1], nums[j+2], nums[j+3]))
        elif cmd in ('L','l'):
            for j in range(0, len(nums), 2):
                if j+1 < len(nums):
                    raw.append((cmd, nums[j], nums[j+1]))
        elif cmd in ('V','v'):
            for n in nums:
                raw.append((cmd, n))
        elif cmd in ('H','h'):
            for n in nums:
                raw.append((cmd, n))
        elif cmd in ('Z','z'):
            raw.append((cmd,))
    return raw

def to_abs(cmds):
    out = []
    cx = cy = sx = sy = 0.0
    for c in cmds:
        cmd = c[0]
        if cmd == 'M':
            out.append(('M', c[1], c[2])); cx, cy = c[1], c[2]; sx, sy = cx, cy
        elif cmd == 'm':
            cx += c[1]; cy += c[2]; out.append(('M', cx, cy)); sx, sy = cx, cy
        elif cmd == 'L':
            out.append(('L', cx, cy, c[1], c[2])); cx, cy = c[1], c[2]
        elif cmd == 'l':
            out.append(('L', cx, cy, cx+c[1], cy+c[2])); cx += c[1]; cy += c[2]
        elif cmd == 'V':
            out.append(('L', cx, cy, cx, c[1])); cy = c[1]
        elif cmd == 'v':
            out.append(('L', cx, cy, cx, cy+c[1])); cy += c[1]
        elif cmd == 'H':
            out.append(('L', cx, cy, c[1], cy)); cx = c[1]
        elif cmd == 'h':
            out.append(('L', cx, cy, cx+c[1], cy)); cx += c[1]
        elif cmd == 'C':
            out.append(('C', cx, cy, c[1], c[2], c[3], c[4], c[5], c[6])); cx, cy = c[5], c[6]
        elif cmd == 'c':
            out.append(('C', cx, cy, cx+c[1], cy+c[2], cx+c[3], cy+c[4], cx+c[5], cy+c[6]))
            cx += c[5]; cy += c[6]
        elif cmd == 'Q':
            out.append(('Q', cx, cy, c[1], c[2], c[3], c[4])); cx, cy = c[3], c[4]
        elif cmd == 'q':
            out.append(('Q', cx, cy, cx+c[1], cy+c[2], cx+c[3], cy+c[4]))
            cx += c[3]; cy += c[4]
        elif cmd in ('Z','z'):
            if abs(cx - sx) > 1e-10 or abs(cy - sy) > 1e-10:
                out.append(('L', cx, cy, sx, sy))
            cx, cy = sx, sy
    return out

def flip_y(cmds, height):
    flipped = []
    for c in cmds:
        if c[0] == 'M':
            flipped.append(('M', c[1], height - c[2]))
        elif c[0] == 'L':
            flipped.append(('L', c[1], height - c[2], c[3], height - c[4]))
        elif c[0] == 'C':
            flipped.append(('C', c[1], height - c[2], c[3], height - c[4], c[5], height - c[6], c[7], height - c[8]))
        elif c[0] == 'Q':
            flipped.append(('Q', c[1], height - c[2], c[3], height - c[4], c[5], height - c[6]))
    return flipped

def desmos_poly(coeffs, var='t'):
    terms = []
    for i, c in enumerate(coeffs):
        c = round(c, 4)
        if abs(c) < 1e-10:
            continue
        power = len(coeffs) - 1 - i
        ac = abs(c)
        if not terms:
            sig = '-' if c < 0 else ''
        else:
            sig = ' - ' if c < 0 else ' + '
        if power == 0:
            mag = f"{ac}"
        elif power == 1:
            mag = var if abs(ac - 1) < 1e-10 else f"{ac}{var}"
        else:
            mag = f"{var}^{power}" if abs(ac - 1) < 1e-10 else f"{ac}{var}^{power}"
        terms.append(sig + mag)
    return ''.join(terms) if terms else '0'

def desmos_expr(cmd):
    c = cmd[0]
    if c == 'C':
        _, p0x, p0y, p1x, p1y, p2x, p2y, p3x, p3y = cmd
        ax = -p0x + 3*p1x - 3*p2x + p3x; bx = 3*p0x - 6*p1x + 3*p2x
        cx = -3*p0x + 3*p1x; dx = p0x
        ay = -p0y + 3*p1y - 3*p2y + p3y; by = 3*p0y - 6*p1y + 3*p2y
        cy = -3*p0y + 3*p1y; dy = p0y
        return f"({desmos_poly([ax,bx,cx,dx])}, {desmos_poly([ay,by,cy,dy])})"
    elif c == 'Q':
        _, p0x, p0y, p1x, p1y, p2x, p2y = cmd
        ax = p0x - 2*p1x + p2x; bx = -2*p0x + 2*p1x; cx = p0x
        ay = p0y - 2*p1y + p2y; by = -2*p0y + 2*p1y; cy = p0y
        return f"({desmos_poly([ax,bx,cx])}, {desmos_poly([ay,by,cy])})"
    elif c == 'L':
        _, p0x, p0y, p1x, p1y = cmd
        return f"({desmos_poly([p1x-p0x, p0x])}, {desmos_poly([p1y-p0y, p0y])})"
    return None

def eval_seg(seg, t):
    if seg[0] == 'C':
        _, x0, y0, x1, y1, x2, y2, x3, y3 = seg
        mt = 1 - t
        x = mt**3 * x0 + 3 * mt**2 * t * x1 + 3 * mt * t**2 * x2 + t**3 * x3
        y = mt**3 * y0 + 3 * mt**2 * t * y1 + 3 * mt * t**2 * y2 + t**3 * y3
        return (x, y)
    if seg[0] == 'Q':
        _, x0, y0, x1, y1, x2, y2 = seg
        mt = 1 - t
        x = mt**2 * x0 + 2 * mt * t * x1 + t**2 * x2
        y = mt**2 * y0 + 2 * mt * t * y1 + t**2 * y2
        return (x, y)
    if seg[0] == 'L':
        _, x0, y0, x1, y1 = seg
        return (x0 + t * (x1 - x0), y0 + t * (y1 - y0))
    return None

def sample_seg(seg, n):
    return [eval_seg(seg, t) for t in (i / (n - 1) for i in range(n))]

def to_gcode(all_cmds, n_pts=10, z_up=5.0, z_down=0.0):
    lines = ['G21', 'G90']
    lines.append(f'G00 Z{z_up:.3f}')
    for cmds in all_cmds:
        segs = [s for s in cmds if s[0] in ('C','Q','L')]
        for si, seg in enumerate(segs):
            pts = sample_seg(seg, n_pts)
            if si == 0:
                lines.append(f'G00 X{pts[0][0]:.3f} Y{pts[0][1]:.3f}')
            else:
                lines.append(f'G00 X{pts[0][0]:.3f} Y{pts[0][1]:.3f}')
            lines.append(f'G00 Z{z_down:.3f}')
            for pt in pts[1:]:
                lines.append(f'G00 X{pt[0]:.3f} Y{pt[1]:.3f}')
            lines.append(f'G00 Z{z_up:.3f}')
    return lines

def parse_viewbox(vb):
    if not vb:
        return None
    parts = [float(x) for x in vb.strip().split()]
    return tuple(parts) if len(parts) == 4 else None

def extract(path, csv_path=None, gcode_path=None, n_pts=10, z_up=5.0, z_down=0.0):
    tree = ET.parse(path)
    root = tree.getroot()

    paths = root.findall('.//{http://www.w3.org/2000/svg}path')
    if not paths:
        paths = root.findall('.//path')

    vb = parse_viewbox(root.get('viewBox'))
    height = vb[1] + vb[3] if vb else None

    # Collect all segments across all paths
    all_cmds = []
    for path_el in paths:
        d = path_el.get('d', '')
        cmds = to_abs(parse(d))
        if height:
            cmds = flip_y(cmds, height)
        all_cmds.append(cmds)

    if gcode_path:
        lines = to_gcode(all_cmds, n_pts, z_up, z_down)
        with open(gcode_path, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        seg_count = sum(len([s for s in c if s[0] in ('C','Q','L')]) for c in all_cmds)
        print(f"Wrote {seg_count} segments ({seg_count * n_pts} points) to {gcode_path}")
        return

    if csv_path:
        with open(csv_path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['path', 'segment', 't', 'x', 'y'])
            for pi, cmds in enumerate(all_cmds):
                si = 0
                for seg in cmds:
                    if seg[0] not in ('C','Q','L'):
                        continue
                    for ti, pt in enumerate(sample_seg(seg, n_pts)):
                        w.writerow([pi + 1, si + 1, round(ti / (n_pts - 1), 6) if n_pts > 1 else 0,
                                    round(pt[0], 6), round(pt[1], 6)])
                    si += 1
        print(f"Wrote {sum(len([s for s in c if s[0] in ('C','Q','L')]) for c in all_cmds) * n_pts} points to {csv_path}")
        return

    # Default: print Desmos expressions
    print(f"Desmos expressions for: {path}")
    if vb:
        print(f"viewBox: {vb[0]} {vb[1]} {vb[2]} {vb[3]} (Y flipped for Cartesian)")
    else:
        print(f"viewBox: unknown")
    print(f"Paste the lines below into Desmos and set slider t from 0 to 1")
    print("-" * 60)

    for cmds in all_cmds:
        for seg in cmds:
            if seg[0] in ('C','Q','L'):
                expr = desmos_expr(seg)
                if expr:
                    print(expr)

    if not paths:
        print("No <path> elements found.")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Extract SVG curve equations or point samples')
    parser.add_argument('svg', nargs='?', default='smile.svg', help='SVG file path')
    parser.add_argument('--csv', help='Output CSV file path (samples points along curves)')
    parser.add_argument('--gcode', help='Output G-code file path (plotter moves from sampled points)')
    parser.add_argument('--n', type=int, default=10, help='Number of points per segment (default 10)')
    parser.add_argument('--z-up', type=float, default=5.0, help='Z lift height in mm (default 5.0)')
    parser.add_argument('--z-down', type=float, default=0.0, help='Z pen-down height in mm (default 0.0)')
    args = parser.parse_args()
    extract(args.svg, csv_path=args.csv, gcode_path=args.gcode, n_pts=args.n, z_up=args.z_up, z_down=args.z_down)
