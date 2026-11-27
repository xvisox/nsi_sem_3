# Talking points: Who gets flagged on Wikipedia?

**The talk in one sentence.** One multilingual model ranks Wikipedia edits better than ORES and flags anonymous
editors less, but "fair" is judged against patrollers' own reverts, and the score is not a probability.

**Time.** About 18 minutes of talk, the rest of the 25 for questions; `S` opens the speaker view with the timer. Each slide below
gives:
- its time window;
- what to say beyond what is printed.

---

## 1 · Who gets flagged on Wikipedia? (0:00–0:30)

- KDD 2023 paper by Wikimedia Foundation researchers and two universities. It proposes a replacement for the model
  that ranks Wikipedia edits for human review.
- Two stories: it ranks better in more languages, and it measures who pays for that, namely anonymous editors.
- It is the paper our joint MSc thesis starts from.

## 2 · ORES ranked edits for patrollers, with three gaps (0:30–2:00)

- Wikipedia is the eighth most visited site, and around 16 pages are edited every second. Patrollers can't read
  everything, so they need a ranked queue.
- ORES's "damaging" model provided that queue.
- The three gaps are the paper's own list:
  - language coverage;
  - precision;
  - bias against anonymous editors.
- Bias matters beyond fairness: the paper links it to newcomers leaving and the shrinking number of active editors.
- Colour code for the rest of the talk: blue is ORES, orange is this paper.

## 3 · Task: will this edit be undone? (2:00–3:45)

- The label comes from Wikimedia's edit history: an edit counts as reverted if a later edit restored an earlier
  version of the page. No one labels anything by hand.
- The problem is edit wars. The authors say about half of the reverted edits in a war are good-faith attempts to
  remove vandalism, and nothing automatic can tell which half.
- Their rule, walk through the diagram:
  - edit 2 drops out of the data because the edit that undid it was itself undone;
  - edit 3 keeps the label "reverted" because its reverter survived.
- So the label records who had the last word, not who was right. Keep that in mind for the fairness part.

## 4 · Anonymous edits are reverted 8× as often (3:45–5:15)

- The data: the 47 most edited Wikipedias, 2022. Train on January–June, test on the week right after.
  Portuguese and Kazakh are left out because they don't allow anonymous edits.
- The gap: an anonymous edit is reverted about 8× as often as a logged-in one, 7.93 exactly. Measured on the test
  week, on the languages ORES covers, because that's where the paper compares the two.
- Remember 7.93: every fairness number later is compared against it.
- Right panel, one dot per language (Polish right next to English), with a straight-line fit: more anonymous
  editing, more reverts. Not one wiki's quirk.
- So "who edited" is a strong signal: good for accuracy, and the root of the fairness problem.

## 5 · Text models first, then boosted trees (5:15–7:00)

- Stage 1 is four multilingual BERT models:
  - three read the inserted, removed and changed text and predict a revert;
  - the fourth predicts a page's revert rate from its title.
- An edit can touch several pieces of text, so each model's scores are pooled with mean and max.
- Stage 2 is CatBoost, on those scores plus metadata: who edited, which wiki, size of the change, and so on.
- Why two stages: only about 56% of test edits change any text at all. The rest touch media, references or
  markup, so text models alone can't score every edit.
- The two stages train on different pages, 60/40, so CatBoost never sees scores from text the BERTs memorised.

## 6 · Better than ORES, most of all on anonymous edits (7:00–8:15)

- AUC: 0.5 is random order, 1 is every reverted edit first.
- The grey bar is a trivial rule that flags every anonymous edit. It already gets 0.75, which shows how much "who
  edited" carries on its own.
- On all edits: 0.88 against ORES's 0.84.
- The bigger gain is on anonymous edits alone: 0.79 against 0.70. ORES leans on who made the edit, which tells it
  nothing among anonymous edits; the new model looks at what the edit changed.
- On languages ORES never covered it gets 0.87, about as good. Coverage goes from 28 to 47 languages.

## 7 · The strongest signal is who made the edit (8:15–9:45)

- The bars are average SHAP values: how far each feature pushes an edit's score, measured in log-odds.
- The top feature is whether the editor is logged in, and five of the top eight describe the editor.
- The text models appear once, in sixth place, as the page-title model.

## 8 · “Who edited” helps ranking and triples the gap (9:45–11:45)

- The formula at the top is the disparate impact ratio, DIR: share of anonymous edits flagged over share of
  registered ones, flagged meaning above the cut-off. Each bar is one model's DIR.
- The dashed line is 7.93, the same ratio computed on the true labels.
- ORES sits at 20, two and a half times the gap in the data, so it exaggerates it.
- Without editor features the paper's models flag anonymous edits only 2–3× as often, under the data's gap.
- Adding "who edited" lifts AUC from 0.84 to 0.88 and DIR from 3.1 to 9.5. The ranking gain is paid in
  disparity, though it stays far below ORES.

## 9 · What should the gap be? (11:45–13:30)

- There are two defensible targets:
  - 1×: flag both groups equally;
  - 7.93×: mirror the reverts. The paper picks this one in a footnote: "the closer to 7.93, the better."
- A revert is a patroller's judgement, not proof of vandalism. Mirroring the reverts makes those judgements the
  definition of fair: if they are biased, the bias becomes the target.

## 10 · What we build on this paper (13:30–14:45)

