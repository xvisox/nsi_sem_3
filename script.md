# Script: Who gets flagged on Wikipedia?

The whole talk written out, slide by slide. It runs about 2,200 words, which is under 20 minutes at a calm 115 words a
minute, so the windows below end at 18:00 and leave time to point at the charts. `speech.md` has the same talk as short points: learn from this file, present from that one or from the
slides alone. Each heading gives the slide and the time it should start and end.

---

## 1 · Who gets flagged on Wikipedia? (0:00–0:30)

Hello everyone, I'm Hubert Michalski. I'll present a KDD 2023 paper by researchers from the Wikimedia Foundation
and two universities: "Fair Multilingual Vandalism Detection System for Wikipedia".

It tells two stories. The new model ranks edits better than the old one, in more languages. And the authors
measure who pays for that: anonymous editors.

It's also the starting point for the MSc thesis I'm writing with Przemysław.

## 2 · ORES ranked edits for patrollers, with three gaps (0:30–2:00)

Wikipedia is the eighth most visited website in the world, and around sixteen pages are edited every second. Most
edits are fine. Some are vandalism.

Catching it is the job of patrollers: volunteers who check new edits by hand. They can't read all of them, so they
need a queue with the most suspicious edits at the top.

In 2022, that queue was sorted by ORES, Wikimedia's machine learning service. In this talk, ORES is always blue.

The paper names three problems with it. First, ORES covered 28 languages with a separate model for each, so it is
hard to extend. Second, it reads text only through fixed word lists, like lists of bad words. Third, it flags
anonymous editors more.

The third one matters beyond fairness. Earlier research found that quality control and its automatic tools are a
big reason why newcomers leave, and the number of active editors on Wikipedia is going down.

On the right, in orange, is this paper: one model for 47 languages, a multilingual BERT that reads the change
itself, and a report of its own bias against anonymous edits.

And that's the question of the whole paper: can one model rank edits better than ORES, and be fairer to anonymous
editors?

## 3 · Task: will this edit be undone? (2:00–3:45)

The task is: given a new edit, predict whether it will be undone. If a later edit brings the page back to an
earlier version, the first edit counts as reverted.

These labels are free. Wikimedia's edit history already records every revert, so nobody labels anything by hand,
and you get millions of examples in 47 languages.

But edit wars make them noisy. Look at the diagram. Edit 2 is a contested change. Edit 3 undoes it, and then
edit 4 undoes edit 3. So who was the vandal? The authors say that in edit wars, about half of the reverted edits
are good-faith attempts to remove vandalism. And nothing automatic can tell which half.

So they use a simple rule. Edit 2 is excluded, because the edit that reverted it, edit 3, was itself reverted.
Edit 3 stays in, labelled "reverted", because its reverter, edit 4, was never undone. Edits 1, 4 and 5 are not
reverted.

They also leave out bots, page creations, and talk and user pages.

Remember one thing for later: this label records who had the last word, not who was right.

## 4 · Anonymous edits are reverted 8× as often (3:45–5:15)

The data covers the 47 most edited Wikipedias, in 2022. The model trains on January to June and is
tested on the week right after. Portuguese and Kazakh were left out, because they don't allow anonymous edits.

And in that data there is a big gap. An anonymous edit gets reverted about eight times as often as an edit by a
logged-in user: 7.93 times, to be exact. That's measured on the test week, on the languages ORES also covers,
because that's where the paper compares the two models.

Please remember this number. Every fairness result later in the talk is compared against it.

The chart on the right shows that this isn't one wiki's quirk. Each dot is one language. Further right means more
edits made without logging in, higher up means more edits reverted. Polish is here, right next to English. The
dashed line is a straight-line fit: the more anonymous editing a wiki has, the more of its edits get reverted.

So "who edited" is a very strong signal. That's good for a model's accuracy. And it's exactly where the fairness
problem comes from.

## 5 · Text models first, then boosted trees (5:15–7:00)

Now the model itself. It has two stages.

Stage one is about text. The authors fine-tune four multilingual BERT models, mBERT for short. One mBERT covers
all 47 languages, which is the point. Three of these models read the edit: the inserted text, the removed text,
and the changed text, before and after. Each one predicts whether the edit gets reverted. The fourth model reads
only the page title and predicts how often that page gets reverted.

One edit can touch several places in a page. So each model scores every piece, and the scores are pooled with
mean and max.

Stage two is CatBoost, which is gradient boosted trees. It gets the text scores plus metadata: who edited, which
language, how big the change is, and so on. Its output is the revert risk, a score from 0 to 1.

Why not just a text model? Because only about 56% of edits change any text. The rest change things like
references, media or tables. A text model can't score those, but the trees still can.

One more detail. The training data is split by page, sixty to forty, between the two stages. So CatBoost never
learns from scores on pages the BERT models were fine-tuned on.

## 6 · Better than ORES, most of all on anonymous edits (7:00–8:15)

So does it beat ORES? The paper compares models with AUC. It measures ranking, so it needs no threshold: 0.5 is random order, and 1
means every reverted edit is ranked first.

Start with the grey bar. It's a trivial rule: flag every anonymous edit, and nothing else. It already gets 0.75.
That's how much "who edited" carries on its own.

On all edits, ORES gets 0.84, and this paper's model gets 0.88.

