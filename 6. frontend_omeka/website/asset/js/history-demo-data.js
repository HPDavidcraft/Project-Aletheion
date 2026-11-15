(() => {
  'use strict';

  const archaeology = window.PLEROMA_ARCHAEOLOGY_DEMO;
  if (!archaeology || archaeology.sites.length < 5) {
    console.error('History demo requires the shared fictional archaeology site fixtures.');
    return;
  }

  const sourceTypes = ['primary_source', 'synthesis', 'database_record', 'personal_communication'];
  const interactionTypes = ['trade', 'warfare', 'migration', 'cultural_diffusion', 'environmental_co_response'];
  const eventTypes = [
    { key: 'treaty', label: 'Treaty / compact' },
    { key: 'battle', label: 'Battle' },
    { key: 'foundation', label: 'Foundation' },
    { key: 'dynastic_transition', label: 'Dynastic transition' },
    { key: 'eruption', label: 'Environmental event' },
    { key: 'epidemic', label: 'Epidemic / health event' },
    { key: 'harvest', label: 'Agricultural event' },
    { key: 'movement', label: 'Migration / movement' },
    { key: 'legal_decree', label: 'Legal decree' },
    { key: 'construction', label: 'Construction' }
  ];
  const resolutionTags = ['consensus', 'minority', 'contested', 'superseded', 'refuted'];
  const chronicleNames = [
    'Saltglass Littoral Chronicle',
    'Morrow Upland Chronicle',
    'Sable Plain Chronicle',
    'Blue Reed Basin Chronicle',
    'Ashen Crossing Chronicle'
  ];
  const trustFixtures = [
    { completeness: 0.94, bibliography: 0.9, spatial: 0.92, methodology: 0.94, currency: 0.9 },
    { completeness: 0.79, bibliography: 0.63, spatial: 0.76, methodology: 0.72, currency: 0.68 },
    { completeness: 0.56, bibliography: 0.34, spatial: 0.5, methodology: 0.5, currency: 0.42 },
    { completeness: 0.2, bibliography: 0.05, spatial: 0.16, methodology: 0.28, currency: 0.2 }
  ];
  const trustWeights = { completeness: 0.3, bibliography: 0.25, spatial: 0.2, methodology: 0.15, currency: 0.1 };
  const references = [];
  const chronicles = [];
  const clusters = [];
  const siteHistories = [];
  const civilizations = [];
  const phases = [];
  const persons = [];
  const events = [];
  const witnesses = [];
  const hypotheses = [];

  const siteByIndex = index => archaeology.sites[index % archaeology.sites.length];
  const yearRange = (start, end) => `${start}/${end}`;
  const trustFixture = index => ({ ...trustFixtures[index % trustFixtures.length], weights: { ...trustWeights } });
  const mediaGallery = id => ({
    id: `HISTORY-DEMO-GALLERY-${id}`,
    assets: [{
      assetType: 'drawing',
      rightsStatementUri: null,
      iiifManifestUri: null,
      status: 'unresolved_demo_placeholder'
    }]
  });
  const citationSlot = (code, index) => {
    const ref = {
      referenceId: `HISTORY-DEMO-REF-${code}-${index + 1}`,
      title: `Fictional chronicle fragment ${code}-${index + 1}`,
      zoteroKey: null,
      citationType: sourceTypes[index % sourceTypes.length],
      pageNumber: 'fixture page only',
      quotation: 'Invented citation slot; not a quotation.',
      doi: null,
      verified: false,
      status: 'fictional_placeholder_not_a_source'
    };
    references.push(ref);
    return ref;
  };
  const auditHistory = (id, name) => [
    {
      actor: 'Synthetic demo editor',
      timestamp: '2026-10-01T10:00:00Z',
      operation: 'create',
      justification: `Generated fictional ${name} fixture ${id}; no canonical record was written.`,
      previousState: null
    },
    {
      actor: 'Synthetic demo editor',
      timestamp: '2026-10-02T10:00:00Z',
      operation: 'version',
      justification: 'Illustrative editorial-history entry only.',
      previousState: { id, publicationStatus: 'draft' }
    }
  ];
  const geometry = name => ({
    status: 'fictional_schematic_not_georeferenced',
    note: `${name}: no real geographic coordinates or boundaries.`
  });

  archaeology.sites.forEach((site, index) => {
    const code = site.code;
    const regionId = `HISTORY-DEMO-REGION-${code}`;
    const clusterId = `HISTORY-DEMO-CLUSTER-${code}`;
    const siteHistoryId = `HISTORY-DEMO-SITE-HISTORY-${code}`;
    const civilizationId = `HISTORY-DEMO-CIVILIZATION-${code}`;
    const ref = citationSlot(code, index);
    const start = -4200 + index * 110;
    const end = -1550 + index * 75;
    const participatingSites = [siteByIndex(index), siteByIndex(index + 1), siteByIndex(index + 2)];

    chronicles.push({
      id: regionId,
      type: 'chronicle',
      code: `RC-${code}`,
      title: chronicleNames[index],
      name: chronicleNames[index],
      summary: `Fictional regional survey for ${site.region}; its geopolitical frame is invented.`,
      generalSurvey: `This synthetic chronicle models a geographically bounded survey around ${site.name}. Its narrative is a fixture to demonstrate how regional claims can contain sites and overlap date ranges.`,
      geopoliticalContext: `The political and environmental context for ${chronicleNames[index]} is wholly fictional. No correspondence to an actual historical region is intended.`,
      region: site.region,
      siteIds: participatingSites.map(item => item.id),
      dateEdtf: yearRange(start, end),
      yearStart: start,
      yearEnd: end,
      certaintyScore: [0.84, 0.68, 0.47, 0.36, 0.74][index],
      geometry: geometry(chronicleNames[index]),
      mediaGallery: mediaGallery(regionId),
      bibliographySlot: ref,
      publicationStatus: 'draft',
      trustFixture: trustFixture(index),
      auditHistory: auditHistory(regionId, 'regional chronicle')
    });

    const clusterEdges = [
      { fromSiteId: participatingSites[0].id, toSiteId: participatingSites[1].id, interactionType: interactionTypes[index % interactionTypes.length], certainty: 0.73 },
      { fromSiteId: participatingSites[1].id, toSiteId: participatingSites[2].id, interactionType: interactionTypes[(index + 1) % interactionTypes.length], certainty: 0.46 },
      { fromSiteId: participatingSites[0].id, toSiteId: participatingSites[2].id, interactionType: interactionTypes[(index + 2) % interactionTypes.length], certainty: 0.31 }
    ];
    clusters.push({
      id: clusterId,
      type: 'cluster',
      code: `CH-${code}`,
      title: `${site.name} interaction cluster`,
      name: `${site.name} interaction cluster`,
      summary: `A fictional ${interactionTypes[index % interactionTypes.length].replaceAll('_', ' ')} network fixture.`,
      interactionType: interactionTypes[index % interactionTypes.length],
      interactionAnalysis: 'This invented network tests neighbor discovery and path queries. Edges are hypothetical interface data, not evidence that these sites interacted.',
      siteIds: participatingSites.map(item => item.id),
      graphEdges: clusterEdges,
      regionId,
      dateEdtf: yearRange(start + 300, end - 150),
      yearStart: start + 300,
      yearEnd: end - 150,
      certaintyScore: [0.69, 0.48, 0.62, 0.38, 0.79][index],
      mediaGallery: mediaGallery(clusterId),
      networkGraphAssetId: null,
      bibliographySlot: citationSlot(code, index + 10),
      publicationStatus: 'draft',
      trustFixture: trustFixture(index + 1),
      auditHistory: auditHistory(clusterId, 'cluster history')
    });

    siteHistories.push({
      id: siteHistoryId,
      type: 'siteHistory',
      code: `SH-${code}`,
      title: `${site.name} site history`,
      name: `${site.name} site history`,
      summary: `Discovery and occupation narrative for the fictional ${site.name} site.`,
      siteId: site.id,
      regionId,
      discoveryHistory: `Synthetic discovery account for ${site.name}: survey and recording conditions are invented and do not describe an actual excavation.`,
      occupationalNarrative: `The fictional sequence at ${site.name} is used to demonstrate how a site narrative can link continuous occupation phases to separate events without treating the two as the same entity.`,
      versions: [
        { version: 1, date: '2026-10-01', note: 'Initial synthetic narrative fixture.' },
        { version: 2, date: '2026-10-02', note: 'Illustrative edit; previous state retained in the sample history.' }
      ],
      dateEdtf: yearRange(start + 200, end - 100),
      yearStart: start + 200,
      yearEnd: end - 100,
      certaintyScore: [0.8, 0.65, 0.44, 0.29, 0.72][index],
      mediaGallery: mediaGallery(siteHistoryId),
      bibliographySlot: citationSlot(code, index + 20),
      publicationStatus: 'draft',
      trustFixture: trustFixture(index + 2),
      auditHistory: auditHistory(siteHistoryId, 'site history')
    });

    const civilization = {
      id: civilizationId,
      type: 'civilization',
      code: `CC-${code}`,
      title: `${site.name} polity tradition`,
      name: `${site.name} polity tradition`,
      summary: `Fictional civilizational container for the ${site.region} dashboard.`,
      regionId,
      siteIds: participatingSites.map(item => item.id),
      dateEdtf: yearRange(start + 100, end - 100),
      yearStart: start + 100,
      yearEnd: end - 100,
      bodyText: 'Invented polity tradition used to demonstrate phases, rulers, capitals, and time-dependent dashboard updates.',
      rulerPersonIds: [],
      capitalSiteId: site.id,
      bibliographySlot: citationSlot(code, index + 30),
      mediaGallery: mediaGallery(civilizationId),
      publicationStatus: 'draft',
      certaintyScore: [0.75, 0.61, 0.49, 0.32, 0.81][index],
      trustFixture: trustFixture(index + 3),
      auditHistory: auditHistory(civilizationId, 'civilization complex')
    };
    civilizations.push(civilization);

    const personA = {
      id: `HISTORY-DEMO-PERSON-${code}-01`,
      type: 'person',
      code: `HP-${code}-01`,
      title: `Person ${code}-01`,
      name: `Person ${code}-01`,
      summary: 'A fictional ruler fixture; no real person is represented.',
      preferredName: `Person ${code}-01`,
      alternateNames: [`Demo name ${code}-A`],
      birthDateEdtf: `${start + 440}`,
      deathDateEdtf: `${start + 480}`,
      yearStart: start + 440,
      yearEnd: start + 480,
      role: 'ruler',
      roleUri: 'https://example.invalid/skos/role/ruler',
      biography: 'Invented biographical entry for dashboard and event-link testing.',
      regionId,
      civilizationId,
      siteId: site.id,
      certaintyScore: 0.54 - index * 0.035,
      vocabularyStatus: 'unverified_demo_role',
      bibliographySlot: citationSlot(code, index + 40),
      mediaGallery: mediaGallery(`PERSON-${code}-01`),
      publicationStatus: 'draft',
      trustFixture: trustFixture(index),
      auditHistory: auditHistory(`HISTORY-DEMO-PERSON-${code}-01`, 'historical person')
    };
    const personB = {
      ...personA,
      id: `HISTORY-DEMO-PERSON-${code}-02`,
      code: `HP-${code}-02`,
      title: `Person ${code}-02`,
      name: `Person ${code}-02`,
      preferredName: `Person ${code}-02`,
      alternateNames: [`Demo name ${code}-B`],
      birthDateEdtf: `${start + 820}`,
      deathDateEdtf: `${start + 860}`,
      yearStart: start + 820,
      yearEnd: start + 860,
      role: 'scribe',
      roleUri: 'https://example.invalid/skos/role/scribe',
      biography: 'Invented biographical entry linked to fictional witness and event records.',
      certaintyScore: 0.43 - index * 0.025,
      mediaGallery: mediaGallery(`PERSON-${code}-02`),
      auditHistory: auditHistory(`HISTORY-DEMO-PERSON-${code}-02`, 'historical person')
    };
    const personC = {
      ...personA,
      id: `HISTORY-DEMO-PERSON-${code}-03`,
      code: `HP-${code}-03`,
      title: `Person ${code}-03`,
      name: `Person ${code}-03`,
      preferredName: `Person ${code}-03`,
      alternateNames: [],
      birthDateEdtf: `${start + 1160}`,
      deathDateEdtf: `${start + 1200}`,
      yearStart: start + 1160,
      yearEnd: start + 1200,
      role: 'envoy',
      roleUri: 'https://example.invalid/skos/role/envoy',
      biography: 'Invented biographical entry for diplomatic event links.',
      certaintyScore: 0.7 - index * 0.04,
      mediaGallery: mediaGallery(`PERSON-${code}-03`),
      auditHistory: auditHistory(`HISTORY-DEMO-PERSON-${code}-03`, 'historical person')
    };
    const regionPeople = [personA, personB, personC];
    persons.push(...regionPeople);
    civilization.rulerPersonIds.push(personA.id, personC.id);

    const phaseStart = start + 300;
    const phaseMiddle = phaseStart + 650;
    const phaseEnd = phaseMiddle + 600;
    const regionPhases = [
      {
        id: `HISTORY-DEMO-PHASE-${code}-01`,
        type: 'phase',
        code: `PP-${code}-01`,
        title: 'Earlier polity phase',
        name: 'Earlier polity phase',
        yearStart: phaseStart,
        yearEnd: phaseMiddle,
        rulerPersonId: personA.id,
        capitalSiteId: participatingSites[0].id,
        displayOrder: 1
      },
      {
        id: `HISTORY-DEMO-PHASE-${code}-02`,
        type: 'phase',
        code: `PP-${code}-02`,
        title: 'Later polity phase',
        name: 'Later polity phase',
        yearStart: phaseMiddle,
        yearEnd: phaseEnd,
        rulerPersonId: personC.id,
        capitalSiteId: participatingSites[1].id,
        displayOrder: 2
      }
    ];
    regionPhases.forEach((phase, phaseIndex) => {
      phases.push({
        ...phase,
        civilizationId,
        regionId,
        summary: `Fictional political configuration ${phaseIndex + 1} for ${site.name}.`,
        dateEdtf: yearRange(phase.yearStart, phase.yearEnd),
        territory: geometry(phase.title),
        climateModel: `HISTORY-DEMO-CLIMATE-${code}-P${phaseIndex + 1}`,
        certaintyScore: phaseIndex === 0 ? 0.64 - index * 0.03 : 0.46 + index * 0.02,
        bibliographySlot: ref,
        mediaGallery: mediaGallery(phase.id),
        trustFixture: trustFixture(index + phaseIndex),
        auditHistory: auditHistory(phase.id, 'polity phase'),
        publicationStatus: 'draft'
      });
    });

    for (let eventIndex = 0; eventIndex < 10; eventIndex += 1) {
      const eventType = eventTypes[(eventIndex + index * 2) % eventTypes.length];
      const eventId = `HISTORY-DEMO-EVENT-${code}-${String(eventIndex + 1).padStart(2, '0')}`;
      const person = regionPeople[eventIndex % regionPeople.length];
      const phase = regionPhases[eventIndex < 5 ? 0 : 1];
      const phaseEventIndex = eventIndex % 5;
      const eventYear = phase.yearStart + 25 + phaseEventIndex * 100;
      const eventEnd = eventYear + (eventIndex % 4 === 0 ? 2 : 0);
      const typeSpecificDescription = {
        battle: 'The fictional annal describes a brief armed encounter near a crossing; no real battle is referenced.',
        treaty: 'The invented record describes an agreement between two fictional polities; its terms are interface fixtures.',
        foundation: 'The fictional narrative records a ceremonial founding event, distinct from the longer occupation period.',
        dynastic_transition: 'The invented account describes a transfer of authority; succession details remain a hypothesis.',
        eruption: 'The fictional chronicle records an environmental disturbance; no real eruption or dated proxy is implied.',
        epidemic: 'The demo narrative describes a reported health crisis, not a diagnosis or verified population event.',
        harvest: 'The fictional text records a disputed harvest failure; no real climate or crop data are represented.',
        movement: 'The invented chronicle describes movement between localities; migration is not inferred as fact.',
        legal_decree: 'The fictional account describes a legal proclamation with no real text or jurisdiction.',
        construction: 'The invented narrative records a construction event; it does not define the continuous life of the site.'
      };
      const outcomes = ['victory', 'defeat', 'inconclusive'];
      events.push({
        id: eventId,
        type: 'event',
        code: `EV-${code}-${String(eventIndex + 1).padStart(2, '0')}`,
        title: `${eventType.label}: ${site.name} ${eventIndex + 1}`,
        name: `${eventType.label}: ${site.name} ${eventIndex + 1}`,
        summary: typeSpecificDescription[eventType.key],
        eventType: eventType.key,
        eventTypeLabel: eventType.label,
        eventDateEdtf: eventEnd === eventYear ? `${eventYear}` : yearRange(eventYear, eventEnd),
        dateEdtf: eventEnd === eventYear ? `${eventYear}` : yearRange(eventYear, eventEnd),
        yearStart: eventYear,
        yearEnd: eventEnd,
        description: typeSpecificDescription[eventType.key],
        interpretation: `One fictional reading links the event to phase ${phase.displayOrder}; an alternative explanation remains open. This is not a scholarly interpretation.`,
        analysis: `In this demo, the event tests links to a regional chronicle, cluster, site history, polity phase, person, and witness. Its wider significance is deliberately unresolved.`,
        regionId,
        clusterId,
        siteHistoryId,
        civilizationId,
        siteId: participatingSites[eventIndex % participatingSites.length].id,
        phaseId: phase.id,
        personIds: [person.id],
        witnessId: `HISTORY-DEMO-WITNESS-${code}-${(eventIndex % 2) + 1}`,
        eventKind: eventType.key,
        battleOutcome: eventType.key === 'battle' ? outcomes[eventIndex % outcomes.length] : null,
        diplomaticStatus: eventType.key === 'treaty' ? 'alliance' : eventType.key === 'battle' ? 'war' : 'unknown',
        mapPoint: { x: 135 + ((eventIndex * 137 + index * 53) % 650), y: 120 + ((eventIndex * 71 + index * 39) % 260) },
        certaintyScore: [0.82, 0.68, 0.49, 0.34, 0.21, 0.76, 0.59, 0.43, 0.31, 0.88][eventIndex],
        sourceType: sourceTypes[eventIndex % sourceTypes.length],
        sourceSummary: `Synthetic witness ${code}-${(eventIndex % 2) + 1} · unresolved citation fixture`,
        resolutionTag: resolutionTags[(eventIndex + index) % resolutionTags.length],
        bibliographySlot: citationSlot(code, eventIndex + 50),
        mediaGallery: mediaGallery(eventId),
        publicationStatus: 'draft',
        trustFixture: trustFixture(eventIndex + index),
        auditHistory: auditHistory(eventId, 'historical event'),
        geometry: geometry(eventId)
      });
    }

    for (let witnessIndex = 0; witnessIndex < 2; witnessIndex += 1) {
      const witnessId = `HISTORY-DEMO-WITNESS-${code}-${witnessIndex + 1}`;
      witnesses.push({
        id: witnessId,
        type: 'witness',
        code: `TW-${code}-${witnessIndex + 1}`,
        title: `Fictional tablet witness ${code}-${witnessIndex + 1}`,
        name: `Fictional tablet witness ${code}-${witnessIndex + 1}`,
        summary: 'A synthetic textual witness for variant comparison; no manuscript or inscription is represented.',
        traditionFamily: `DEMO-TRADITION-${code}`,
        shelfmark: `DEMO-SHELF-${code}-${witnessIndex + 1}`,
        dateEdtf: yearRange(start + 800 + witnessIndex * 30, start + 850 + witnessIndex * 30),
        yearStart: start + 800 + witnessIndex * 30,
        yearEnd: start + 850 + witnessIndex * 30,
        script: 'fictional reed-mark script',
        language: `DEMO-LANG-${code}`,
        languageStatus: 'unverified fictional code; not a Glottolog identifier',
        baseText: 'At the reed gate, the council recorded the water allotment for the eastern terraces.',
        variantText: witnessIndex === 0
          ? 'At the reed gate, the council recorded the water allotment for the eastern terraces.'
          : 'At the reed gate, the elders recorded the seed allotment for the eastern terraces.',
        variantReadings: [
          { locus: 'line 1', reading: witnessIndex === 0 ? 'council' : 'elders' },
          { locus: 'line 2', reading: witnessIndex === 0 ? 'water' : 'seed' }
        ],
        interpolations: witnessIndex === 1 ? [{ passage: 'for the eastern terraces', status: 'possible_interpolation', certainty: 0.38 }] : [],
        regionId,
        personId: regionPeople[1].id,
        certaintyScore: witnessIndex === 0 ? 0.67 : 0.42,
        bibliographySlot: citationSlot(code, witnessIndex + 70),
        mediaGallery: mediaGallery(witnessId),
        publicationStatus: 'draft',
        trustFixture: trustFixture(witnessIndex + index),
        auditHistory: auditHistory(witnessId, 'text witness')
      });
    }

    const regionHypotheses = [
      {
        tag: 'contested',
        claim: `The fictional ${site.name} event sequence reflects a single coordinated transition.`,
        alternative: 'The same sample pattern could represent several unrelated local changes.'
      },
      {
        tag: 'minority',
        claim: `The fictional ${site.region} network was organized through seasonal exchange.`,
        alternative: 'The observed links could instead reflect later convergence or shared environment.'
      }
    ];
    regionHypotheses.forEach((seedHypothesis, hypothesisIndex) => {
      const hypothesisId = `HISTORY-DEMO-HYPOTHESIS-${code}-${hypothesisIndex + 1}`;
      hypotheses.push({
        id: hypothesisId,
        type: 'hypothesis',
        code: `IH-${code}-${hypothesisIndex + 1}`,
        title: `Interpretation ${hypothesisIndex + 1}: ${site.name}`,
        name: `Interpretation ${hypothesisIndex + 1}: ${site.name}`,
        summary: seedHypothesis.claim,
        argument: `${seedHypothesis.claim} ${seedHypothesis.alternative} Both positions are fabricated to demonstrate qualified debate states.`,
        proponent: regionPeople[hypothesisIndex].name,
        proponentId: regionPeople[hypothesisIndex].id,
        conflictResolutionTag: seedHypothesis.tag,
        supportingReferences: [`HISTORY-DEMO-REF-${code}-SUP-${hypothesisIndex + 1}`],
        opposingReferences: [`HISTORY-DEMO-REF-${code}-OPP-${hypothesisIndex + 1}`],
        opposes: `HISTORY-DEMO-HYPOTHESIS-${code}-${hypothesisIndex === 0 ? 2 : 1}`,
        consensusScore: [0.48, 0.34][hypothesisIndex] + index * 0.015,
        regionId,
        dateEdtf: yearRange(start + 150, end - 50),
        yearStart: start + 150,
        yearEnd: end - 50,
        certaintyScore: hypothesisIndex === 0 ? 0.41 : 0.63,
        bibliographySlot: citationSlot(code, hypothesisIndex + 80),
        mediaGallery: mediaGallery(hypothesisId),
        publicationStatus: 'draft',
        trustFixture: trustFixture(hypothesisIndex + index + 2),
        auditHistory: auditHistory(hypothesisId, 'interpretation hypothesis')
      });
    });
  });

  const records = [
    ...chronicles, ...clusters, ...siteHistories, ...civilizations,
    ...phases, ...persons, ...events, ...witnesses, ...hypotheses
  ];

  window.PLEROMA_HISTORY_DEMO = {
    demoOnly: true,
    sites: archaeology.sites,
    eventTypes,
    resolutionTags,
    chronicles,
    clusters,
    siteHistories,
    civilizations,
    phases,
    persons,
    events,
    witnesses,
    hypotheses,
    references,
    records
  };
})();