- One joint MSc thesis, vandalism detection on Wikipedia. Each of us leads one part.
- The shared aim is to try modern open models up to 7B and understand how they behave across languages.
- My part is calibration: scores that are easier to interpret and compare (more on slide 12). I also check the
  score against Wikipedians' hand labels for bad faith and poor quality: a revert isn't proof of bad faith, and
  these labels show how often good-faith edits get flagged.
- Przemysław's is distillation: training large models is feasible, but deploying them needs very efficient
  inference. He compares classical distillation with newer methods such as Angular-KD.
- Step 0 for both of us is reproducing this paper.

## 11 · Reproduced: our numbers land on the paper's (14:45–16:00)

- Retrained both stages ourselves from the authors' public data and code. Each dot is one number: the authors'
  value across, ours up. On the diagonal means the same number.
- Panels 1–3, the whole model in six configurations, our trees on our own text models: AUC within about 0.005,
  precision within 0.008, DIR within 0.05.
- Last panel: the stage-1 text models from slide 5, each scored on its own (Table 2). Fine-tuned on a GPU cluster
  (about 20 GPU-hours), they land at or above the paper by up to 0.03, which is why most dots in panels 1–3 sit
  a hair above the diagonal. Two of our runs with identical settings differ by up to 0.025, and the paper reports
  single runs.
- If asked: on the authors' published text features instead, our trees match within 0.0015 AUC. The three
  configurations without text models don't read BERT scores, so for them it makes no difference.

## 12 · Making the score mean what it says (16:00–18:00)

- The model ranks well, but its score is not a probability, and the paper never checks this.
- Measured on our copy of the paper's model, test week, all 1.08M edits grouped by score: of edits scored 0.5,
  7% get reverted; of edits scored 0.9, 40%.
- Why: balanced class weights make each reverted edit count about 12× a normal one, so the model learns a world
  where half of all edits are reverted, while really about 7% are.
- AUC can't see this, because the order of edits doesn't change. It matters as soon as someone reads the score
  or picks a threshold, and every wiki picks its own.
- My plan has two routes: fix the score after training, or change the training, for example with label
  smoothing. The thesis compares the two.
- The simplest fix, just undoing the class weights, already puts the line almost on the diagonal: ECE from 0.235
  to 0.006.

Thank you. Questions?

---

## If asked

- **How exactly does the edit-war filter work?**
  - The authors' code takes each edit's first reverting edit. If that edit was itself reverted, the original edit
    is dropped.
  - In their own notebook for English Wikipedia, January–July 2022: 18% of reverted edits had a reverter that was
    later reverted, and the filter dropped 1.7% of all edits.
  - The paper's text describes the rule a little differently from its Figure 3. The code follows the figure.
- **Is the new model fast enough?**
  - 1,000 edits were sent one at a time to Lift Wing's staging cluster, on CPU only: median 1.0 s, 75th percentile
    1.7 s, 95th percentile 4.0 s. That is the whole API response, including fetching the edit.
  - ORES's paper reported 1.1, 1.2 and 1.9 s. The authors call the two comparable, with long text changes slower.
- **What does better AUC mean in practice?** At 75% recall, 28% of the edits a patroller opens are real reverts,
  against ORES's 22% (Table 3).
- **How big is the data?**
  - Training: 8.6M edits from all users (17% anonymous, 8% reverted) and 3.7M anonymous-only edits (28%
    reverted), January to June 2022.
  - Test: 1.08M edits from the following week (19% anonymous, 7% reverted).
  - At most 300K training and 100K test edits per language.
- **How stable is DIR?**
  - Not very. In the reproduction we fed the best model, unchanged, the text scores from the BERTs tuned on
    anonymous edits instead: same edits, same labels.
  - AUC barely moves (0.879 against 0.875), but DIR drops from 9.6 to 6.6, below the 7.93 target.
  - The swap shifts the scores, so fewer anonymous edits cross 0.5. DIR depends on the level of the scores, which
    is calibration, not ranking.
  - For the same reason DIR always belongs to one cut-off: a different one gives a different DIR, and the paper
    reports one number per model.
- **Is it just the class weights?**
  - Almost entirely, for this model. On the test set, all 47 wikis, its ECE is 0.235 on raw scores and 0.006 after
    simply undoing the class weights.
  - Per group: from 0.464 to 0.024 for anonymous editors and from 0.179 to 0.002 for registered ones.
- **Does calibration change fairness?**
  - Not by itself. Any order-preserving rescaling plus a matching threshold flags exactly the same edits.
  - What calibration adds is that a threshold means the same risk on every wiki and in every group.
- **What is Angular-KD?**
  - It distils from one teacher as if there were several: small heads on the teacher produce varied versions of
    its output, kept apart by angle but close to the original.
  - It is from NeurIPS 2025. The authors tested it only on images, so whether it transfers to text is part of
    Przemysław's work.
- **Why does the AUC axis start at 0.5?** 0.5 is random order, and every model here is above it. From zero, the
  gaps would be invisible.
- **Why not just compare F1?**
  - At the default threshold of 0.5, the paper's best model has 4.5% lower Macro-F1 than ORES.
  - The authors set it aside because F1 needs a threshold, and each wiki chooses its own based on patrollers'
    workload. AUC compares ranking across all thresholds.
  - Fair for comparing rankings, but patrollers do work at a threshold. That is one reason calibration matters.
- **What are the paper's limits?**
  - One test week, single runs, so no error bars.
  - mBERT is the only text model tried; the authors list this as a limitation themselves.
  - Only 56% of edits change any text. Changes to references, media or tables get no text score.
