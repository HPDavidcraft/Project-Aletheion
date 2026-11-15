# Roadmap phases

`roadmap.json` translates the phase objectives and exit criteria in sections 1.4
and 12 of `Pleroma_Guidelines_v1.0.pdf` into an editable progress manifest.
Milestone and exit-criterion statuses begin as `not_assessed`; the guideline
labels Beta as current at version 1.0, but that does not establish the
repository's present completion state.

Allowed progress statuses are:

- `not_assessed`
- `in_progress`
- `blocked` (requires a `blocker` explanation)
- `done` (requires an `evidence` reference, such as a PR, test report, or
  repository path)

Run the structure and evidence checks:

```sh
python3 validate_roadmap.py --validate
```

Print completion and start eligibility for every phase:

```sh
python3 validate_roadmap.py
```

Check a phase gate and all preceding gates:

```sh
python3 validate_roadmap.py --gate beta
```

The checker verifies manifest consistency and recorded completion evidence. It
does not independently test infrastructure or prove that evidence is accurate.
Post-release priorities have no formal exit gate in the guidelines, so their
completion report is a progress summary rather than a release decision.
