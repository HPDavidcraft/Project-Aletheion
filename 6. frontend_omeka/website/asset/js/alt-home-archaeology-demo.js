(() => {
  'use strict';

  const records = [
    { id: 'SIM-001', zone: 'Saltglass Inlet', context: 'Ash lens beneath reed floor', interval: '4,800–4,550 demo BP', material: 'Charcoal', quantity: 12, phase: 'Shoreline camp', hypothesis: 'Brief fireside activity; fictional.' },
    { id: 'SIM-002', zone: 'Saltglass Inlet', context: 'Small cut through pale silt', interval: '4,760–4,500 demo BP', material: 'Flint', quantity: 7, phase: 'Shoreline camp', hypothesis: 'A shallow pit; function unknown.' },
    { id: 'SIM-003', zone: 'Saltglass Inlet', context: 'Sherd scatter at floor edge', interval: '4,700–4,420 demo BP', material: 'Ceramic', quantity: 9, phase: 'Shoreline camp', hypothesis: 'Several vessels may be represented.' },
    { id: 'SIM-004', zone: 'Saltglass Inlet', context: 'Shell fragments in grey fill', interval: '4,650–4,400 demo BP', material: 'Shell', quantity: 3, phase: 'Shoreline camp', hypothesis: 'Food waste or natural accumulation.' },
    { id: 'SIM-005', zone: 'Saltglass Inlet', context: 'Charcoal flecks in compact floor', interval: '4,430–4,180 demo BP', material: 'Charcoal', quantity: 5, phase: 'Hearth cluster', hypothesis: 'Repeated burning is one possibility.' },
    { id: 'SIM-006', zone: 'Saltglass Inlet', context: 'Bone fragments beside dark stain', interval: '4,390–4,100 demo BP', material: 'Bone', quantity: 6, phase: 'Hearth cluster', hypothesis: 'Association requires further testing.' },
    { id: 'SIM-007', zone: 'Morrow Ridge', context: 'Pebble surface over orange clay', interval: '4,350–4,050 demo BP', material: 'Stone', quantity: 8, phase: 'Hearth cluster', hypothesis: 'Prepared surface; use is uncertain.' },
    { id: 'SIM-008', zone: 'Morrow Ridge', context: 'Broken rim in shallow hollow', interval: '4,300–4,020 demo BP', material: 'Ceramic', quantity: 4, phase: 'Hearth cluster', hypothesis: 'Discard or accidental breakage.' },
    { id: 'SIM-009', zone: 'Morrow Ridge', context: 'Thin charcoal seam at wall base', interval: '4,100–3,820 demo BP', material: 'Charcoal', quantity: 10, phase: 'Rebuilt floor', hypothesis: 'A burning episode; not a lab date.' },
    { id: 'SIM-010', zone: 'Morrow Ridge', context: 'Worked stone near floor repair', interval: '4,060–3,790 demo BP', material: 'Flint', quantity: 3, phase: 'Rebuilt floor', hypothesis: 'Tool use is a fictional interpretation.' },
    { id: 'SIM-011', zone: 'Morrow Ridge', context: 'Ochre-colored flecks in fill', interval: '4,020–3,740 demo BP', material: 'Mineral pigment', quantity: 2, phase: 'Rebuilt floor', hypothesis: 'Color alone does not establish purpose.' },
    { id: 'SIM-012', zone: 'Morrow Ridge', context: 'Shell bead-like object in mixed layer', interval: '3,980–3,700 demo BP', material: 'Shell', quantity: 11, phase: 'Rebuilt floor', hypothesis: 'Object and layer may not be contemporary.' },
    { id: 'SIM-013', zone: 'Sable Plain', context: 'Pebbles in a linear arrangement', interval: '3,820–3,550 demo BP', material: 'Stone', quantity: 6, phase: 'Ridge exchange', hypothesis: 'Possible boundary; entirely invented.' },
    { id: 'SIM-014', zone: 'Sable Plain', context: 'Ceramic pieces beside the line', interval: '3,780–3,500 demo BP', material: 'Ceramic', quantity: 5, phase: 'Ridge exchange', hypothesis: 'Movement between zones is unproven.' },
    { id: 'SIM-015', zone: 'Sable Plain', context: 'Charcoal flecks in windblown sand', interval: '3,740–3,460 demo BP', material: 'Charcoal', quantity: 7, phase: 'Ridge exchange', hypothesis: 'Could be residual or intrusive.' },
    { id: 'SIM-016', zone: 'Sable Plain', context: 'Bone in shallow silty depression', interval: '3,540–3,260 demo BP', material: 'Bone', quantity: 4, phase: 'Marsh reuse', hypothesis: 'Human activity is not established.' },
    { id: 'SIM-017', zone: 'Sable Plain', context: 'Shell fragments in later surface', interval: '3,500–3,220 demo BP', material: 'Shell', quantity: 9, phase: 'Marsh reuse', hypothesis: 'Reuse of the place is only a model.' },
    { id: 'SIM-018', zone: 'Morrow Ridge', context: 'Small ceramic cluster in fill', interval: '3,460–3,180 demo BP', material: 'Ceramic', quantity: 6, phase: 'Marsh reuse', hypothesis: 'Context boundaries need review.' }
  ];

  const phaseOrder = ['Shoreline camp', 'Hearth cluster', 'Rebuilt floor', 'Ridge exchange', 'Marsh reuse'];
  const materialOrder = ['Ceramic', 'Charcoal', 'Flint', 'Stone', 'Shell', 'Bone', 'Mineral pigment'];
  const zoneFilter = document.getElementById('demo-zone-filter');
  const searchInput = document.getElementById('demo-record-search');
  const resetButton = document.getElementById('demo-reset');
  const exportButton = document.getElementById('demo-export');
  const rowContainer = document.getElementById('demo-record-rows');
  const countOutput = document.getElementById('demo-record-count');
  const phaseChart = document.getElementById('demo-phase-chart');
  const materialChart = document.getElementById('demo-material-chart');

  if (!zoneFilter || !searchInput || !rowContainer || !countOutput || !phaseChart || !materialChart) {
    console.error('Interactive archaeology demo is missing required page elements.');
    return;
  }

  const stats = {
    records: document.querySelector('[data-demo-metric="records"]'),
    zones: document.querySelector('[data-demo-metric="zones"]'),
    phases: document.querySelector('[data-demo-metric="phases"]')
  };
  if (stats.records) stats.records.textContent = String(records.length);
  if (stats.zones) stats.zones.textContent = String(new Set(records.map(record => record.zone)).size);
  if (stats.phases) stats.phases.textContent = String(new Set(records.map(record => record.phase)).size);

  let sortKey = 'id';
  let sortDirection = 1;

  function getFilteredRecords() {
    const zone = zoneFilter.value;
    const query = searchInput.value.trim().toLocaleLowerCase();
    return records.filter(record => {
      if (zone && record.zone !== zone) return false;
      return !query || Object.values(record).some(value => String(value).toLocaleLowerCase().includes(query));
    });
  }

  function makeCell(tag, value) {
    const cell = document.createElement(tag);
    cell.textContent = String(value);
    return cell;
  }

  function renderTable(filtered) {
    const sorted = [...filtered].sort((a, b) => {
      const left = a[sortKey];
      const right = b[sortKey];
      if (typeof left === 'number' && typeof right === 'number') return (left - right) * sortDirection;
      return String(left).localeCompare(String(right), undefined, { numeric: true }) * sortDirection;
    });

    rowContainer.replaceChildren();
    if (!sorted.length) {
      const row = document.createElement('tr');
      const message = makeCell('td', 'No fictional records match these filters.');
      message.colSpan = 7;
      row.appendChild(message);
      rowContainer.appendChild(row);
    } else {
      sorted.forEach(record => {
        const row = document.createElement('tr');
        [
          record.id,
          record.zone,
          record.context,
          record.interval,
          record.material,
          record.quantity,
          record.hypothesis
        ].forEach(value => row.appendChild(makeCell('td', value)));
        rowContainer.appendChild(row);
      });
    }

    document.querySelectorAll('.demo-record-table [data-sort]').forEach(button => {
      const heading = button.closest('th');
      if (!heading) return;
      if (button.dataset.sort === sortKey) {
        heading.setAttribute('aria-sort', sortDirection === 1 ? 'ascending' : 'descending');
      } else {
        heading.removeAttribute('aria-sort');
      }
    });
    countOutput.textContent = `Showing ${sorted.length} of ${records.length} fictional records. All values are invented.`;
    return sorted;
  }

  function renderBarChart(svg, labels, totals, title) {
    const namespace = 'http://www.w3.org/2000/svg';
    const rowHeight = 42;
    const chartHeight = Math.max(100, labels.length * rowHeight + 26);
    const barStart = 228;
    const barWidth = 340;
    const maxValue = Math.max(1, ...labels.map(label => totals.get(label) || 0));

    svg.replaceChildren();
    svg.setAttribute('viewBox', `0 0 640 ${chartHeight}`);
    const titleElement = document.createElementNS(namespace, 'title');
    titleElement.textContent = title;
    const description = document.createElementNS(namespace, 'desc');
    description.textContent = labels.length
      ? 'Bars represent invented counts and change when the table filters are used.'
      : 'No fictional records match the selected filters.';
    svg.append(titleElement, description);

    if (!labels.length) {
      const empty = document.createElementNS(namespace, 'text');
      empty.setAttribute('x', '16');
      empty.setAttribute('y', '42');
      empty.setAttribute('class', 'demo-chart-empty');
      empty.textContent = 'No records match the current filters.';
      svg.appendChild(empty);
      return;
    }

    labels.forEach((label, index) => {
      const value = totals.get(label) || 0;
      const y = index * rowHeight + 18;
      const labelElement = document.createElementNS(namespace, 'text');
      labelElement.setAttribute('x', '4');
      labelElement.setAttribute('y', String(y + 15));
      labelElement.setAttribute('class', 'demo-chart-label');
      labelElement.textContent = label;

      const bar = document.createElementNS(namespace, 'rect');
      bar.setAttribute('x', String(barStart));
      bar.setAttribute('y', String(y));
      bar.setAttribute('width', String(Math.max(value ? 2 : 0, barWidth * value / maxValue)));
      bar.setAttribute('height', '22');
      bar.setAttribute('rx', '2');
      bar.setAttribute('class', 'demo-chart-bar');

      const valueElement = document.createElementNS(namespace, 'text');
      valueElement.setAttribute('x', String(barStart + barWidth + 10));
      valueElement.setAttribute('y', String(y + 16));
      valueElement.setAttribute('class', 'demo-chart-value');
      valueElement.textContent = String(value);
      svg.append(labelElement, bar, valueElement);
    });
  }

  function render() {
    const filtered = getFilteredRecords();
    const sorted = renderTable(filtered);
    const phaseTotals = new Map(phaseOrder.map(phase => [phase, 0]));
    const materialTotals = new Map(materialOrder.map(material => [material, 0]));

    filtered.forEach(record => {
      phaseTotals.set(record.phase, (phaseTotals.get(record.phase) || 0) + record.quantity);
      materialTotals.set(record.material, (materialTotals.get(record.material) || 0) + record.quantity);
    });

    renderBarChart(
      phaseChart,
      phaseOrder.filter(phase => [...phaseTotals.values()].some(value => value > 0) && filtered.some(record => record.phase === phase)),
      phaseTotals,
      'Fictional find counts by activity phase'
    );
    renderBarChart(
      materialChart,
      materialOrder.filter(material => filtered.some(record => record.material === material)),
      materialTotals,
      'Fictional find counts by material'
    );
    return sorted;
  }

  function csvValue(value) {
    return `"${String(value).replaceAll('"', '""')}"`;
  }

  zoneFilter.addEventListener('change', render);
  searchInput.addEventListener('input', render);
  resetButton?.addEventListener('click', () => {
    zoneFilter.value = '';
    searchInput.value = '';
    sortKey = 'id';
    sortDirection = 1;
    render();
  });
  document.querySelectorAll('.demo-record-table [data-sort]').forEach(button => {
    button.addEventListener('click', () => {
      const nextKey = button.dataset.sort;
      sortDirection = sortKey === nextKey ? sortDirection * -1 : 1;
      sortKey = nextKey;
      render();
    });
  });
  exportButton?.addEventListener('click', () => {
    const selected = render();
    const headers = ['Record ID', 'Fictional zone', 'Context note', 'Demo interval', 'Material', 'Count', 'Working hypothesis'];
    const rows = selected.map(record => [
      record.id, record.zone, record.context, record.interval,
      record.material, record.quantity, record.hypothesis
    ]);
    const csv = [headers, ...rows].map(row => row.map(csvValue).join(',')).join('\r\n');
    const file = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = file;
    link.download = 'pleroma-fictional-demo-records.csv';
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(file), 1000);
  });

  render();
})();
