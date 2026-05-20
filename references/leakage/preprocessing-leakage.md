
# Preprocessing fit on test data

**General** leakage check, domain-agnostic. Applies to *any*
supervised ML paper that does feature transformation before
fitting the model.

This is **Kapoor-Narayanan leakage types L1.2 (preprocessing on
train + test together) and L1.3 (feature selection on train +
test together)**, and **Whalen pitfall 4 (leaky preprocessing)**.
Kaufman et al. (2012) treat it as the textbook "no-time-machine"
violation. Findings here are owned by the **main audit's §2 (data
splitting)** with a cross-reference to the domain skill if one
applies.

All rules of `../../audit-prompt.md` §0 apply.
Per rule I, run the deterministic greps as code under
`scripts/`.

## §LP1. Canonical shapes

   1. **Scaler / normaliser fit on full data.** `StandardScaler`,
      `MinMaxScaler`, `RobustScaler`, `QuantileTransformer`,
      `Normalizer` called with `fit_transform(X_all)` before the
      split — or fit on `X_all` and then the *labels* sliced
      out. Test-set statistics inform the scaler.
      *Symptom:* deployment performance lower than reported.

   2. **Imputation on full data.** `SimpleImputer`,
      `IterativeImputer`, `KNNImputer`, median / mean fill
      computed across all rows. Test rows contribute to the
      imputed value used in training.

   3. **Encoders on full data.** `OneHotEncoder`,
      `OrdinalEncoder`, `LabelEncoder`, `TargetEncoder` —
      target encoding is the worst: it directly leaks label
      information when fit on the full set.

   4. **Dimensionality reduction on full data.** `PCA`, `t-SNE`,
      `UMAP`, `TruncatedSVD`, `KernelPCA`, autoencoder embedding,
      ICA fit on `X_all` before split.

   5. **Feature selection on full data.** `SelectKBest`,
      `mutual_info_classif`, `f_regression`, Lasso-based
      selection, recursive feature elimination over all rows.
      Selecting features by their correlation with the label
      across train + test is L1.3.

   6. **Batch correction on full data.** ComBat, Harmony, RUV,
      PEER, scVI integration computed across all batches —
      including test batches. Common in genomics and
      single-cell.

   7. **Oversampling / resampling on full data.** SMOTE,
      ADASYN, random oversampling applied before the split.
      Synthetic samples can be derived from train + test
      neighbourhoods together.

   8. **Augmentation before split.** Image augmentation
      (`RandomCrop`, `RandomFlip`, `Mixup`, `CutMix`),
      back-translation, paraphrasing, elastic deformations
      applied to the full pool before splitting puts augmented
      copies of training samples into the test set. Lones
      2024 explicit warning.

   9. **Outlier removal using the label.** Filtering rows
      whose target value is far from the mean — the filter
      itself encodes the label.

  10. **Pipeline not wrapping CV.** Even when the user knows to
      fit-on-train, doing it manually outside the CV loop
      (`X_scaled = scaler.fit_transform(X); cross_val_score(model, X_scaled, y)`)
      leaks across folds within CV.

## §LP2. Checks to run

   A. **Order trace.** For every transformation step, identify
      the call site (`file:line`) of `fit_transform` /
      `fit` / `transform`. Trace whether the input array
      contains test rows.

   B. **Grep patterns** (delegate to `scripts/`):

         grep -nE "fit_transform|\.fit\(.*X[^_]*\)|fit\(X[, )]"
         grep -nE "StandardScaler|MinMaxScaler|RobustScaler|QuantileTransformer"
         grep -nE "SimpleImputer|KNNImputer|IterativeImputer"
         grep -nE "PCA\(|TruncatedSVD|KernelPCA|UMAP\(|TSNE\("
         grep -nE "SelectKBest|SelectPercentile|RFE\(|mutual_info_"
         grep -nE "SMOTE|ADASYN|oversample|resample\("
         grep -nE "combat|harmony|RUVg|peer_factor"
         grep -nE "augment|RandomFlip|RandomCrop|elastic|mixup|cutmix"

      Then for each hit, open the call site and decide whether
      the input contains test rows.

   C. **Pipeline check.** Look for `sklearn.pipeline.Pipeline`
      wrapping the preprocessing + estimator. Its absence in
      a CV harness is suspicious by itself.

   D. **`X_full` sanity.** Variable names like `X_all`,
      `X_full`, `X_combined`, `data_all`, `df_all`,
      `merged_data` near a `fit_transform` call are a high-
      confidence red flag.

The script is intentionally **noisy** — many of these patterns
appear in correct code too. The agent must open each
high-priority hit (`fit_transform_on_X`, `fit_on_X_full`,
`augmentation_keyword` near a `Dataset`/`Dataloader`
construction) and decide whether the leakage shape applies.

## §LP4. Phrasing

Good:
   "`preprocess.py:34` calls
   `scaler = StandardScaler().fit_transform(X_all)`. The
   `X_all` variable is constructed on line 22 by
   `pd.concat([X_train, X_test])`. The scaler's mean and
   variance therefore include test-set statistics, which leak
   into the rescaled training rows. Kapoor-Narayanan L1.2.
   See `scripts/check_preprocessing_leakage.py` and
   `out/preprocessing_hits.csv:row=4`."

Bad:
   "Preprocessing might be leaking."

Severity: high when preprocessing demonstrably uses test
rows and the model's headline metric depends on the
preprocessed features. Confidence: high (it's a static-
analysis finding).

## §LP5. Known false-positives

- `transform(X_test)` after a fit on `X_train` only — the
  *cleanest* pattern, will trigger the `fit_transform_on_X`
  regex if `fit_transform` was used on `X_train` but is
  benign. Inspect the variable name.
- Per-sample preprocessing (e.g., per-image normalisation by
  its own min/max) is fine; it does not pool statistics
  across samples.
- Some kinds of representation learning (autoencoders for
  self-supervised pretraining) are explicitly applied to the
  full dataset and are not a leakage finding when the
  downstream task evaluation is run *without* the autoencoder
  having seen test labels. Distinguish "feature extraction"
  from "feature engineering using the label".
