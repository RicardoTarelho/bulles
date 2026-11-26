# Bulles

Read comics in the language you're learning. Tap a bubble you don't understand
and it flips into a language you already know, right on the page.

**Read it here:** https://ricardotarelho.github.io/bulles/

## Current library

**Pepper&Carrot** by David Revoy: all 39 published episodes, in French, English,
Portuguese and Spanish. Any of these can be the language you learn or the one
you know. Episode 39 has no Portuguese version upstream yet, so it is skipped
when you learn Portuguese and flips to English when Portuguese is the one you know.

**Books**, from public-domain French editions on Wikisource. Read any of them in French, English, Portuguese or Spanish,
and tap a sentence to see it in another of those languages. The French is the original;
the other languages were translated sentence by sentence with Claude for Bulles.

- *Contes de Perrault* by Charles Perrault (1697), B1–B2: 4 tales (Little Red Riding Hood, The Fairies, Puss in Boots, Cinderella, or the Little Glass Slipper).
- *Les Malheurs de Sophie* by Comtesse de Ségur (1858), A2: 22 chapters.
- *Contes d’Andersen* by Hans Christian Andersen (1876, French translation by David Soldi), A2–B1: 5 tales (The Princess and the Pea, The Emperor's New Clothes, The Little Match Girl, The Steadfast Tin Soldier, The Ugly Duckling).
- *Contes de Grimm* by Jacob et Wilhelm Grimm (1864, French translation by Frédéric Baudry), B1: 4 tales (The Town Musicians of Bremen, The Hare and the Hedgehog, Lucky Hans, The Fisherman and His Wife).
- *Contes de Daudet* by Alphonse Daudet (1869), B1–B2: 4 stories (Monsieur Seguin's Goat, Master Cornille's Secret, The Stars, The Last Lesson).
- *Contes de Maupassant* by Guy de Maupassant (1884), B2: 3 stories (The Necklace, In the Country, My Uncle Jules).

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
| `data/episodes/epNN/<language>.js` | One language's speech bubbles for that episode (fr, en, pt, es). |
| `data/books/<book>/<chapter>.js` | One book chapter or tale: the French sentences with their English and Portuguese translations. |
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

`tools/build_book.py` builds the Perrault tales and `tools/build_books.py` the other books, from the texts and translations in `tools/book-batch/`; `tools/build_library.py` holds the shared code for reading the bubble layers, SVGs and transcripts.
