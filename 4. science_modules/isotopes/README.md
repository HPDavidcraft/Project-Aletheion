# Isotopes

Base-R helpers for the stable-isotope and strontium work listed in the PLEROMA
Computational Lab guidelines:

- `isotope_analysis.R` validates paired δ13C/δ15N measurements, reports
  measurement counts and descriptive group summaries, and creates a biplot
  with each measurement's supplied uncertainty intervals. It writes a plot,
  CSV summary, analyst-authored dietary interpretation, and execution
  provenance through `run_cn_analysis()`.
- `strontium_analysis.R` compares supplied 87Sr/86Sr measurement intervals
  against explicitly sourced baseline intervals. It reports only whether
  intervals overlap or lie above/below one another; it does not assign a
  geographic origin or infer mobility.
- `carbon_nitrogen_ratios.ipynb` is an input-driven R notebook template. It
  contains no sample data or default dietary interpretation.

The C/N input CSV must have unique `measurement_id` values and these columns:
`sample_id`, `record_type` (`sample` or `reference`), `group`, `delta13c`,
`delta13c_uncertainty`, `delta13c_uncertainty_basis`, `delta13c_scale`,
`delta15n`, `delta15n_uncertainty`, `delta15n_uncertainty_basis`,
`delta15n_scale`, and `source_reference`. A biplot requires consistent scales
and uncertainty bases within each isotope. Values are not auto-corrected,
normalized, or interpreted. Each row's source citation and measurement
uncertainty must come from the lab or referenced dataset.

Strontium measurement inputs require `measurement_id`, `sample_id`, `sr87_sr86`,
`uncertainty`, `uncertainty_basis`, and `source_reference`. Baselines require
`baseline_id`, `baseline_label`, `lower`, `upper`, and `source_reference`.
Intervals are compared as given; overlap is not proof of local origin, and a
non-overlap is not a migration determination.

All interpretation remains the analyst's responsibility. The C/N runner
requires analyst-authored interpretation text and records its input SHA-256,
parameter-set UUID, notebook revision, execution time, and R version. It
refuses to overwrite prior output files. Register the biplot and written
interpretation as `computational_output` Media_Assets through the authorized
writeback API; no isotope result schema, database, MinIO, or Media_Asset
integration is configured in this folder. Use only inputs authorized for the
Computational Lab; apply the project's access and cultural-rights controls
before sharing results.

The scripts use base R and require `sha256sum` or `shasum` for the C/N input
checksum. Run the tests from `4. science_modules`:

```sh
Rscript isotopes/tests/test_isotopes.R
```
