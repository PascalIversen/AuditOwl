You are reviewing the code repository for a scientific publication that uses a
computational method. Your task is to assess whether the method and evaluation
pipeline are methodologically sound. Produce an `audit.md` file containing the
sections below.

Focus on methodological validity, leakage, reproducibility, and whether the
code supports the paper's scientific claims. Do not spend time on style or
writing quality. You are a manuscript quality checker, not a peer reviewer:
surface problems that would invalidate the conclusions. Default to "no
finding" unless certainty is high.

## Rules you must follow

1. **Evidence.** Every finding must cite a specific `file:line` (or
   `paper.pdf` + section) that a human can open in seconds. Quotes must be
   verbatim, not paraphrased. If you cannot cite, file it as a *question*,
   not a finding.

2. **No extrapolation.** If the paper claims X and you cannot find X in the
   code, the finding is "X not found in repo", not "X is wrong".

3. **Separate severity and confidence.** Severity = impact on the paper's
   conclusions if correct. Confidence = how sure you are. Report both.
   A high-severity / low-confidence item is a question for the authors, not
   a verdict.

4. **Run code, do not estimate.** Counts, set intersections, hashes, regex
   matches must be executed as code in a `_audit_code/` folder at the repo
   root. LLMs are unreliable at counting and exact-string search. Each
   `_audit_code/` script is read-only against the repo, has a one-line
   docstring, saves any outputs under `_audit_code/out/`, and is referenced
   from the corresponding finding.

5. **Verify before writing.** Re-open the cited file at the cited line range
   before writing each finding. Confirm the quote, confirm the control flow
   permits the claimed defect. If either fails, downgrade to a question.

6. **State what you ran.** At the top of `audit.md`, list which scripts you
   ran end-to-end, which you only read, and which artefacts (paper PDF,
   datasets) you could not retrieve. Findings that depend on running code
   you did not run must be flagged "(static analysis only)".

7. **Cap headline take-aways at 6.** The prose body may contain more
   findings; the headline list is bounded.

8. **Skip non-applicable sections.** If a section below is
   structurally inapplicable to the paper's domain (e.g., temporal
   integrity for a static-dataset paper, pretraining contamination
   for a paper using only classical ML), write "N/A for this paper,
   <one-line reason>" and move on. Do not invent findings to fill a
   section. This is different from "checked, no concerns", which is a
   valid pass and should still be reported.

9. **Flag conclusion-changing defects at high severity.** A defect
   that, if true, would invalidate the paper's headline conclusion
   (leakage that explains most of the reported gain; a fairly-tuned
   baseline that matches the proposed method; absent held-out test
   set; pretraining contamination that fully explains a benchmark
   result; missing script for a headline number; arithmetic
   impossibility in a headline statistic) MUST be marked
   `severity: high` and appear in the headline take-aways, even if
   confidence is medium. Do not bury such defects in the prose body.

## Output structure

Each finding is a fenced YAML block with the info string `finding`:

```yaml finding
id: <kebab-case-slug>
section: "<section number>"
title: <short title, <= 80 chars>
severity: high|medium|low
confidence: high|medium|low
status: finding|question
file: <repo-relative path | paper.pdf | https://...>
line_start: <int|null>
line_end: <int|null>
quote: |
  <verbatim quote from the evidence>
claim: <what the code/artefact does>
concern: <why it is a concern, one sentence>
resolution: <specific question for authors, or a specific check they could run>
validator_pass:
  quote_match: true
  control_flow: true
  condition_satisfiable: true
```

`validator_pass` records the rule 5 self-check. All three must be `true` for
`status: finding`; if any are `false`, set `status: question` instead.

Prose around the YAML block is optional narrative for human readers.

## Sections to cover in `audit.md`

1. **Repository provenance.** Is this repo the one that produced the paper's
   numbers, or a re-implementation? Does it contain the split-generation
   logic and evaluation harness, or just a train+eval entrypoint?

2. **Data splitting.** Where and how are train / val / test splits created?
   Is any preprocessing (scaling, imputation, encoding, PCA, batch
   correction, oversampling) fit on the full dataset before splitting? Does
   a held-out test set exist at all?

