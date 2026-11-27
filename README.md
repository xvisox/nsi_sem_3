# Who gets flagged on Wikipedia?

NSI seminar talk, 20 November 2026, on Trokhymovych, Aslam, Chou, Baeza-Yates, Saez-Trumper, *Fair Multilingual
Vandalism Detection System for Wikipedia*, KDD 2023 ([arXiv 2306.01650](https://arxiv.org/abs/2306.01650),
[doi 10.1145/3580305.3599823](https://doi.org/10.1145/3580305.3599823), copy in `papers/`).

The paper is the starting point of our joint MSc thesis (my part calibration, Przemysław's distillation), so the
last slides say what we build on it. The earlier deck on Pecher et al., EMNLP 2025, is on the local branch
`emnlp-deck`.

Online at <https://xvisox.github.io/nsi_sem_3/>, deployed from `main` by `.github/workflows/pages.yml`.
Or open `index.html` in a browser. Everything is local, including fonts and KaTeX, so it works offline.

- `S` opens the speaker view with a pacing timer for the 25-minute slot (5 of them kept for questions),
  `F` goes fullscreen, `Esc` shows the overview
- Alt+click zooms into a figure
- `index.html?print-pdf` then print to PDF for a handout

`speech.md` has the talking points per slide with time windows for about 18 minutes, plus answers to likely questions.
`script.md` is the same talk written out in full, to learn from.

Built on reveal.js 6.0.2 (master, `e240e17`). The deck's own styles are in `css/custom/`. The ranking, fairness and fairness-target
charts are generated from the paper's Tables 3, 4 and 5 and the calibration chart from its
training revert rate (Table 1). The language scatter and the feature ranking are redrawn
from values read off its Figures 7 and 12 by pixel position, so they stay legible from the back of a room.
The reproduction chart pairs the authors' notebook values with ours from the thesis repo (`wikipedia-mgr`, runs
`full` and `mlm-full`):

```bash
python3 tools/charts.py index.html
```

The edit-war and pipeline diagrams are redrawn from the paper's Figures 3 and 1. Blue means ORES everywhere
in the deck.
