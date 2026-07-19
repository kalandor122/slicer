# slicer

Convert SVG path data into parametric equations, point samples, or plotter G-code.

Zero external dependencies — only Python's standard library.

## Usage

```bash
python main.py input.svg              # Desmos-ready parametric equations
python main.py input.svg --csv out.csv # Sampled points as CSV
python main.py input.svg --gcode out.gcode # Plotter G-code
```

### Arguments

| Argument | Default | Description |
|---|---|---|
| `svg` | `smile.svg` | Input SVG file |
| `--n` | `10` | Points sampled per curve segment |
| `--csv` | — | Write point samples to CSV file |
| `--gcode` | — | Write plotter G-code to file |
| `--z-up` | `5.0` | Pen-up Z height (mm) |
| `--z-down` | `0.0` | Pen-down Z height (mm) |

## Output modes

### 1. Desmos expressions (default)

Prints copy-paste parametric equations for each curve segment:

```text
(-0.26t^3 - 0.6429t^2 + 1.2918t + 14.9348, 0.4338t^3 - 0.9705t^2 - 0.5163t + 10.8275)
(0.3432t^3 - 1.3432t^2 + 10.0, -0.3432t^3 - 0.3137t^2 + 1.6568t + 15.0)
```

Set slider `t` from `0` to `1` in Desmos.

### 2. CSV (`--csv`)

Samples each segment at `n` evenly-spaced parameter values:

```csv
path,segment,t,x,y
1,1,0.0,14.9348,10.8275
1,1,0.0526,15.0010,10.7977
```

Columns: `path` (1-based per `<path>` element), `segment` (1-based per curve), `t` (parameter value), `x`, `y` (Cartesian coordinates, Y-flipped).

### 3. G-code (`--gcode`)

Generates plotter G-code with pen-up/down Z moves between segments:

```gcode
G21
G90
G00 Z5.000
G00 X14.935 Y10.828
G00 Z0.000
G00 X15.001 Y10.798
G00 X15.063 Y10.763
...
G00 Z5.000
```

- Raises Z to `--z-up` between segments (pen up)
- Lowers Z to `--z-down` at segment starts (pen down)
- All moves use `G00` (rapid — no feedrate specified)
- Coordinates in mm

## How it works

1. **Parse** — tokenizes the SVG `d` attribute into path commands (`M`, `C`, `Q`, `L`, `V`, `H`, `Z`)
2. **Resolve** — converts relative commands to absolute, resolves `Z` closes
3. **Flip Y** — negates Y coordinates (SVG Y-down → Cartesian Y-up)
4. **Convert** — each cubic bezier (`C`), quadratic (`Q`), or line (`L`) is converted to expanded polynomial form or sampled at `n` points

## Point sampling flow

When `--csv` or `--gcode` is used, each curve segment is sampled at `n` evenly-spaced values of the parameter `t` ∈ [0, 1]:

```
for each <path> element in the SVG:
    parse d attribute into raw commands
    resolve relative -> absolute coordinates
    flip Y (height - y)
    group into subpaths

    for each subpath:
        for each curve segment (C, Q, L):
            for i in 0 .. n-1:
                t = i / (n - 1)
                compute P(t) using the segment's formula
                store (path_id, segment_id, t, x, y)
```

### Evaluation formulas

Each segment type is evaluated at `t` using its parametric form:

**Cubic bezier** (`C`)
```
P(t) = (1-t)³·P0 + 3(1-t)²·t·P1 + 3(1-t)·t²·P2 + t³·P3
```

**Quadratic bezier** (`Q`)
```
P(t) = (1-t)²·P0 + 2(1-t)·t·P1 + t²·P2
```

**Line** (`L`)
```
P(t) = P0 + t·(P1 - P0)
```

The first point of a segment (t=0) overlaps the last point of the previous segment (t=1), ensuring continuous paths. Between segments the pen lifts (G-code mode) or a new segment starts (CSV mode).

## Example

```bash
python main.py smile.svg --gcode smile.gcode --n 20
```

The included `smile.svg` produces 32 curve segments. Sampled at 20 points each:

![smile.svg](smile.svg)
