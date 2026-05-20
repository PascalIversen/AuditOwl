
# statcheck — arithmetic consistency of reported NHST

Extension to the main audit prompt for verifying that inline
test statistics in the manuscript text — `t(df) = X, p = Y`,
`F(df1, df2) = X, p = Y`, `χ²(df) = X, p = Y`, `r(df) = X,
p = Y` — are internally consistent.

Findings here belong in the **main audit's §14 (statistical
integrity)**.

Implements the procedure of Nuijten et al. (2016) — the same
algorithm as the R package `statcheck`. ~50 % of published
psychology papers contain at least one inconsistent p-value;
~13 % contain a *gross* inconsistency (a flip in significance
verdict at α = 0.05).

All rules of `../../audit-prompt.md` §0 apply.
Per rule I, run the checks as code under `scripts/`.

## §S1. When this skill applies

The paper must report inline NHST statistics in APA-style or
near-APA-style format. Most common in:

   - Clinical / biomedical prediction papers.
   - Social-science and behavioural studies.
   - ML benchmark papers that include hypothesis testing
     (Wilcoxon between models, McNemar, paired t-tests across
     folds).

Less applicable to pure-method ML papers that report only
metric numbers without test statistics.

## §S2. Inputs

The paper's main text (and supplement) as plain text or PDF.

The agent should:

   1. Convert the PDF to text (e.g., `pdftotext`, `pypdf`).
   2. Run statcheck regex extraction.
   3. For each extracted `(stat_type, df1, df2, value, p_reported,
      tail)`, recompute p from `(stat_type, df1, df2, value)`
      using `scipy.stats`.
   4. Flag mismatches.

## §S3. Regex patterns (Nuijten et al. 2016)

The reference patterns the R statcheck package uses. Capture
test-type and statistic value separately from df and p.

       t-test:
         t\s*\(\s*(?P<df>[\d.]+)\s*\)\s*[=≈]\s*(?P<val>-?[\d.]+)\s*,\s*
         p\s*(?P<op>[<≤>≥=])\s*(?P<p>[\d.]+)

       F-test:
         F\s*\(\s*(?P<df1>[\d.]+)\s*,\s*(?P<df2>[\d.]+)\s*\)\s*[=≈]\s*(?P<val>[\d.]+)\s*,\s*
         p\s*(?P<op>[<≤>≥=])\s*(?P<p>[\d.]+)

       chi-square:
         (?:χ2|χ²|chi[- ]?square|χ\s*²)\s*\(\s*(?P<df>[\d.]+)\s*(?:,\s*N\s*=\s*\d+)?\s*\)\s*[=≈]\s*
         (?P<val>[\d.]+)\s*,\s*p\s*(?P<op>[<≤>≥=])\s*(?P<p>[\d.]+)

       r (correlation):
         r\s*\(\s*(?P<df>[\d.]+)\s*\)\s*[=≈]\s*(?P<val>-?[\d.]+)\s*,\s*
         p\s*(?P<op>[<≤>≥=])\s*(?P<p>[\d.]+)

       Z:
         (?:Z|z)\s*[=≈]\s*(?P<val>-?[\d.]+)\s*,\s*p\s*(?P<op>[<≤>≥=])\s*(?P<p>[\d.]+)

## §S4. The check

For each extracted hit, recompute the *expected* two-sided p
from the test statistic and df, using the same conventions as
the R statcheck package:

       t:    p_calc = 2 * (1 - t.cdf(|val|, df))
       F:    p_calc = 1 - f.cdf(val, df1, df2)
       χ²:   p_calc = 1 - chi2.cdf(val, df)
       r:    convert to t = r·sqrt(df/(1-r²)); then t-test on df
       Z:    p_calc = 2 * (1 - norm.cdf(|val|))

Define:

   - **inconsistent** if `p_calc` (rounded to the same decimals
     as `p_reported`) ≠ `p_reported`, taking the comparator
     `<` / `=` into account.
   - **gross inconsistency** if the rounded `p_calc` lies on the
     other side of the α = 0.05 threshold from the reported p.

A gross inconsistency is the highest-severity flavour because
it changes the verdict.

## §S5. Phrasing the finding

Good:
   "Paper reports `t(20) = 2.50, p < 0.001` (Section 3.2, p. 7).
   Recomputed two-sided p for `t = 2.50, df = 20` is `0.0212`.
   The reported `p < 0.001` is mathematically inconsistent and
   flips the significance verdict (gross inconsistency).
   See `scripts/check_statcheck.py` and `out/statcheck.csv`."

Good (minor):
   "Paper reports `F(2, 35) = 4.12, p = 0.03`. Recomputed
   p = 0.0244. Inconsistent at the 2-decimal level but does not
   flip the significance verdict at α = 0.05."

Bad:
   "The reported p doesn't seem right."

Severity: high for any gross inconsistency, medium for a
minor inconsistency. Confidence: high (deterministic
arithmetic).

## §S6. Reference implementation

The reference scan lives at `scripts/check_statcheck.py`.

## §S7. Known false-positive sources

- One-tailed tests reported as if two-tailed (the recomputation
  assumes two-tailed for t and Z by default). If the paper
  declares one-tailed, halve `p_calc`.
- Welch-corrected t-tests reported with the original df (the
  Welch df differs and is non-integer); flag as a question,
  not a verdict.
- Rounding of df (degrees of freedom shown as integers when
  fractional). Tolerate ±1 in df.
- Inline-cited statistics from a different study (the paper
  reports another paper's t-value as part of a literature
  review). Filter by surrounding text or only test results
  in the paper's own "Results" sections.
