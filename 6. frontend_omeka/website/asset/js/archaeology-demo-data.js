(() => {
  'use strict';

  const materials = [
    { key: 'ceramic', label: 'Ceramic', color: '#b65e35' },
    { key: 'flint', label: 'Flint', color: '#536475' },
    { key: 'obsidian', label: 'Obsidian', color: '#292b34' },
    { key: 'shell', label: 'Shell', color: '#d8a747' },
    { key: 'copper', label: 'Copper alloy', color: '#44836f' },
    { key: 'stone', label: 'Stone', color: '#927d61' }
  ];

  const sitesSeed = [
    { code: 'SGR', name: 'Saltglass Reach', region: 'Fictional North Coast', aliases: ['Saltglass Inlet', 'SGR demo locality'], base: 3900, x: 500, y: 280 },
    { code: 'MRD', name: 'Morrow Ridge', region: 'Fictional Inner Uplands', aliases: ['Morrow Heights', 'MRD demo locality'], base: 3750, x: 500, y: 280 },
    { code: 'SBP', name: 'Sable Plain', region: 'Fictional Southern Plain', aliases: ['Sable Flats', 'SBP demo locality'], base: 3600, x: 500, y: 280 },
    { code: 'BRB', name: 'Blue Reed Basin', region: 'Fictional Eastern Basin', aliases: ['Blue Reed Hollow', 'BRB demo locality'], base: 3450, x: 500, y: 280 },
    { code: 'ASC', name: 'Ashen Crossing', region: 'Fictional Western Pass', aliases: ['Ash Crossing', 'ASC demo locality'], base: 3300, x: 500, y: 280 }
  ];

  const trustFixtures = [
    { completeness: 0.96, bibliography: 0.92, spatial: 0.95, methodology: 0.92, currency: 0.94 },
    { completeness: 0.82, bibliography: 0.66, spatial: 0.78, methodology: 0.74, currency: 0.69 },
    { completeness: 0.58, bibliography: 0.35, spatial: 0.48, methodology: 0.52, currency: 0.40 },
    { completeness: 0.20, bibliography: 0.05, spatial: 0.18, methodology: 0.28, currency: 0.20 }
  ];

  const weights = {
    completeness: 0.30,
    bibliography: 0.25,
    spatial: 0.20,
    methodology: 0.15,
    currency: 0.10
  };

  const materialsByKey = new Map(materials.map(material => [material.key, material]));
  const sites = [];
  const periods = [];
  const strata = [];
  const relationships = [];
  const features = [];
  const finds = [];
  const chronometricSamples = [];
  const references = [];

  function makeTrustFixture(index) {
    return { ...trustFixtures[index % trustFixtures.length], weights: { ...weights } };
  }

  function makeMediaGallery(id) {
    return {
      id: `DEMO-GALLERY-${id}`,
      recordPresent: true,
      assets: [{
        assetType: 'drawing',
        resolution: 'synthetic fixture',
        rightsStatementUri: null,
        iiifManifestUri: null,
        annotationLayer: [],
        status: 'unresolved_demo_placeholder'
      }]
    };
  }

  function makeBibliographySlot(site) {
    return {
      referenceId: `DEMO-BIB-${site.code}`,
      title: `Fictional excavation report: ${site.name}`,
      zoteroKey: null,
      citationType: 'excavation_report',
      pageNumber: 'fixture page only',
      quotation: 'Invented citation slot for interface testing; not a quotation.',
      doi: null,
      verified: false,
      status: 'fictional_placeholder_not_a_source'
    };
  }

  function makeAuditHistory(id, title) {
    return [
      {
        actor: 'Synthetic demo curator',
        timestamp: '2026-10-01T10:00:00Z',
        operation: 'create',
        justification: `Generated the fictional ${title} fixture for interface testing.`,
        previousState: null
      },
      {
        actor: 'Synthetic demo curator',
        timestamp: '2026-10-02T10:00:00Z',
        operation: 'review',
        justification: 'Fixture review event; no canonical record was written.',
        previousState: { fixtureId: id, status: 'synthetic_unpublished' }
      }
    ];
  }

  function makeGeometry(kind, label) {
    return {
      kind,
      coordinates: null,
      status: 'fictional_schematic_not_georeferenced',
      note: `${label}: map coordinates are local drawing coordinates, not longitude/latitude.`
    };
  }

  function formatEdtf(start, end) {
    return `-${start}/-${end}`;
  }

  sitesSeed.forEach((seed, siteIndex) => {
    const siteId = `DEMO-SITE-${seed.code}`;
    const earlyStart = seed.base;
    const earlyEnd = seed.base - 200;
    const lateStart = earlyEnd;
    const lateEnd = earlyEnd - 200;
    const reference = makeBibliographySlot(seed);
    references.push(reference);

    const site = {
      id: siteId,
      type: 'site',
      code: seed.code,
      title: seed.name,
      name: seed.name,
      region: seed.region,
      altNames: seed.aliases,
      summary: `Fictional site fixture in ${seed.region}; no real-world location is implied.`,
      bodyText: 'Invented settlement record used to demonstrate the PLEROMA site hierarchy.',
      dateEdtf: formatEdtf(seed.base, seed.base - 400),
      yearStart: -seed.base,
      yearEnd: -(seed.base - 400),
      certaintyScore: [0.82, 0.68, 0.47, 0.34, 0.76][siteIndex],
      geometry: makeGeometry('Polygon', seed.name),
      climateModel: `DEMO-PALEO-${seed.code}-PRIMARY`,
      mediaGallery: makeMediaGallery(siteId),
      bibliographySlot: reference,
      publicationStatus: 'draft',
      trustFixture: makeTrustFixture(siteIndex),
      auditHistory: makeAuditHistory(siteId, 'site'),
      siteId
    };
    sites.push(site);

    const sitePeriods = [];
    for (let periodIndex = 0; periodIndex < 2; periodIndex += 1) {
      const start = periodIndex === 0 ? earlyStart : lateStart;
      const end = periodIndex === 0 ? earlyEnd : lateEnd;
      const periodId = `DEMO-PERIOD-${seed.code}-${periodIndex + 1}`;
      const period = {
        id: periodId,
        type: 'period',
        code: `${seed.code}-P${periodIndex + 1}`,
        title: periodIndex === 0 ? 'Earlier occupation' : 'Later occupation',
        name: periodIndex === 0 ? 'Earlier occupation' : 'Later occupation',
        summary: `Fictional occupation slice at ${seed.name}.`,
        dateEdtf: formatEdtf(start, end),
        yearStart: -start,
        yearEnd: -end,
        certaintyScore: periodIndex === 0 ? 0.64 - siteIndex * 0.045 : 0.79 - siteIndex * 0.06,
        geometry: makeGeometry('Polygon', `${seed.name} period ${periodIndex + 1}`),
        climateModel: `DEMO-PALEO-${seed.code}-P${periodIndex + 1}`,
        siteId,
        mediaGallery: makeMediaGallery(periodId),
        bibliographySlot: reference,
        publicationStatus: 'draft',
        trustFixture: makeTrustFixture(siteIndex + periodIndex),
        auditHistory: makeAuditHistory(periodId, 'occupational period')
      };
      sitePeriods.push(period);
      periods.push(period);
    }

    const siteUnits = [];
    for (let unitIndex = 0; unitIndex < 4; unitIndex += 1) {
      const periodIndex = unitIndex < 2 ? 1 : 0;
      const period = sitePeriods[periodIndex];
      const unitId = `DEMO-UNIT-${seed.code}-${String(unitIndex + 1).padStart(2, '0')}`;
      const start = [
        lateStart - 100,
        lateStart,
        earlyStart - 100,
        earlyStart
      ][unitIndex];
      const end = start - 100;
      const unit = {
        id: unitId,
        type: 'stratum',
        code: `${seed.code}-SU-${String(unitIndex + 1).padStart(2, '0')}`,
        title: `Stratigraphic Unit ${String(unitIndex + 1).padStart(2, '0')}`,
        name: `Stratigraphic Unit ${String(unitIndex + 1).padStart(2, '0')}`,
        summary: [
          'Compact occupation surface',
          'Silty floor deposit',
          'Ash-rich lens',
          'Natural basal sediment'
        ][unitIndex],
        fieldNotes: `Synthetic field note for ${seed.name}, Unit ${unitIndex + 1}; boundaries and description are invented.`,
        depositionInterpretation: [
          'occupation_surface',
          'floor_deposit',
          'ash_deposit',
          'natural_sediment'
        ][unitIndex],
        depositionInterpretationUri: `https://example.invalid/pleroma/deposition/${['occupation-surface', 'floor-deposit', 'ash-deposit', 'natural-sediment'][unitIndex]}`,
        dateEdtf: formatEdtf(start, end),
        yearStart: -start,
        yearEnd: -end,
        certaintyScore: [0.71, 0.58, 0.44, 0.31][(unitIndex + siteIndex) % 4],
        geometry: makeGeometry('Polygon', `${seed.name} unit ${unitIndex + 1}`),
        siteId,
        periodId: period.id,
        mediaGallery: makeMediaGallery(unitId),
        bibliographySlot: reference,
        publicationStatus: 'draft',
        trustFixture: makeTrustFixture(unitIndex + siteIndex),
        auditHistory: makeAuditHistory(unitId, 'stratigraphic unit'),
        mapBounds: {
          x: 175 + (unitIndex % 2) * 350,
          y: 160 + Math.floor(unitIndex / 2) * 150,
          width: 300,
          height: 118
        }
      };
      siteUnits.push(unit);
      strata.push(unit);

      if (unitIndex > 0) {
        relationships.push({
          id: `DEMO-EDGE-${seed.code}-${unitIndex}`,
          siteId,
          unitId: siteUnits[unitIndex - 1].id,
          relatedUnitId: unit.id,
          relationshipType: 'above',
          notes: 'Synthetic Harris Matrix relationship.'
        });
      }
    }

    const featureSeeds = [
      { type: 'hearth', title: 'Circular hearth', description: 'A shallow circular feature; its function is an invented interpretation.' },
      { type: 'wall', title: 'Low wall segment', description: 'A short linear feature; construction sequence is a demo question.' }
    ];
    featureSeeds.forEach((featureSeed, featureIndex) => {
      const unit = siteUnits[featureIndex * 2];
      const featureId = `DEMO-FEATURE-${seed.code}-${featureIndex + 1}`;
      features.push({
        id: featureId,
        type: 'feature',
        code: `${seed.code}-F${featureIndex + 1}`,
        title: featureSeed.title,
        name: featureSeed.title,
        summary: featureSeed.description,
        contextualDescription: featureSeed.description,
        interpretationNotes: 'Interpretation is separate from the observed shape and is not a finding.',
        featureTypeUri: `https://example.invalid/aat/feature/${featureSeed.type}`,
        siteId,
        periodId: unit.periodId,
        unitId: unit.id,
        dateEdtf: unit.dateEdtf,
        yearStart: unit.yearStart,
        yearEnd: unit.yearEnd,
        certaintyScore: featureIndex === 0 ? 0.62 : 0.43,
        geometry: makeGeometry('Geometry', `${seed.name} feature ${featureIndex + 1}`),
        mapPoint: { x: 365 + featureIndex * 270, y: 235 + featureIndex * 75 },
        material: '',
        bibliographySlot: reference,
        mediaGallery: makeMediaGallery(featureId),
        publicationStatus: 'draft',
        trustFixture: makeTrustFixture(featureIndex + siteIndex + 1),
        auditHistory: makeAuditHistory(featureId, 'feature')
      });
    });

    for (let findIndex = 0; findIndex < 20; findIndex += 1) {
      const unit = siteUnits[Math.floor(findIndex / 5)];
      const material = materials[findIndex % materials.length];
      const objectTypes = [
        { label: 'Vessel fragment', shape: 'vessel', uri: 'vessel-fragment' },
        { label: 'Cutting tool', shape: 'tool', uri: 'cutting-tool' },
        { label: 'Personal ornament', shape: 'ornament', uri: 'ornament' },
        { label: 'Ground-stone object', shape: 'stone-tool', uri: 'ground-stone-tool' },
        { label: 'Worked object fragment', shape: 'artifact', uri: 'worked-object' }
      ];
      const objectType = objectTypes[findIndex % objectTypes.length];
      const findId = `DEMO-FIND-${seed.code}-${String(findIndex + 1).padStart(3, '0')}`;
      const blockedStatuses = ['contested', 'under_review', 'repatriated', 'stolen', 'under_review'];
      const legalStatus = findIndex >= 18 ? blockedStatuses[siteIndex] : 'clear';
      const hasSource = material.key === 'obsidian' && findIndex % 2 === 0;
      const point = {
        x: 230 + (findIndex % 5) * 130 + ((siteIndex * 7) % 24),
        y: 205 + Math.floor(findIndex / 5) * 72 + ((siteIndex * 5) % 20)
      };
      finds.push({
        id: findId,
        type: 'find',
        code: `${seed.code}-FND-${String(findIndex + 1).padStart(3, '0')}`,
        title: `${objectType.label} ${String(findIndex + 1).padStart(3, '0')}`,
        name: `${objectType.label} ${String(findIndex + 1).padStart(3, '0')}`,
        summary: `${material.label} object from ${unit.code}; all object and context details are fictional.`,
        physicalDescription: `Synthetic ${material.label.toLowerCase()} object fixture with an invented context note.`,
        iconographyAnalysis: findIndex % 4 === 0 ? 'Illustrative motif description only; no verified identification.' : '',
        inventoryInstitution: 'Fictional Aletheion Demo Storehouse',
        inventoryId: `${seed.code}-DEMO-${String(findIndex + 1).padStart(3, '0')}`,
        objectType: objectType.label,
        objectShape: objectType.shape,
        objectTypeUri: `https://example.invalid/aat/${objectType.uri}`,
        vocabularyStatus: 'unverified_demo_mapping',
        material: material.label,
        materialKey: material.key,
        materialColor: material.color,
        materialTypeUri: `https://example.invalid/pleroma/material/${material.key}`,
        siteId,
        periodId: unit.periodId,
        unitId: unit.id,
        dateEdtf: unit.dateEdtf,
        yearStart: unit.yearStart,
        yearEnd: unit.yearEnd,
        certaintyScore: [0.84, 0.67, 0.49, 0.38, 0.24][findIndex % 5],
        geometry: makeGeometry('Point', findId),
        mapPoint: point,
        bibliographySlot: reference,
        mediaGallery: makeMediaGallery(findId),
        publicationStatus: 'draft',
        trustFixture: makeTrustFixture(findIndex + siteIndex),
        auditHistory: makeAuditHistory(findId, 'find'),
        provenanceChain: [{
          custodian: 'Fictional demo storehouse',
          acquisitionMethod: 'excavation',
          dateEdtf: formatEdtf(seed.base - 10, seed.base - 20),
          legalStatus,
          claimantCommunity: legalStatus === 'clear' ? null : `Fictional community claimant ${seed.code}`
        }],
        sourceLocation: hasSource ? {
          id: `DEMO-SOURCE-${seed.code}-${findIndex + 1}`,
          label: 'Fictional geological source polygon',
          x: 100 + (siteIndex * 11),
          y: 455,
          certainty: findIndex % 4 === 0 ? 0.82 : 0.38
        } : null,
        conservation: {
          condition: findIndex % 29 === 0 ? 'active_corrosion' : findIndex % 17 === 0 ? 'fragmenting' : 'stable',
          treatmentHistory: findIndex % 29 === 0
            ? ['Synthetic inspection fixture; conservator alert workflow not connected.']
            : [],
          storageEnvironment: 'No measured environment; demo placeholder.',
          lastInspection: 'Fixture date only'
        },
        excavationProtocol: {
          methodType: siteIndex % 2 === 0 ? 'open_area' : 'surface_survey',
          samplingStrategy: siteIndex % 2 === 0 ? 'stratified' : 'systematic',
          sieveMeshMm: siteIndex % 2 === 0 ? 4 : null,
          minimumFindSizeMm: siteIndex % 2 === 0 ? 10 : null,
          significanceBiasFactor: [0.04, 0.12, 0.2, 0.32, 0.08][siteIndex]
        }
      });
    }

    for (let periodIndex = 0; periodIndex < 2; periodIndex += 1) {
      const period = sitePeriods[periodIndex];
      const unit = siteUnits[periodIndex === 0 ? 3 : 1];
      const sampleId = `DEMO-SAMPLE-${seed.code}-P${periodIndex + 1}`;
      const start = period.yearStart;
      const end = period.yearEnd;
      const center = Math.round((start + end) / 2);
      chronometricSamples.push({
        id: sampleId,
        siteId,
        periodId: period.id,
        unitId: unit.id,
        labCode: `LAB-DEMO-${seed.code}-${periodIndex + 1}`,
        method: 'AMS C14',
        rawDateBp: 5450 - siteIndex * 145 - periodIndex * 210,
        errorMargin1Sigma: 25 + ((siteIndex + periodIndex) % 4) * 5,
        materialContext: 'Synthetic charcoal sample fixture; association and measurement are invented.',
        calibrationCurve: periodIndex === 0 ? 'IntCal20' : 'Marine20',
        rawMeasurementImmutable: true,
        calibrationResults: [
          {
            id: `${sampleId}-CAL-A`,
            version: 1,
            curve: periodIndex === 0 ? 'IntCal20' : 'Marine20',
            dateEdtf: period.dateEdtf,
            probabilityCurve: [
              { year: start, probability: 0.12 },
              { year: Math.round(start * 0.67 + end * 0.33), probability: 0.48 },
              { year: Math.round(start * 0.33 + end * 0.67), probability: 0.31 },
              { year: end, probability: 0.09 }
            ]
          },
          {
            id: `${sampleId}-CAL-B`,
            version: 2,
            curve: periodIndex === 0 ? 'IntCal20' : 'Marine20',
            dateEdtf: formatEdtf(Math.abs(center) + 35, Math.abs(end) + 15),
            probabilityCurve: [
              { year: start - 35, probability: 0.08 },
              { year: Math.round(start * 0.6 + end * 0.4) - 25, probability: 0.42 },
              { year: Math.round(start * 0.3 + end * 0.7) - 15, probability: 0.38 },
              { year: end - 15, probability: 0.12 }
            ]
          }
        ],
        status: 'synthetic_calibration_fixture_not_scientific_output'
      });
    }
  });

  const records = [...sites, ...periods, ...strata, ...features, ...finds];
  const dataset = {
    demoOnly: true,
    generatedAt: '2026-10-02T10:00:00Z',
    materials,
    sites,
    periods,
    strata,
    relationships,
    features,
    finds,
    chronometricSamples,
    references,
    records
  };

  window.PLEROMA_ARCHAEOLOGY_DEMO = dataset;
})();
