import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from genomics.datasets import (
    GenomicDataError,
    GenomicDataset,
    SampleLabOutput,
    sha256_file,
)
from genomics.dispersion import DispersionAnalysis, DispersionAnalysisError
from genomics.ethics import (
    GenomicPublicationContext,
    GenomicReleaseDenied,
    require_public_genomic_release,
)
from genomics.haplogroups import (
    HaplogroupAssignment,
    HaplogroupDataError,
    HaplogroupObservation,
    aggregate_haplogroup_frequencies,
    frequency_chart_spec,
    frequency_payload,
)


def lab_output(**overrides):
    values = {
        "id": uuid4(),
        "bio_sample_id": uuid4(),
        "storage_uri": "s3://pleroma-genomics/sample-01/reads.h5",
        "file_format": "HDF5",
        "checksum_sha256": "a" * 64,
        "created_by": uuid4(),
    }
    values.update(overrides)
    return SampleLabOutput(**values)


class GenomicDatasetTests(unittest.TestCase):
    def test_external_object_and_dataset_payloads_preserve_sample_provenance(self):
        output = lab_output()
        dataset = GenomicDataset(
            id=uuid4(),
            bio_sample_id=output.bio_sample_id,
            output=output,
            sequencing_method="shotgun ancient DNA",
            created_by=uuid4(),
            reference_assembly="GRCh38",
            dataset_metadata={"coverage": 0.25, "library_type": "single-stranded"},
        )

        payload = dataset.writeback_payload()
        self.assertEqual(payload["output_id"], str(output.id))
        self.assertEqual(output.writeback_payload()["storage_uri"], output.storage_uri)
        json.dumps({"output": output.writeback_payload(), "dataset": payload})

    def test_rejects_mismatched_sample_and_non_object_or_non_json_metadata(self):
        output = lab_output()
        with self.assertRaises(GenomicDataError):
            GenomicDataset(
                id=uuid4(),
                bio_sample_id=uuid4(),
                output=output,
                sequencing_method="shotgun",
                created_by=uuid4(),
            )
        with self.assertRaises(GenomicDataError):
            GenomicDataset(
                id=uuid4(),
                bio_sample_id=output.bio_sample_id,
                output=output,
                sequencing_method="shotgun",
                created_by=uuid4(),
                dataset_metadata={"invalid": object()},
            )
        with self.assertRaises(GenomicDataError):
            lab_output(storage_uri="https://example.test/reads.h5")

    def test_hashes_files_incrementally(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reads.h5"
            path.write_bytes(b"genomic object")
            self.assertEqual(
                sha256_file(path, chunk_size=3),
                "63672a256b48f0b78d6b513bb42762cd0336f0d5389378d9282c3607f4d7ccdc",
            )


class GenomicEthicsTests(unittest.TestCase):
    def test_human_genomic_release_requires_all_ethics_and_rights_gates(self):
        context = GenomicPublicationContext(
            sample_id=uuid4(),
            sample_type="human_sample",
            provenance_public_export_allowed=True,
            public_release_authorized=True,
            review_reference="ETHICS-REVIEW-12",
            human_remains_ethics_reviewed=True,
            nagpra_compliance_reviewed=True,
            descendant_consultation_status="completed",
            repatriation_request_status="none",
        )
        require_public_genomic_release(context)

        with self.assertRaises(GenomicReleaseDenied):
            require_public_genomic_release(
                replace(context, descendant_consultation_status="in_progress")
            )

    def test_non_clear_provenance_fails_closed(self):
        with self.assertRaises(GenomicReleaseDenied):
            require_public_genomic_release(
                GenomicPublicationContext(
                    sample_id=uuid4(),
                    sample_type="flora_specimen",
                    provenance_public_export_allowed=False,
                    public_release_authorized=True,
                    review_reference="REVIEW-1",
                )
            )


class HaplogroupTests(unittest.TestCase):
    def test_assignment_interval_and_database_payload(self):
        assignment = HaplogroupAssignment(
            id=uuid4(),
            bio_sample_id=uuid4(),
            marker_type="mitochondrial",
            haplogroup_label="H1",
            confidence_lower=0.8,
            confidence_upper=0.95,
            assigned_by="analyst-12",
        )
        payload = assignment.writeback_payload()
        self.assertEqual(payload["assigned_by"], "analyst-12")
        json.dumps(payload)
        with self.assertRaises(HaplogroupDataError):
            HaplogroupAssignment(
                id=uuid4(),
                bio_sample_id=uuid4(),
                marker_type="mitochondrial",
                haplogroup_label="H1",
                confidence_lower=0.96,
                confidence_upper=0.95,
            )

    def test_aggregation_uses_unique_sample_counts_and_release_suppresses_small_cells(self):
        region = uuid4()
        sample_ids = (uuid4(), uuid4(), uuid4())
        observations = [
            HaplogroupObservation(sample_ids[0], region, "1000/1100", "mitochondrial", "H1", 0.8, 1),
            HaplogroupObservation(sample_ids[1], region, "1000/1100", "mitochondrial", "H1", 0.6, 0.9),
            HaplogroupObservation(sample_ids[2], region, "1000/1100", "mitochondrial", "U", 0.7, 0.95),
        ]
        report = aggregate_haplogroup_frequencies(observations)
        contexts = tuple(
            GenomicPublicationContext(
                sample_id=sample_id,
                sample_type="flora_specimen",
                provenance_public_export_allowed=True,
                public_release_authorized=True,
                review_reference="REVIEW-1",
            )
            for sample_id in sample_ids
        )
        self.assertEqual([row.sample_count for row in report.rows], [2, 1])
        self.assertAlmostEqual(float(report.rows[0].sample_frequency), 2 / 3)
        self.assertEqual(
            report.public_rows(minimum_cohort_size=2, publication_contexts=contexts), ()
        )
        self.assertEqual(
            frequency_payload(
                report,
                public=True,
                minimum_cohort_size=1,
                publication_contexts=contexts,
            ),
            tuple(row.to_dict() for row in report.rows),
        )
        with self.assertRaises(GenomicReleaseDenied):
            report.public_rows(
                minimum_cohort_size=1,
                publication_contexts=(
                    replace(contexts[0], provenance_public_export_allowed=False),
                    *contexts[1:],
                ),
            )
        self.assertEqual(frequency_chart_spec(report)["encoding"]["y"]["field"], "sample_frequency")

    def test_rejects_duplicate_sample_assignments_in_a_partition(self):
        sample_id = uuid4()
        region_id = uuid4()
        repeated = HaplogroupObservation(
            sample_id, region_id, "undated", "mitochondrial", "H1", 0.8, 0.9
        )
        with self.assertRaises(HaplogroupDataError):
            aggregate_haplogroup_frequencies((repeated, repeated))
        with self.assertRaises(ValueError):
            frequency_payload(
                aggregate_haplogroup_frequencies((repeated,)),
                public=True,
                minimum_cohort_size=1,
            )


class DispersionTests(unittest.TestCase):
    def test_run_state_transitions_and_writeback_links(self):
        run = DispersionAnalysis(
            id=uuid4(),
            analysis_type="genome",
            title="Haplogroup dispersion",
            notebook_uri="s3://pleroma-notebooks/genomics/dispersion.ipynb",
            notebook_revision="git:8ab3d2e",
            environment_reference="python-3.14;requirements-lock:sha256:abc",
            created_by=uuid4(),
            sample_ids=(uuid4(), uuid4()),
            regional_chronicle_ids=(uuid4(),),
            parameters={"minimum_assignment_confidence": 0.8},
        )
        started = run.start(datetime(2026, 1, 1, tzinfo=timezone.utc))
        completed = started.finish(
            datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
            media_assets=((uuid4(), "interactive_visualization"),),
        )
        payload = completed.writeback_payload()
        self.assertEqual(payload["analysis"]["status"], "complete")
        self.assertEqual(len(payload["samples"]), 2)
        self.assertEqual(payload["media_assets"][0]["asset_role"], "interactive_visualization")
        json.dumps(payload)
        with self.assertRaises(DispersionAnalysisError):
            completed.start(datetime(2026, 1, 2, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
