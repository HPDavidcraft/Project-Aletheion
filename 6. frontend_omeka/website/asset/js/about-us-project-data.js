// Extend projectData for about_us.html sections
        Object.assign(projectData, {
            'section_deepmap': {
                title: 'The Deep Map State Machine',
                year: '2026',
                role: '4D-GIS Infrastructure',
                client: 'Project Aletheion',
                description: 'We do not simply place points on a map. We model the Stratigraphic Unit. The system validates Harris Matrices to ensure acyclic temporal relationships. The "Deep Map" defines deterministic layer stacks per user selection (site / period / stratum / find), automatically switching base and overlay layers via Geoserver WFS.',
                extended: 'Advanced geospatial modeling for archaeological stratigraphy.'
            },
            'section_science': {
                title: 'Genomics & Chronometry',
                year: '2026',
                role: 'Bio-Archaeology Module',
                client: 'Project Aletheion',
                description: 'Radiocarbon (C14): Raw uncalibrated dates are stored permanently. Bayesian calibration is performed on-demand via OxCal API wrappers. aDNA Storage: High-throughput sequencing data is stored in HDF5/BioSQL containers, allowing for real-time generation of haplogroup dispersion graphs via Python pipelines.',
                extended: 'Integrating hard sciences with archaeological data.'
            },
            'section_intangible': {
                title: 'Theological Architecture',
                year: '2026',
                role: 'Ontology of Belief',
                client: 'Project Aletheion',
                description: 'Ad-hoc naming is prohibited. All narrative elements are indexed using the Aarne-Thompson-Uther (ATU) or Thompson Motif-Index logic via SKOS. We model the Liturgical Event as a temporal node with recurrence rules (RRULE), linked to astronomical alignments and temple features.',
                extended: 'Modeling intangible cultural heritage.'
            }
        });
        document.querySelector('.close-btn')?.addEventListener('click', () => window.closeProject());
