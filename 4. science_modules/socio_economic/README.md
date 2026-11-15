# Socio-economic analysis

This package implements the two analyses identified in the PLEROMA guidelines:

- `silver_equivalence.py` converts explicitly sourced commodity-quantity and
  silver-per-unit ranges into silver-gram ranges, then normalizes each
  region/commodity/unit series against a caller-selected baseline period
  (baseline index = 100). All quantities, units, exchange-rate intervals, and
  Bibliographic_Reference UUIDs are supplied inputs. It does not invent
  historical exchange rates or apply an inflation/purchasing-power adjustment.
- `trade_network.py` analyzes directed Movement_Vector records associated by
  the caller with a `trade` Cluster_History. It reports unique-neighbor in/out
  degree, normalized degree and betweenness centrality, directed unweighted
  shortest paths, and deterministic label-propagation communities on an
  undirected projection. Movement route source and category remain attached
  to each edge.
- `economic_indicators.ipynb` and `network_analyzer.ipynb` are input-driven,
  parameterized templates. They contain no sample observations.

The economic input CSV has one aggregated observation per
region/commodity/unit/period and requires `observation_id`, `commodity_uri`,
`region_id`, `period_label`, `period_order`, `commodity_unit`,
`quantity_lower`, `quantity_upper`, `silver_grams_per_unit_lower`,
`silver_grams_per_unit_upper`, `quantity_reference_id`, and
`exchange_rate_reference_id`. The baseline period must exist for every series.
The application must validate period labels as EDTF and provide a justified
ordering key; this package does not guess date ordering or combine repeated
measurements.

The network input uses `site_id` rows from `cluster_history_site` and selected
Movement_Vector fields (`vector_id`, endpoints, category URI, route source, and
optional JSON subtype attributes). The caller must time-filter vectors and
record the explicit selection criteria in `analysis_scope`; all movement
categories must match the requested trade concept and every endpoint must
belong to the Cluster_History.
The emitted `trade_network.json` is directed node-link data suitable for a
NetworkX adapter; the metrics and calculations here use only Python's standard
library. The SVG is a schematic circular layout, **not a geographic map**.
Community labels are exploratory, unweighted, and computed after dropping
direction; non-convergence is reported rather than silently substituted.

The network writeback payload requires SHA-256 digests for both CSV inputs,
the parameter-set UUID, notebook revision, environment reference, and a
timezone-aware execution timestamp. These values and `analysis_scope` travel
with the graph and metrics rather than being inferred from the query.

The existing schema has no `Economic_Index` table or graph-metrics writeback
endpoint. The methods return reproducible payloads and local artifacts only.
Register generated PNG/SVG or textual results through the authorized API;
published Cluster_History records require their `network_graph` Media_Asset
and bibliography under the historiographical schema. No database, NetworkX,
or object-store integration is configured in this folder.

Run tests from `4. science_modules`:

```sh
python3 -m unittest discover -s socio_economic/tests -t . -v
```
