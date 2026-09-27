"""SVG rendering of the original ink layer with optional derived-layer overlays.

Coordinates: page frame {P} in micrometres (ICD section 1: e_x right, e_y up)
mapped to SVG millimetres with the y axis flipped (SVG y points down), so the
page appears as written.  Output is deterministic (fixed number formatting,
no time stamps) so renders are reproducible byte for byte.

Overlays
--------
* ``hand_path_estimate``: dashed polyline per stroke (e.g. housing path
  before stage correction) over the deposited ink;
* ``segmentation``: word and line boxes;
* ``recognition`` / effective text (``NoteStore.effective_text``): word boxes
  with the recognised text;
* highlight: strokes cited by an ``ai_summary`` answer, plus its sentences as a
  caption.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape, quoteattr

import numpy as np

from . import SYNTHETIC_LABEL
from ._util import ids_from_ranges
from .notes import OriginalLayer

INK = "#1b1b1b"
MUTED = "#8a8882"
OVERLAY = "#d0592a"
BOXES = "#2a78d6"
HIGHLIGHT = "#1baf7a"


@dataclass
class RenderOptions:
    force_width: bool = False
    width_mm: float = 0.35                       # fixed ink width
    width_range_mm: Tuple[float, float] = (0.12, 0.60)
    force_range_mN: Tuple[float, float] = (0.0, 2000.0)
    width_levels: int = 8
    margin_mm: float = 4.0
    font_mm: float = 1.8
    title: str = ""
    label: Optional[str] = None                  # e.g. SYNTHETIC_LABEL
    show_legend: bool = True


def _f(v: float) -> str:
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _pt(x_um: float, y_um: float) -> str:
    return f"{_f(x_um / 1000.0)},{_f(-y_um / 1000.0)}"


def _width_level(force_mN: np.ndarray, opt: RenderOptions) -> np.ndarray:
    f0, f1 = opt.force_range_mN
    frac = np.clip((np.asarray(force_mN, float) - f0) / max(f1 - f0, 1e-9), 0.0, 1.0)
    return np.minimum((frac * opt.width_levels).astype(int), opt.width_levels - 1)


def _level_width(level: int, opt: RenderOptions) -> float:
    w0, w1 = opt.width_range_mm
    return w0 + (w1 - w0) * (level + 0.5) / opt.width_levels


class _Canvas:
    def __init__(self):
        self.parts: List[str] = []
        self.xs: List[float] = []
        self.ys: List[float] = []

    def extend_bounds(self, x_um: Iterable[float], y_um: Iterable[float]) -> None:
        self.xs.extend(float(v) for v in x_um)
        self.ys.extend(float(v) for v in y_um)


def _stroke_polylines(orig: OriginalLayer, opt: RenderOptions, highlight: Optional[set]) -> List[str]:
    s = orig.samples
    out = []
    for sid, a, b in orig.stroke_runs:
        x = s["x_um"][a:b].astype(float)
        y = s["y_um"][a:b].astype(float)
        color = HIGHLIGHT if highlight and sid in highlight else INK
        cls = "ink highlighted" if highlight and sid in highlight else "ink"
        if b - a == 1:                         # a single sample renders as a dot
            r = (_level_width(int(_width_level(s["force_mN"][a:b], opt)[0]), opt) if opt.force_width
                 else opt.width_mm) / 2
            out.append(f'<circle class="{cls}" data-stroke-id="{sid}" cx="{_f(x[0] / 1000)}" '
                       f'cy="{_f(-y[0] / 1000)}" r="{_f(r)}" fill="{color}"/>')
            continue
        if not opt.force_width:
            pts = " ".join(_pt(xi, yi) for xi, yi in zip(x, y))
            out.append(f'<polyline class="{cls}" data-stroke-id="{sid}" points="{pts}" '
                       f'stroke="{color}" stroke-width="{_f(opt.width_mm)}"/>')
            continue
        f = s["force_mN"][a:b].astype(float)
        lev = _width_level(0.5 * (f[:-1] + f[1:]), opt)       # one level per segment
        k = 0
        while k < len(lev):
            m = k
            while m + 1 < len(lev) and lev[m + 1] == lev[k]:
                m += 1
            pts = " ".join(_pt(x[i], y[i]) for i in range(k, m + 2))
            out.append(f'<polyline class="{cls}" data-stroke-id="{sid}" points="{pts}" stroke="{color}" '
                       f'stroke-width="{_f(_level_width(int(lev[k]), opt))}"/>')
            k = m + 1
    return out


def _rect(b: Sequence[float], cls: str, color: str, extra: str = "", dash: str = "") -> str:
    x0, y0, x1, y1 = (float(v) for v in b)
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect class="{cls}"{extra} x="{_f(x0 / 1000)}" y="{_f(-y1 / 1000)}" width="{_f((x1 - x0) / 1000)}" '
            f'height="{_f((y1 - y0) / 1000)}" fill="none" stroke="{color}" stroke-width="0.08"{d}/>')


def render_svg(orig: OriginalLayer, *, overlays: Sequence[dict] = (), highlight_ranges=None,
               caption: Sequence[str] = (), options: Optional[RenderOptions] = None,
               note_id: Optional[str] = None) -> str:
    """Render the original layer; ``overlays`` are derived layers (or an
    effective-text dict from ``NoteStore.effective_text``)."""
    opt = options or RenderOptions()
    s = orig.samples
    cv = _Canvas()
    cv.extend_bounds(s["x_um"], s["y_um"])
    highlight = set(ids_from_ranges(highlight_ranges)) if highlight_ranges else None
    body: List[str] = []
    legend: List[Tuple[str, str]] = [(INK, f"ink: original layer sha256 {orig.sha256[:16]}"
                                          + (" (width from force)" if opt.force_width else ""))]
    for ov in overlays:
        kind = ov.get("kind") or ("effective_text" if "recognition_layer_id" in ov else "unknown")
        lid = ov.get("layer_id") or ov.get("recognition_layer_id", "")
        g: List[str] = []
        if kind == "hand_path_estimate":
            for st in ov["payload"]["strokes"]:
                pts = " ".join(_pt(xu, yu) for xu, yu in zip(st["x_um"], st["y_um"]))
                cv.extend_bounds(st["x_um"], st["y_um"])
                g.append(f'<polyline class="hand-path" data-stroke-id="{st["stroke_id"]}" points="{pts}" '
                         f'stroke="{OVERLAY}" stroke-width="0.12" stroke-dasharray="0.6 0.35"/>')
            legend.append((OVERLAY, f"dashed: hand-path estimate, layer {lid}"))
        elif kind == "segmentation":
            for sp in ov["payload"]["spans"]:
                dash = "0.5 0.3" if sp["level"] == "line" else ""
                g.append(_rect(sp["bbox_um"], f"seg-{sp['level']}", BOXES,
                               f' data-span-id={quoteattr(sp["span_id"])}', dash))
            legend.append((BOXES, f"boxes: segmentation words (solid) / lines (dashed), layer {lid}"))
        elif kind in ("recognition", "effective_text"):
            spans = ov["payload"]["spans"] if kind == "recognition" else ov["spans"]
            for sp in spans:
                if sp["level"] != "word" or sp.get("superseded"):
                    continue
                edited = bool(sp.get("edited_by"))
                g.append(_rect(sp["bbox_um"], "word-box", OVERLAY if edited else BOXES,
                               f' data-span-id={quoteattr(sp["span_id"])}'))
                x0, _, _, y1 = sp["bbox_um"]
                g.append(f'<text class="word-text" data-span-id={quoteattr(sp["span_id"])} '
                         f'x="{_f(x0 / 1000)}" y="{_f(-y1 / 1000 - 0.5)}" font-size="{_f(opt.font_mm)}" '
                         f'fill="{OVERLAY if edited else BOXES}">{escape(sp["text"])}</text>')
                cv.extend_bounds([x0], [y1 + 1000 * (opt.font_mm + 0.6)])
            src = lid if kind == "recognition" else "effective text " + ", ".join(
                [ov["recognition_layer_id"]] + ov.get("user_edit_layer_ids", []))
            legend.append((BOXES, f"boxes + text: recognised words ({src}); orange = user-edited"))
        else:
            raise ValueError(f"cannot render overlay of kind {kind!r}")
        body.append(f'<g class="overlay" data-kind="{escape(kind)}" data-layer-id={quoteattr(lid)} '
                    f'fill="none" stroke-linecap="round" stroke-linejoin="round">' + "".join(g) + "</g>")
    if highlight:
        legend.append((HIGHLIGHT, "green: strokes cited by the answer"))
    x0 = min(cv.xs) / 1000 - opt.margin_mm
    x1 = max(cv.xs) / 1000 + opt.margin_mm
    ytop = -max(cv.ys) / 1000 - opt.margin_mm
    ybot = -min(cv.ys) / 1000 + opt.margin_mm
    lines_top: List[str] = []
    fs = opt.font_mm
    header_rows = ([opt.title] if opt.title else []) + ([opt.label] if opt.label else [])
    n_head = len(header_rows) + (len(legend) if opt.show_legend else 0)
    ytop_ext = ytop - n_head * fs * 1.35
    y = ytop_ext + fs * 1.1
    for i, txt in enumerate(header_rows):
        weight = ' font-weight="bold"' if i == 0 and opt.title else ""
        color = "#b3261e" if txt == opt.label else INK
        lines_top.append(f'<text x="{_f(x0 + 0.5)}" y="{_f(y)}" font-size="{_f(fs)}" fill="{color}"{weight}>'
                         f'{escape(txt)}</text>')
        y += fs * 1.35
    if opt.show_legend:
        for color, txt in legend:
            lines_top.append(f'<rect x="{_f(x0 + 0.5)}" y="{_f(y - fs * 0.7)}" width="{_f(fs * 0.8)}" '
                             f'height="{_f(fs * 0.8)}" fill="{color}"/>'
                             f'<text x="{_f(x0 + 0.5 + fs * 1.2)}" y="{_f(y)}" font-size="{_f(fs * 0.85)}" '
                             f'fill="{MUTED}">{escape(txt)}</text>')
            y += fs * 1.35
    cap_parts: List[str] = []
    yc = ybot + fs * 0.4
    for txt in caption:
        yc += fs * 1.35
        cap_parts.append(f'<text x="{_f(x0 + 0.5)}" y="{_f(yc)}" font-size="{_f(fs)}" fill="{INK}">'
                         f'{escape(txt)}</text>')
    ybot_ext = yc + (fs * 0.8 if caption else 0.0)
    # widen the canvas so header, legend and caption text are not clipped (~0.55 em per character)
    text_w = [len(t) * fs * 0.56 for t in header_rows + list(caption)]
    text_w += [fs * 1.2 + len(t) * fs * 0.85 * 0.56 for _, t in legend] if opt.show_legend else []
    x1 = max(x1, x0 + 0.5 + max(text_w, default=0.0) + opt.margin_mm / 2)
    width = x1 - x0
    height = ybot_ext - ytop_ext
    ink = _stroke_polylines(orig, opt, highlight)
    desc = (f"note {note_id or '-'}; original layer sha256 {orig.sha256}; {orig.n_samples} samples; "
            f"page frame micrometres rendered in mm with y up; "
            + (opt.label or "evidence status: see note labels"))
    return "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{_f(x0)} {_f(ytop_ext)} {_f(width)} {_f(height)}" '
        f'width="{_f(width)}mm" height="{_f(height)}mm" font-family="Helvetica, Arial, sans-serif">',
        f"<title>{escape(opt.title or 'pen note')}</title>",
        f"<desc>{escape(desc)}</desc>",
        f'<rect x="{_f(x0)}" y="{_f(ytop_ext)}" width="{_f(width)}" height="{_f(height)}" fill="#ffffff"/>',
        '<g class="original" fill="none" stroke-linecap="round" stroke-linejoin="round">',
        *ink,
        "</g>",
        *body,
        *lines_top,
        *cap_parts,
        "</svg>",
        "",
    ])


def save_svg(path, svg: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")
    return path


def render_note(store, note_id: str, *, overlay: Optional[str] = None, force_width: bool = False,
                highlight_ranges=None, caption: Sequence[str] = (), title: Optional[str] = None,
                width_mm: float = 0.35) -> str:
    """Convenience wrapper: render a stored note with the latest layer of ``overlay`` kind.

    ``overlay`` may be a layer kind, a layer id, or ``"text"`` for the
    effective recognised text (recognition + user edits).
    """
    note = store.get_note(note_id)
    orig = store.get_original(note["original_sha256"])
    overlays = []
    if overlay == "text":
        eff = store.effective_text(note_id)
        if eff is None:
            raise ValueError("note has no recognition layer")
        overlays.append(eff)
    elif overlay:
        if "-" in overlay and overlay.split("-")[0] in ("recognition", "segmentation", "hand_path_estimate"):
            overlays.append(store.get_layer(overlay))
        else:
            layers = store.list_layers(note_id=note_id, kind=overlay)
            if not layers:
                raise ValueError(f"note {note_id} has no {overlay} layer")
            overlays.append(layers[-1])
    label = SYNTHETIC_LABEL if "synthetic" in note.get("labels", []) else None
    opt = RenderOptions(force_width=force_width, title=title or f"{note_id}", label=label, width_mm=width_mm)
    return render_svg(orig, overlays=overlays, highlight_ranges=highlight_ranges, caption=caption,
                      options=opt, note_id=note_id)
