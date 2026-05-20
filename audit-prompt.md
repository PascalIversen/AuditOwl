You are reviewing the code repository for a scientific publication that uses
a computational method. Your task is to assess whether the method and
evaluation pipeline is methodologically sound. Work through the repository
systematically and report your findings.

Focus on methodological validity, leakage, reproducibility, and whether the
code supports the paper's scientific claims. Do not spend time on style,
novelty, or writing quality unless they affect the claims or the evaluation.
Surface problems that would invalidate the conclusions; ignore minor issues and
limitations the authors have already acknowledged.

Create an `audit.md` file containing the sections below. The output is
intended to be read by a human expert who will verify each finding before
acting on it. Optimise for verifiability: every claim should be checkable
in minutes, not hours.

================================================================
0. HOW TO AUDIT, RULES YOU MUST FOLLOW THROUGHOUT

These rules apply to every section below. They exist because LLM-based
audits hallucinate, double-count, over-grade under user pressure, and
produce confident verdicts on top of fabricated reasoning.

A. EVIDENCE RULE.
   Every concrete finding MUST point to a specific, verifiable location
   the reviewer can open in seconds. Acceptable forms:
     - file path + line range (e.g. `src/train.py:42-58`),
     - a git-tracked artefact identified by commit hash + path,
     - a URL that you actually retrieved (not one you guessed plausible).
   If you cannot point to such a location, do NOT call it a finding,
   call it a *question* instead. Quotes from the code should be verbatim,
   not paraphrased. A claim is grounded only if the evidence at the
   pointed-to location *fully* entails it; partial correctness is not
   enough.

B. NO-EXTRAPOLATION RULE.
   Do not infer a defect from one section that you have not verified in
   the code. Do not infer a defect from the paper's prose alone. If the
   paper claims X and you cannot find X in the code, the finding is
   "X not found in repo", NOT "X is wrong". Do not produce verdicts for
   things outside the audited artefact's scope, even if those statements
   would be factually correct in isolation, that counts as a
   hallucination here.

C. SINGLE-OWNER RULE (anti-double-counting).
   A single underlying defect often touches multiple categories below.
   Pick one category as the primary owner of that finding. In the other
   categories, *cross-reference* it ("see §N finding N.x"); do not
   re-grade it. The scoreboard at the end should not double-count.
   Common collisions:
   - Random pair-split: primary owner is §3 (sample independence),
     not §2 (data splitting); §2 just notes "random row split, see §3".
   - Test-as-validation: primary owner is §9 (hyperparameter tuning),
     cross-referenced from §6 (evaluation consistency).
   - Foundation-model pretraining/test overlap: primary owner is §4
     (target/shortcut features), cross-referenced from §11 (figure
     reproducibility) when figures are produced by foundation-model
     embeddings.

D. SEPARATE SEVERITY FROM CONFIDENCE.
   - *Severity* describes the impact on the paper's conclusions if the
     finding is correct: high / medium / low.
   - *Confidence* describes how sure you are the finding is correct:
     high / medium / low.
   Report both. A high-severity / low-confidence finding is a question
   to put to the authors, not a verdict.

E. EXECUTABILITY STATEMENT.
   At the start of the audit, state explicitly:
   - Which scripts (if any) you ran end-to-end.
   - Which scripts you read but did not run (and why, missing data,
     missing dependencies, GPU required, etc.).
   - Which artefacts you retrieved from outside the repo (paper PDF,
     external dataset, Zenodo archive) and which you could not.
   Findings that depend on running code that you did not actually run
   must be flagged "(static analysis only)".

F. DOWNGRADE WHEN AMBIGUOUS.
   When the evidence is consistent with both a benign and a problematic
   reading, choose the lower-severity grade and note the ambiguity. A
   reviewer can re-grade upward with new evidence; an over-graded
   finding is harder to retract once it has propagated. Default to "no
   finding" unless certainty is high.

G. ANSWER STRUCTURE PER FINDING.
   Each finding MUST be emitted as a fenced YAML block with the info
   string `finding` (see Appendix B and `references/findings-schema.md`).
   The block carries these fields, each of which corresponds to a
   verifier action:
   - `claim`: what the code does (verbatim quote in `quote` + `file` +
     `line_start`/`line_end`).
   - `concern`: why it is a concern (one sentence).
   - `severity` / `confidence`: separate ratings, see D.
   - `resolution`: a specific question for the authors, or a specific
     check the authors could run.
   - `cross_refs`: pointers to the same finding mentioned elsewhere.
   Prose around the YAML block is optional narrative; the block itself
   is authoritative and is what downstream tools consume.

