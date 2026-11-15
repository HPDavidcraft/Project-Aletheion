(() => {
  'use strict';

  const data = window.PLEROMA_ARCHAEOLOGY_DEMO;
  if (!data || !Array.isArray(data.records) || !Array.isArray(data.finds)) {
    console.error('Archaeology demo data is missing or malformed.');
    return;
  }

  const byId = new Map(data.records.map(record => [record.id, record]));
  const siteById = new Map(data.sites.map(site => [site.id, site]));
  const periodById = new Map(data.periods.map(period => [period.id, period]));
  const unitById = new Map(data.strata.map(unit => [unit.id, unit]));
  const svgNamespace = 'http://www.w3.org/2000/svg';
  const pageSize = 12;

  const elements = {
    metricSites: document.getElementById('metric-sites'),
    metricFinds: document.getElementById('metric-finds'),
    metricEntities: document.getElementById('metric-entities'),
    metricRestricted: document.getElementById('metric-restricted'),
    searchForm: document.getElementById('archaeology-search-form'),
    query: document.getElementById('query-filter'),
    siteFilter: document.getElementById('site-filter'),
    typeFilter: document.getElementById('type-filter'),
    materialFilter: document.getElementById('material-filter'),
    periodFilter: document.getElementById('period-filter'),
    sortFilter: document.getElementById('sort-filter'),
    uncertaintyFilter: document.getElementById('uncertainty-filter'),
    regionShortcuts: document.getElementById('region-shortcuts'),
    mapSiteSelect: document.getElementById('map-site-select'),
    mapPeriodSelect: document.getElementById('map-period-select'),
    chronologySet: document.getElementById('chronology-set'),
    mapZoom: document.getElementById('map-zoom'),
    timeScrubber: document.getElementById('time-scrubber'),
    timeOutput: document.getElementById('time-output'),
    mapStateLabel: document.getElementById('map-state-label'),
    mapSiteTitle: document.getElementById('map-site-title'),
    mapStateDescription: document.getElementById('map-state-description'),
    mapDynamic: document.getElementById('map-dynamic-layer'),
    mapLegend: document.getElementById('map-legend'),
    mapLayerBase: document.getElementById('layer-base'),
    mapLayerPrimary: document.getElementById('layer-primary'),
    mapLayerSecondary: document.getElementById('layer-secondary'),
    inspector: document.getElementById('record-inspector'),
    inspectorTitle: document.getElementById('inspector-title'),
    trustBadge: document.getElementById('trust-badge'),
    siteIndex: document.getElementById('site-index-list'),
    resultsSummary: document.getElementById('results-summary'),
    resultList: document.getElementById('result-list'),
    pageStatus: document.getElementById('page-status'),
    pagePrevious: document.getElementById('page-previous'),
    pageNext: document.getElementById('page-next'),
    exportButton: document.getElementById('export-dataset'),
    exportStatus: document.getElementById('export-status'),
    matrixSiteLabel: document.getElementById('matrix-site-label'),
    matrixDynamic: document.getElementById('matrix-dynamic-layer'),
    matrixStatus: document.getElementById('matrix-status'),
    cycleButton: document.getElementById('test-cycle'),
    sampleSelect: document.getElementById('sample-select'),
    sampleDetails: document.getElementById('sample-details'),
    distributionTitle: document.getElementById('distribution-title'),
    probabilityBars: document.getElementById('probability-bars'),
    distributionCaption: document.getElementById('distribution-caption')
  };

  const requiredElements = [
    'searchForm', 'query', 'siteFilter', 'typeFilter', 'materialFilter',
    'periodFilter', 'sortFilter', 'uncertaintyFilter', 'mapSiteSelect',
    'mapPeriodSelect', 'mapDynamic', 'inspector', 'resultList',
    'matrixDynamic', 'sampleSelect'
  ];
  const missingElements = requiredElements.filter(key => !elements[key]);
  if (missingElements.length) {
    console.error(`Archaeology page is missing required elements: ${missingElements.join(', ')}`);
    return;
  }

  let selectedSiteId = data.sites[0].id;
  let selectedPeriodId = '';
  let selectedRecordId = data.sites[0].id;
  let selectedSampleId = data.chronometricSamples[0]?.id || '';
  let activeMapState = 'site';
  let currentPage = 0;
  let lastFilteredRecords = [];

  const chronologyOffsets = { baseline: 0, high: 50, low: -50 };
  const typeNames = {
    site: 'Site',
    period: 'Occupational period',
    stratum: 'Stratigraphic unit',
    feature: 'Feature',
    find: 'Find'
  };
  const stateNames = {
    site: 'Site',
    period: 'Occupational_Period',
    stratum: 'Stratigraphic_Unit',
    find: 'Find'
  };
  const mapStateNotes = {
    site: 'Site boundary with find clusters; no occupation period selected.',
    period: 'Period boundary with stratigraphic outlines and finds clustered by context.',
    stratum: 'Selected stratum, adjacent units, and individual finds.',
    find: 'One find in context; geological source vector appears when a source link exists.'
  };

  function textElement(tag, text, className = '') {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = text;
    return element;
  }

  function svgElement(tag, attributes = {}) {
    const node = document.createElementNS(svgNamespace, tag);
    Object.entries(attributes).forEach(([name, value]) => node.setAttribute(name, String(value)));
    return node;
  }

  function clear(element) {
    element.replaceChildren();
  }

  function getSite(record) {
    return record ? siteById.get(record.siteId || record.id) || null : null;
  }

  function getPeriod(record) {
    if (!record) return null;
    if (record.type === 'period') return record;
    if (record.periodId) return periodById.get(record.periodId) || null;
    if (record.type === 'site') return null;
    return null;
  }

  function getUnit(record) {
    if (!record) return null;
    if (record.type === 'stratum') return record;
    return record.unitId ? unitById.get(record.unitId) || null : null;
  }

  function numberWithSign(year) {
    const offset = chronologyOffsets[elements.chronologySet.value] || 0;
    return year + offset;
  }

  function formatYear(year) {
    const shifted = numberWithSign(year);
    if (shifted < 0) return `${Math.abs(shifted).toLocaleString()} BCE`;
    if (shifted > 0) return `${shifted.toLocaleString()} CE`;
    return '1 BCE / 1 CE boundary';
  }

  function formatDateRange(record) {
    if (!record || typeof record.yearStart !== 'number' || typeof record.yearEnd !== 'number') {
      return 'No EDTF date supplied';
    }
    return `${formatYear(record.yearStart)} – ${formatYear(record.yearEnd)} · EDTF ${record.dateEdtf}`;
  }

  function trustScore(record) {
    const inputs = record.trustFixture;
    if (!inputs) return 0;
    const w = inputs.weights;
    return (
      inputs.completeness * w.completeness +
      inputs.bibliography * w.bibliography +
      inputs.spatial * w.spatial +
      inputs.methodology * w.methodology +
      inputs.currency * w.currency
    );
  }

  function trustLevel(score) {
    if (score >= 0.8) return { label: 'Gold', className: 'gold' };
    if (score >= 0.55) return { label: 'Silver', className: 'silver' };
    if (score >= 0.3) return { label: 'Bronze', className: 'bronze' };
    return { label: 'Incomplete', className: 'incomplete' };
  }

  function findLegalStatus(find) {
    return find?.provenanceChain?.[0]?.legalStatus || 'not_applicable';
  }

  function siteFinds(siteId) {
    return data.finds.filter(find => find.siteId === siteId);
  }

  function sitePeriods(siteId) {
    return data.periods.filter(period => period.siteId === siteId);
  }

  function entitySiteId(record) {
    return record.type === 'site' ? record.id : record.siteId;
  }

  function setSelectOptions(select, options, includeAllLabel = '') {
    clear(select);
    if (includeAllLabel) {
      const all = document.createElement('option');
      all.value = '';
      all.textContent = includeAllLabel;
      select.appendChild(all);
    }
    options.forEach(option => {
      const node = document.createElement('option');
      node.value = option.value;
      node.textContent = option.label;
      select.appendChild(node);
    });
  }

  function initializeControls() {
    elements.metricSites.textContent = String(data.sites.length);
    elements.metricFinds.textContent = String(data.finds.length);
    elements.metricEntities.textContent = String(data.records.length);
    elements.metricRestricted.textContent = String(
      data.finds.filter(find => findLegalStatus(find) !== 'clear').length
    );

    const siteOptions = data.sites.map(site => ({ value: site.id, label: `${site.name} · ${site.region}` }));
    setSelectOptions(elements.siteFilter, siteOptions, 'All fictional sites');
    setSelectOptions(elements.mapSiteSelect, siteOptions);

    const periodOptions = data.periods.map(period => ({
      value: period.id,
      label: `${siteById.get(period.siteId).code} · ${period.name} · ${formatDateRange(period)}`
    }));
    setSelectOptions(elements.periodFilter, periodOptions, 'All occupation periods');
    setSelectOptions(elements.mapPeriodSelect, [], 'Site view · no period selected');

    setSelectOptions(
      elements.materialFilter,
      data.materials.map(material => ({ value: material.key, label: material.label })),
      'All materials'
    );
    elements.mapSiteSelect.value = selectedSiteId;
    elements.siteFilter.value = '';
    updatePeriodControls();
    renderRegionShortcuts();
    renderSiteIndex();
    renderLegend();
    renderResults();
    renderSelectedRecord();
    renderMap();
    renderMatrix();
    renderChronometricSamples();
  }

  function updatePeriodControls() {
    const periods = sitePeriods(selectedSiteId);
    const options = periods.map(period => ({
      value: period.id,
      label: `${period.name} · ${formatDateRange(period)}`
    }));
    setSelectOptions(elements.mapPeriodSelect, options, 'Site view · no period selected');
    elements.mapPeriodSelect.value = periods.some(period => period.id === selectedPeriodId) ? selectedPeriodId : '';
    const starts = periods.map(period => period.yearStart);
    const ends = periods.map(period => period.yearEnd);
    elements.timeScrubber.min = String(Math.min(...starts));
    elements.timeScrubber.max = String(Math.max(...ends));
    const selectedPeriod = periodById.get(selectedPeriodId) || periods[0];
    const current = selectedPeriod
      ? Math.round((selectedPeriod.yearStart + selectedPeriod.yearEnd) / 2)
      : Math.round((Math.min(...starts) + Math.max(...ends)) / 2);
    elements.timeScrubber.value = String(current);
    elements.timeOutput.textContent = formatYear(current);
  }

  function updatePeriodFilterLabels() {
    const selected = elements.periodFilter.value;
    setSelectOptions(
      elements.periodFilter,
      data.periods.map(period => ({
        value: period.id,
        label: `${siteById.get(period.siteId).code} · ${period.name} · ${formatDateRange(period)}`
      })),
      'All occupation periods'
    );
    elements.periodFilter.value = selected;
  }

  function renderRegionShortcuts() {
    clear(elements.regionShortcuts);
    data.sites.forEach(site => {
      const button = textElement('button', site.region, 'region-shortcut');
      button.type = 'button';
      button.addEventListener('click', () => {
        elements.siteFilter.value = site.id;
        currentPage = 0;
        renderResults();
      });
      elements.regionShortcuts.appendChild(button);
    });
  }

  function renderSiteIndex() {
    clear(elements.siteIndex);
    data.sites.forEach(site => {
      const item = document.createElement('li');
      const button = document.createElement('button');
      button.type = 'button';
      button.className = `site-index-button${site.id === selectedSiteId ? ' is-active' : ''}`;
      const label = textElement('span', site.name);
      const count = textElement('span', `${siteFinds(site.id).length} finds`);
      button.append(label, count);
      button.addEventListener('click', () => selectSite(site.id));
      item.appendChild(button);
      elements.siteIndex.appendChild(item);
    });
  }

  function getPeriodFilterMatch(record, periodId) {
    if (!periodId) return true;
    if (record.type === 'period') return record.id === periodId;
    if (record.type === 'site') return data.periods.some(period => period.siteId === record.id && period.id === periodId);
    return record.periodId === periodId;
  }

  function getFilteredRecords() {
    const query = elements.query.value.trim().toLocaleLowerCase();
    const siteId = elements.siteFilter.value;
    const type = elements.typeFilter.value;
    const materialKey = elements.materialFilter.value;
    const periodId = elements.periodFilter.value;
    const lowCertaintyOnly = elements.uncertaintyFilter.checked;

    const matches = data.records.filter(record => {
      if (siteId && entitySiteId(record) !== siteId) return false;
      if (type && record.type !== type) return false;
      if (materialKey && (record.type !== 'find' || record.materialKey !== materialKey)) return false;
      if (!getPeriodFilterMatch(record, periodId)) return false;
      if (lowCertaintyOnly && record.certaintyScore >= 0.5) return false;
      if (!query) return true;
      const searchValues = [
        record.id, record.code, record.title, record.name, record.summary,
        record.region, record.material, record.objectType, record.depositionInterpretation,
        record.fieldNotes, record.physicalDescription, record.interpretationNotes,
        record.dateEdtf, record.inventoryId
      ].filter(Boolean);
      const site = getSite(record);
      if (site) searchValues.push(site.name, site.region, ...site.altNames);
      return searchValues.some(value => String(value).toLocaleLowerCase().includes(query));
    });

    const sort = elements.sortFilter.value;
    if (sort === 'trust') {
      matches.sort((a, b) => trustScore(b) - trustScore(a) || a.title.localeCompare(b.title));
    } else if (sort === 'date') {
      matches.sort((a, b) => (a.yearStart ?? 0) - (b.yearStart ?? 0) || a.title.localeCompare(b.title));
    } else if (sort === 'name') {
      matches.sort((a, b) => a.title.localeCompare(b.title, undefined, { numeric: true }));
    } else {
      const order = { site: 0, period: 1, stratum: 2, feature: 3, find: 4 };
      matches.sort((a, b) =>
        order[a.type] - order[b.type] ||
        (a.siteId || a.id).localeCompare(b.siteId || b.id) ||
        a.title.localeCompare(b.title, undefined, { numeric: true })
      );
    }
    return matches;
  }

  function renderResults() {
    const filtered = getFilteredRecords();
    lastFilteredRecords = filtered;
    const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
    currentPage = Math.min(currentPage, pageCount - 1);
    const start = currentPage * pageSize;
    const visible = filtered.slice(start, start + pageSize);
    clear(elements.resultList);

    if (!visible.length) {
      elements.resultList.appendChild(textElement('p', 'No fictional records match these filters.', 'empty-results'));
    } else {
      visible.forEach(record => {
        const score = trustScore(record);
        const level = trustLevel(score);
        const card = document.createElement('button');
        card.type = 'button';
        card.className = `result-card${record.id === selectedRecordId ? ' is-selected' : ''}`;
        card.setAttribute('aria-label', `${typeNames[record.type]} ${record.title}, ${formatDateRange(record)}`);

        const main = document.createElement('span');
        main.className = 'result-card__main';
        main.append(
          textElement('span', record.code || record.id, 'result-card__id'),
          textElement('span', record.title, 'result-card__title'),
          textElement('span', `${typeNames[record.type]} · ${getSite(record)?.name || 'Site not linked'}`, 'result-card__summary')
        );
        const badge = textElement('span', `Demo ${level.label}`, `result-card__badge trust-badge--${level.className}`);
        const date = textElement('span', formatDateRange(record), 'result-card__date');
        card.append(main, badge, date);
        card.addEventListener('click', () => selectRecord(record.id));
        elements.resultList.appendChild(card);
      });
    }

    elements.resultsSummary.textContent =
      `Showing ${filtered.length.toLocaleString()} of ${data.records.length.toLocaleString()} synthetic hierarchy records · ${data.finds.length} finds across ${data.sites.length} fictional sites.`;
    elements.pageStatus.textContent = filtered.length
      ? `Page ${currentPage + 1} of ${pageCount} · ${start + 1}–${Math.min(start + pageSize, filtered.length)} shown`
      : 'Page 0 of 0 · no matching records';
    elements.pagePrevious.disabled = currentPage === 0;
    elements.pageNext.disabled = currentPage >= pageCount - 1;
  }

  function selectRecord(recordId) {
    const record = byId.get(recordId);
    if (!record) return;
    selectedRecordId = record.id;
    const siteId = entitySiteId(record);
    if (siteById.has(siteId)) {
      selectedSiteId = siteId;
      elements.mapSiteSelect.value = siteId;
      const period = getPeriod(record);
      if (period) selectedPeriodId = period.id;
      else if (record.type === 'site') selectedPeriodId = '';
      activeMapState = record.type === 'feature' ? 'stratum' : record.type;
      updatePeriodControls();
    }
    renderSiteIndex();
    renderSelectedRecord();
    renderMap();
    renderMatrix();
    renderResults();
  }

  function selectSite(siteId) {
    if (!siteById.has(siteId)) return;
    selectedSiteId = siteId;
    selectedPeriodId = '';
    selectedRecordId = siteId;
    activeMapState = 'site';
    elements.mapSiteSelect.value = siteId;
    updatePeriodControls();
    renderSiteIndex();
    renderSelectedRecord();
    renderMap();
    renderMatrix();
    renderResults();
  }

  function selectPeriod(periodId) {
    const period = periodById.get(periodId);
    if (!period) return;
    selectedSiteId = period.siteId;
    selectedPeriodId = period.id;
    selectedRecordId = period.id;
    activeMapState = 'period';
    elements.mapSiteSelect.value = period.siteId;
    updatePeriodControls();
    elements.mapPeriodSelect.value = period.id;
    const middle = Math.round((period.yearStart + period.yearEnd) / 2);
    elements.timeScrubber.value = String(middle);
    elements.timeOutput.textContent = formatYear(middle);
    renderSiteIndex();
    renderSelectedRecord();
    renderMap();
    renderMatrix();
    renderResults();
  }

  function addText(parent, tag, value, className) {
    const child = textElement(tag, value, className);
    parent.appendChild(child);
    return child;
  }

  function addDefinitionList(parent, items) {
    const list = document.createElement('dl');
    list.className = 'inspector-dl';
    items.forEach(([label, value]) => {
      const row = document.createElement('div');
      row.append(textElement('dt', label), textElement('dd', value || 'Not supplied'));
      list.appendChild(row);
    });
    parent.appendChild(list);
  }

  function addInspectorSection(parent, heading, content) {
    const section = document.createElement('section');
    section.className = 'inspector-section';
    section.appendChild(textElement('h4', heading));
    if (typeof content === 'string') {
      section.appendChild(textElement('p', content));
    } else {
      section.appendChild(content);
    }
    parent.appendChild(section);
    return section;
  }

  function renderTrustDetails(parent, record) {
    const score = trustScore(record);
    const inputs = record.trustFixture;
    const level = trustLevel(score);
    elements.trustBadge.className = `trust-badge trust-badge--${level.className}`;
    elements.trustBadge.textContent = `Demo ${level.label} · ${score.toFixed(2)}`;
    elements.trustBadge.setAttribute('aria-label', `Synthetic trust score preview: ${level.label}, ${score.toFixed(2)}; not a real assessment`);

    const values = [
      ['Completeness · 30%', inputs.completeness],
      ['Bibliographic density · 25%', inputs.bibliography],
      ['Spatial precision · 20%', inputs.spatial],
      ['Excavation method · 15%', inputs.methodology],
      ['Data currency · 10%', inputs.currency]
    ];
    const list = document.createElement('ul');
    values.forEach(([label, value]) => {
      list.appendChild(textElement('li', `${label}: ${Number(value).toFixed(2)} (fixture input)`));
    });
    addInspectorSection(parent, `Trust Score preview · ${score.toFixed(2)} / 1.00`, list);
    if (score < 0.5 || record.certaintyScore < 0.5) {
      const warning = textElement(
        'div',
        `Uncertainty indicator: certainty ${record.certaintyScore.toFixed(2)}. Values below 0.50 are flagged by the guideline.`,
        'uncertainty-callout'
      );
      warning.setAttribute('role', 'note');
      parent.appendChild(warning);
    }
  }

  function renderSelectedRecord() {
    const record = byId.get(selectedRecordId);
    if (!record) return;
    const site = getSite(record);
    clear(elements.inspector);
    elements.inspectorTitle.textContent = record.title;
    addText(elements.inspector, 'span', record.code || record.id, 'inspector-record-id');
    addText(elements.inspector, 'p', record.summary || 'No summary supplied.', 'inspector-lead');

    const baseItems = [
      ['Entity type', typeNames[record.type]],
      ['Site', site?.name || 'Not linked'],
      ['Canonical EDTF', record.dateEdtf || 'Not supplied'],
      ['Displayed date range', formatDateRange(record)],
      ['Assertion certainty', `${record.certaintyScore.toFixed(2)} / 1.00`],
      ['Publication state', `${record.publicationStatus || 'draft'} · synthetic fixture`],
      ['Geometry', record.geometry?.note || 'No geometry supplied']
    ];
    if (record.type === 'site') {
      baseItems.push(
        ['Official name', record.name],
        ['Alternative names', record.altNames.join('; ')],
        ['Primary climate pointer', record.climateModel]
      );
    } else if (record.type === 'period') {
      baseItems.push(['Climate model pointer', record.climateModel], ['Parent site', site?.name]);
    } else if (record.type === 'stratum') {
      baseItems.push(
        ['Site-unique unit ID', record.code],
        ['Deposition interpretation', record.depositionInterpretation],
        ['Interpretation concept URI', record.depositionInterpretationUri],
        ['Field notes', record.fieldNotes]
      );
    } else if (record.type === 'feature') {
      baseItems.push(
        ['Feature concept URI', record.featureTypeUri],
        ['Contextual description', record.contextualDescription],
        ['Interpretation notes', record.interpretationNotes]
      );
    } else if (record.type === 'find') {
      baseItems.push(
        ['Inventory ID', `${record.inventoryInstitution} · ${record.inventoryId}`],
        ['Object type', `${record.objectType} · vocabulary mapping unverified`],
        ['Material type', `${record.material} · vocabulary mapping unverified`],
        ['Physical description', record.physicalDescription],
        ['Iconography analysis', record.iconographyAnalysis || 'No interpretation supplied']
      );
    }
    addDefinitionList(elements.inspector, baseItems);
    renderTrustDetails(elements.inspector, record);

    const bibliography = record.bibliographySlot;
    const citationList = document.createElement('ul');
    citationList.appendChild(textElement('li', `${bibliography.title} · ${bibliography.citationType.replaceAll('_', ' ')}`));
    citationList.appendChild(textElement('li', `Zotero key: ${bibliography.zoteroKey || 'missing'} · DOI: ${bibliography.doi || 'not supplied'}`));
    citationList.appendChild(textElement('li', `${bibliography.pageNumber}; quotation field: fixture-only, not a quotation`));
    const citationSection = addInspectorSection(elements.inspector, 'Bibliographic link', citationList);
    citationSection.appendChild(textElement('div', 'Synthetic source slot only. It is not a real publication or valid citation; publication guards must reject it.', 'unresolved-callout'));

    const gallery = record.mediaGallery;
    const mediaSection = addInspectorSection(
      elements.inspector,
      'Media gallery / IIIF',
      `Fixture gallery ${gallery.id} · ${gallery.assets.length} planned asset · manifest unresolved · rights statement missing.`
    );
    mediaSection.appendChild(textElement('div', 'Production assets require rights review, checksums, archival masters, MinIO storage, and a resolvable Cantaloupe IIIF manifest.', 'unresolved-callout'));

    if (record.type === 'find') {
      const chain = record.provenanceChain[0];
      const chainList = document.createElement('ul');
      chainList.appendChild(textElement('li', `Custodian: ${chain.custodian} · acquisition: ${chain.acquisitionMethod}`));
      chainList.appendChild(textElement('li', `Legal status: ${chain.legalStatus}${chain.claimantCommunity ? ` · claimant: ${chain.claimantCommunity}` : ''}`));
      if (record.sourceLocation) {
        chainList.appendChild(textElement('li', `Geological source link: ${record.sourceLocation.label} · certainty ${record.sourceLocation.certainty.toFixed(2)}`));
      } else {
        chainList.appendChild(textElement('li', 'No geological source link in this fixture.'));
      }
      const provenanceSection = addInspectorSection(elements.inspector, 'Provenance chain', chainList);
      if (chain.legalStatus !== 'clear') {
        provenanceSection.appendChild(textElement('div', 'Export blocked: the public demo exporter excludes every non-clear legal status.', 'legal-callout legal-callout--blocked'));
      } else {
        provenanceSection.appendChild(textElement('div', 'Fixture status is clear; this does not establish real-world title, rights, or legal clearance.', 'legal-callout'));
      }

      const conservation = record.conservation;
      addInspectorSection(
        elements.inspector,
        'Conservation / field method',
        `Condition: ${conservation.condition.replaceAll('_', ' ')} · inspection: ${conservation.lastInspection}. Campaign method ${record.excavationProtocol.methodType.replaceAll('_', ' ')}, ${record.excavationProtocol.samplingStrategy} sampling; significance-bias factor ${record.excavationProtocol.significanceBiasFactor.toFixed(2)} (fixture).`
      );
      if (conservation.condition === 'active_corrosion' || conservation.condition === 'fragmenting') {
        addInspectorSection(elements.inspector, 'Conservation alert', 'This synthetic condition would trigger a conservator notification in the connected service; no alert service is configured.');
      }
    }

    const historyList = document.createElement('ul');
    record.auditHistory.forEach(event => {
      historyList.appendChild(textElement(
        'li',
        `${event.operation} · ${event.timestamp} · ${event.actor}: ${event.justification}`
      ));
    });
    const historySection = addInspectorSection(elements.inspector, 'Editorial history preview', historyList);
    historySection.appendChild(textElement('div', 'These are fictional display fixtures, not immutable server audit events. Real history requires the append-only audit service.', 'unresolved-callout'));
  }

  function setSvgTitle() {
    const site = siteById.get(selectedSiteId);
    const title = document.getElementById('map-svg-title');
    const desc = document.getElementById('map-svg-desc');
    title.textContent = `Fictional map schematic for ${site.name}`;
    desc.textContent = `Local schematic with ${siteFinds(site.id).length} synthetic finds. Not a real geographic map.`;
  }

  function addMapMarker(shape, x, y, fill, record, className = 'map-symbol') {
    let node;
    const attrs = { class: className, fill, tabindex: 0, role: 'button', 'aria-label': `${typeNames[record.type]} ${record.title}` };
    if (shape === 'diamond') {
      node = svgElement('path', { ...attrs, d: `M ${x} ${y - 12} L ${x + 12} ${y} L ${x} ${y + 12} L ${x - 12} ${y} Z` });
    } else if (shape === 'triangle') {
      node = svgElement('path', { ...attrs, d: `M ${x} ${y - 13} L ${x + 12} ${y + 11} L ${x - 12} ${y + 11} Z` });
    } else if (shape === 'square') {
      node = svgElement('rect', { ...attrs, x: x - 10, y: y - 10, width: 20, height: 20, rx: 1 });
    } else {
      node = svgElement('circle', { ...attrs, cx: x, cy: y, r: 10 });
    }
    if (record.id === selectedRecordId) node.classList.add('is-active');
    node.appendChild(svgElement('title')).textContent = `${record.title} · ${record.material || typeNames[record.type]}`;
    node.addEventListener('click', () => selectRecord(record.id));
    node.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        selectRecord(record.id);
      }
    });
    elements.mapDynamic.appendChild(node);
    return node;
  }

  function renderLegend() {
    clear(elements.mapLegend);
    data.materials.forEach(material => {
      const item = document.createElement('span');
      item.className = 'legend-item';
      const swatch = document.createElement('span');
      swatch.className = 'legend-swatch';
      swatch.style.backgroundColor = material.color;
      item.append(swatch, textElement('span', material.label));
      elements.mapLegend.appendChild(item);
    });
    const featureItem = document.createElement('span');
    featureItem.className = 'legend-item';
    const featureSwatch = document.createElement('span');
    featureSwatch.className = 'legend-swatch legend-swatch--feature';
    featureItem.append(featureSwatch, textElement('span', 'Feature · hollow symbol'));
    elements.mapLegend.appendChild(featureItem);
  }

  function renderMap() {
    const site = siteById.get(selectedSiteId);
    if (!site) return;
    const record = byId.get(selectedRecordId);
    const period = periodById.get(selectedPeriodId) || null;
    const unit = getUnit(record);
    const selectedFind = record?.type === 'find' ? record : null;
    clear(elements.mapDynamic);
    setSvgTitle();

    const boundary = svgElement('path', {
      d: 'M 105 95 L 827 75 L 920 180 L 868 446 L 530 505 L 150 430 L 70 245 Z',
      class: 'site-boundary'
    });
    elements.mapDynamic.appendChild(boundary);

    if (activeMapState === 'period' && period) {
      const periodIndex = sitePeriods(site.id).findIndex(item => item.id === period.id);
      const shape = svgElement('path', {
        d: periodIndex === 0
          ? 'M 185 128 L 815 118 L 852 210 L 785 306 L 202 292 L 145 220 Z'
          : 'M 200 300 L 785 310 L 845 408 L 540 472 L 170 412 Z',
        class: 'period-shape is-active'
      });
      shape.setAttribute('tabindex', '0');
      shape.setAttribute('role', 'button');
      shape.setAttribute('aria-label', `${period.name}; select period`);
      shape.addEventListener('click', () => selectPeriod(period.id));
      elements.mapDynamic.appendChild(shape);
      const label = svgElement('text', { x: 500, y: periodIndex === 0 ? 150 : 440, class: 'map-label', 'text-anchor': 'middle' });
      label.textContent = `${period.name} · ${formatDateRange(period)}`;
      elements.mapDynamic.appendChild(label);
    }

    const visibleUnits = data.strata.filter(item =>
      item.siteId === site.id && (!period || activeMapState === 'site' || item.periodId === period.id)
    );
    visibleUnits.forEach(item => {
      const isSelected = unit?.id === item.id || record?.id === item.id;
      const rect = svgElement('rect', {
        x: item.mapBounds.x,
        y: item.mapBounds.y,
        width: item.mapBounds.width,
        height: item.mapBounds.height,
        rx: 8,
        class: `stratum-shape${isSelected ? ' is-active' : ''}`
      });
      rect.setAttribute('tabindex', '0');
      rect.setAttribute('role', 'button');
      rect.setAttribute('aria-label', `${item.code}, ${item.summary}`);
      rect.addEventListener('click', () => selectRecord(item.id));
      rect.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          selectRecord(item.id);
        }
      });
      elements.mapDynamic.appendChild(rect);
      const label = svgElement('text', {
        x: item.mapBounds.x + item.mapBounds.width / 2,
        y: item.mapBounds.y + item.mapBounds.height / 2 + 5,
        class: 'map-sub-label',
        'text-anchor': 'middle'
      });
      label.textContent = `${item.code} · ${item.summary}`;
      elements.mapDynamic.appendChild(label);
    });

    const visibleFeatures = data.features.filter(feature =>
      feature.siteId === site.id && (!period || activeMapState === 'site' || feature.periodId === period.id)
    );
    visibleFeatures.forEach(feature => {
      const marker = addMapMarker('square', feature.mapPoint.x, feature.mapPoint.y, 'transparent', feature, 'map-symbol feature-symbol');
      marker.setAttribute('fill', 'rgba(255,249,242,0.35)');
    });

    let visibleFinds = siteFinds(site.id);
    if (period && activeMapState !== 'site') {
      visibleFinds = visibleFinds.filter(find => find.periodId === period.id);
    }
    if (activeMapState === 'stratum' && unit) {
      visibleFinds = visibleFinds.filter(find => find.unitId === unit.id);
    }
    if (activeMapState === 'find' && selectedFind) {
      visibleFinds = [selectedFind];
    }

    const zoom = elements.mapZoom.value;
    if (zoom === 'low' && (activeMapState === 'site' || activeMapState === 'period')) {
      const groups = activeMapState === 'site'
        ? [
            { finds: visibleFinds.slice(0, 5), x: 300, y: 215 },
            { finds: visibleFinds.slice(5, 10), x: 690, y: 215 },
            { finds: visibleFinds.slice(10, 15), x: 300, y: 385 },
            { finds: visibleFinds.slice(15, 20), x: 690, y: 385 }
          ]
        : [
            { finds: visibleFinds.slice(0, 5), x: 365, y: 235 },
            { finds: visibleFinds.slice(5, 10), x: 635, y: 375 }
          ];
      groups.filter(group => group.finds.length).forEach(group => {
        const bubble = svgElement('circle', { cx: group.x, cy: group.y, r: 24, class: 'cluster-bubble', tabindex: 0, role: 'button' });
        bubble.setAttribute('aria-label', `${group.finds.length} clustered fictional finds`);
        bubble.addEventListener('click', () => selectRecord(group.finds[0].id));
        const count = svgElement('text', { x: group.x, y: group.y, class: 'cluster-count' });
        count.textContent = String(group.finds.length);
        elements.mapDynamic.append(bubble, count);
      });
    } else {
      visibleFinds.forEach(find => {
        const shape = find.objectShape === 'tool' ? 'diamond'
          : find.objectShape === 'stone-tool' ? 'square'
            : find.objectShape === 'artifact' ? 'triangle'
              : 'circle';
        addMapMarker(shape, find.mapPoint.x, find.mapPoint.y, find.materialColor, find);
      });
    }

    if (selectedFind?.sourceLocation) {
      const source = selectedFind.sourceLocation;
      const point = selectedFind.mapPoint;
      const sourceShape = svgElement('polygon', {
        points: `${source.x - 25},${source.y - 20} ${source.x + 25},${source.y - 20} ${source.x + 32},${source.y + 14} ${source.x - 24},${source.y + 14}`,
        class: 'source-polygon'
      });
      const vector = svgElement('path', {
        d: `M ${source.x + 24} ${source.y - 7} Q ${(source.x + point.x) / 2} ${Math.min(source.y, point.y) - 30} ${point.x} ${point.y}`,
        class: `source-vector${source.certainty < 0.5 ? ' is-inferred' : ''}`
      });
      elements.mapDynamic.append(sourceShape, vector);
      const sourceLabel = svgElement('text', { x: source.x, y: source.y + 31, class: 'map-sub-label', 'text-anchor': 'middle' });
      sourceLabel.textContent = `Source · ${source.certainty.toFixed(2)} certainty`;
      elements.mapDynamic.appendChild(sourceLabel);
    }

    elements.mapStateLabel.textContent = stateNames[activeMapState] || 'Site';
    elements.mapSiteTitle.textContent = site.name;
    elements.mapStateDescription.textContent = mapStateNotes[activeMapState] || mapStateNotes.site;

    const climate = period?.climateModel || site.climateModel;
    if (activeMapState === 'site') {
      elements.mapLayerBase.textContent = 'OpenStreetMap + modern elevation · unavailable';
      elements.mapLayerPrimary.textContent = 'Site boundary polygon · schematic';
      elements.mapLayerSecondary.textContent = 'Find clusters at site level';
    } else if (activeMapState === 'period') {
      elements.mapLayerBase.textContent = `Paleoclimate GeoTIFF · ${climate} · fixture`;
      elements.mapLayerPrimary.textContent = 'Occupation-period boundary · schematic';
      elements.mapLayerSecondary.textContent = 'Stratigraphic outlines; finds clustered by unit';
    } else if (activeMapState === 'stratum') {
      elements.mapLayerBase.textContent = 'Site orthophoto · unavailable';
      elements.mapLayerPrimary.textContent = 'Selected stratum polygon · schematic';
      elements.mapLayerSecondary.textContent = 'Adjacent units + individual finds';
    } else {
      elements.mapLayerBase.textContent = 'Stratum/site orthophoto · unavailable';
      elements.mapLayerPrimary.textContent = 'Find point + surrounding feature symbols';
      elements.mapLayerSecondary.textContent = selectedFind?.sourceLocation
        ? `Source arrow · certainty ${selectedFind.sourceLocation.certainty.toFixed(2)}`
        : 'No geological source link for this find';
    }
  }

  function findGraphCycle(units, edges) {
    const adjacency = new Map(units.map(unit => [unit.id, []]));
    edges
      .filter(edge => edge.relationshipType === 'above' || edge.relationshipType === 'below')
      .forEach(edge => {
        const from = edge.relationshipType === 'above' ? edge.unitId : edge.relatedUnitId;
        const to = edge.relationshipType === 'above' ? edge.relatedUnitId : edge.unitId;
        adjacency.get(from)?.push(to);
      });

    const state = new Map();
    const path = [];
    let cycle = null;
    function visit(id) {
      state.set(id, 1);
      path.push(id);
      for (const next of adjacency.get(id) || []) {
        if (state.get(next) === 1) {
          const cycleStart = path.indexOf(next);
          cycle = [...path.slice(cycleStart), next];
          return true;
        }
        if (!state.has(next) && visit(next)) return true;
      }
      path.pop();
      state.set(id, 2);
      return false;
    }

    for (const unit of units) {
      if (!state.has(unit.id) && visit(unit.id)) break;
    }
    return cycle;
  }

  function renderMatrix() {
    const site = siteById.get(selectedSiteId);
    if (!site) return;
    const units = data.strata
      .filter(unit => unit.siteId === site.id)
      .sort((a, b) => a.code.localeCompare(b.code));
    const edges = data.relationships.filter(edge => edge.siteId === site.id);
    const activeUnit = getUnit(byId.get(selectedRecordId));
    clear(elements.matrixDynamic);
    elements.matrixSiteLabel.textContent = `${site.name} · ${units.length} units`;

    const defs = svgElement('defs');
    const arrow = svgElement('marker', {
      id: 'matrix-arrow',
      markerWidth: 10,
      markerHeight: 10,
      refX: 8,
      refY: 3,
      orient: 'auto',
      markerUnits: 'strokeWidth'
    });
    arrow.appendChild(svgElement('path', { d: 'M0,0 L0,6 L9,3 z', fill: '#70563f' }));
    defs.appendChild(arrow);
    elements.matrixDynamic.appendChild(defs);

    const positions = new Map(units.map((unit, index) => [unit.id, { x: 380, y: 28 + index * 75 }]));
    edges.forEach(edge => {
      const upperId = edge.relationshipType === 'above' ? edge.unitId : edge.relatedUnitId;
      const lowerId = edge.relationshipType === 'above' ? edge.relatedUnitId : edge.unitId;
      const upper = positions.get(upperId);
      const lower = positions.get(lowerId);
      if (!upper || !lower) return;
      elements.matrixDynamic.appendChild(svgElement('path', {
        d: `M 380 ${upper.y + 48} L 380 ${lower.y - 5}`,
        class: 'matrix-edge'
      }));
      const relationLabel = svgElement('text', {
        x: 505,
        y: Math.round((upper.y + lower.y) / 2) + 10,
        class: 'map-sub-label'
      });
      relationLabel.textContent = 'above';
      elements.matrixDynamic.appendChild(relationLabel);
    });

    units.forEach(unit => {
      const position = positions.get(unit.id);
      const group = svgElement('g', {
        class: `matrix-node${activeUnit?.id === unit.id ? ' is-active' : ''}`,
        tabindex: 0,
        role: 'button',
        'aria-label': `${unit.code}, ${unit.summary}`
      });
      group.appendChild(svgElement('rect', { x: 270, y: position.y, width: 220, height: 48 }));
      const code = svgElement('text', { x: 380, y: position.y + 20 });
      code.textContent = unit.code;
      const date = svgElement('text', { x: 380, y: position.y + 37, class: 'matrix-date' });
      date.textContent = formatDateRange(unit);
      group.append(code, date);
      group.addEventListener('click', () => selectRecord(unit.id));
      group.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          selectRecord(unit.id);
        }
      });
      elements.matrixDynamic.appendChild(group);
    });

    const cycle = findGraphCycle(units, edges);
    if (cycle) {
      const codes = cycle.map(id => unitById.get(id)?.code || id);
      elements.matrixStatus.textContent = `Invalid fixture graph: cycle found (${codes.join(' → ')}).`;
    } else {
      elements.matrixStatus.textContent = `${units.length} units · ${edges.length} directed relationships · no cycle detected in this fixture.`;
    }
  }

  function renderChronometricSamples() {
    const samples = data.chronometricSamples;
    setSelectOptions(
      elements.sampleSelect,
      samples.map(sample => ({
        value: sample.id,
        label: `${sample.labCode} · ${siteById.get(sample.siteId).name} · ${sample.method}`
      }))
    );
    if (!samples.some(sample => sample.id === selectedSampleId)) {
      selectedSampleId = samples[0]?.id || '';
    }
    elements.sampleSelect.value = selectedSampleId;
    renderSelectedSample();
  }

  function renderSelectedSample() {
    const sample = data.chronometricSamples.find(item => item.id === elements.sampleSelect.value);
    if (!sample) return;
    selectedSampleId = sample.id;
    const period = periodById.get(sample.periodId);
    clear(elements.sampleDetails);
    addDefinitionList(elements.sampleDetails, [
      ['Lab code', sample.labCode],
      ['Method', sample.method],
      ['Raw date', `${sample.rawDateBp.toLocaleString()} BP ± ${sample.errorMargin1Sigma} (1σ)`],
      ['Material context', sample.materialContext],
      ['Calibration curve', `${sample.calibrationCurve} · fixture label only`],
      ['Raw measurement', sample.rawMeasurementImmutable ? 'Retained unchanged in fixture' : 'Not specified'],
      ['Linked period', period?.title || 'Not linked'],
      ['Canonical EDTF', period?.dateEdtf || 'Not supplied']
    ]);

    const label = document.createElement('label');
    label.className = 'toolbar-field';
    label.appendChild(textElement('span', 'Calibration result version'));
    const select = document.createElement('select');
    select.id = 'calibration-result-select';
    sample.calibrationResults.forEach(result => {
      const option = document.createElement('option');
      option.value = result.id;
      option.textContent = `Result v${result.version} · ${result.curve}`;
      select.appendChild(option);
    });
    label.appendChild(select);
    elements.sampleDetails.appendChild(label);

    const updateChart = () => {
      const result = sample.calibrationResults.find(item => item.id === select.value);
      if (result) renderProbabilityChart(sample, result);
    };
    select.addEventListener('change', updateChart);
    updateChart();
  }

  function renderProbabilityChart(sample, result) {
    clear(elements.probabilityBars);
    elements.distributionTitle.textContent = `${sample.labCode} · result v${result.version}`;
    const points = result.probabilityCurve;
    const maxProbability = Math.max(0.01, ...points.map(point => point.probability));
    const baseY = 170;
    const barWidth = 72;
    const gap = 64;
    elements.probabilityBars.appendChild(svgElement('line', {
      x1: 40,
      y1: baseY,
      x2: 610,
      y2: baseY,
      class: 'probability-axis'
    }));
    points.forEach((point, index) => {
      const x = 70 + index * (barWidth + gap);
      const height = Math.max(4, (point.probability / maxProbability) * 112);
      const rect = svgElement('rect', {
        x,
        y: baseY - height,
        width: barWidth,
        height,
        rx: 3,
        class: 'probability-bar',
        opacity: point.probability < 0.3 ? 0.42 : 0.78
      });
      const year = svgElement('text', { class: 'probability-label' });
      year.textContent = formatYear(point.year);
      year.setAttribute('x', String(x + barWidth / 2));
      year.setAttribute('y', String(baseY + 22));
      year.setAttribute('text-anchor', 'middle');
      const probability = svgElement('text', { class: 'probability-value' });
      probability.textContent = `${Math.round(point.probability * 100)}%`;
      probability.setAttribute('x', String(x + barWidth / 2));
      probability.setAttribute('y', String(baseY - height - 7));
      probability.setAttribute('text-anchor', 'middle');
      elements.probabilityBars.append(rect, probability, year);
    });
    elements.distributionCaption.textContent =
      `Illustrative curve only · EDTF ${result.dateEdtf} · offset is display-only · no radiocarbon calibration was performed.`;
  }

  function tryCycleRejection() {
    const site = siteById.get(selectedSiteId);
    const units = data.strata.filter(unit => unit.siteId === site.id);
    const currentEdges = data.relationships.filter(edge => edge.siteId === site.id);
    if (units.length < 2) {
      elements.matrixStatus.textContent = 'Cycle test unavailable: this site has fewer than two units.';
      return;
    }
    const first = units[0];
    const last = units[units.length - 1];
    const proposedEdge = {
      id: `TEST-EDGE-${site.code}`,
      siteId: site.id,
      unitId: last.id,
      relatedUnitId: first.id,
      relationshipType: 'above'
    };
    const cycle = findGraphCycle(units, [...currentEdges, proposedEdge]);
    if (cycle) {
      const codes = cycle.map(id => unitById.get(id)?.code || id);
      elements.matrixStatus.textContent =
        `Rejected hypothetical ${last.code} above ${first.code}: it closes a cycle (${codes.join(' → ')}). No fixture data changed.`;
    } else {
      elements.matrixStatus.textContent = 'The hypothetical edge did not create a cycle; fixture data were not changed.';
    }
  }

  function downloadCsv() {
    const matchingFinds = lastFilteredRecords.filter(record => record.type === 'find');
    const allowed = matchingFinds.filter(find => findLegalStatus(find) === 'clear');
    const excluded = matchingFinds.length - allowed.length;
    if (!allowed.length) {
      elements.exportStatus.textContent = matchingFinds.length
        ? 'Export blocked: all matching finds have non-clear provenance status.'
        : 'No matching finds to export. Adjust the filters and try again.';
      return;
    }
    const headers = [
      'Demo record ID',
      'Inventory ID',
      'Site',
      'Occupation period',
      'Stratigraphic unit',
      'Object type',
      'Material',
      'EDTF date',
      'Certainty score',
      'Synthetic legal status'
    ];
    const rows = allowed.map(find => [
      find.id,
      find.inventoryId,
      siteById.get(find.siteId)?.name,
      periodById.get(find.periodId)?.title,
      unitById.get(find.unitId)?.code,
      find.objectType,
      find.material,
      find.dateEdtf,
      find.certaintyScore,
      findLegalStatus(find)
    ]);
    const csvValue = value => `"${String(value ?? '').replaceAll('"', '""')}"`;
    const csv = [headers, ...rows].map(row => row.map(csvValue).join(',')).join('\r\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'pleroma-fictional-archaeology-clear-finds.csv';
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    elements.exportStatus.textContent =
      `Downloaded ${allowed.length} clear-status synthetic find records. ${excluded} non-clear record(s) were excluded. This is a local demo export, not a public API response.`;
  }

  function handleMapSiteChange() {
    const siteId = elements.mapSiteSelect.value;
    if (!siteById.has(siteId)) return;
    selectedSiteId = siteId;
    selectedPeriodId = '';
    selectedRecordId = siteId;
    activeMapState = 'site';
    updatePeriodControls();
    renderSiteIndex();
    renderSelectedRecord();
    renderMap();
    renderMatrix();
    renderResults();
  }

  function handleMapPeriodChange() {
    const periodId = elements.mapPeriodSelect.value;
    if (!periodId) {
      selectSite(selectedSiteId);
      return;
    }
    selectPeriod(periodId);
  }

  function handleTimeScrubber() {
    const year = Number(elements.timeScrubber.value);
    elements.timeOutput.textContent = formatYear(year);
    const periods = sitePeriods(selectedSiteId);
    const active = periods.find(period => year >= period.yearStart && year <= period.yearEnd)
      || periods.reduce((nearest, period) => {
        const middle = (period.yearStart + period.yearEnd) / 2;
        return Math.abs(middle - year) < Math.abs((nearest.yearStart + nearest.yearEnd) / 2 - year) ? period : nearest;
      }, periods[0]);
    selectedPeriodId = active.id;
    selectedRecordId = active.id;
    activeMapState = 'period';
    elements.mapPeriodSelect.value = active.id;
    renderSelectedRecord();
    renderMap();
    renderMatrix();
    renderResults();
  }

  function handleChronologySetChange() {
    updatePeriodFilterLabels();
    updatePeriodControls();
    elements.timeOutput.textContent = formatYear(Number(elements.timeScrubber.value));
    renderResults();
    renderSelectedRecord();
    renderMap();
    renderMatrix();
    renderSelectedSample();
  }

  elements.searchForm.addEventListener('submit', event => {
    event.preventDefault();
    currentPage = 0;
    renderResults();
    document.getElementById('results-title').scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  elements.searchForm.addEventListener('reset', () => {
    window.setTimeout(() => {
      currentPage = 0;
      renderResults();
    }, 0);
  });
  [elements.siteFilter, elements.typeFilter, elements.materialFilter, elements.periodFilter,
    elements.sortFilter, elements.uncertaintyFilter].forEach(control => {
    control.addEventListener('change', () => {
      currentPage = 0;
      renderResults();
    });
  });
  elements.query.addEventListener('input', () => {
    currentPage = 0;
    renderResults();
  });
  elements.pagePrevious.addEventListener('click', () => {
    currentPage = Math.max(0, currentPage - 1);
    renderResults();
  });
  elements.pageNext.addEventListener('click', () => {
    const lastPage = Math.max(0, Math.ceil(lastFilteredRecords.length / pageSize) - 1);
    currentPage = Math.min(lastPage, currentPage + 1);
    renderResults();
  });
  elements.exportButton.addEventListener('click', downloadCsv);
  elements.mapSiteSelect.addEventListener('change', handleMapSiteChange);
  elements.mapPeriodSelect.addEventListener('change', handleMapPeriodChange);
  elements.timeScrubber.addEventListener('input', handleTimeScrubber);
  elements.mapZoom.addEventListener('change', renderMap);
  elements.chronologySet.addEventListener('change', handleChronologySetChange);
  elements.cycleButton.addEventListener('click', tryCycleRejection);
  elements.sampleSelect.addEventListener('change', renderSelectedSample);

  initializeControls();
})();
