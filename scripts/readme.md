# Scripts

Helper scripts for turning raw WAMIT runs (see
[`data/vessels/readme.md`](../data/vessels/readme.md) for the data layout)
into MSS-toolbox vessel structs and state-space models.

| Script | Purpose |
| --- | --- |
| [`wamit_v7_to_v6.py`](wamit_v7_to_v6.py) | Convert WAMIT v7.x `.pot`/`.frc` control files to v6.x format |
| [`vessel_station_keeping.m`](vessel_station_keeping.m) | Interactive: build `vessel.wamit.json`/`vessel.wamit.abc.json` for a chosen vessel |
| [`voyager_station_keeping.m`](voyager_station_keeping.m) | Same pipeline, hardcoded to the `voyager` vessel |
| `discover_wamit_files.m` | List `outputs/` runs that have a matching `.cfg` (sanity check before processing) |
| `restrict_vessel_for_state_space.m` | Trims `vessel.freqs/A/B/C` so `vessel2ss` accepts them |
| `gdf_dims.m` | Reads `Lpp`/`Boa`/`T_draught` straight out of a `.gdf` mesh file |
| [`fix_frc_mass_matrix.m`](fix_frc_mass_matrix.m) | Corrects `vessel.main.CG`/`vessel.MRB` for vessels under 1000 kg, where `wamit2vessel.m`'s FRC-format auto-detection misfires (see its docstring) |

All the `.m` scripts add the repo root to the MATLAB/Octave path themselves
(`addpath(genpath(base_dir))`), so just `cd` into `scripts/` and run them, or
run from anywhere and give the full path — no manual path setup needed.
Requires the [MSS toolbox](https://github.com/cybergalactic/MSS) submodule
(`git submodule update --init external/MSS`).

## `wamit_v7_to_v6.py`

The MSS toolbox's `wamit2vessel` only understands WAMIT v6.x control-file
syntax, but WAMIT is normally run with v7.x/7.5 `.pot`/`.frc` files. This
script converts those v7 files to v6 format, and also stages the raw
numeric run output so the MSS parsers can read it. Python 3.9+, no
dependencies beyond the standard library.

It does two related but separate jobs:

1. **Convert control files** — rewrite a `.pot`/`.frc` pair from v7 syntax
   to v6 syntax (expands `NPERGROUP`, re-inserts `NEWMDS`, remaps `IOPTN`
   field-pressure/velocity/mean-drift options, etc. — see the docstring at
   the top of the file for the full list of what's handled and what isn't,
   e.g. FRC Alternative form 3 is not supported).
2. **Stage a vessel's outputs** — copy `outputs/*.1/.3/.4/.8/.out` into
   `processed/`, stripping the `NUMHDR=1` banner line WAMIT writes (which
   older MSS parsers choke on), and synthesizing zero-/infinite-frequency
   rows in the `.1` file if WAMIT wasn't run with periods `-1`/`0` (with a
   console warning — this is an approximation, not a real WAMIT solve).

### Usage

Convert one file pair, writing `test01_v6.pot`/`.frc` next to the originals:

```bash
python scripts/wamit_v7_to_v6.py data/vessels/<vessel>/hydro/wamit/inputs/<vessel>.pot \
                                  data/vessels/<vessel>/hydro/wamit/inputs/<vessel>.frc
```

Convert into a separate directory, pulling `NEWMDS`/`IALTFRC`/etc. from the
v7 `.cfg` and writing a v6 `.cfg` snippet for anything that moved between
files:

```bash
python scripts/wamit_v7_to_v6.py *.pot *.frc -o v6_files \
    --cfg test01.cfg --cfg-out test01_v6.cfg
```

**Normal use for this repo** — walk every `data/vessels/*/hydro/wamit/`
folder, convert each vessel's `inputs/*.pot`/`*.frc`, and copy/patch its
`outputs/*` into `processed/`, all in one go:

```bash
python scripts/wamit_v7_to_v6.py --walk
```

Run this (or re-run it after a new WAMIT run) before using
`vessel_station_keeping.m` / `voyager_station_keeping.m`, since those point
`wamit2vessel` at `processed/`, not `outputs/`. `processed/` is generated —
don't hand-edit it, rerun the script instead.

Other useful flags: `--alt {1,2}` forces the FRC alternative form instead
of auto-detecting it; `--newmds`/`--irr` set per-body values explicitly
(comma-separated for multi-body models); `--keep-compact` keeps the
negative NPER/NBETA shorthand instead of expanding it to an explicit list.

## `vessel_station_keeping.m` / `voyager_station_keeping.m`

Turns a vessel's `processed/` WAMIT files into the two JSON artifacts used
downstream for station-keeping / DP analysis:

- `processed/vessel.wamit.json` — full MSS vessel struct from `wamit2vessel`
  (all frequencies, untouched).
- `processed/vessel.wamit.abc.json` — state-space (A/B/C) model from
  `vessel2ss`, fitted after dropping any real frequency above the 10 rad/s
  infinite-frequency stand-in (via `restrict_vessel_for_state_space.m`) —
  needed for model-scale vessels whose period sweep goes above that.

### Running it

Run `wamit_v7_to_v6.py --walk` first so `processed/` is populated, then in
MATLAB/Octave:

```matlab
cd scripts
vessel_station_keeping
```

It prompts:

```text
Enter vessel name:
```

Type the vessel's folder name under `data/vessels/` (e.g. `voyager`,
`enterprise`, `drillship`, `milliAmpere1`). The script then:

1. Looks for `data/vessels/<vessel>/hydro/wamit/mesh/<vessel>.gdf` to read
   `Lpp`/`Boa`/`T_draught` automatically (via `gdf_dims.m`); if the mesh
   file isn't there, it asks for those three dimensions manually.
2. Runs `wamit2vessel` against `processed/<vessel>` and writes
   `vessel.wamit.json`.
3. Fits the state-space model and writes `vessel.wamit.abc.json`.

`voyager_station_keeping.m` is the same script with `vessel_name` hardcoded
to `'voyager'` instead of prompted — use it (or copy it) if you want a
non-interactive script for a specific vessel.
