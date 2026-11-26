"""Estimated CEFR levels for Bulles content.

These are rough estimates from how much text there is and how long the
sentences are, not an official assessment.

Comics (per episode, from the French transcript, title and credits pages and
sound effects excluded):
  under 60 words in total (mostly wordless)   -> A1
  under 260 words and sentences of <= 5 words -> A2
  otherwise                                   -> B1
Books are rated by hand per chapter (see build_book.py), because literary
tenses and old vocabulary matter more than length there.
"""
import re

ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]


def episode_level(transcript_pages):
    """transcript_pages: {page id: [(position, speaker, text, concatenate)]} from build_library.transcript."""
    pages = sorted(transcript_pages)
    body = [p for p in pages if p != "P00" and p != pages[-1]] if len(pages) > 2 else pages
    skip = {"crédits", "credits", "générique", "notes", "son", "sound", "sons"}
    txt = [r[2] for p in body for r in transcript_pages[p] if r[1].lower() not in skip]
    sents = [s for t in txt for s in re.split(r"(?<=[.!?…])\s+", t) if s.split()]
    words = re.findall(r"[A-Za-zÀ-ÿ’']+", " ".join(txt))
    n = len(words)
    asl = n / max(1, len(sents))
    if n < 60:
        return "A1"
    if n < 260 and asl <= 5:
        return "A2"
    return "B1"


def level_range(levels):
    ks = sorted({ORDER.index(l) for l in levels})
    return ORDER[ks[0]] if len(ks) == 1 else ORDER[ks[0]] + "–" + ORDER[ks[-1]]
