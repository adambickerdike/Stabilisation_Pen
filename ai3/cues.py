"""Task 2, physical feedback: what each cue would do for a writer who misspells (SIMULATION with ASSUMED responses).

The words, the misspellings, the detector's flags and when they fire come from REAL data (Holbrook children's writing,
the checker of spell.py); when a letter can be recognised while it is written comes from the real-handwriting
recogniser (task 1).  How a writer responds to each cue is an ASSUMPTION, anchored where literature exists:
  * students with learning disabilities corrected 9 % of their errors unaided and 37 % with a spelling checker; when
    the checker offered the right word they chose it 82 % of the time (MacArthur et al. 1996, LIT HAP-130)
  * adults with dyslexia correcting sentences: 78 % right with no help, 90 % with the errors marked, 93 % with
    suggestions (Rello et al. 2015, Spanish real-word errors, LIT HAP-133)
  * vibrotactile detection thresholds at the fingertip rise during FAST hand movement (50-60 cm/s) but not
    significantly during slow movement (10-20 cm/s; Yildiz et al. 2015, LIT HAP-131); handwriting moves the pen at
    about 3 cm/s (LIT CON-20), so a clear tick is assumed to be noticed most of the time
Cues (PROPOSED DESIGN):
  none         nothing while writing (the ink stays as written)
  app_after    the app underlines the flagged words after the note (no physical cue); corrections are digital only
  tick_after   an LRA tick as soon as the word is flagged (on the suspect letter, or at the word's end)
  tick_before  an LRA tick BEFORE a letter the model thinks is likely to go wrong (a warning, no knowledge of the answer)
  withhold     the pen lifts the ball once the letter being written is recognised AND flagged (stricter threshold): the
               rest of the wrong letter is not drawn; the app shows the suggestion; the writer continues
  tick_lift    the pen lift when the checker is very sure (theta_w) mid-word, an LRA tick for every other flag
  show_me      opt-in: after a flag, the nose draws the correct next letter lightly within its reach for the writer
               to trace (the pen writes a letter only in this mode)
  heel_steer   the heel wheel steers the start of the next letter toward the correct letter (it cannot move the pen)
  pause_offer  the review's interaction (section 10): nothing mid-word; at the next natural pause (the pen lift after a
               flagged word) one tick and the app shows up to 3 suggestions (optionally read aloud); the writer chooses
Interaction measures (rule I1): suggestion lists read per 100 words (reading burden), cues felt while a word is being
written per 100 words (flow interruptions), cues at pauses, correct words made wrong (harmful edits), extra seconds.
Invariant checked by the simulation: outside show_me the pen never draws a letter the writer did not write.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

import numpy as np

CUES = ("none", "app_after", "tick_after", "tick_before", "withhold", "tick_lift", "show_me", "heel_steer", "pause_offer")
LABELS = {"none": "No cue", "app_after": "App underlines afterwards (no physical cue)",
          "tick_after": "LRA tick on the suspect letter", "tick_before": "LRA tick before a risky letter",
          "withhold": "Pen lift: the wrong letter is not drawn", "tick_lift": "Tick, plus pen lift when very sure",
          "show_me": "Show me (opt-in): nose draws the next letter", "heel_steer": "Heel wheel steers toward the right letter",
          "pause_offer": "Tick at the next pause + suggestions"}


@dataclass
class Response:
    """Writer-response parameters (ASSUMPTIONS unless a LIT id is given)."""
    p_notice_tick: float = 0.9        # a tick while writing is noticed (LIT HAP-131: no significant gating at slow speed)
    p_notice_ink: float = 0.95        # missing ink is noticed (the writer is looking at the tip)
    p_look: float = 0.7               # after noticing, the writer looks at the app's suggestion
    p_pick: float = 0.82              # chooses the right word when it is among the suggestions (LIT HAP-130)
    p_self: float = 0.35              # fixes the word once told WHERE it is wrong, without a suggestion (children with
                                      # LD: 9 % unaided, LIT HAP-130; adults with dyslexia: about 54 % of the sentences
                                      # they missed were fixed with detection only, LIT HAP-133)
    p_prevent: float = 0.25           # a warning before a risky letter makes the writer get that letter right
    p_follow_show: float = 0.85       # traces/copies the letter the nose draws
    p_follow_steer: float = 0.25      # lets the wheel's steer change which letter they start
    p_harm: float = 0.1               # changes a correct word to a suggested wrong one after a false alarm they check
    t_letter: float = 0.45            # s per letter written (LIT CON-20 speed, UJI path lengths; CALC)
    t_notice: float = 1.1             # s to stop and react to a cue
    t_look: float = 2.0               # s to read the suggestion on the phone
    t_warn: float = 0.6               # s lost to a warning tick
    t_cross: float = 0.8              # s to cross out a word or letter


LOW = Response(p_notice_tick=0.75, p_look=0.5, p_pick=0.7, p_self=0.15, p_prevent=0.1, p_follow_show=0.7,
               p_follow_steer=0.1, p_harm=0.2)
HIGH = Response(p_notice_tick=0.97, p_look=0.9, p_pick=0.9, p_self=0.55, p_prevent=0.4, p_follow_show=0.95,
                p_follow_steer=0.4, p_harm=0.05)


def flag_at(tok: Dict, theta: float, use_end: bool = True) -> Optional[int]:
    for k, p in enumerate(tok["p_dev"]):
        if p >= theta:
            return k + 1
    if use_end and tok["p_err_end"] >= theta:
        return len(tok["p_dev"]) + 1
    return None


def warn_at(tok: Dict, theta_b: float) -> Optional[int]:
    """Letter (1-based) BEFORE which a warning tick fires: p_next after letter k-1 >= theta_b (k=1: before the word)."""
    for k, p in enumerate(tok["p_next"]):
        if p >= theta_b and k + 2 <= len(tok["p_dev"]):
            return k + 2
    return None


def sugg_at(tok: Dict, k: Optional[int]) -> List[str]:
    """What the app shows when the word is flagged at letter k: the spelling-tolerant completions after k letters
    (mid-word), or the ranked corrections of the finished word (at its end)."""
    ct = tok.get("complete_top") or []
    if k is not None and k <= len(tok["p_dev"]) and len(ct) >= k and ct[k - 1]:
        return list(ct[k - 1])[:3]
    return list(tok.get("suggestions") or [])[:3]


def first_dev(target: str, written: str) -> int:
    for i, c in enumerate(written):
        if i >= len(target) or c != target[i]:
            return i + 1
    return len(written) + 1


def simulate(records: List[List[Dict]], cue: str, theta: float, theta_w: float, theta_b: float, R: Response,
             commit: Dict, reach_ok: float, seed: int = 0, n_rep: int = 20) -> Dict:
    """Monte Carlo over the words of the given writers.  commit: {'p_before_end', 'frac_median'} of the recogniser
    (task 1), reach_ok: share of next letters within the nose's autowrite reach (CALC)."""
    rng = np.random.default_rng(seed)
    n_err = n_cor = 0
    fixed_paper = fixed_digital = harmed = interventions_err = false_int = 0
    pen_letters = 0
    extra_t = 0.0
    base_t = 0.0
    caught = 0
    fragments = 0
    reads = interrupts = pause_cues = 0
    for _ in range(n_rep):
        for recs in records:
            for u in recs:
                if u["kind"] not in ("error", "correct") or not u["tokens"]:
                    continue
                if len(u["tokens"]) != 1:            # split/run-on spans: only the digital review can help
                    if u["kind"] == "error":
                        n_err += 1
                    continue
                tok = u["tokens"][0]
                L = len(tok["written"])
                base_t += (L + 1) * R.t_letter
                tgt = u["target"].lower()
                is_err = u["kind"] == "error"
                n_err += is_err; n_cor += (not is_err)
                f = flag_at(tok, theta)
                sugg_ok = tgt in sugg_at(tok, f)
                if cue == "none":
                    continue
                if cue == "app_after":
                    if f is not None:
                        extra_t += R.t_look * 0.5
                        reads += 1
                        if is_err:
                            caught += 1
                            if (sugg_ok and rng.random() < R.p_pick) or (not sugg_ok and rng.random() < R.p_self):
                                fixed_digital += 1
                        else:
                            false_int += 1
                            if rng.random() < R.p_harm:
                                harmed += 1
                    continue
                if cue == "tick_before":
                    wk = warn_at(tok, theta_b)
                    if wk is not None:
                        extra_t += R.t_warn
                        interrupts += 1
                        if is_err and wk == first_dev(tgt, tok["written"]):
                            interventions_err += 1
                            if rng.random() < R.p_notice_tick * R.p_prevent:
                                fixed_paper += 1
                        elif not is_err:
                            false_int += 1
                        else:
                            interventions_err += 1
                    continue
                if cue == "heel_steer":
                    # steer before the next letter once the word is flagged mid-word, or when a warning fires
                    wk = warn_at(tok, theta_b)
                    fk = f if (f is not None and f <= L) else None
                    k = min([x for x in (wk, fk) if x is not None], default=None)
                    if k is not None:
                        interrupts += 1
                        if is_err:
                            interventions_err += 1
                            fd = first_dev(tgt, tok["written"])
                            if k <= fd and rng.random() < R.p_follow_steer:
                                fixed_paper += 1
                        else:
                            false_int += 1
                            if rng.random() < R.p_follow_steer * 0.2:
                                harmed += 1
                    continue
                if cue in ("tick_after", "pause_offer"):
                    if f is None:
                        continue
                    if cue == "pause_offer":
                        f = L + 1                                # only at the pause after the word
                        sugg_ok = tgt in sugg_at(tok, f)
                    if is_err:
                        caught += 1; interventions_err += 1
                    else:
                        false_int += 1
                    if rng.random() > R.p_notice_tick:
                        continue
                    if f <= L:
                        interrupts += 1
                    else:
                        pause_cues += 1
                    extra_t += R.t_notice
                    looked = rng.random() < R.p_look                  # same look rate for both (no assumed advantage)
                    extra_t += R.t_look if looked else 0.0
                    reads += int(looked)
                    if is_err:
                        ok = (looked and sugg_ok and rng.random() < R.p_pick) or (not looked and rng.random() < R.p_self)
                        if ok:
                            fixed_paper += 1; fixed_digital += 1
                            extra_t += R.t_cross + min(f, L) * R.t_letter      # cross out, rewrite what was written
                    else:
                        if looked and rng.random() < R.p_harm:
                            harmed += 1
                    continue
                if cue in ("withhold", "tick_lift"):
                    fp = None
                    for k, p in enumerate(tok["p_dev"]):
                        if p >= theta_w:
                            fp = k + 1
                            break
                    if fp is None and cue == "tick_lift" and f is not None:
                        # not sure enough to lift: an LRA tick instead (as tick_after)
                        if is_err:
                            caught += 1; interventions_err += 1
                        else:
                            false_int += 1
                        if rng.random() > R.p_notice_tick:
                            continue
                        extra_t += R.t_notice
                        if f <= L:
                            interrupts += 1
                        else:
                            pause_cues += 1
                        looked = rng.random() < R.p_look
                        extra_t += R.t_look if looked else 0.0
                        reads += int(looked)
                        if is_err:
                            if (looked and sugg_ok and rng.random() < R.p_pick) or (not looked and rng.random() < R.p_self):
                                fixed_paper += 1; fixed_digital += 1
                                extra_t += R.t_cross + min(f, L) * R.t_letter
                        elif looked and rng.random() < R.p_harm:
                            harmed += 1
                        continue
                    if fp is None:
                        continue
                    sugg_ok = tgt in sugg_at(tok, fp)
                    # the letter must be recognised before its end for the lift to save any of it
                    before_end = rng.random() < commit["p_before_end"]
                    if is_err:
                        caught += 1; interventions_err += 1
                    else:
                        false_int += 1
                    if not before_end:
                        fp += 1                          # lift from the next letter on
                    else:
                        fragments += 1
                    if rng.random() > R.p_notice_ink:
                        continue
                    extra_t += R.t_notice + R.t_look
                    interrupts += 1
                    reads += 1
                    if is_err:
                        if (sugg_ok and rng.random() < R.p_pick) or (not sugg_ok and rng.random() < R.p_self):
                            fixed_paper += 1; fixed_digital += 1
                            extra_t += R.t_cross * 0.5
                    else:
                        extra_t += R.t_letter + R.t_cross * 0.5            # redo the cut letter
                        if rng.random() < R.p_harm:
                            harmed += 1
                    continue
                if cue == "show_me":
                    if f is None:
                        continue
                    if is_err:
                        caught += 1; interventions_err += 1
                    else:
                        false_int += 1
                    if rng.random() > R.p_notice_tick:
                        continue
                    extra_t += R.t_notice
                    interrupts += int(f <= L)
                    pause_cues += int(f > L)
                    if is_err:
                        can = sugg_ok and rng.random() < reach_ok
                        if can:
                            fd = first_dev(tgt, tok["written"])
                            n_draw = max(1, len(tgt) - fd + 1) if f > L else 1
                            pen_letters += n_draw
                            extra_t += n_draw * 0.32 + R.t_cross     # nose draws at 3.1 letters/s (SIM nose_v2)
                            if rng.random() < R.p_follow_show:
                                fixed_paper += 1; fixed_digital += 1
                        elif rng.random() < R.p_self:
                            fixed_paper += 1; fixed_digital += 1
                            extra_t += R.t_cross + L * R.t_letter
                    else:
                        pen_letters += 1
                        extra_t += 0.32
                        if rng.random() < R.p_harm:
                            harmed += 1
                    continue
    n_err = max(n_err, 1); n_cor = max(n_cor, 1)
    return {"cue": cue, "n_errors": n_err // n_rep, "n_correct": n_cor // n_rep,
            "caught_per_10_errors": 10.0 * caught / n_err,
            "fixed_on_paper_per_10_errors": 10.0 * fixed_paper / n_err,
            "fixed_in_app_per_10_errors": 10.0 * max(fixed_digital, fixed_paper) / n_err,
            "false_interventions_per_100_correct": 100.0 * false_int / n_cor,
            "correct_words_made_wrong_per_100_correct": 100.0 * harmed / n_cor,
            "extra_time_pct": 100.0 * extra_t / max(base_t, 1e-9),
            "letters_drawn_by_pen_per_100_words": 100.0 * pen_letters / (n_err + n_cor),
            "suggestion_lists_read_per_100_words": 100.0 * reads / (n_err + n_cor),
            "interruptions_per_100_words": 100.0 * interrupts / (n_err + n_cor),
            "cues_at_pauses_per_100_words": 100.0 * pause_cues / (n_err + n_cor),
            "extra_seconds_per_100_words": 100.0 * extra_t / (n_err + n_cor),
            "wrong_letter_fragments_per_100_words": 100.0 * fragments / (n_err + n_cor)}


def run_all(records, theta, theta_w, theta_b, commit, reach_ok, seed=0, n_rep=20) -> Dict:
    out = {}
    for name, R in (("nominal", Response()), ("low", LOW), ("high", HIGH)):
        out[name] = {c: simulate(records, c, theta, theta_w, theta_b, R, commit, reach_ok, seed=seed, n_rep=n_rep)
                     for c in CUES}
    out["responses"] = {"nominal": asdict(Response()), "low": asdict(LOW), "high": asdict(HIGH)}
    return out
