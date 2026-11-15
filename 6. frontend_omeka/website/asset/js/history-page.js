(() => {
  'use strict';

  const data = window.PLEROMA_HISTORY_DEMO;
  if (!data || !Array.isArray(data.records) || !Array.isArray(data.events)) {
    console.error('History demo data is missing or malformed.');
    return;
  }

  const svgNamespace = 'http://www.w3.org/2000/svg';
  const pageSize = 12;
  const byId = new Map(data.records.map(record => [record.id, record]));
  const siteById = new Map(data.sites.map(site => [site.id, site]));
  const phaseById = new Map(data.phases.map(phase => [phase.id, phase]));
  const personById = new Map(data.persons.map(person => [person.id, person]));
  const witnessById = new Map(data.witnesses.map(witness => [witness.id, witness]));
  const typeNames = {
    chronicle: 'Regional chronicle',
    cluster: 'Cluster history',
    siteHistory: 'Site history',
    event: 'Historical event',
    civilization: 'Civilization complex',
    phase: 'Polity phase',
    person: 'Historical person',
    witness: 'Text witness',
    hypothesis: 'Interpretation hypothesis'
  };
  const typeOrder = ['chronicle', 'cluster', 'siteHistory', 'event', 'civilization', 'phase', 'person', 'witness', 'hypothesis'];
  const chronologyOffsets = { baseline: 0, high: 50, low: -50 };
  const battleColors = { victory: '#477653', defeat: '#a74f42', inconclusive: '#727b82' };

  const el = {
    metricChronicles: document.getElementById('metric-chronicles'),
    metricEvents: document.getElementById('metric-events'),
    metricRecords: document.getElementById('metric-records'),
    metricUncertain: document.getElementById('metric-uncertain'),
    searchForm: document.getElementById('history-search-form'),
    query: document.getElementById('history-query'),
    chronicleFilter: document.getElementById('chronicle-filter'),
    typeFilter: document.getElementById('history-type-filter'),
    eventTypeFilter: document.getElementById('event-type-filter'),
    sourceTypeFilter: document.getElementById('source-type-filter'),
    resolutionFilter: document.getElementById('resolution-filter'),
    sortFilter: document.getElementById('history-sort'),
    lowCertainty: document.getElementById('low-certainty-filter'),
    threadShortcuts: document.getElementById('thread-shortcuts'),
    mapContext: document.getElementById('map-context'),
    atlasChronicle: document.getElementById('atlas-chronicle'),
    chronologySet: document.getElementById('history-chronology-set'),
    timeScrubber: document.getElementById('history-time-scrubber'),
    timeOutput: document.getElementById('history-time-output'),
    mapLayer: document.getElementById('history-map-layer'),
    mapTitle: document.getElementById('atlas-map-title'),
    mapStateLabel: document.getElementById('atlas-state-label'),
    mapDescription: document.getElementById('atlas-state-description'),
    baseLayer: document.getElementById('atlas-base-layer'),
    primaryLayer: document.getElementById('atlas-primary-layer'),
    secondaryLayer: document.getElementById('atlas-secondary-layer'),
    phaseTitle: document.getElementById('phase-title'),
    phaseSummary: document.getElementById('phase-summary'),
    phaseDate: document.getElementById('phase-date'),
    ruler: document.getElementById('ruler-panel'),
    capital: document.getElementById('capital-panel'),
    activeSites: document.getElementById('active-sites-list'),
    diplomacy: document.getElementById('diplomacy-rows'),
    haplogroupChart: document.querySelector('#haplogroup-chart g'),
    languageChart: document.querySelector('#language-chart g'),
    commodityChart: document.querySelector('#commodity-chart g'),
    timeline: document.getElementById('history-timeline'),
    timelineSummary: document.getElementById('timeline-summary'),
    resultsSummary: document.getElementById('history-results-summary'),
    results: document.getElementById('history-results'),
    pageStatus: document.getElementById('history-page-status'),
    pagePrev: document.getElementById('history-page-prev'),
    pageNext: document.getElementById('history-page-next'),
    exportButton: document.getElementById('history-export'),
    exportStatus: document.getElementById('history-export-status'),
    inspectorTitle: document.getElementById('history-inspector-title'),
    trustBadge: document.getElementById('history-trust-badge'),
    inspector: document.getElementById('history-inspector'),
    publicationTest: document.getElementById('test-publication-gate'),
    publicationStatus: document.getElementById('publication-gate-status'),
    clusterSelect: document.getElementById('cluster-select'),
    networkStart: document.getElementById('network-start'),
    networkEnd: document.getElementById('network-end'),
    networkQuery: document.getElementById('network-query'),
    networkLayer: document.getElementById('network-layer'),
    networkOutput: document.getElementById('network-output'),
    networkNeighbors: document.getElementById('network-neighbors'),
    witnessA: document.getElementById('witness-a'),
    witnessB: document.getElementById('witness-b'),
    compareWitnesses: document.getElementById('compare-witnesses'),
    witnessMetadata: document.getElementById('witness-metadata'),
    witnessDiff: document.getElementById('witness-diff'),
    hypothesisList: document.getElementById('hypothesis-list'),
    hypothesisGraph: document.getElementById('hypothesis-graph-layer'),
    hypothesisStatus: document.getElementById('hypothesis-status')
  };

  const requiredElements = [
    'searchForm', 'query', 'chronicleFilter', 'typeFilter', 'eventTypeFilter',
    'sourceTypeFilter', 'resolutionFilter', 'sortFilter', 'lowCertainty',
    'mapContext', 'atlasChronicle', 'chronologySet', 'timeScrubber',
    'mapLayer', 'timeline', 'results', 'inspector', 'clusterSelect',
    'networkStart', 'networkEnd', 'witnessA', 'witnessB', 'hypothesisList'
  ];
  const missing = requiredElements.filter(key => !el[key]);
  if (missing.length) {
    console.error(`History page is missing required elements: ${missing.join(', ')}`);
    return;
  }

  let activeChronicleId = data.chronicles[0].id;
  let selectedRecordId = data.chronicles[0].id;
  let currentYear = -3500;
  let currentPage = 0;
  let filteredRecords = [];
  let currentClusterId = data.clusters[0].id;

  function html(tag, text = '', className = '') {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = text;
    return node;
  }

  function svg(tag, attributes = {}) {
    const node = document.createElementNS(svgNamespace, tag);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, String(value)));
    return node;
  }

  function clear(node) {
    node.replaceChildren();
  }

  function options(select, values, allLabel = '') {
    clear(select);
    if (allLabel) {
      const option = document.createElement('option');
      option.value = '';
      option.textContent = allLabel;
      select.appendChild(option);
    }
    values.forEach(item => {
      const option = document.createElement('option');
      option.value = item.value;
      option.textContent = item.label;
      select.appendChild(option);
    });
  }

  function offsetYear(year) {
    return year + (chronologyOffsets[el.chronologySet.value] || 0);
  }

  function formatYear(year) {
    const shifted = offsetYear(year);
    return shifted < 0 ? `${Math.abs(shifted).toLocaleString()} BCE` : `${shifted.toLocaleString()} CE`;
  }

  function formatDate(record) {
    if (!record || typeof record.yearStart !== 'number' || typeof record.yearEnd !== 'number') {
      return record?.dateEdtf || 'No date supplied';
    }
    return `${formatYear(record.yearStart)} – ${formatYear(record.yearEnd)} · EDTF ${record.dateEdtf}`;
  }

  function trustScore(record) {
    const t = record.trustFixture;
    if (!t) return 0;
    const w = t.weights;
    return t.completeness * w.completeness +
      t.bibliography * w.bibliography +
      t.spatial * w.spatial +
      t.methodology * w.methodology +
      t.currency * w.currency;
  }

  function trustBand(score) {
    if (score >= 0.8) return { label: 'Gold', key: 'gold' };
    if (score >= 0.55) return { label: 'Silver', key: 'silver' };
    if (score >= 0.3) return { label: 'Bronze', key: 'bronze' };
    return { label: 'Incomplete', key: 'incomplete' };
  }

  function siteName(siteId) {
    return siteById.get(siteId)?.name || 'Unknown fictional site';
  }

  function chronicleOf(record) {
    if (record.type === 'chronicle') return record;
    return data.chronicles.find(chronicle => chronicle.id === record.regionId) || null;
  }

  function selectedChronicle() {
    return data.chronicles.find(item => item.id === activeChronicleId) || data.chronicles[0];
  }

  function eventsForChronicle(chronicleId = activeChronicleId) {
    return data.events.filter(event => event.regionId === chronicleId);
  }

  function phasesForChronicle(chronicleId = activeChronicleId) {
    return data.phases.filter(phase => phase.regionId === chronicleId).sort((a, b) => a.displayOrder - b.displayOrder);
  }

  function activePhase() {
    const phases = phasesForChronicle();
    return phases.find(phase => currentYear >= phase.yearStart && currentYear <= phase.yearEnd)
      || phases.reduce((nearest, phase) => {
        const middle = (phase.yearStart + phase.yearEnd) / 2;
        const nearestMiddle = (nearest.yearStart + nearest.yearEnd) / 2;
        return Math.abs(middle - currentYear) < Math.abs(nearestMiddle - currentYear) ? phase : nearest;
      }, phases[0]);
  }

  function recordDescription(record) {
    return record.summary || record.description || record.argument || record.generalSurvey || record.biography || '';
  }

  function renderShortcuts() {
    clear(el.threadShortcuts);
    ['contested', 'minority', 'superseded'].forEach(tag => {
      const button = html('button', `${tag[0].toUpperCase()}${tag.slice(1)} readings`, 'thread-chip');
      button.type = 'button';
      button.addEventListener('click', () => {
        el.resolutionFilter.value = tag;
        currentPage = 0;
        renderResults();
        document.getElementById('history-results-title').scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
      el.threadShortcuts.appendChild(button);
    });
  }

  function initializeControls() {
    document.getElementById('metric-chronicles').textContent = String(data.chronicles.length);
    document.getElementById('metric-events').textContent = String(data.events.length);
    document.getElementById('metric-records').textContent = String(data.records.length);
    document.getElementById('metric-uncertain').textContent = String(
      data.records.filter(record => record.certaintyScore < 0.5).length
    );
    const chronicles = data.chronicles.map(item => ({ value: item.id, label: `${item.name} · ${item.region}` }));
    options(el.chronicleFilter, chronicles, 'All fictional regions');
    options(el.atlasChronicle, chronicles);
    options(el.eventTypeFilter, data.eventTypes.map(type => ({ value: type.key, label: type.label })), 'All event types');
    options(el.clusterSelect, data.clusters.map(cluster => ({ value: cluster.id, label: cluster.name })));
    options(el.witnessA, data.witnesses.map(witness => ({ value: witness.id, label: `${witness.code} · ${witness.title}` })));
    options(el.witnessB, data.witnesses.map(witness => ({ value: witness.id, label: `${witness.code} · ${witness.title}` })));
    el.atlasChronicle.value = activeChronicleId;
    el.clusterSelect.value = currentClusterId;
    el.witnessA.value = data.witnesses[0].id;
    el.witnessB.value = data.witnesses[1].id;
    updateTimeRange();
    renderShortcuts();
    renderResults();
    renderInspector();
    renderAtlas();
    renderNetwork();
    renderWitnessComparison();
    renderHypotheses();
  }

  function updateTimeRange() {
    const chronicle = selectedChronicle();
    el.timeScrubber.min = String(chronicle.yearStart);
    el.timeScrubber.max = String(chronicle.yearEnd);
    currentYear = Math.max(chronicle.yearStart, Math.min(chronicle.yearEnd, currentYear));
    el.timeScrubber.value = String(currentYear);
    el.timeOutput.textContent = formatYear(currentYear);
  }

  function getMatches() {
    const query = el.query.value.trim().toLocaleLowerCase();
    const chronicleId = el.chronicleFilter.value;
    const type = el.typeFilter.value;
    const eventType = el.eventTypeFilter.value;
    const sourceType = el.sourceTypeFilter.value;
    const resolution = el.resolutionFilter.value;
    const lowOnly = el.lowCertainty.checked;

    const result = data.records.filter(record => {
      if (chronicleId && chronicleOf(record)?.id !== chronicleId) return false;
      if (type && record.type !== type) return false;
      if (eventType && (record.type !== 'event' || record.eventType !== eventType)) return false;
      if (sourceType && (record.type !== 'event' || record.sourceType !== sourceType)) return false;
      const tag = record.conflictResolutionTag || record.resolutionTag;
      if (resolution && tag !== resolution) return false;
      if (lowOnly && record.certaintyScore >= 0.5) return false;
      if (!query) return true;
      const searchable = [
        record.id, record.code, record.title, record.name, record.summary,
        record.description, record.interpretation, record.analysis, record.argument,
        record.generalSurvey, record.geopoliticalContext, record.occupationalNarrative,
        record.discoveryHistory, record.biography, record.eventTypeLabel,
        record.interactionType, record.role, record.script, record.language,
        record.sourceSummary, record.sourceType, record.resolutionTag,
        record.conflictResolutionTag, record.dateEdtf, record.shelfmark,
        record.preferredName, record.traditionFamily, record.region
      ].filter(Boolean);
      const chronicle = chronicleOf(record);
      if (chronicle) searchable.push(chronicle.name, chronicle.region, chronicle.generalSurvey);
      if (record.siteId) searchable.push(siteName(record.siteId));
      if (Array.isArray(record.siteIds)) record.siteIds.forEach(id => searchable.push(siteName(id)));
      const citation = record.bibliographySlot;
      if (citation) searchable.push(citation.title, citation.citationType);
      return searchable.some(value => String(value).toLocaleLowerCase().includes(query));
    });

    if (el.sortFilter.value === 'date') {
      result.sort((a, b) => (a.yearStart ?? 0) - (b.yearStart ?? 0) || a.title.localeCompare(b.title));
    } else if (el.sortFilter.value === 'trust') {
      result.sort((a, b) => trustScore(b) - trustScore(a) || a.title.localeCompare(b.title));
    } else if (el.sortFilter.value === 'name') {
      result.sort((a, b) => a.title.localeCompare(b.title, undefined, { numeric: true }));
    } else {
      result.sort((a, b) =>
        typeOrder.indexOf(a.type) - typeOrder.indexOf(b.type) ||
        (a.regionId || a.id).localeCompare(b.regionId || b.id) ||
        a.title.localeCompare(b.title, undefined, { numeric: true })
      );
    }
    return result;
  }

  function renderResults() {
    filteredRecords = getMatches();
    const pages = Math.max(1, Math.ceil(filteredRecords.length / pageSize));
    currentPage = Math.min(currentPage, pages - 1);
    const start = currentPage * pageSize;
    const visible = filteredRecords.slice(start, start + pageSize);
    clear(el.results);

    if (!visible.length) {
      el.results.appendChild(html('p', 'No fictional historical records match these filters.', 'empty-history-results'));
    }
    visible.forEach(record => {
      const score = trustScore(record);
      const band = trustBand(score);
      const card = html('button', '', `history-result-card${record.id === selectedRecordId ? ' is-selected' : ''}`);
      card.type = 'button';
      card.setAttribute('aria-label', `${typeNames[record.type]}: ${record.title}`);
      const top = html('span', '', 'history-result-card__top');
      top.append(
        html('span', record.code || record.id, 'history-record-code'),
        html('span', `Demo ${band.label} · ${score.toFixed(2)}`, `history-result-badge history-trust--${band.key}`)
      );
      card.append(
        top,
        html('strong', record.title, 'history-result-title'),
        html('span', `${typeNames[record.type]} · ${chronicleOf(record)?.name || 'No region link'}`, 'history-result-subtitle'),
        html('span', recordDescription(record), 'history-result-description'),
        html('span', `${formatDate(record)} · certainty ${record.certaintyScore.toFixed(2)}`, 'history-result-date')
      );
      card.addEventListener('click', () => selectRecord(record.id));
      el.results.appendChild(card);
    });

    el.resultsSummary.textContent =
      `${filteredRecords.length} of ${data.records.length} synthetic historical records · ${data.events.length} discrete events · five fictional chronicles.`;
    el.pageStatus.textContent = filteredRecords.length
      ? `Page ${currentPage + 1} of ${pages} · ${start + 1}–${Math.min(start + pageSize, filteredRecords.length)} records`
      : 'No results';
    el.pagePrev.disabled = currentPage === 0;
    el.pageNext.disabled = currentPage >= pages - 1;
  }

  function selectRecord(id) {
    const record = byId.get(id);
    if (!record) return;
    selectedRecordId = record.id;
    const chronicle = chronicleOf(record);
    if (chronicle) {
      activeChronicleId = chronicle.id;
      el.atlasChronicle.value = activeChronicleId;
      updateTimeRange();
    }
    if (typeof record.yearStart === 'number' && typeof record.yearEnd === 'number') {
      currentYear = Math.round((record.yearStart + record.yearEnd) / 2);
      el.timeScrubber.value = String(currentYear);
      el.timeOutput.textContent = formatYear(currentYear);
    }
    if (record.type === 'event') el.mapContext.value = 'event';
    else if (record.type === 'siteHistory') el.mapContext.value = 'site';
    else if (record.type === 'civilization' || record.type === 'phase' || record.type === 'person') el.mapContext.value = 'civilization';
    else if (record.type === 'chronicle' || record.type === 'cluster') el.mapContext.value = 'regional';
    renderInspector();
    renderResults();
    renderAtlas();
    renderHypotheses();
  }

  function definitionList(parent, entries) {
    const dl = document.createElement('dl');
    dl.className = 'history-definition-list';
    entries.forEach(([term, value]) => {
      const row = document.createElement('div');
      row.append(html('dt', term), html('dd', value || 'Not supplied'));
      dl.appendChild(row);
    });
    parent.appendChild(dl);
    return dl;
  }

  function inspectorSection(parent, heading, content) {
    const section = document.createElement('section');
    section.className = 'inspector-section';
    section.appendChild(html('h4', heading));
    if (typeof content === 'string') section.appendChild(html('p', content));
    else section.appendChild(content);
    parent.appendChild(section);
    return section;
  }

  function renderInspector() {
    const record = byId.get(selectedRecordId);
    if (!record) return;
    clear(el.inspector);
    el.inspectorTitle.textContent = record.title;
    const band = trustBand(trustScore(record));
    el.trustBadge.className = `trust-badge history-trust--${band.key}`;
    el.trustBadge.textContent = `Demo ${band.label} · ${trustScore(record).toFixed(2)}`;
    el.trustBadge.setAttribute('aria-label', `Synthetic trust score preview; ${band.label}; not a real assessment`);

    el.inspector.appendChild(html('span', record.code || record.id, 'history-record-code'));
    el.inspector.appendChild(html('p', record.summary || recordDescription(record), 'history-inspector-summary'));

    const common = [
      ['Record type', typeNames[record.type]],
      ['Regional chronicle', chronicleOf(record)?.name || 'Not linked'],
      ['EDTF expression', record.dateEdtf || record.eventDateEdtf || 'Not supplied'],
      ['Displayed date', formatDate(record)],
      ['Certainty score', `${record.certaintyScore.toFixed(2)} / 1.00`],
      ['Publication state', `${record.publicationStatus || 'draft'} · synthetic fixture`]
    ];
    if (record.type === 'chronicle') common.push(
      ['Region polygon', record.geometry.note],
      ['Contained site IDs', record.siteIds.map(siteName).join('; ')]
    );
    if (record.type === 'cluster') common.push(
      ['Interaction type', record.interactionType.replaceAll('_', ' ')],
      ['Participating sites', record.siteIds.map(siteName).join('; ')],
      ['Network graph asset', 'Unresolved; no Media_Asset is attached']
    );
    if (record.type === 'siteHistory') common.push(
      ['Site', siteName(record.siteId)],
      ['Versioned history', record.versions.map(version => `v${version.version} (${version.date})`).join('; ')]
    );
    if (record.type === 'event') common.push(
      ['Event kind', record.eventTypeLabel],
      ['Discrete / continuous', 'Discrete Historical_Event; not an Occupational_Period'],
      ['Linked site', siteName(record.siteId)],
      ['Polity phase', phaseById.get(record.phaseId)?.title || 'Not linked'],
      ['Source type', record.sourceType.replaceAll('_', ' ')],
      ['Diplomatic status', record.diplomaticStatus],
      ['Battle outcome', record.battleOutcome || 'Not a battle']
    );
    if (record.type === 'civilization') common.push(
      ['Ordered ruler list', record.rulerPersonIds.map(id => personById.get(id)?.name || id).join(' → ')],
      ['Capital site', siteName(record.capitalSiteId)]
    );
    if (record.type === 'phase') common.push(
      ['Civilization', byId.get(record.civilizationId)?.name],
      ['Ruler', personById.get(record.rulerPersonId)?.name],
      ['Capital site', siteName(record.capitalSiteId)],
      ['Paleoclimate model', record.climateModel],
      ['Territorial geometry', record.territory.note]
    );
    if (record.type === 'person') common.push(
      ['Preferred name', record.preferredName],
      ['Alternative names', record.alternateNames.join('; ') || 'None supplied'],
      ['Birth / death EDTF', `${record.birthDateEdtf} / ${record.deathDateEdtf}`],
      ['Role', `${record.role} · vocabulary mapping unverified`],
      ['Biography', record.biography]
    );
    if (record.type === 'witness') common.push(
      ['Tradition family', record.traditionFamily],
      ['Shelfmark', record.shelfmark],
      ['Script', record.script],
      ['Language code', `${record.language} · ${record.languageStatus}`],
      ['Variant readings', record.variantReadings.map(item => `${item.locus}: ${item.reading}`).join('; ')],
      ['Flagged interpolations', record.interpolations.map(item => `${item.passage} (${item.status}, ${item.certainty})`).join('; ') || 'None in this fixture']
    );
    if (record.type === 'hypothesis') common.push(
      ['Proponent', record.proponent],
      ['Conflict-resolution tag', record.conflictResolutionTag],
      ['Opposing hypothesis', byId.get(record.opposes)?.title || 'Not linked'],
      ['Supporting references', 'Fictional placeholder only'],
      ['Opposing references', 'Fictional placeholder only'],
      ['Qualified consensus fixture', `${(record.consensusScore * 100).toFixed(0)}% · not a judgment`]
    );
    definitionList(el.inspector, common);

    if (record.type === 'event') {
      inspectorSection(el.inspector, 'Description · what is said to have happened', record.description);
      inspectorSection(el.inspector, 'Interpretation · one reading', record.interpretation);
      inspectorSection(el.inspector, 'Analysis · significance and limits', record.analysis);
    } else if (record.type === 'chronicle') {
      inspectorSection(el.inspector, 'General survey', record.generalSurvey);
      inspectorSection(el.inspector, 'Geopolitical context', record.geopoliticalContext);
    } else if (record.type === 'siteHistory') {
      inspectorSection(el.inspector, 'Discovery history', record.discoveryHistory);
      inspectorSection(el.inspector, 'Occupational narrative', record.occupationalNarrative);
    } else if (record.type === 'cluster') {
      inspectorSection(el.inspector, 'Interaction analysis', record.interactionAnalysis);
    } else if (record.type === 'civilization') {
      inspectorSection(el.inspector, 'Civilizational body text', record.bodyText);
    } else if (record.type === 'hypothesis') {
      inspectorSection(el.inspector, 'Argument and counter-reading', record.argument);
    }

    const trustInputs = record.trustFixture;
    const trustList = document.createElement('ul');
    [
      ['Completeness · 30%', trustInputs.completeness],
      ['Bibliographic density · 25%', trustInputs.bibliography],
      ['Spatial precision · 20%', trustInputs.spatial],
      ['Methodology · 15%', trustInputs.methodology],
      ['Data currency · 10%', trustInputs.currency]
    ].forEach(([label, value]) => trustList.appendChild(html('li', `${label}: ${Number(value).toFixed(2)} (fixture input)`)));
    inspectorSection(el.inspector, `Trust Score preview · ${trustScore(record).toFixed(2)} / 1.00`, trustList);

    if (record.certaintyScore < 0.5) {
      el.inspector.appendChild(html(
        'div',
        `Uncertainty indicator: certainty ${record.certaintyScore.toFixed(2)} is below 0.50. EDTF bounds and interpretations remain distinct.`,
        'history-uncertainty'
      ));
    }

    const reference = record.bibliographySlot;
    const citation = document.createElement('ul');
    citation.append(
      html('li', `${reference.title} · ${reference.citationType.replaceAll('_', ' ')}`),
      html('li', `Zotero key: ${reference.zoteroKey || 'missing'} · DOI: ${reference.doi || 'not supplied'} · ${reference.pageNumber}`),
      html('li', 'Fixture quotation field is invented and is not a primary-source excerpt.')
    );
    const citationSection = inspectorSection(el.inspector, 'Bibliographic anchor', citation);
    citationSection.appendChild(html('p', 'This synthetic reference slot is not a real or verified source; publication must remain blocked.', 'history-integrity-note'));

    const gallery = record.mediaGallery;
    const mediaSection = inspectorSection(
      el.inspector,
      'Media gallery / IIIF',
      `${gallery.id} · ${gallery.assets.length} planned asset · rights statement missing · manifest unresolved.`
    );
    mediaSection.appendChild(html('p', 'Production records need a rights-cleared gallery and resolvable IIIF manifest.', 'history-integrity-note'));

    const audit = document.createElement('ul');
    record.auditHistory.forEach(change => {
      audit.appendChild(html('li', `${change.operation} · ${change.timestamp} · ${change.actor}: ${change.justification}`));
    });
    const auditSection = inspectorSection(el.inspector, 'Editorial history preview', audit);
    auditSection.appendChild(html('p', 'Fictional UI rows only; immutable edits and justifications require the server audit log.', 'history-integrity-note'));
  }

  const siteCoordinates = [
    { x: 150, y: 170 },
    { x: 300, y: 125 },
    { x: 465, y: 175 },
    { x: 630, y: 130 },
    { x: 765, y: 250 }
  ];

  function siteCoordinate(siteId) {
    const index = data.sites.findIndex(site => site.id === siteId);
    return siteCoordinates[index < 0 ? 0 : index];
  }

  function selectedHistoricalEvent() {
    const selected = byId.get(selectedRecordId);
    if (selected?.type === 'event') return selected;
    return eventsForChronicle().reduce((nearest, event) =>
      Math.abs((event.yearStart + event.yearEnd) / 2 - currentYear) <
      Math.abs((nearest.yearStart + nearest.yearEnd) / 2 - currentYear) ? event : nearest
    , eventsForChronicle()[0]);
  }

  function eventMarker(event, x = event.mapPoint.x, y = event.mapPoint.y, focus = false) {
    let node;
    if (event.eventType === 'battle') {
      const color = battleColors[event.battleOutcome] || battleColors.inconclusive;
      node = svg('path', {
        d: `M ${x} ${y - 11} L ${x + 11} ${y} L ${x} ${y + 11} L ${x - 11} ${y} Z`,
        class: `event-marker battle-marker battle-${event.battleOutcome}${focus ? ' is-selected' : ''}`,
        fill: color
      });
    } else {
      node = svg('circle', {
        cx: x,
        cy: y,
        r: focus ? 10 : 7,
        class: `event-marker${focus ? ' is-selected' : ''}`,
        fill: event.certaintyScore < 0.3 ? '#a98156' : '#684f39'
      });
    }
    node.setAttribute('tabindex', '0');
    node.setAttribute('role', 'button');
    node.setAttribute('aria-label', `${event.eventTypeLabel}: ${event.title}; ${formatDate(event)}`);
    node.setAttribute('opacity', event.certaintyScore < 0.3 ? '0.42' : '0.92');
    node.appendChild(svg('title')).textContent =
      `${event.title} · ${event.battleOutcome || event.eventTypeLabel} · certainty ${event.certaintyScore.toFixed(2)}`;
    node.addEventListener('click', () => selectRecord(event.id));
    node.addEventListener('keydown', eventKey => {
      if (eventKey.key === 'Enter' || eventKey.key === ' ') {
        eventKey.preventDefault();
        selectRecord(event.id);
      }
    });
    el.mapLayer.appendChild(node);
    return node;
  }

  function renderAtlas() {
    const chronicle = selectedChronicle();
    const focus = el.mapContext.value;
    const events = eventsForChronicle(chronicle.id);
    const sites = chronicle.siteIds.map(id => siteById.get(id)).filter(Boolean);
    const phase = activePhase();
    const selectedEvent = selectedHistoricalEvent();
    const selectedRecord = byId.get(selectedRecordId);
    clear(el.mapLayer);

    const boundary = svg('path', {
      d: 'M 90 102 L 240 72 L 400 94 L 575 72 L 792 116 L 850 250 L 762 393 L 565 425 L 358 390 L 160 425 L 65 270 Z',
      class: 'chronicle-boundary'
    });
    el.mapLayer.appendChild(boundary);
    const regionLabel = svg('text', { x: 450, y: 58, class: 'atlas-map-label', 'text-anchor': 'middle' });
    regionLabel.textContent = chronicle.name;
    el.mapLayer.appendChild(regionLabel);

    if (focus === 'civilization') {
      const phaseIndex = phase.displayOrder;
      const phaseShape = svg('path', {
        d: phaseIndex === 1
          ? 'M 155 122 L 480 105 L 635 187 L 512 316 L 190 300 L 105 205 Z'
          : 'M 270 130 L 700 130 L 815 255 L 665 366 L 330 342 L 175 235 Z',
        class: 'polity-phase-shape'
      });
      el.mapLayer.appendChild(phaseShape);
    }

    if (focus === 'site') {
      const siteHistory = selectedRecord?.type === 'siteHistory'
        ? selectedRecord
        : data.siteHistories.find(item => item.siteId === sites[0]?.id);
      const site = siteById.get(siteHistory?.siteId || sites[0]?.id);
      if (site) {
        const point = siteCoordinate(site.id);
        el.mapLayer.appendChild(svg('circle', { cx: point.x, cy: point.y, r: 45, class: 'site-focus-ring' }));
        const label = svg('text', { x: point.x, y: point.y + 61, class: 'atlas-map-label', 'text-anchor': 'middle' });
        label.textContent = site.name;
        el.mapLayer.appendChild(label);
        events.filter(item => item.siteId === site.id).forEach(item => eventMarker(item));
      }
    } else if (focus === 'event') {
      if (selectedEvent) {
        const linkedSite = siteCoordinate(selectedEvent.siteId);
        el.mapLayer.appendChild(svg('circle', { cx: linkedSite.x, cy: linkedSite.y, r: 30, class: 'site-focus-ring' }));
        eventMarker(selectedEvent, selectedEvent.mapPoint.x, selectedEvent.mapPoint.y, true);
        const label = svg('text', {
          x: selectedEvent.mapPoint.x,
          y: selectedEvent.mapPoint.y - 20,
          class: 'atlas-map-label',
          'text-anchor': 'middle'
        });
        label.textContent = selectedEvent.eventTypeLabel;
        el.mapLayer.appendChild(label);
      }
    } else {
      sites.forEach(site => {
        const point = siteCoordinate(site.id);
        const markerClass = focus === 'civilization' && phase.capitalSiteId === site.id
          ? 'site-marker capital-marker'
          : 'site-marker';
        const marker = svg('circle', { cx: point.x, cy: point.y, r: 10, class: markerClass });
        marker.setAttribute('tabindex', '0');
        marker.setAttribute('role', 'button');
        marker.setAttribute('aria-label', `Open site history for ${site.name}`);
        marker.appendChild(svg('title')).textContent = site.name;
        marker.addEventListener('click', () => {
          const history = data.siteHistories.find(item => item.siteId === site.id);
          if (history) selectRecord(history.id);
        });
        el.mapLayer.appendChild(marker);
        const label = svg('text', { x: point.x, y: point.y + 26, class: 'atlas-map-label', 'text-anchor': 'middle' });
        label.textContent = site.code;
        el.mapLayer.appendChild(label);
      });

      if (focus === 'regional') {
        const buckets = new Map();
        events.forEach(event => {
          const century = Math.floor(event.yearStart / 100) * 100;
          buckets.set(century, [...(buckets.get(century) || []), event]);
        });
        [...buckets.entries()].forEach(([century, bucket], index) => {
          const x = 225 + (index % 4) * 155;
          const y = 325 + Math.floor(index / 4) * 42;
          const circle = svg('circle', { cx: x, cy: y, r: 15 + Math.min(bucket.length, 8), class: 'event-cluster' });
          circle.setAttribute('tabindex', '0');
          circle.setAttribute('role', 'button');
          circle.setAttribute('aria-label', `${bucket.length} events clustered in century ${century}`);
          circle.addEventListener('click', () => selectRecord(bucket[0].id));
          el.mapLayer.appendChild(circle);
          const count = svg('text', { x, y: y + 4, class: 'event-cluster-count', 'text-anchor': 'middle' });
          count.textContent = String(bucket.length);
          el.mapLayer.appendChild(count);
        });
      } else {
        const inCentury = events.filter(event => Math.abs(event.yearStart - currentYear) <= 150);
        inCentury.forEach(event => eventMarker(event));
      }
    }

    if (focus === 'regional') {
      el.mapStateLabel.textContent = 'Regional_Chronicle';
      el.mapTitle.textContent = chronicle.name;
      el.mapDescription.textContent = 'Sites cluster within this fictional region; event bubbles summarize discrete records by century.';
      el.baseLayer.textContent = 'Paleo-Köppen climate map · unavailable';
      el.primaryLayer.textContent = 'Regional boundary polygon · schematic';
      el.secondaryLayer.textContent = 'Site-density / century event clusters';
    } else if (focus === 'civilization') {
      el.mapStateLabel.textContent = 'Civilization_Complex';
      el.mapTitle.textContent = byId.get(phase.civilizationId)?.name || 'Fictional polity';
      el.mapDescription.textContent = 'Time selects a polity phase and capital. Polygon transition is a static schematic, not interpolated GIS data.';
      el.baseLayer.textContent = `Paleoclimate raster · ${phase.climateModel} · unavailable`;
      el.primaryLayer.textContent = `${phase.title} territorial extent · schematic`;
      el.secondaryLayer.textContent = 'Capital marker + century event clusters';
    } else if (focus === 'site') {
      el.mapStateLabel.textContent = 'Site_History';
      el.mapTitle.textContent = 'Site history focus';
      el.mapDescription.textContent = 'One site and its linked discrete events; occupation remains a separate continuous entity.';
      el.baseLayer.textContent = 'Modern basemap + elevation · unavailable';
      el.primaryLayer.textContent = 'Site boundary · schematic';
      el.secondaryLayer.textContent = 'Site-linked historical events';
    } else {
      el.mapStateLabel.textContent = 'Historical_Event';
      el.mapTitle.textContent = selectedEvent?.title || 'Historical event';
      el.mapDescription.textContent = 'A single event is focused with its associated site; battle outcome symbols are outcome-coded.';
      el.baseLayer.textContent = 'Site orthophoto · unavailable';
      el.primaryLayer.textContent = 'Selected event point';
      el.secondaryLayer.textContent = 'Related site / battle outcome';
    }
    renderCivilizationSidebar(chronicle, phase, events, sites);
    renderTimeline(events);
  }

  function renderCivilizationSidebar(chronicle, phase, events, sites) {
    const ruler = personById.get(phase.rulerPersonId);
    const capital = siteById.get(phase.capitalSiteId);
    el.phaseTitle.textContent = `${chronicle.name} · ${phase.title}`;
    el.phaseSummary.textContent = phase.summary;
    el.phaseDate.textContent = formatDate(phase);
    el.ruler.textContent = ruler ? `${ruler.preferredName} · ${ruler.role} (fictional)` : 'No ruler fixture';
    el.capital.textContent = capital ? `${capital.name} · validity follows this phase (fixture)` : 'No capital linked';

    clear(el.activeSites);
    const contemporary = sites.filter(site => currentYear >= site.yearStart && currentYear <= site.yearEnd);
    (contemporary.length ? contemporary : sites).forEach(site => {
      const item = html('li', '', '');
      const button = html('button', `${site.name} · ${contemporary.length ? 'active fixture' : 'chronicle site'}`, 'active-site-button');
      button.type = 'button';
      button.addEventListener('click', () => {
        const history = data.siteHistories.find(record => record.siteId === site.id);
        if (history) selectRecord(history.id);
      });
      item.appendChild(button);
      el.activeSites.appendChild(item);
    });

    const diplomaticEvents = events.filter(event =>
      (event.eventType === 'treaty' || event.eventType === 'battle') &&
      Math.abs(event.yearStart - currentYear) <= 250
    ).slice(0, 5);
    clear(el.diplomacy);
    if (!diplomaticEvents.length) {
      const row = document.createElement('tr');
      const cell = html('td', 'No nearby diplomatic fixture events.');
      cell.colSpan = 3;
      row.appendChild(cell);
      el.diplomacy.appendChild(row);
    } else {
      diplomaticEvents.forEach(event => {
        const cluster = data.clusters.find(item => item.id === event.clusterId);
        const pair = cluster?.siteIds.slice(0, 2).map(siteName).join(' ↔ ') || 'Fictional polity pair';
        const row = document.createElement('tr');
        row.append(
          html('td', pair),
          html('td', event.diplomaticStatus),
          html('td', event.title)
        );
        el.diplomacy.appendChild(row);
      });
    }
    renderDashboardCharts(chronicle, phase);
  }

  function renderDashboardCharts(chronicle, phase) {
    const offset = Math.abs(Math.floor(currentYear / 100)) + chronicle.code.charCodeAt(3);
    renderBarChart(el.haplogroupChart, [
      ['DEMO-H1', 18 + offset % 17],
      ['DEMO-H2', 14 + (offset * 2) % 20],
      ['DEMO-H3', 10 + (offset * 3) % 15]
    ]);
    renderBarChart(el.languageChart, [
      ['Fictional family A', 30 + offset % 55],
      ['Fictional family B', 20 + (offset * 2) % 60],
      ['Reconstructed zone', 10 + (offset * 3) % 38]
    ]);
    renderBarChart(el.commodityChart, [
      ['Ceramic (fixture)', 12 + offset % 35],
      ['Stone (fixture)', 18 + (offset * 2) % 44],
      ['Shell (fixture)', 8 + (offset * 3) % 27]
    ]);
  }

  function renderBarChart(group, rows) {
    if (!group) return;
    clear(group);
    const max = Math.max(...rows.map(([, value]) => value));
    rows.forEach(([label, value], index) => {
      const y = 26 + index * 39;
      const text = svg('text', { x: 4, y: y + 14, class: 'dashboard-chart-label' });
      text.textContent = label;
      const rect = svg('rect', {
        x: 142,
        y,
        width: Math.max(2, 220 * value / max),
        height: 22,
        rx: 3,
        class: 'dashboard-chart-bar'
      });
      const number = svg('text', { x: 375, y: y + 15, class: 'dashboard-chart-value' });
      number.textContent = String(value);
      group.append(text, rect, number);
    });
  }

  function renderTimeline(events) {
    const near = events.filter(event => Math.abs(event.yearStart - currentYear) <= 225)
      .sort((a, b) => a.yearStart - b.yearStart);
    const timelineEvents = near.length ? near : [...events]
      .sort((a, b) => Math.abs(a.yearStart - currentYear) - Math.abs(b.yearStart - currentYear))
      .slice(0, 5)
      .sort((a, b) => a.yearStart - b.yearStart);
    clear(el.timeline);
    timelineEvents.forEach(event => {
      const button = html('button', '', `timeline-event${event.certaintyScore < 0.3 ? ' is-low-certainty' : ''}`);
      button.type = 'button';
      button.setAttribute('role', 'listitem');
      button.append(
        html('span', formatDate(event), 'timeline-event__date'),
        html('strong', event.title, 'timeline-event__title'),
        html('span', `${event.eventTypeLabel} · certainty ${event.certaintyScore.toFixed(2)}`, 'timeline-event__meta')
      );
      button.addEventListener('click', () => selectRecord(event.id));
      el.timeline.appendChild(button);
    });
    el.timelineSummary.textContent = near.length
      ? `${near.length} event fixtures within ±225 years of ${formatYear(currentYear)}.`
      : `No close events; showing the nearest fixtures to ${formatYear(currentYear)}.`;
  }

  function selectedCluster() {
    return data.clusters.find(cluster => cluster.id === el.clusterSelect.value) || data.clusters[0];
  }

  function updateNetworkOptions() {
    const cluster = selectedCluster();
    const values = cluster.siteIds.map(id => ({ value: id, label: siteName(id) }));
    const start = el.networkStart.value;
    const end = el.networkEnd.value;
    options(el.networkStart, values);
    options(el.networkEnd, values);
    el.networkStart.value = values.some(item => item.value === start) ? start : values[0]?.value || '';
    el.networkEnd.value = values.some(item => item.value === end) ? end : values.at(-1)?.value || '';
  }

  function graphAdjacency(cluster) {
    const adjacency = new Map(cluster.siteIds.map(id => [id, new Set()]));
    cluster.graphEdges.forEach(edge => {
      adjacency.get(edge.fromSiteId)?.add(edge.toSiteId);
      adjacency.get(edge.toSiteId)?.add(edge.fromSiteId);
    });
    return adjacency;
  }

  function shortestPath(adjacency, start, end) {
    if (!adjacency.has(start) || !adjacency.has(end)) return null;
    const queue = [start];
    const previous = new Map([[start, null]]);
    while (queue.length) {
      const current = queue.shift();
      if (current === end) break;
      for (const neighbor of adjacency.get(current) || []) {
        if (previous.has(neighbor)) continue;
        previous.set(neighbor, current);
        queue.push(neighbor);
      }
    }
    if (!previous.has(end)) return null;
    const path = [];
    for (let cursor = end; cursor !== null; cursor = previous.get(cursor)) path.unshift(cursor);
    return path;
  }

  function renderNetwork() {
    const cluster = selectedCluster();
    currentClusterId = cluster.id;
    updateNetworkOptions();
    clear(el.networkLayer);
    const adjacency = graphAdjacency(cluster);
    const positions = new Map(cluster.siteIds.map((id, index) => {
      const angle = -Math.PI / 2 + (Math.PI * 2 * index) / cluster.siteIds.length;
      return [id, { x: 360 + Math.cos(angle) * 225, y: 145 + Math.sin(angle) * 90 }];
    }));

    cluster.graphEdges.forEach(edge => {
      const from = positions.get(edge.fromSiteId);
      const to = positions.get(edge.toSiteId);
      if (!from || !to) return;
      const line = svg('line', {
        x1: from.x, y1: from.y, x2: to.x, y2: to.y,
        class: 'network-edge',
        'stroke-dasharray': edge.certainty < 0.5 ? '7 6' : 'none'
      });
      line.appendChild(svg('title')).textContent =
        `${edge.interactionType.replaceAll('_', ' ')} · certainty ${edge.certainty.toFixed(2)}`;
      el.networkLayer.appendChild(line);
    });

    cluster.siteIds.forEach(siteId => {
      const point = positions.get(siteId);
      const group = svg('g', { class: 'network-node', tabindex: 0, role: 'button', 'aria-label': siteName(siteId) });
      group.appendChild(svg('circle', { cx: point.x, cy: point.y, r: 27 }));
      const label = svg('text', { x: point.x, y: point.y + 48, class: 'network-node-label', 'text-anchor': 'middle' });
      label.textContent = siteName(siteId);
      group.appendChild(label);
      group.addEventListener('click', () => {
        const history = data.siteHistories.find(item => item.siteId === siteId);
        if (history) selectRecord(history.id);
      });
      group.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          const history = data.siteHistories.find(item => item.siteId === siteId);
          if (history) selectRecord(history.id);
        }
      });
      el.networkLayer.appendChild(group);
    });

    const start = el.networkStart.value;
    const end = el.networkEnd.value;
    const path = shortestPath(adjacency, start, end);
    const neighbors = [...(adjacency.get(start) || [])];
    const degree = neighbors.length;
    const centrality = cluster.siteIds.length > 1 ? degree / (cluster.siteIds.length - 1) : 0;
    el.networkOutput.textContent = path
      ? `${path.map(siteName).join(' → ')} · ${path.length - 1} edge(s). Degree centrality of start node: ${centrality.toFixed(2)}.`
      : 'No path exists between these nodes in the current fixture.';
    clear(el.networkNeighbors);
    if (neighbors.length) {
      neighbors.forEach(id => el.networkNeighbors.appendChild(html('li', `${siteName(id)} · direct neighbor`)));
    } else {
      el.networkNeighbors.appendChild(html('li', 'No direct neighbors.'));
    }
  }

  function getWitness(id) {
    return witnessById.get(id) || data.witnesses[0];
  }

  function renderWitnessComparison() {
    const left = getWitness(el.witnessA.value);
    const right = getWitness(el.witnessB.value);
    clear(el.witnessMetadata);
    [left, right].forEach((witness, index) => {
      const card = html('article', '', 'witness-metadata-card');
      card.append(
        html('h3', `${index === 0 ? 'Witness A' : 'Witness B'} · ${witness.code}`),
        html('p', `${witness.traditionFamily} · ${witness.shelfmark}`),
        html('p', `EDTF ${witness.dateEdtf} · ${witness.script}`),
        html('p', `${witness.language} · ${witness.languageStatus}`)
      );
      if (witness.interpolations.length) {
        card.appendChild(html(
          'p',
          `Flagged interpolation: ${witness.interpolations.map(item => `${item.passage} (${item.status}, ${item.certainty})`).join('; ')}`,
          'interpolation-warning'
        ));
      } else {
        card.appendChild(html('p', 'No interpolation flagged in this fixture.'));
      }
      el.witnessMetadata.appendChild(card);
    });

    clear(el.witnessDiff);
    if (left.traditionFamily !== right.traditionFamily) {
      el.witnessDiff.appendChild(html(
        'p',
        'These witnesses belong to different fictional traditions. Comparison is shown only as a UI test; it is not a meaningful textual collation.',
        'history-integrity-note'
      ));
    }
    const aWords = left.variantText.split(/\s+/);
    const bWords = right.variantText.split(/\s+/);
    const maxLength = Math.max(aWords.length, bWords.length);
    const aLine = document.createElement('p');
    const bLine = document.createElement('p');
    aLine.className = 'diff-line';
    bLine.className = 'diff-line';
    for (let index = 0; index < maxLength; index += 1) {
      const aWord = aWords[index] || '';
      const bWord = bWords[index] || '';
      if (aWord === bWord) {
        aLine.append(document.createTextNode(`${aWord}${index < maxLength - 1 ? ' ' : ''}`));
        bLine.append(document.createTextNode(`${bWord}${index < maxLength - 1 ? ' ' : ''}`));
      } else {
        const del = html('del', aWord);
        const ins = html('ins', bWord);
        aLine.append(del, document.createTextNode(' '));
        bLine.append(ins, document.createTextNode(' '));
      }
    }
    el.witnessDiff.append(
      html('h4', `A · ${left.code}`), aLine,
      html('h4', `B · ${right.code}`), bLine
    );
  }

  function renderHypotheses() {
    clear(el.hypothesisList);
    data.hypotheses.forEach(hypothesis => {
      const button = html('button', '', `hypothesis-card${hypothesis.id === selectedRecordId ? ' is-selected' : ''}`);
      button.type = 'button';
      button.append(
        html('span', hypothesis.conflictResolutionTag, `hypothesis-tag tag-${hypothesis.conflictResolutionTag}`),
        html('strong', hypothesis.title),
        html('span', hypothesis.summary),
        html('small', `Demo consensus indicator ${(hypothesis.consensusScore * 100).toFixed(0)}% · not a verdict`)
      );
      button.addEventListener('click', () => {
        selectRecord(hypothesis.id);
        renderHypotheses();
      });
      el.hypothesisList.appendChild(button);
    });

    const selected = byId.get(selectedRecordId);
    const hypothesis = selected?.type === 'hypothesis'
      ? selected
      : data.hypotheses.find(item => item.regionId === activeChronicleId) || data.hypotheses[0];
    const opponent = byId.get(hypothesis.opposes);
    clear(el.hypothesisGraph);
    const edge = svg('line', { x1: 190, y1: 110, x2: 450, y2: 110, class: 'hypothesis-opposition' });
    el.hypothesisGraph.appendChild(edge);
    [
      { item: hypothesis, x: 155, className: 'hypothesis-node hypothesis-node--selected' },
      { item: opponent, x: 485, className: 'hypothesis-node' }
    ].forEach(({ item, x, className }) => {
      const group = svg('g', { class: className });
      group.appendChild(svg('rect', { x: x - 115, y: 65, width: 230, height: 90, rx: 8 }));
      const title = svg('text', { x, y: 96, class: 'hypothesis-node-title', 'text-anchor': 'middle' });
      title.textContent = item?.conflictResolutionTag || 'unlinked';
      const score = svg('text', { x, y: 124, class: 'hypothesis-node-score', 'text-anchor': 'middle' });
      score.textContent = item ? `${(item.consensusScore * 100).toFixed(0)}% fixture indicator` : 'No opponent';
      group.append(title, score);
      el.hypothesisGraph.appendChild(group);
    });
    el.hypothesisStatus.textContent =
      `Opposition link: ${hypothesis.title} ↔ ${opponent?.title || 'not linked'}. Supporting/opposing bibliography is synthetic and unverified.`;
  }

  function testPublicationGate() {
    const record = byId.get(selectedRecordId);
    if (!record || record.type !== 'event') {
      el.publicationStatus.textContent = 'The publication gate applies to Historical_Event records. Select an event first.';
      return;
    }
    const missingSections = ['description', 'interpretation', 'analysis']
      .filter(field => typeof record[field] !== 'string' || !record[field].trim());
    const blockers = [];
    if (missingSections.length) blockers.push(`required sections empty: ${missingSections.join(', ')}`);
    if (!record.bibliographySlot?.verified || !record.bibliographySlot?.zoteroKey) blockers.push('no verified bibliographic anchor');
    if (!record.mediaGallery?.assets?.some(asset => asset.iiifManifestUri && asset.rightsStatementUri)) blockers.push('no rights-cleared, resolvable IIIF asset');
    el.publicationStatus.textContent = blockers.length
      ? `Blocked (correctly): ${blockers.join('; ')}. The three event narrative sections ${missingSections.length ? 'must be completed' : 'are present'}; this fixture remains unpublished.`
      : 'The required event sections and evidence links passed the local fixture check.';
  }

  function exportEvents() {
    const matching = filteredRecords.filter(record => record.type === 'event');
    if (!matching.length) {
      el.exportStatus.textContent = 'No matching event fixtures to export. Adjust the filters.';
      return;
    }
    const headers = ['Demo event ID', 'Title', 'Event type', 'EDTF date', 'Chronicle', 'Description', 'Interpretation', 'Analysis', 'Certainty'];
    const rows = matching.map(event => [
      event.id,
      event.title,
      event.eventType,
      event.eventDateEdtf,
      chronicleOf(event)?.name,
      event.description,
      event.interpretation,
      event.analysis,
      event.certaintyScore
    ]);
    const quote = value => `"${String(value ?? '').replaceAll('"', '""')}"`;
    const csv = [headers, ...rows].map(row => row.map(quote).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'pleroma-fictional-history-events.csv';
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    el.exportStatus.textContent = `Downloaded ${matching.length} synthetic event records from the current filters. This is a local fixture export, not a public API result.`;
  }

  function refreshFilters() {
    currentPage = 0;
    renderResults();
    const selected = byId.get(selectedRecordId);
    if (selected) renderInspector();
  }

  function bindEvents() {
    el.searchForm.addEventListener('submit', event => {
      event.preventDefault();
      refreshFilters();
    });
    el.searchForm.addEventListener('reset', () => {
      window.setTimeout(() => {
        currentPage = 0;
        renderResults();
      }, 0);
    });
    [el.query, el.chronicleFilter, el.typeFilter, el.eventTypeFilter, el.sourceTypeFilter,
      el.resolutionFilter, el.sortFilter, el.lowCertainty].forEach(control => {
      control.addEventListener(control === el.query ? 'input' : 'change', refreshFilters);
    });
    el.pagePrev.addEventListener('click', () => {
      currentPage = Math.max(0, currentPage - 1);
      renderResults();
    });
    el.pageNext.addEventListener('click', () => {
      currentPage += 1;
      renderResults();
    });
    el.exportButton.addEventListener('click', exportEvents);
    el.publicationTest.addEventListener('click', testPublicationGate);
    el.atlasChronicle.addEventListener('change', () => {
      activeChronicleId = el.atlasChronicle.value;
      updateTimeRange();
      if (chronicleOf(byId.get(selectedRecordId))?.id !== activeChronicleId) {
        selectedRecordId = activeChronicleId;
        renderInspector();
        renderResults();
      }
      renderAtlas();
      renderHypotheses();
    });
    el.mapContext.addEventListener('change', renderAtlas);
    el.timeScrubber.addEventListener('input', () => {
      currentYear = Number(el.timeScrubber.value);
      el.timeOutput.textContent = formatYear(currentYear);
      renderAtlas();
    });
    el.chronologySet.addEventListener('change', () => {
      el.timeOutput.textContent = formatYear(currentYear);
      renderResults();
      renderInspector();
      renderAtlas();
    });
    el.clusterSelect.addEventListener('change', renderNetwork);
    el.networkStart.addEventListener('change', renderNetwork);
    el.networkEnd.addEventListener('change', renderNetwork);
    el.networkQuery.addEventListener('click', renderNetwork);
    el.compareWitnesses.addEventListener('click', renderWitnessComparison);
    el.witnessA.addEventListener('change', renderWitnessComparison);
    el.witnessB.addEventListener('change', renderWitnessComparison);
  }

  initializeControls();
  bindEvents();
})();
