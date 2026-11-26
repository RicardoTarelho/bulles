# Bulles

Read comics in the language you're learning. Tap a bubble you don't understand
and it flips into a language you already know, right on the page.

**Read it here:** https://ricardotarelho.github.io/bulles/

## Current library

**Pepper&Carrot** by David Revoy: all 39 published episodes, in French, English,
Portuguese, Spanish, German and Italian. Any of these can be the language you
learn or the one you know. Episode 39 has no Portuguese or Italian translation yet, so for those
its bubbles flip to English instead.

**Contes de Perrault** by Charles Perrault (1697): four tales (Little Red Riding Hood,
The Fairies, Puss in Boots, Cinderella) in the original French, from the 1886 Montréal
edition on Wikisource (public domain). Tap any sentence to see it in English or
Portuguese. Those translations were made with Claude for Bulles.

Every comic episode and every tale has an estimated CEFR level (A1–C2). Pick your
own level on the start page and Bulles marks what is at your level, easy, a stretch
or hard. `tools/levels.py` explains how the levels are estimated.

## What's in this folder

| Folder | What it holds |
|---|---|
| `index.html` | The page to open. |
| `css/`, `js/` | Styles and code. |
| `data/library.js` | The series, its episodes, titles in every language, and credits. |
| `data/covers.js` | The small cover pictures for the episode list. |
| `data/episodes/epNN/pages.js` | One episode's artwork, plus where every bubble is and what it says in each language. |
| `data/episodes/epNN/<language>.js` | One language's speech bubbles for that episode (fr, en, pt, es, de, it). |
| `tools/` | The scripts that rebuild `data/` from the sources. |
| `CREDITS.md` | Who made the comics, and the licence. |

The pictures are stored inside the `.js` files so the app also runs straight
from a downloaded copy, without a server or internet.

## How the flip works

Each language's speech bubbles come as a separate transparent layer. The app
shows the artwork with the bubbles of the language you're learning on top.
When you tap a bubble, it covers that bubble with a white patch and draws the
same bubble from your other language over it. Every translation is a human one,
made by the Pepper&Carrot volunteer translators.

## Rebuilding or adding episodes

1. Download the episode sources from https://www.peppercarrot.com/0_sources/ into one folder (one folder per episode).
2. Run `python tools/build_series.py <that folder> .` (needs Python with numpy, scipy and Pillow).

`tools/build_book.py` builds the book from its text and translations; `tools/build_library.py` holds the shared code for reading the bubble layers, SVGs and transcripts.