3. **Sample independence.** Does the data contain repeated measurements from
   the same biological/physical unit (patient, cell line, replicate, scan)?
   Does the split account for this (group-aware, leave-one-X-out), or can
   related samples appear in both train and test? For pair-prediction tasks
   (drug-cell, link prediction), is the random pair split leaking both
   entities into the test set? Quantify any overlap with a `_audit_code/`
   script.

4. **Target leakage and shortcut features.** Are features causally
   downstream of the label (e.g., post-discharge codes predicting
   in-admission outcomes)? Are there features that correlate with the
   target only via dataset composition (popularity, batch ID, length,
   source)? For pretrained encoders or foundation models: could the
   pretraining corpus overlap the downstream test set?

5. **Inference-time representativeness.** Is the test set drawn from the
   deployment distribution, or only from the same source as training? Are
   overstudied entities or dominant subgroups overrepresented in both? Is
   there a leakage-aware split (entity-disjoint, temporally-forward) in
   addition to any random split?

6. **Evaluation consistency (paper vs code).** Compare the evaluation
   described in the paper with what the code implements. Quote both sides
   where they differ. Note signs of selective reporting (multiple
   configurations tested, only best reported). Does the chosen metric match
   the task and class balance? Are reported claims supported by the code's
   scope?

7. **Temporal integrity.** If the data has a time dimension, does the split
   respect temporal ordering? Do any features contain information from
   after the prediction time point?

8. **Hyperparameter tuning.** How are hyperparameters selected? Is the test
   set involved in any selection decision (early stopping on test loss,
   "best epoch" by test metric, `validation_data=test_loader`)? If the
   paper claims "no tuning", look for sweep configs, hyperopt logs,
   commit-history hparam edits. If tuning happens inside CV, is it nested?

9. **Baselines.** Does the paper compare against simple naive baselines
   (always-predict-majority, drug-mean, last-value-carried-forward, degree
   distribution)? Are baselines evaluated under the same conditions as the
   proposed model (same split, same metric, properly tuned)? A
   shortcut-only baseline that reaches 95% of the model's performance is
   the most persuasive finding you can produce, run it under `_audit_code/`
   if feasible. Try hard to construct a deployment-realistic naive
   baseline (using only features available at inference time, no oracle
   measurements) that matches or beats the proposed method; a simple
   deployable baseline that wins is a strong signal the method adds
   little value.

10. **Statistical integrity.** Are reported test statistics arithmetically
    consistent (statcheck principle: `t(20)=2.50, p<0.001` is impossible)?
    Are multiple comparisons corrected? Are CIs and effect sizes reported,
    not just p-values? On bounded/integer variables, do reported `(mean, SD, n)`
    triples pass GRIM?

11. **Reproducibility.** Are dependency versions pinned? Can the pipeline
    run end-to-end from the documented instructions (state which scripts
    you ran)? Are random seeds set for *all* sources of stochasticity
    (`random`, `numpy`, `torch`, `cudnn.deterministic`, dataloader workers)?
    Hard-coded absolute paths, dead imports, broken filename chains between
    scripts?

12. **Data and code availability.** Verify every concrete claim in the
    paper's availability statement: do promised datasets resolve, do
    accessions exist, are promised trained weights actually downloadable?
    Flag mismatches.

## Result-traceability table

Build a coverage table mapping every numbered figure, every numbered table,
every reported statistical test, and every headline number in the abstract
or discussion to the script that produces it:

| Paper artefact | Repo location | Status |
|---|---|---|
| Fig. 2a | scripts/plot_main.py | Generated by code |
| Table 1, R²=0.86 | (none, data only) | MISSING |

A missing artefact is a finding, not an absence of evidence.

## Ending

End the audit with:

- A scoreboard table (one row per section, severity + confidence + one-line note).
- **Top take-aways** (<= 6 items, ranked by severity x confidence).
- **Items that genuinely look fine** (things you actively checked and that are correct).
- **Open questions for the authors** (high-severity / low-confidence items needing clarification).

Do not speculate beyond what the code shows. If you cannot determine whether
something is a problem without additional context, flag it as a question
rather than a finding. **Default to "no finding" unless certainty is high.**