H. RESULT-TRACEABILITY RULE.
   Every quantitative claim, figure, table, and statistical test in
   the paper should be traceable to a specific script, function, or
   notebook in the repository that produces it. Build a coverage table
   as part of the audit:

      | Paper artefact         | Repo location           | Status                |
      |------------------------|-------------------------|-----------------------|
      | Fig. 2a                | scripts/plot_main.py    | Generated by code     |
      | Fig. 3 (per-fold bars) | (none)                  | MISSING               |
      | Table 1, R²=0.86       | (none, data only)      | MISSING               |
      | Table 1, MSE column    | scripts/cv_eval.py:120  | Generated by code     |
      | Wilcoxon p-values      | (none)                  | MISSING (no test code)|
      | Ablation Tab. S2       | scripts/ablate.py       | Generated by code     |
      | Bootstrap CIs (Fig 4)  | (none)                  | MISSING               |

   Cover at minimum: every numbered figure, every numbered table,
   every reported statistical test (t-test, Wilcoxon, ANOVA, bootstrap
   CI, permutation, etc.), every headline number quoted in the
   abstract or discussion, and every ablation. If an artefact is not
   produced by any script in the repo, list it as MISSING, do not
   guess that "it was probably done in a notebook that wasn't
   committed". A missing artefact is a finding, not an absence of
   evidence.

   This table is the single most load-bearing artefact of the audit;
   everything else flows from it.

   Statistical-test scripts are an especially common omission: the
   paper reports a p-value but the repo contains no code that produces
   it. Treat that as a §14 finding ("statistical claim made without
   reproducible test code"), not a footnote.

I. DETERMINISTIC vs SEMANTIC SPLIT.
   Bifurcate every check by what kind of evidence it requires:

   - **Deterministic checks** (greps, file-existence, AST queries,
     regex, hash comparisons, JSON-schema validation, set-intersection
     between train/test IDs, numeric range assertions, line-count and
     token-count) MUST be executed as code. Their outputs are
     higher-confidence than any prose interpretation you can produce.
     LLMs are unreliable at counting, exact-substring search, and
     numeric comparisons, do not estimate these. If a constraint can
     be verified by code, you MUST run code, not reason about it.
   - **Semantic checks** (does feature X plausibly cause leakage given
     the task; does the implementation match the algorithm described;
     does this metric fit this class balance) require domain reasoning.
     These are lower-confidence and should be flagged as such.

   When you would otherwise estimate a count, a length, a hash, or a
   set-membership, write a small script under `_audit_code/` instead
   (see rule K). High verdict consistency is *not* evidence of correct
   reasoning, it can mask fabricated justifications.

J. VALIDATOR PASS BEFORE WRITING EACH FINDING.
   Before writing any finding to `audit.md`:
   1. Re-open the file at the line range you are about to point to.
   2. Confirm the verbatim quote still matches.
   3. Confirm the surrounding control flow / data flow / scope is
      consistent with the claimed defect (e.g., a "leakage from train
      to test" claim requires the variable order, scope, and data flow
      to actually permit that flow).
   4. If the path the finding describes involves multiple branches or
      conditions, confirm the union of conditions is satisfiable.
   5. If any check fails, drop the finding or downgrade it to a
      *question*. Do NOT keep the finding because the verdict "feels
      right", that is the failure mode this rule guards against.

   This pass empirically eliminates roughly 70–80% of LLM-audit false
   positives in published evaluations of LLM code-audit agents.

K. THE `_audit_code/` FOLDER.
   Feel free to implement small checks and tests, naive baselines,
   train/test ID intersections, p-value floors, file-existence tests,
   shape consistency between predictions and ground-truth files,
   shortcut-only baselines, label-shuffle sanity checks. **Always
   write the code in a separate `_audit_code/` folder at the
   repository root.** Never modify the repo's own scripts. Each
   `_audit_code/` script:
   - Runs read-only against the repo (no in-place modification).
   - Has a one-line docstring stating what it checks and which
     finding it supports.
   - Saves any outputs (CSV, JSON, plots) under `_audit_code/out/`.
   - Is referenced by file:line from the corresponding finding.
   Think of `_audit_code/` as your worked-out evidence. If a reviewer
   wants to verify a finding, they should be able to `cd _audit_code
   && python check_xyz.py` and see the same output you saw.

L. BOUNDED OUTPUT.
   Cap the *Top take-aways* list at the **k=6** most consequential
   findings. Make extra sure that these findings are double-checked. Forcing prioritization is a documented anti-hallucination
   measure. It is fine for the prose body to
   contain more findings, the cap is on the headline list.

M. SCOPE FILTER.
   If a section below is structurally inapplicable to this paper's
   domain (e.g., §7 temporal integrity for a static-dataset paper;
   §4 pretraining contamination for a paper that uses only classical
   ML with no pretrained encoders; clinical/EHR specifics in §4 and
   §7 for a non-medical paper), write "N/A for this paper, <one-line
   reason>" under the section heading and move on. Mark "-" for that
   row in the scoreboard. Do NOT invent findings to fill a section.
   Be conservative: skip only when the section is structurally
   inapplicable, not when the answer is "no concerns found"; the
   latter is a valid finding-free pass and should still be reported.

N. CONCLUSION-CHANGING DEFECTS GO TO THE TOP.
   Any defect that, if true, would invalidate the paper's headline
   conclusion MUST be marked `severity: high` and appear in the
   Top take-aways, even if confidence is medium. Examples:
   - a leakage source that explains most of the reported gain;
   - a fairly-tuned baseline that matches or beats the proposed
     method;
   - absence of a held-out test set when one is claimed;
   - pretraining contamination that fully explains a benchmark
     result;
   - a missing script for a headline number, table row, or figure
     panel (per rule H);
   - statistical-arithmetic impossibility in a headline statistic.
   Do not bury a conclusion-changing defect in the prose body alone.
   If more than six conclusion-changers exist, exceed the rule L
   cap and explain why.

================================================================
0a. UP-FRONT CLASSIFICATION

At the very top of `audit.md`, before any section, record:

- **Reproducibility documentation type (Gundersen R1–R4)**: assign one.
   - R1 = Description only (text).
   - R2 = Code + description.
   - R3 = Data + description.
   - R4 = Code + data + description.
- **Reproducibility tier (Heil)**: assign Bronze / Silver / Gold / Below Bronze.
   - Bronze = data + trained models + code publicly shared in a
     third-party archive (Zenodo, Dryad, model zoo). GitHub-only is
     below Bronze.
   - Silver = Bronze + dependencies installable in one command + key
     analysis details documented (script order, OS, runtime, system
     resources) + all random components made deterministic (seeds set,
     framework determinism flags, weights published).
   - Gold = Silver + entire analysis reproducible from a single
     command (full automation, ideally via a workflow manager such as
     Snakemake or Nextflow).
- **REFORMS modules covered (1–8)**: list the REFORMS modules the repo
  supplies evidence for and the ones it does not.

This classification is informational, not a verdict. It frames the
rest of the audit so the reader knows the floor.

================================================================
1. REPOSITORY PROVENANCE

Before auditing the code, establish whether *this* repository is the one
that produced the paper's reported numbers. A repository that the paper
links to but that does not contain the experimental protocol is a
finding in itself, and it changes the meaning of every other section.

   - Does the README state that this repo is a re-implementation, port,
     or "the best architecture from the paper" rather than the original
     experimental code?
   - Does the repo contain the split-generation logic, cross-validation
     harness, or driver scripts that produce the paper's headline
     numbers? Or only a single train+eval entrypoint?
   - If the paper cites a different repository (e.g. an older TF
     version, a private fork), retrieve that repo and check it has the
     missing pieces. If neither repo contains the protocol, that is the
     primary finding and you should say so explicitly.
   - Is the commit being audited tagged with a version that matches the
     paper submission, or is it a moving `main` branch?

================================================================
2. DATA SPLITTING
   (REFORMS Module 4 + 6a; Kapoor & Narayanan leakage type L1.2/L1.3.)

   - Identify where and how train / test / validation splits are
     created. Quote the call site (file:line).
   - Check whether any preprocessing step (scaling, normalisation,
     imputation, encoding, feature selection, dimensionality reduction,
     oversampling, batch correction, ComBat-style adjustment, PCA) is
     fitted on the full dataset before the split occurs. Component
     weightings for any reduction must be determined from training data
     only, then applied to test.
   - Distinguish "preprocessing fit on full data" (a leakage concern)
     from "preprocessing applied to full data after fitting on train"
     (usually fine).
   - Check explicitly that a held-out test set exists at all
     (Kapoor-Narayanan L1.1, "no test set"). One large empirical
     audit found 45 of 100 neuropsychiatry prediction papers reported
     only in-sample statistical fit, with no held-out test.

================================================================
3. SAMPLE INDEPENDENCE AND IID TEST-SET DESIGN
   (REFORMS Module 6b; Kapoor & Narayanan L3.2; Whalen pitfall 2.)

   - Determine whether the data contains repeated measurements from the
     same biological/physical unit (same patient, same cell line, same
     replicate, multiple slices from the same scan, multiple cells from
     the same donor, multiple frames from the same video).
   - Check whether the splitting strategy accounts for this (group-aware
     split, leave-one-X-out, blocking by chromosome / patient / batch /
     site / family / protein) or whether related samples can appear in
     both training and test. If yes, **quantify the overlap** with a
     `_audit_code/` script, e.g. "X of Y test entities also appear in
     train" with the actual numbers from a `set` intersection.
   - Look for near-duplicate / similarity-based leakage: paraphrased or
     augmented copies, items with high feature- or embedding-space
     similarity, items connected in an underlying graph, or samples
     derived from a common upstream source. Augmentation done before
     splitting puts augmented variants of training samples into the
     test set. Flag explicitly.
   - For tasks predicting relations between pairs (link prediction,
     interaction prediction, drug–cell, recommendation, matching),
     check the split axis. A random pair split typically leaves both
     entities of a test pair already seen during training and only
     tests memorisation. Whalen et al. show auPR can be inflated by
     >0.5 under random CV in graph data with hub structure; the
     decisive diagnostic is **performance survives label shuffling**
     (run a label-shuffle baseline under `_audit_code/` if you can).
   - For tasks where negatives are constructed (link prediction,
     contrastive learning, anomaly detection), check the
     negative-sampling distribution. If negatives differ from positives
     in popularity, degree, length, source, or batch, the model can
     exploit those differences as a shortcut.

================================================================
4. TARGET LEAKAGE, SHORTCUT FEATURES, AND PRETRAINING CONTAMINATION
   (REFORMS Module 6c; Kapoor & Narayanan L2; Whalen pitfalls 3 & 4;
   Lones 2024 "do not allow test data to leak"; Davis et al. 2025 for
   ICD-code label leakage.)

   - Examine the feature set for variables that are direct functions
     of, proxies for, or downstream consequences of the prediction
     target.
   - Distinguish three failure modes; do not conflate them:
       (i)   *Target leakage proper*: features causally downstream of
             the label (e.g., antibiotic prescription used to predict
             sepsis; ICD codes finalised post-discharge used to predict
             in-hospital outcomes).
       (ii)  *Shortcut / surrogate leakage*: features that correlate
             with the target only because of dataset composition
             (popularity, batch ID, source dataset, site, length,
             entity ID, sequencing depth, instrument). Whalen pitfall 3.
       (iii) *Label-construction artefact*: the label itself does not
             measure what the paper says it measures (e.g., right-truncated
             cohorts, median-split on test cohort, surrogate labels
             where one label corresponds to one source). This is NOT
             feature→target leakage; report under §6 (evaluation
             consistency) and cross-reference here.
   - Identify features that are valid in principle but expensive or
     hard to obtain at inference time (manual annotation, oracle
     measurement, experimentally derived structure). If their
     availability correlates with how well-studied a sample is, they
     introduce an inference-time gap.
   - **Pretraining contamination** (foundation models, pretrained
     encoders, downloaded embeddings):
       - Was the pretraining corpus likely to contain, or be highly
         similar to, samples in the downstream test set? The authors
         should report or bound this overlap, not just acknowledge
         that pretraining was used. Explicit warning from the
         literature: "their training data included the test sets
         from community benchmarks."
       - Were embeddings extracted before the train/test split was
         made? (E.g. `compute_embeddings_for_all_cells.py` run before
         `split.py`.)
       - Is the pretraining objective closely related to the downstream
         task such that label-relevant information could be memorised
         in the embeddings (reconstruction over labelled data,
         auxiliary tasks exposing the label)?
       - If frozen pretrained embeddings are used, is performance
         compared to a no-pretraining baseline?
       - For commercial foundation models: nondeterminism of the
         underlying API plus undocumented training-data composition
         makes the comparison unreproducible (REFORMS notes this as a
         "gray area" of ML-based science).

================================================================
5. INFERENCE-TIME REPRESENTATIVENESS AND DISTRIBUTION SHIFT
   (REFORMS Module 8; Kapoor & Narayanan L3.3; Whalen pitfall 1.)

   - Does the paper describe the intended inference-time use case
     (which entities, under what conditions)?
   - Is the test set drawn from the deployment distribution, or only
     from the same source as training? Identify overstudied entities,
     dominant subgroups, or well-resourced sources that are
     overrepresented in both train and test but absent at inference.
   - Look for evidence that the model relies on dataset-specific
     shortcuts: is performance dominated by easy/popular entities? Is
     there a per-subgroup breakdown? (Whalen: predictions tracking
     ancestry / batch / depth / site rather than the biology.)
   - Check whether evaluation includes a leakage-aware split
     (entity-disjoint, group-disjoint, similarity-bounded, temporally
     forward) in addition to any random split. A large gap between
     random and leakage-aware splits is itself a finding.
   - For class-imbalanced or constructed-negative settings, check
     whether the test label distribution matches the inference-time
     distribution. (Whalen pitfall 5.)
   - Whalen's diagnostic / symptom pattern: under improper split,
     "performance will be higher in cross-validation (same setting)
     than on the prediction set (different setting)", flag if no
     such drop is reported despite the data structure suggesting one.

================================================================
6. EVALUATION CONSISTENCY (PAPER vs CODE)
   (REFORMS Modules 5c, 5d, 7a; SciCoQA discrepancy taxonomy.)

   - Compare the evaluation procedure described in the paper with what
     the code actually implements. Quote both sides where they differ.
   - Classify each discrepancy by type (SciCoQA taxonomy):
       - **Difference**: paper and code describe distinct logic.
       - **Paper Omission**: code includes critical components the
         paper does not describe.
       - **Code Omission**: a step described in the paper is absent
         from the code.
   - Check whether all reported experiments are present in the code
     and whether the code contains experiments not reported in the
     paper.
   - Note signs of selective reporting (multiple model configurations
     tested, only best reported; many seeds logged, subset presented;
     "no tuning" claimed but a tuning script exists).
   - Are there overly strong claims in the paper given the code's
     scope?
   - Check whether the chosen metric matches the task and class
     balance. For imbalanced classification flag accuracy without a
     more informative metric (balanced accuracy, F1, Cohen's κ,
     Matthews correlation coefficient, ROC-AUC, PR-AUC). For
     regression / time-series forecasting, RMSE alone can be beaten by
     "always predict no change". Check for naive baselines (§10).
   - Label-construction artefacts (see §4 (iii)) are reported here.
   - **Exclusions** that do NOT count as evaluation-consistency
     findings: bugs unrelated to the paper's scientific description;
     hyperparameter mismatches when the code supports the paper's
     setting via config/CLI; trivial engineering omissions
     (numerical-stability epsilons).

================================================================
7. TEMPORAL INTEGRITY
   (REFORMS Module 6a; Kapoor & Narayanan L3.1; Lones 2024 "look-ahead bias".)

   - If the data has a time dimension, check whether the splitting
     respects temporal ordering (`TimeSeriesSplit`, blocked CV) rather
     than `KFold`/`train_test_split` with shuffle.
   - Check whether any features contain information from after the
     prediction time point.
   - Look-ahead via preprocessing: scaling to [0,1] before splitting
     reveals the future range; running PCA or ComBat over the entire
     time series leaks future statistics. Flag.
   - For clinical/EHR data, check that diagnostic codes finalised
     post-discharge are not used to predict in-admission outcomes.

================================================================
8. ABLATION STUDIES
   (REFORMS Module 5b, justify model types; Ferrari Dacrema 2019.)

   - Check whether the paper includes ablation or sensitivity
     analyses, and whether they are present in the code.
   - Verify that ablations use the same split and evaluation
     procedure as the main method (avoid cherry-picking).
   - Identify whether design choices (number of layers, kernel size,
     loss function, regularisation strength) are justified by
     empirical evidence or are ad hoc.
   - Look for missing ablations: is preprocessing ablated? Feature
     selection? Architecture? Are the ablations in the code only the
     "favourable" ones?

================================================================
9. HYPERPARAMETER TUNING
   (REFORMS Modules 5d, model selection; 5e, hyperparameter tuning;
   Pineau 2021 ML Reproducibility Checklist: "the range of
   hyper-parameters considered, method to select the best
   hyper-parameter configuration, and specification of all
   hyper-parameters used to generate results"; Lones 2024.)

   - Identify how hyperparameters are selected (grid, random,
     Bayesian, manual).
   - Check whether tuning uses a separate validation set or whether
     the test set is involved in any selection decision (early
     stopping on test loss, "best epoch" chosen by test metric,
     Keras `validation_data` passed the test loader, etc.).
   - Check whether the tuning procedure is fully described in the
     paper: search ranges, number of trials, selection criterion.
   - If tuning happens inside CV, verify it is *nested* (inner loop
     for tuning, outer for evaluation) rather than the same folds.
     Lones is explicit: "Nested CV (double CV) is required when doing
     hyperparameter optimization."
   - If the paper claims "no tuning was performed", look for tuning
     traces in the repo (sweep configs, hyperopt logs,
     `trainer_state.json`, tensorboard runs, commit history with
     hparam edits).
   - Beware **sequential overfitting / over-hyping**: the
     same test set used to evaluate many models in succession leads to
     gradual test-set overfitting even with no explicit tuning.
   - **Caveat: leakage requires *influence*, not visibility.** A
     test-set value is only a leak when it altered something that
     fed back into the reported metric (model selection, early
     stopping, hyperparameter choice, threshold tuning). Merely
     *printing* or *logging* the test loss during training, without
     using it to choose a checkpoint, epoch, or hyperparameter, is
     not leakage. The diagnostic is: "If the test loss had been a
     hidden NaN, would the reported metric still be exactly what the
     paper reports?" If yes, no leakage; if no, leakage. Apply this
     before flagging a "test loss printed during training" finding.

================================================================
10. BASELINES
   (REFORMS Module 5f; Ferrari Dacrema 2019; Lones 2024 "do use
   meaningful baselines"; Whalen et al. 2022 conclusions.)

   - Check whether the paper compares against simple naive baselines:
       - Always-predict-mean / median / majority-class.
       - Always-predict-previous-value (last-value-carried-forward) for
         time series.
       - Domain-specific naive baselines: degree distribution in
         networks; drug-mean and cell-mean in drug-response prediction;
         HVG-LR in single-cell foundation models; genomic distance for
         chromatin interaction prediction; majority-class predictor on
         imbalanced data.
   - If baselines are included, check they are evaluated under the
     same conditions as the proposed model (same split, same metric,
     same preprocessing, properly tuned). Asymmetric tuning (heavily
     tuned proposed model vs. default-hyperparam baseline) invalidates
     the comparison.
   - If no simple baselines are present, flag this. Strong
     performance is uninterpretable without a lower bound on task
     difficulty.
   - Consider a **shortcut-only baseline** using only suspected
     surrogate features (entity ID, popularity, degree, source,
     length). If the shortcut baseline approaches the proposed
     model, the model is largely exploiting the shortcut.
   - Where feasible, run the shortcut-only baseline yourself under
     `_audit_code/` and compare numbers. A 1-line baseline that
     reaches 95% of the model's reported performance is the most
     persuasive finding you can produce.
   - **Actively hunt for a deployment-realistic naive baseline that
     beats the proposed method.** Try hard to construct a simple
     model that uses only features available at inference time (no
     oracle measurements, no test-set lookups, no information the
     deployed system would not have) and that matches or beats the
     proposed method under the same split and metric. The "applicable
     in practice" constraint rules out baselines that depend on
     unavailable information. A deployable baseline that wins is
     a §10 finding with severity=high and is one of the strongest
     possible signals that the method is not adding value.

================================================================
11. FIGURE REPRODUCIBILITY
   (REFORMS Module 2e; Trisovic 2022; Hardwicke 2018; Pimentel 2019.)

   - Identify where the code generates each paper figure.
   - Check whether figures can be regenerated from raw data and code.
   - Compare against published figures: axes, scales, error bars,
     legends, sample sizes.
   - Check whether intermediate data (per-fold metrics, predictions)
     needed to regenerate figures are saved.
   - Flag missing figure code: if a figure is in the paper but not
     produced by any committed script, how was it created?

================================================================
12. DATA AVAILABILITY AND PREPROCESSING
   (REFORMS Modules 2a, 3a, 3b, 4; Heil tier criteria; Datasheets for
   Datasets, Gebru et al. 2021; Stodden 2018; Gabelica 2022.)

   - Are preprocessing scripts in the repo?
   - For public datasets, verify download/fetch scripts work and
     point to current URLs (datasets move or disappear).
   - Check whether data licensing is documented.
   - Identify whether raw data, preprocessed data, or both are
     required.
   - Look for preprocessing performed *outside* the repository before
     running. If so, the repo is at most R2 (code-only) on the
     Gundersen scale. Note in §0a.
   - If data cannot be shared, check whether authors provide
     synthetic or small example data for pipeline validation.
   - For the dataset, check whether a datasheet (or equivalent
     description: motivation / composition / collection / preprocessing
     / uses / distribution / maintenance) is provided. Absence is not a
     finding by itself. Note it under §0a.

================================================================
13. REPRODUCIBILITY BASICS
   (REFORMS Module 2; Pineau 2021 ML Reproducibility Checklist; Heil
   Silver-tier criteria; Glatard 2015 for cross-OS issues.)

   - Check whether dependency versions are pinned (requirements.txt,
     environment.yml, Dockerfile, lock file). Heil Silver: dependencies
     installable in a single command.
   - Check whether the pipeline can be run end-to-end from the
     provided instructions. State which scripts you actually ran.
     Heil Gold: entire analysis reproducible from a single command.
   - Check if any part of the code is missing, broken, or likely to
     fail (hard-coded absolute paths, missing files referenced by the
     scripts, dead imports, undefined CLI flags).
   - Verify random seeds are set for reproducibility, and that they
     are propagated to *all* sources of stochasticity (`random`,
     `numpy.random`, `torch.manual_seed`, `torch.cuda.manual_seed_all`,
     `tf.random.set_seed`, `cudnn.deterministic`, dataloader
     `worker_init_fn`). Heil Silver requires "all random components
     made deterministic".
   - Cross-OS / hardware non-determinism: GPU non-determinism may make
     exact retraining impossible. Heil notes that *trained model
     weights* should then be released so the model is at least
     evaluable.
   - Apply the Pineau ML Reproducibility Checklist as a floor:
       * For models / algorithms: clear math/algorithm description;
         complexity analysis; downloadable source code with all
         dependencies including external libraries.
       * For each figure / table of empirical results: data collection
         description with sample size; downloadable dataset or
         simulation environment; explanation of excluded data and
         preprocessing; explanation of train/val/test allocation;
         hyperparameter range, selection method, and final values;
         exact number of evaluation runs; description of how
         experiments were run; clearly defined metric; clearly defined
         error bars; central tendency + variation; computing
         infrastructure used.
   - Anything below this floor is at most R1 (description only) on
     the Gundersen scale.

================================================================
14. STATISTICAL INTEGRITY AND POST-HOC SELECTION
   (REFORMS Module 7c; Lones 2024 "do correct for multiple
   comparisons"; Nuijten et al. 2016; Simmons, Nelson & Simonsohn 2011.)

   - Look for signs of post-hoc selection or p-hacking:
       - Multiple comparisons without correction (Bonferroni, FDR).
         Lones is explicit: 20 pairwise tests at α=0.05 → ~1 false
         positive expected by chance.
       - "We found X in subgroup Y" after testing many subgroups.
       - Metric cherry-picking.
       - One-sided vs two-sided tests not declared in advance.
       - Choice of statistical test post-hoc to fit the data.
   - Check whether the authors pre-specified hypotheses and outcome
     measures.
   - Verify CIs / bootstrap intervals are constructed correctly (not
     biased by leakage or selection).
   - Look for inflated effect sizes, missing CIs/error bars, or
     significance reported without effect size.
   - Check whether reported improvements are tested for statistical
     significance with an appropriate test (McNemar's for two
     classifiers' per-sample outputs, Mann-Whitney U for two model
     distributions over multiple runs, Wilcoxon signed-rank for paired
     fold-wise scores).
   - Sanity-check claimed p-values against sample size: with n paired
     folds, the minimum achievable p-value of a Wilcoxon signed-rank
     test is bounded; flag p-values that violate that bound. (Run
     under `_audit_code/` if needed.)
   - Cross-check reported test statistics and p-values for arithmetic
     consistency (the statcheck principle): a reported
     `t(20)=2.50, p<0.001` is mathematically inconsistent.

================================================================
15. CODE PERMANENCE AND ARCHIVAL
   (REFORMS Modules 2a, 2b; Heil Bronze tier requirement.)

   - Is the code hosted on Zenodo, figshare, or a similar archival
     repository (not just GitHub)? Heil Bronze requires third-party
     archive (e.g., GitHub project archived in Zenodo). GitHub-only
     is below Bronze.
   - Does the archive include version tags matching paper submission?
   - Is the repository linked to the paper via DOI or supplementary
     materials?
   - Are trained model weights deposited in a public model zoo
     (Kipoi/Sfaira/HuggingFace) or in Zenodo? Heil Bronze: yes.

================================================================
16. DATA AND CODE AVAILABILITY STATEMENT
   (REFORMS Module 2; TRIPOD+AI Open Science items 18a–18f; Gabelica 2022.)

   - Locate the statement in the paper.
   - Extract every concrete claim it makes (datasets, repos,
     accessions, URLs, DOIs, scripts, trained models, supplementary
     files).
   - Verify each claim against the repo and any linked archives:
       - Does the promised code exist (not just be referenced)?
       - Do promised datasets resolve (URLs live, accessions valid,
         DOIs resolve)?
       - Are promised trained weights / intermediate outputs / figure
         data actually present or downloadable?
       - Do access-controlled resources list a clear request
         procedure?
   - Flag mismatches: items claimed as "available" but missing,
     broken, behind an unspecified request process, or pointing to a
     different version than the one used in the paper. Gabelica 2022
     reports that 93% of authors whose data-availability statements
     promised "available on request" either did not respond or
     declined when contacted. Treat such statements with calibrated
     skepticism.
   - Flag omissions: code, data, or artefacts clearly required to
     reproduce the results but not mentioned in the statement.
   - Check the statement distinguishes openly available, available on
     request, and not shareable, and that restriction reasons are
     plausible (privacy, licensing, size).

================================================================
APPENDIX A, COMMON ANTI-PATTERNS TO GREP FOR

These are concrete bugs that have appeared across multiple audits.
Run these greps even if the prose review of the relevant section
finds nothing. Per rule I, prefer running an `_audit_code/` script
over estimating counts.

   1. *Preprocessing before split.*
      `grep -nE "fit_transform|StandardScaler\(\)\.fit_transform|fit\(.*X\)|\.fit\(X\)" *.py`
      then check whether the call precedes the split.

   2. *StratifiedKFold over rows when groups should be set.*
      `grep -nE "StratifiedKFold|KFold" *.py`. If `groups=` is
      absent and the data has repeated entities, that is sample-
      dependent CV. Compare against `GroupKFold` /
      `StratifiedGroupKFold`.

   3. *Test set passed as validation_data in Keras.*
      `grep -n "validation_data" *.py`. Confirm the argument is
      not the test loader.

   4. *Early stopping on test metric.*
      `grep -nE "best_weight|best_epoch|EarlyStopping|patience" *.py`
      and trace which split it monitors.

   5. *Argparse type=bool bug.*
      `grep -n "type=bool" *.py`. `argparse.type=bool` does NOT
      parse "False" as False; any non-empty string is True. Common
      cause of "ablation flag silently ignored".

   6. *Hard-coded absolute paths.*
      `grep -nE "/home/|/Users/|/data/|/scratch/" *.py`. Must be
      edited before the script runs; often signals the script was
      never re-run after submission.

   7. *Single seed across replicates.*
      `grep -nE "seed\(0\)|seed\(42\)|manual_seed|random_state" *.py`.
      If rep0/rep1/rep2 share a seed, they are not real
      replicates.

   8. *Append-mode output files.*
      `grep -nE "open\(.*'a'|open\(.*'ab'" *.py`. Re-running the
      script silently doubles the output.

   9. *Cached / pickled splits silently overriding fresh ones.*
       `grep -nE "torch.load|pickle.load|os.path.exists" *.py` near
       the data pipeline. Cached splits can persist across runs and
       defeat any new shuffling.

   10. *DataLoader shuffle on test loader, drop_last=True.*
       `grep -nE "DataLoader.*test|shuffle=True|drop_last=True" *.py`.
       Both indicate a test loader being used as a training-time
       artefact.

   11. *In-place file extension or filename mismatch between scripts.*
       Trace the input/output filename of each script in the
       documented pipeline. A `.p` output and a `.p.gz` input is a
       broken pipeline.

   12. *p-values smaller than the test's combinatorial floor.*
       For a Wilcoxon signed-rank on n paired observations, the
       smallest achievable two-sided p-value is bounded by the
       number of distinct sign-rank assignments; e.g. n=5 gives
       p_min ≈ 0.062. Reported p-values smaller than this floor
       are mathematically impossible at the per-fold level.

   13. *Augmentation before split.*
       `grep -nE "augment|RandomFlip|RandomCrop|elastic|mixup|cutmix" *.py`.
       Confirm augmentation is applied to training data only after
       splitting.

   14. *Sklearn `Pipeline` not used where it should be.*
       Standardization, imputation, feature selection inside a CV
       loop without a `Pipeline` is a classic leakage source. If the
       repo uses `cross_val_score(model, X_scaled, y)` where
       `X_scaled` was scaled outside, that is leakage L1.2.

   15. *Foundation-model embedding extraction over the full dataset.*
       Look for a script that runs an encoder over `all_*` and saves
       embeddings, then a separate `split.py` consuming those
       embeddings. Order matters: embeddings extracted before split
       can encode test-set information.

================================================================
APPENDIX B, OUTPUT TEMPLATE

Top of `audit.md` (after rule 0a):

   - Reproducibility documentation type: R{1,2,3,4}
   - Reproducibility tier (Heil): Below Bronze / Bronze / Silver / Gold
   - REFORMS modules covered: {1,2,3,4,5,6,7,8} → list missing

Each finding MUST be emitted as a fenced YAML block with the info string
`finding`. The block is the authoritative, machine-readable representation
of the finding; surrounding prose is optional narrative. See
`references/findings-schema.md` for the full schema and worked examples.
Required fields: `id` (kebab-case, ≤ 40 chars), `section`, `title`,
`severity`, `confidence`, `status` (`finding` or `question`), `file`,
`quote`, `claim`, `concern`, `resolution`, and the Rule J self-check
`validator_pass.{quote_match, control_flow, condition_satisfiable}`. All
three `validator_pass.*` must be `true` for `status: finding`; otherwise
downgrade to `status: question`.

After writing `audit.md`, run `python scripts/extract_findings.py audit.md
--out findings.json` to produce the structured sidecar. The sidecar is
derived, never edit `findings.json` by hand.

End the audit with a scoreboard table:

   | § | Topic                          | Severity | Confidence | Note (one line) |
   |---|--------------------------------|----------|------------|-----------------|
   | 1 | Repository provenance          | ...      | ...        | ...             |
   | 2 | Data splitting                 | ...      | ...        | ...             |
   ...

Use `-` for "no concern". Do not invent severity to fill rows.

End with three short lists:
   - **Top take-aways** (≤ 6 items, ranked by combined severity ×
     confidence): the most consequential findings.
   - **Items that genuinely look fine**: things you actively checked
     and that are correct. (This guards against the impression that
     the audit is reflexively negative.)
   - **Open questions for the authors**: high-severity / low-confidence
     items that need clarification rather than action.

================================================================

Do not speculate beyond what the code shows. If you cannot determine
whether something is a problem without additional context (domain
knowledge about when a biomarker is measured, the meaning of a flag
in an external file, etc.), flag it as a question rather than a
finding. If you need additional information or data, ask. **Default
to "no finding" unless certainty is high.**
