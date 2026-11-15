# Demographic modeling

`SettlementPopulationModel` implements an explicit interval-based
settlement-capacity estimator using:

1. Settlement area in hectares (with a UUID identifying the source record).
2. The inhabited fraction of that area.
3. Housing density in dwellings per hectare.
4. Persons per dwelling.
5. A separately estimated carrying-capacity range in persons.

The housing-capacity bounds are the products of the corresponding input
bounds. Each population bound is constrained by its matching carrying-capacity
bound, then rounded outward to whole persons so the reported range does not
hide fractional uncertainty. The exact unrounded constrained range is also
retained in the payload. This is a capacity-based scenario, not a census count
or an archaeological fact; all numeric assumptions are required inputs, not
hardcoded defaults. No density, household-size, or subsistence coefficient is
invented by this module.

The writeback payload records all input ranges, the settlement-area source
UUID, model and notebook versions, timezone-aware execution timestamp,
parameter-set UUID, and bibliography reference UUIDs. The caller must persist
the payload through the project's designated structured writeback path and
store any notebook snapshot or visualization as a versioned Media_Asset.

`population_estimates.ipynb` is an input-driven notebook template that uses
this model without sample population data. The repository does not yet include
a population-estimate table or writeback endpoint, so the payload is a
reproducible service contract rather than a database write. The model accepts
the settlement area measurement explicitly; compute it from the validated
PostGIS site geometry and record that source rather than approximating polygon
area in this module.

Run tests from `4. science_modules`:

```sh
python3 -m unittest discover -s demographic_modeling/tests -t . -v
```
