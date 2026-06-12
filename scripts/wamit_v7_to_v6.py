#!/usr/bin/env python3
"""
wamit75_to_v6.py
================
Convert WAMIT v7.x (incl. 7.5) POT and FRC control files to WAMIT v6.x format.

What it handles
---------------
POT files:
  * Expands the v7.1+ "NPERGROUP = m" multi-group period definition into a
    single flat period list (not supported in v6).
  * Optionally expands negative NPER / NBETA (uniform-increment shorthand)
    into explicit lists (--expand, on by default for maximum v6 compatibility;
    use --keep-compact to keep the +/- shorthand, which v6.2+ also accepts).
  * Re-inserts the per-body NEWMDS line required by the v6 POT format
    (removed from the POT file in v7; value taken from --newmds, from a v7
    CFG file given with --cfg, or 0 by default).
  * Optionally appends IRR to the XBODY line (v6 style) via --irr / --cfg.

FRC files (Alternative forms 1 and 2, auto-detected or forced with --alt):
  * Remaps the IOPTN array to v6 numbering:
      v7 IOPTN(6) (field pressure AND velocity, values 0..3 / -3..0)
         -> v6 IOPTN(6) (field pressure only)  and  v6 IOPTN(7) (field velocity)
      v7 IOPTN(7) (mean drift from control surface)
         -> no IOPTN slot in v6; the script warns and (with --cfg-out) writes
            ICTRSURF=1 into a v6 CFG snippet.
      v7 IOPTN(8), IOPTN(9) -> unchanged (momentum / pressure drift).
  * Optionally expands negative NBETAH shorthand.
  * Passes through everything after a negative NFIELD verbatim with a warning
    (uniform field-point arrays; check your v6 version supports them).

Also writes (with --cfg-out FILE) a v6 CFG snippet collecting the settings
that moved between CFG and control files (IALTFRC, ICTRSURF, NEWMDS, IRR,
IPERIN -> IPERIO note).

Usage
-----
    python wamit75_to_v6.py test01.pot test01.frc
    python wamit75_to_v6.py *.pot *.frc -o v6_files --cfg test01.cfg --cfg-out test01_v6.cfg
    python wamit75_to_v6.py body.frc --alt 2
    python wamit75_to_v6.py model.pot --newmds 4,0   (per-body NEWMDS values)

Output files are named <name>_v6.pot / <name>_v6.frc unless -o DIR is given,
in which case the original names are kept inside DIR.

Limitations
-----------
* FRC Alternative form 3 (separate per-body FRC files, IALTFRC=3) is not
  converted automatically; convert each per-body file with --alt 1/2.
* External force files / .rao / .dmp inputs are v7 features with no v6
  equivalent; the script does not touch them.
* Always check the generated files against the v6 manual before running.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def warn(msg: str) -> None:
    print(f"WARNING: {msg}", file=sys.stderr)


def info(msg: str) -> None:
    print(f"  {msg}", file=sys.stderr)


def fmt(x: float) -> str:
    """Format a real number the WAMIT-friendly way (always with a decimal point)."""
    if x == int(x) and abs(x) < 1e15:
        return f"{x:.1f}"
    s = f"{x:.6g}"
    if "." not in s and "e" not in s and "E" not in s:
        s += "."
    return s


def chunk(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


class TokenStream:
    """Free-format token reader that can also hand back whole raw lines
    (needed for the GDF filename lines, which are not numeric tokens)."""

    def __init__(self, lines: list[str]):
        self.lines = lines          # raw lines (header already stripped off)
        self.iline = 0              # current line index
        self.tokens: list[str] = [] # tokens remaining on the current line

    def _fill(self) -> bool:
        while not self.tokens:
            if self.iline >= len(self.lines):
                return False
            self.tokens = self.lines[self.iline].split()
            self.iline += 1
        return True

    def eof(self) -> bool:
        return not self._fill()

    def peek(self) -> str | None:
        return self.tokens[0] if self._fill() else None

    def next_token(self) -> str:
        if not self._fill():
            raise ValueError("unexpected end of file")
        return self.tokens.pop(0)

    def next_int(self, name: str) -> int:
        t = self.next_token()
        try:
            return int(float(t))
        except ValueError:
            raise ValueError(f"expected integer for {name}, got '{t}'")

    def next_float(self, name: str) -> float:
        t = self.next_token()
        try:
            return float(t)
        except ValueError:
            raise ValueError(f"expected number for {name}, got '{t}'")

    def end_record(self) -> None:
        """Discard the rest of the current line (trailing comment labels),
        mimicking a Fortran list-directed READ ending mid-line."""
        self.tokens = []

    def peek_is_number(self) -> bool:
        t = self.peek()
        if t is None:
            return False
        try:
            float(t)
            return True
        except ValueError:
            return False

    def next_line(self) -> str:
        """Return the rest of the current line if mid-line, else the next
        non-blank raw line (for filename fields like GDF)."""
        if self.tokens:
            s = " ".join(self.tokens)
            self.tokens = []
            return s
        while self.iline < len(self.lines):
            line = self.lines[self.iline].strip()
            self.iline += 1
            if line:
                return line
        raise ValueError("unexpected end of file while reading a filename line")

    def remaining_raw(self) -> list[str]:
        out = []
        if self.tokens:
            out.append(" ".join(self.tokens))
            self.tokens = []
        out.extend(self.lines[self.iline:])
        self.iline = len(self.lines)
        return out


def read_file(path: str) -> tuple[str, TokenStream]:
    with open(path, "r", errors="replace") as f:
        raw = f.read().splitlines()
    if not raw:
        raise ValueError(f"{path} is empty")
    header = raw[0].rstrip()
    return header, TokenStream(raw[1:])


def contains_numbers(text: str) -> bool:
    for t in text.split():
        try:
            float(t)
            return True
        except ValueError:
            pass
    return False


# --------------------------------------------------------------------------
# v7 CFG scanning (only to recover NEWMDS / IRR / IPERIN / IALTFRC)
# --------------------------------------------------------------------------

def scan_cfg(path: str) -> dict:
    """Very tolerant scan of a v7 CFG file for parameters relevant here.
    Handles 'NAME = value' and 'NAME(k) = value' forms."""
    out: dict = {"NEWMDS": {}, "IRR": {}}
    pat = re.compile(r"^\s*([A-Za-z_0-9]+)\s*(?:\(\s*(\d+)\s*\))?\s*=\s*([^!]+)")
    with open(path, "r", errors="replace") as f:
        for line in f:
            m = pat.match(line)
            if not m:
                continue
            name = m.group(1).upper()
            idx = int(m.group(2)) if m.group(2) else None
            val = m.group(3).split()[0] if m.group(3).split() else ""
            if name in ("NEWMDS", "IRR"):
                try:
                    v = int(float(val))
                except ValueError:
                    continue
                out[name][idx if idx is not None else 1] = v
            elif name in ("IALTFRC", "IPERIN", "NBODY", "ILOWHI"):
                try:
                    out[name] = int(float(val))
                except ValueError:
                    pass
    return out


# --------------------------------------------------------------------------
# POT conversion
# --------------------------------------------------------------------------

@dataclass
class PotData:
    header: str
    hbot: float
    irad: int
    idiff: int
    nper: int                 # signed value to WRITE (after expansion choice)
    per: list[float]
    nbeta: int
    beta: list[float]
    nbody: int
    bodies: list[dict] = field(default_factory=list)  # gdf, xbody[4], mode[6]


def parse_signed_list(ts: TokenStream, n_signed: int, what: str,
                      expand: bool) -> tuple[int, list[float]]:
    """Read a PER/BETA style array given its signed count. Returns the count
    and values to write, expanding the negative-shorthand if requested.
    Trailing comment text after the last value is discarded."""
    if n_signed == 0:
        return 0, []
    if n_signed > 0:
        vals = [ts.next_float(f"{what}({i+1})") for i in range(n_signed)]
        ts.end_record()
        return n_signed, vals
    # negative: start + increment shorthand
    start = ts.next_float(f"{what}(1)")
    inc = ts.next_float(f"{what}(2) increment")
    ts.end_record()
    if expand:
        n = -n_signed
        return n, [start + i * inc for i in range(n)]
    return n_signed, [start, inc]


def parse_pot(path: str, expand: bool) -> PotData:
    header, ts = read_file(path)
    hbot = ts.next_float("HBOT")
    ts.end_record()
    irad = ts.next_int("IRAD")
    idiff = ts.next_int("IDIFF")
    ts.end_record()

    # --- periods: plain NPER, or v7.1+ 'NPERGROUP = m' --------------------
    peek = ts.peek()
    per: list[float] = []
    if peek is not None and peek.upper().startswith("NPERGROUP"):
        # consume 'NPERGROUP', optional '=', then m
        tok = ts.next_token()
        if "=" in tok and tok.split("=")[-1].strip():
            m = int(tok.split("=")[-1])
        else:
            t = ts.next_token()
            if t == "=":
                t = ts.next_token()
            elif t.startswith("="):
                t = t[1:] or ts.next_token()
            m = int(float(t))
        ts.end_record()
        info(f"{os.path.basename(path)}: expanding NPERGROUP={m} "
             f"(not supported in v6)")
        for _ in range(m):
            ng = ts.next_int("NPER (group)")
            ts.end_record()
            _, vals = parse_signed_list(ts, ng, "PER", expand=True)
            per.extend(vals)
        nper = len(per)
    else:
        nper_signed = ts.next_int("NPER")
        ts.end_record()
        nper, per = parse_signed_list(ts, nper_signed, "PER", expand)

    nbeta_signed = ts.next_int("NBETA")
    ts.end_record()
    nbeta, beta = parse_signed_list(ts, nbeta_signed, "BETA", expand)

    nbody = ts.next_int("NBODY")
    ts.end_record()
    bodies = []
    for k in range(nbody):
        gdf = ts.next_line().split()[0]   # filename = first token of the line
        xbody = [ts.next_float(f"XBODY({i+1},{k+1})") for i in range(4)]
        # v6 files may append IRR after XBODY(4) on the same line
        irr_file = None
        if ts.tokens and ts.peek_is_number():
            irr_file = ts.next_int("IRR")
            info(f"{os.path.basename(path)}: found v6-style IRR={irr_file} "
                 f"on the XBODY line of body {k+1} (kept)")
        ts.end_record()
        mode = [ts.next_int(f"MODE({i+1},{k+1})") for i in range(6)]
        ts.end_record()
        # v6-style files (or hand-kept ones) may already contain NEWMDS
        newmds_file = None
        if ts.peek_is_number():
            newmds_file = ts.next_int("NEWMDS")
            ts.end_record()
            info(f"{os.path.basename(path)}: found NEWMDS={newmds_file} for "
                 f"body {k+1} in the file (v6-style input, kept)")
        bodies.append({"gdf": gdf, "xbody": xbody, "mode": mode,
                       "irr": irr_file, "newmds": newmds_file})

    if not ts.eof():
        leftover = " ".join(ts.remaining_raw()).strip()
        if leftover and contains_numbers(leftover):
            warn(f"{path}: unexpected extra data after body {nbody}: "
                 f"'{leftover[:60]}...' — left out of the converted file.")

    return PotData(header, hbot, irad, idiff, nper, per, nbeta, beta,
                   nbody, bodies)


def write_pot_v6(pot: PotData, path: str, newmds: list[int],
                 irr: list[int] | None) -> None:
    L: list[str] = [pot.header]
    L.append(f"{fmt(pot.hbot)}")
    L.append(f"{pot.irad} {pot.idiff}")
    L.append(f"{pot.nper}")
    vals = pot.per
    if pot.nper != 0:
        for c in chunk(vals, 8):
            L.append(" ".join(fmt(v) for v in c))
    L.append(f"{pot.nbeta}")
    if pot.nbeta != 0:
        for c in chunk(pot.beta, 8):
            L.append(" ".join(fmt(v) for v in c))
    L.append(f"{pot.nbody}")
    for k, b in enumerate(pot.bodies):
        L.append(b["gdf"])
        xline = " ".join(fmt(v) for v in b["xbody"])
        irr_k = irr[k] if irr is not None else b.get("irr")
        if irr_k is not None:
            xline += f" {irr_k}"
        L.append(xline)
        L.append(" ".join(str(m) for m in b["mode"]))
        # NEWMDS line, required by the v6 POT format:
        # CLI value > value already present in the file > cfg/default
        nm = b.get("newmds")
        L.append(str(newmds[k] if newmds[k] is not None else
                     (nm if nm is not None else 0)))
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")


# --------------------------------------------------------------------------
# FRC conversion
# --------------------------------------------------------------------------

@dataclass
class FrcData:
    header: str
    alt: int
    ioptn: list[int]
    # alt 1
    vcg: float | None = None
    xprdct: list[float] | None = None        # 9 values
    # alt 2
    rho: float | None = None
    xcg: list[float] | None = None           # 3 values
    imass: int | None = None
    mass: list[float] | None = None          # 36 values
    idamp: int | None = None
    damp: list[float] | None = None
    istif: int | None = None
    stif: list[float] | None = None
    # common tail
    nbetah: int = 0
    betah: list[float] = field(default_factory=list)
    nfield: int = 0
    xfield: list[float] = field(default_factory=list)   # 3*NFIELD values
    raw_tail: list[str] = field(default_factory=list)   # NFIELD<0 passthrough


def _parse_frc_tail(ts: TokenStream, frc: FrcData, expand: bool,
                    path: str, strict: bool) -> None:
    nbh = ts.next_int("NBETAH")
    ts.end_record()
    frc.nbetah, frc.betah = parse_signed_list(ts, nbh, "BETAH", expand)
    nf = ts.next_int("NFIELD")
    ts.end_record()
    if nf < 0:
        warn(f"{path}: NFIELD={nf} (uniform field-point arrays). The block is "
             f"copied verbatim — verify your v6 version supports this input.")
        frc.nfield = nf
        frc.raw_tail = ts.remaining_raw()
        return
    frc.nfield = nf
    frc.xfield = []
    for _ in range(nf):
        frc.xfield += [ts.next_float("XFIELD") for _ in range(3)]
        ts.end_record()
    if not ts.eof():
        extra = " ".join(ts.remaining_raw()).strip()
        if extra and contains_numbers(extra):
            if strict:
                raise ValueError(f"trailing data after field points: "
                                 f"'{extra[:40]}...'")
            warn(f"{path}: extra data after field points ignored: "
                 f"'{extra[:60]}'")


def _try_parse_frc(header: str, lines: list[str], alt: int, expand: bool,
                   path: str, strict: bool = False) -> FrcData:
    ts = TokenStream(list(lines))
    ioptn = [ts.next_int(f"IOPTN({i+1})") for i in range(9)]
    ts.end_record()
    frc = FrcData(header=header, alt=alt, ioptn=ioptn)
    if alt == 1:
        frc.vcg = ts.next_float("VCG")
        ts.end_record()
        frc.xprdct = []
        for _ in range(3):
            frc.xprdct += [ts.next_float("XPRDCT") for _ in range(3)]
            ts.end_record()
    else:
        frc.rho = ts.next_float("RHO")
        ts.end_record()
        frc.xcg = [ts.next_float("XCG/YCG/ZCG") for _ in range(3)]
        ts.end_record()
        frc.imass = ts.next_int("IMASS")
        ts.end_record()
        if frc.imass not in (0, 1):
            raise ValueError(f"IMASS must be 0/1, got {frc.imass}")
        frc.mass = _read_matrix(ts, "EXMASS") if frc.imass else None
        frc.idamp = ts.next_int("IDAMP")
        ts.end_record()
        if frc.idamp not in (0, 1):
            raise ValueError(f"IDAMP must be 0/1, got {frc.idamp}")
        frc.damp = _read_matrix(ts, "EXDAMP") if frc.idamp else None
        frc.istif = ts.next_int("ISTIF")
        ts.end_record()
        if frc.istif not in (0, 1):
            raise ValueError(f"ISTIF must be 0/1, got {frc.istif}")
        frc.stif = _read_matrix(ts, "EXSTIF") if frc.istif else None
    _parse_frc_tail(ts, frc, expand, path, strict)
    return frc


def _read_matrix(ts: TokenStream, name: str) -> list[float]:
    out: list[float] = []
    for _ in range(6):
        out += [ts.next_float(name) for _ in range(6)]
        ts.end_record()
    return out


def parse_frc(path: str, alt_forced: int | None, expand: bool) -> FrcData:
    header, ts = read_file(path)
    lines = ts.remaining_raw()
    if alt_forced in (1, 2):
        return _try_parse_frc(header, lines, alt_forced, expand, path)
    # auto-detect: strict parse (must consume the whole file cleanly)
    # auto-detect: try both, keep whichever parses cleanly
    results, errors = {}, {}
    for alt in (1, 2):
        try:
            results[alt] = _try_parse_frc(header, lines, alt, expand, path,
                                          strict=True)
        except ValueError as e:
            errors[alt] = str(e)
    if len(results) == 1:
        alt = next(iter(results))
        info(f"{os.path.basename(path)}: detected FRC Alternative form {alt}")
        return results[alt]
    if len(results) == 2:
        raise ValueError(
            f"{path}: file is consistent with both FRC forms; rerun with "
            f"--alt 1 or --alt 2 (check IALTFRC in your v7 CFG).")
    raise ValueError(
        f"{path}: could not parse as either FRC form.\n"
        f"  as Alt 1: {errors.get(1)}\n  as Alt 2: {errors.get(2)}")


def remap_ioptn_v7_to_v6(ioptn: list[int], path: str) -> tuple[list[int], bool]:
    """v7 -> v6 option numbering. Returns (new array, ctrsurf_needed)."""
    new = list(ioptn)
    i6, i7 = ioptn[5], ioptn[6]

    # v7 option 6 combines field pressure (1) and velocity (2), 3 = both,
    # negative = source formulation. v6 splits these into options 6 and 7.
    sgn = -1 if i6 < 0 else 1
    a = abs(i6)
    new[5] = sgn * 1 if a in (1, 3) else 0          # v6 opt 6: field pressure
    new[6] = sgn * 1 if a in (2, 3) else 0          # v6 opt 7: field velocity
    if i6 != 0:
        info(f"{os.path.basename(path)}: IOPTN(6)={i6} (v7 field p+v) -> "
             f"v6 IOPTN(6)={new[5]} (pressure), IOPTN(7)={new[6]} (velocity)")

    ctrsurf = i7 != 0
    if ctrsurf:
        warn(f"{path}: IOPTN(7)={i7} requests control-surface mean drift "
             f"forces. v6 has no FRC option for this; it is dropped from the "
             f"FRC file. In v6.4+ set ICTRSURF=1 in the CFG file and provide "
             f"the control-surface input (output goes to the .9c file).")
    return new, ctrsurf


def write_frc_v6(frc: FrcData, path: str) -> None:
    L: list[str] = [frc.header]
    L.append(" ".join(str(i) for i in frc.ioptn))
    if frc.alt == 1:
        L.append(fmt(frc.vcg))
        for row in chunk(frc.xprdct, 3):
            L.append(" ".join(fmt(v) for v in row))
    else:
        L.append(fmt(frc.rho))
        L.append(" ".join(fmt(v) for v in frc.xcg))
        for flag, mat in ((frc.imass, frc.mass), (frc.idamp, frc.damp),
                          (frc.istif, frc.stif)):
            L.append(str(flag))
            if flag:
                for row in chunk(mat, 6):
                    L.append(" ".join(fmt(v) for v in row))
    L.append(str(frc.nbetah))
    if frc.nbetah != 0:
        for c in chunk(frc.betah, 8):
            L.append(" ".join(fmt(v) for v in c))
    L.append(str(frc.nfield))
    if frc.nfield > 0:
        for row in chunk(frc.xfield, 3):
            L.append(" ".join(fmt(v) for v in row))
    elif frc.nfield < 0:
        L.extend(frc.raw_tail)
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def discover_and_convert_files() -> int:
    """
    Finds all .pot and .frc files under ../data/vessels/**/inputs/*.(pot|frc|cfg).
    Converts the .pot and .frc files and saves them to
    ../data/vessels/**/outputs/*.(pot|frc) with the appropriate --cfg and --cfg-out settings.
    """
    # get the directory with respect to the scripts location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data","vessels")

    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith(".pot") or file.endswith(".frc"):
                input_path = os.path.join(root, file)
                output_dir = os.path.join(root, "..", "outputs")
                # Check if input path has "outputs" in its path, if so, skip it to avoid converting already converted files
                if "output" in input_path:
                    continue

                cfg_path = None
                print(f"Processing {input_path}...")
                # look for a .cfg file in the same directory
                for cfg_file in files:
                    if cfg_file.endswith(".cfg"):
                        cfg_path = os.path.join(root, cfg_file)
                        break
                out_cfg_path = os.path.join(output_dir, f"{os.path.splitext(file)[0]}.cfg")
                # convert the file
                main([input_path, "-o", output_dir, "--cfg", cfg_path, "--cfg-out", out_cfg_path, "--suffix", ""])


def out_path(in_path: str, outdir: str | None, suffix: str | None = '_v6') -> str:
    base = os.path.basename(in_path)
    if outdir:
        os.makedirs(outdir, exist_ok=True)
        return os.path.join(outdir, base)
    root, ext = os.path.splitext(in_path)
    return f"{root}{suffix}{ext}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Convert WAMIT v7.x POT/FRC files to v6.x format.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("files", nargs="*", help=".pot and/or .frc files")
    ap.add_argument("-o", "--outdir", default=None,
                    help="output directory (default: write *_v6.* in place)")
    ap.add_argument("--alt", type=int, choices=(1, 2), default=None,
                    help="force FRC alternative form (default: auto-detect)")
    ap.add_argument("--newmds", default=None,
                    help="NEWMDS per body for the v6 POT file, e.g. '0' or "
                         "'4,0' (default: from --cfg, else 0)")
    ap.add_argument("--irr", default=None,
                    help="optional IRR per body to append to the XBODY lines "
                         "(v6 style), e.g. '1' or '1,0'")
    ap.add_argument("--cfg", default=None,
                    help="v7 CFG file to read NEWMDS/IRR/IALTFRC/IPERIN from")
    ap.add_argument("--cfg-out", default=None,
                    help="write a v6 CFG snippet with relocated parameters")
    ap.add_argument("--keep-compact", action="store_true",
                    help="keep negative NPER/NBETA(H) shorthand instead of "
                         "expanding to explicit lists")
    ap.add_argument("--walk", action="store_true",
                    help="discover files under ../data/vessel/**/input/ and convert ")
    ap.add_argument("--suffix", default="_v6",
                    help="suffix to add before the file extension (default: '_v6')")
    args = ap.parse_args(argv)
    expand = not args.keep_compact

    cfg = scan_cfg(args.cfg) if args.cfg else {}
    if args.alt is None and cfg.get("IALTFRC") in (1, 2):
        args.alt = cfg["IALTFRC"]
        info(f"using IALTFRC={args.alt} from {args.cfg}")

    cfg_lines: list[str] = []
    if args.irr is None:
        for k, v in sorted(cfg.get("IRR", {}).items()):
            cfg_lines.append(f"IRR({k})={v}" if k != 1 or len(cfg["IRR"]) > 1
                             else f"IRR={v}")
    if cfg.get("IPERIN", 1) != 1:
        warn(f"v7 CFG has IPERIN={cfg['IPERIN']}; the equivalent v6 input "
             f"parameter is IPERIO — set IPERIO={cfg['IPERIN']} in the v6 CFG.")
        cfg_lines.append(f"IPERIO={cfg['IPERIN']}")
    status = 0



    if args.walk:
        discover_and_convert_files()

    for f in args.files:
        ext = os.path.splitext(f)[1].lower()
        try:
            if ext == ".pot":
                pot = parse_pot(f, expand)
                nb = pot.nbody
                if args.newmds is not None:
                    nm = [int(x) for x in args.newmds.split(",")]
                    nm = (nm + [nm[-1]] * nb)[:nb]
                else:
                    # None lets write_pot_v6 prefer a value found in the file,
                    # falling back to the cfg value / 0
                    nm = [None if pot.bodies[k].get("newmds") is not None
                          else cfg.get("NEWMDS", {}).get(k + 1,
                               cfg.get("NEWMDS", {}).get(1, 0) if nb == 1 else 0)
                          for k in range(nb)]
                irr = None
                if args.irr is not None:
                    iv = [int(x) for x in args.irr.split(",")]
                    irr = (iv + [iv[-1]] * nb)[:nb]
                dst = out_path(f, args.outdir, suffix=args.suffix)
                write_pot_v6(pot, dst, nm, irr)
                print(f"{f} -> {dst}  (POT, NBODY={nb}, NPER={pot.nper}, "
                      f"NEWMDS={nm})")

            elif ext == ".frc":
                frc = parse_frc(f, args.alt, expand)
                frc.ioptn, need_csf = remap_ioptn_v7_to_v6(frc.ioptn, f)
                dst = out_path(f, args.outdir, suffix=args.suffix)
                write_frc_v6(frc, dst)
                print(f"{f} -> {dst}  (FRC Alt {frc.alt})")
                if frc.alt == 2:
                    cfg_lines.append("IALTFRC=2")
                if need_csf:
                    cfg_lines.append("ICTRSURF=1   ! check v6.4 manual ch.14")
            else:
                warn(f"{f}: unknown extension '{ext}' (expected .pot/.frc), "
                     f"skipped")
        except (ValueError, OSError) as e:
            warn(f"{f}: conversion FAILED — {e}")
            status = 1

    if args.cfg_out:
        seen, uniq = set(), []
        for c in cfg_lines:
            if c not in seen:
                seen.add(c)
                uniq.append(c)
        with open(args.cfg_out, "w") as fh:
            fh.write("! v6 CFG snippet generated by wamit75_to_v6.py\n")
            fh.write("! merge into your existing v6 config file\n")
            fh.write("IALTPOT=2\n")
            fh.write("\n".join(uniq) + ("\n" if uniq else ""))
        print(f"v6 CFG snippet -> {args.cfg_out}")


    return status

if __name__ == "__main__":
    sys.exit(main())