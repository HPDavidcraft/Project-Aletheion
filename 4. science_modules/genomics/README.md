# Genomics

This package provides small, dependency-free service helpers for the PLEROMA
genomic records and analysis contracts:

- `SampleLabOutput` and `GenomicDataset` validate external object metadata,
  checksums, sample linkage, and JSON metadata, then produce payloads aligned
  with `sample_lab_output` and `genomic_dataset`.
- `sha256_file` hashes large local inputs incrementally. HDF5, sequence reads,
  and other binary content remain in S3/MinIO; the PostgreSQL payload contains
  only object references and metadata.
- `HaplogroupAssignment` validates marker labels and confidence intervals.
  Frequency aggregation counts unique samples using caller-resolved regional
  and time-slice assignments; it does not infer migration, chronology, or
  geographic membership. The returned Vega-Lite specification can be rendered
  by an approved client without adding a plotting dependency.
- `require_public_genomic_release` fails closed unless the trusted database
  provenance check and release review authorize publication. Human samples
  additionally require the ethics, NAGPRA, consultation, and repatriation
  conditions to be cleared. It is not a substitute for API/RBAC checks and
  does not implement administrator overrides.
- `HaplogroupFrequencyReport.public_rows()` requires trusted release contexts
  for every contributing sample and an explicit, governance-selected minimum
  cohort size. A region/time/marker partition is withheld if any haplogroup
  group falls below that threshold; no threshold is assumed by this package.
- `DispersionAnalysis` records notebook revision, environment, parameters,
  execution state, and sample/region/Media_Asset links in a payload matching
  the hard-sciences schema.

The notebook `haplogroup_dispersion.ipynb` is an input-driven internal analysis
template. Inputs must be supplied from an authorized, provenance-aware
application query; do not put sequence data or sample-level exports in the
notebook. Public release must independently pass the ethics gate and the
governance-configured cohort threshold.

No BioSQL, object-store, PostgreSQL, access-control, or Media_Asset integration
is configured here. The module does not parse HDF5 or sequence files, perform
variant calling, infer haplogroups, or upload artifacts. `writeback_payload()`
methods are service contracts to be mapped to authorized persistence adapters.
The human-sample review attributes must be loaded from trusted records, not
supplied by an end user.

Run tests from `4. science_modules`:

```sh
python3 -m unittest discover -s genomics/tests -t . -v
```