The bigger gain is on anonymous edits alone: from 0.70 to 0.79. ORES leans heavily on who made the edit, and
among anonymous edits that tells it nothing. The new model reads what the edit changed.

And on the languages ORES never covered, the model gets 0.87, about as good. So coverage goes from 28 to 47
languages.

## 7 · The strongest signal is who made the edit (8:15–9:45)

To see which features the model relies on, the authors use SHAP. SHAP splits each prediction into one
contribution per feature. Average their size over all edits, and you get how much each feature matters: that's
the length of each bar.

The model has 137 features, and these are the top eight. The colour shows the kind: who edited, a text model, or
metadata about the edit.

At the top is whether the editor is anonymous. And five of the top eight are about the editor: anonymous or not,
and which user groups they're in, like autopatrolled or administrator.

The text models, the expensive part of the system, show up only once, in sixth place. And that's the page-title
model, not one that reads the edit.

The authors say they weren't surprised, given the 0.75 of the anonymous-only rule on the last slide.

## 8 · “Who edited” helps ranking and triples the gap (9:45–11:45)

This is the paper's main fairness result, from Table 5.

It's measured with the formula at the top, the disparate impact ratio, or DIR: the share of anonymous edits that
get flagged, divided by the share of registered edits that get flagged. "Flagged" means the score is above the
cut-off. So each bar says how many times as often a model flags anonymous edits as registered ones. On the
right is each model's AUC on all edits, so you can see ranking and fairness side by side.

The dashed line is our 7.93: the same ratio, but computed on the true labels, on how often edits are really
reverted.

Start at the top. ORES flags anonymous edits twenty times as often as registered ones. That's two and a half
times the gap in the data. So ORES doesn't just reflect the gap, it exaggerates it.

Next are the paper's models without any features about the editor. Trained on anonymous edits only, or on all
edits, they flag anonymous edits two to three times as often. That's below the gap in the data.

Then the authors add who edited. AUC goes up from 0.84 to 0.88, the best result in the paper. But DIR goes from
3.1 to 9.5. It triples.

So the ranking gain is paid for in disparity. It's still less than half of ORES. But 9.5 is above 7.93, so the
gap in the model's flags is bigger than the gap in the reverts.

## 9 · What should the gap be? (11:45–13:30)

What should DIR be, then? There are two answers you can defend.

The first is 1: flag both groups equally, whatever their revert rates. In the fairness literature, that's
demographic parity.

The second is 7.93: flag each group as often as it really gets reverted, so mirror the data. The paper picks this
one, in a footnote: "the closer to 7.93, the better."

The problem is where 7.93 comes from. It comes from reverts, and a revert is a patroller's judgement, not proof of
vandalism. If those judgements are biased against anonymous editors, then mirroring them makes that bias the
target.

## 10 · What we build on this paper (13:30–14:45)

That's the paper. Now our own work. Przemysław Fuchs and I are writing one MSc thesis together: vandalism detection on Wikipedia. Each of us leads
one part of it.

Our shared aim is to try modern open models, up to seven billion parameters, and understand how they behave
across languages.

My part is calibration: scores that are easier to interpret and to compare. I'll come back to this in a minute.
I'll also check the score against Wikipedians' hand labels for bad faith and poor quality. A revert isn't proof of
bad faith, and these labels show how often good-faith edits get flagged.

Przemysław's part is distillation. Training large models is feasible, but deploying them needs very efficient
inference. He compares classical distillation with newer methods, such as Angular-KD.

And step zero for both of us is to reproduce this paper.

## 11 · Reproduced: our numbers land on the paper's (14:45–16:00)

We retrained both stages ourselves, from the authors' public data and code. Each dot is one number from the paper:
the authors' value across, ours up. A dot on the diagonal means we got the same number.

The first three panels are the whole model in its six configurations: our trees on top of our own text models. AUC
matches within about 0.005, precision within 0.008, and DIR within 0.05.

The last panel is stage one alone, the text models from slide 5. We fine-tuned them on a GPU cluster, about twenty
GPU-hours. Ours land at or above the paper, by up to 0.03, which is also why most dots in the first panels sit a
hair above the diagonal. That's run-to-run noise: two of our runs with identical settings already differ by up to
0.025, and the paper reports single runs.

So the paper's numbers hold up.

## 12 · Making the score mean what it says (16:00–18:00)

The model ranks well, but its score is not a probability, and the paper never checks this.

First, what does calibrated mean? Take all the edits that get a score of 0.3. If the model is calibrated, 30% of
them get reverted. That's the diagonal.

The orange line is what I measured on our copy of the paper's model. I took all million edits of the test week,
grouped them by score, and counted how many in each group were really reverted. Of edits scored 0.5, only 7% get
reverted, not 50%. Even of edits scored 0.9, it's 40%. The model overstates the risk everywhere.

The reason is the training. The paper uses balanced class weights: each reverted edit counts about twelve times as
much as a normal one, so both classes weigh the same. The model learns a world where half of all edits get
reverted, while really about 7% do.

And AUC can't see this problem at all, because the order of the edits doesn't change. It matters as soon as
someone reads the score as a probability, or picks a threshold, and every wiki picks its own.

My plan has two routes. The first is to fix the score after training, and the simplest fix, just undoing the
class weights, already puts this line almost on the diagonal. The second is to change the training itself, for
example with label smoothing. The thesis compares the two.

Thank you. I'm happy to take questions.
