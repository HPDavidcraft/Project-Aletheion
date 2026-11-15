(() => {
  'use strict';

  const archaeology = window.PLEROMA_ARCHAEOLOGY_DEMO;
  if (!archaeology || !Array.isArray(archaeology.sites) || archaeology.sites.length < 5) {
    console.error('Linguistics demo requires the shared fictional archaeology site fixtures.');
    return;
  }

  const familySeeds = [
    { key: 'ASTER', name: 'Asteric demo family', parent: null, color: '#28766d', proto: 'Fictional reconstruction: a two-vowel contrast and a small set of stop consonants. This description is invented and has no comparative evidence.' },
    { key: 'NORTH', name: 'Northern Asteric branch', parent: 'ASTER', color: '#3e6e9a', proto: 'Fictional branch-level notes: a possible prefix pattern and a contrast between oral and nasal stops; no actual language is represented.' },
    { key: 'COAST', name: 'Coastal subgroup', parent: 'NORTH', color: '#4e789f', proto: 'Synthetic characteristics: hypothetical stress on the final syllable and a maritime vocabulary set created for this interface.' },
    { key: 'RIDGE', name: 'Ridge subgroup', parent: 'NORTH', color: '#527b91', proto: 'Synthetic characteristics: a possible lateral series and agglutinative morphology; not a scholarly reconstruction.' },
    { key: 'SOUTH', name: 'Southern Asteric branch', parent: 'ASTER', color: '#9a6244', proto: 'Fictional branch-level notes: vowel length and a verb-final order are proposed solely to populate the demo record.' },
    { key: 'BASIN', name: 'Basin subgroup', parent: 'SOUTH', color: '#a66b4b', proto: 'Synthetic characteristics: a hypothetical evidential suffix set and a three-way stop series; no source text exists.' },
    { key: 'PASS', name: 'Pass subgroup', parent: 'SOUTH', color: '#8a6c45', proto: 'Synthetic characteristics: a proposed consonant cluster reduction and a small case-marking system; entirely fictional.' }
  ];

  const familyColors = Object.fromEntries(familySeeds.map(seed => [seed.key, seed.color]));
  const familyIds = Object.fromEntries(familySeeds.map((seed, index) => [seed.key, `LING-DEMO-FAMILY-${String(index + 1).padStart(2, '0')}`]));
  const statusCycle = ['attested', 'reconstructed', 'hypothetical'];
  const scriptNames = [
    'Demo reed-mark script',
    'Demo line-and-dot script',
    'Demo basin notation',
    'Demo ridge marks'
  ];
  const scriptRanges = [
    'U+E000-U+E0FF',
    'U+E100-U+E1FF',
    'U+E200-U+E2FF',
    'U+E300-U+E3FF'
  ];
  const sitePoints = [
    { x: 155, y: 205 },
    { x: 335, y: 145 },
    { x: 520, y: 235 },
    { x: 690, y: 175 },
    { x: 765, y: 350 }
  ];
  const families = [];
  const zones = [];

  function makeCitation(id) {
    return {
      referenceId: `LING-DEMO-REF-${id}`,
      title: `Fictional linguistic field note ${id}`,
      zoteroKey: null,
      doi: null,
      citationType: 'synthesis',
      pageNumber: 'demo page only',
      quotation: 'Invented reference slot; not a quotation or bibliographic record.',
      verified: false,
      status: 'fictional_placeholder_not_a_source'
    };
  }

  function makeGallery(id) {
    return {
      id: `LING-DEMO-GALLERY-${id}`,
      recordPresent: true,
      assets: [{
        assetType: 'drawing',
        rightsStatementUri: null,
        iiifManifestUri: null,
        status: 'unresolved_demo_placeholder'
      }]
    };
  }

  function makeTrust(index) {
    const values = [
      { completeness: 0.94, bibliography: 0.9, spatial: 0.93, methodology: 0.91, currency: 0.9 },
      { completeness: 0.75, bibliography: 0.62, spatial: 0.71, methodology: 0.68, currency: 0.65 },
      { completeness: 0.52, bibliography: 0.31, spatial: 0.46, methodology: 0.48, currency: 0.39 },
      { completeness: 0.2, bibliography: 0.04, spatial: 0.12, methodology: 0.27, currency: 0.18 }
    ];
    return {
      ...values[index % values.length],
      weights: { completeness: 0.3, bibliography: 0.25, spatial: 0.2, methodology: 0.15, currency: 0.1 }
    };
  }

  function makeAudit(id, label) {
    return [
      {
        actor: 'Synthetic demo editor',
        timestamp: '2026-11-01T10:00:00Z',
        operation: 'create',
        justification: `Generated fictional ${label} fixture ${id}; no canonical record was written.`
      },
      {
        actor: 'Synthetic demo editor',
        timestamp: '2026-11-02T10:00:00Z',
        operation: 'review',
        justification: 'Illustrative editorial-history row only; no external authority or evidence was checked.'
      }
    ];
  }

  familySeeds.forEach((seed, index) => {
    const id = familyIds[seed.key];
    families.push({
      id,
      type: 'family',
      code: `zzzz${String(1 + index).padStart(4, '0')}`,
      name: seed.name,
      title: seed.name,
      parentFamilyId: seed.parent ? familyIds[seed.parent] : null,
      protoLanguageCharacteristics: seed.proto,
      childCount: 0,
      color: familyColors[seed.key],
      bibliographySlot: makeCitation(`FAMILY-${index + 1}`),
      mediaGallery: makeGallery(`FAMILY-${index + 1}`),
      publicationStatus: 'draft',
      trustFixture: makeTrust(index),
      auditHistory: makeAudit(id, 'language family')
    });
  });
  families.forEach(family => {
    if (family.parentFamilyId) {
      const parent = families.find(item => item.id === family.parentFamilyId);
      if (parent) parent.childCount += 1;
    }
  });

  familySeeds.forEach((familySeed, familyIndex) => {
    const familyId = familyIds[familySeed.key];
    for (let branchIndex = 0; branchIndex < 2; branchIndex += 1) {
      const zoneIndex = familyIndex * 2 + branchIndex;
      const id = `LING-DEMO-ZONE-${String(zoneIndex + 1).padStart(2, '0')}`;
      const start = -4300 + zoneIndex * 55;
      const end = -2250 + (zoneIndex % 5) * 90;
      const status = statusCycle[(familyIndex + branchIndex) % statusCycle.length];
      const scriptIndex = (familyIndex + branchIndex) % scriptNames.length;
      const siteAIndex = zoneIndex % archaeology.sites.length;
      const siteBIndex = (siteAIndex + 1 + (zoneIndex % 2)) % archaeology.sites.length;
      const linkedSiteIndices = [...new Set([siteAIndex, siteBIndex])];
      const siteLinks = linkedSiteIndices.map(siteIndex => {
        const site = archaeology.sites[siteIndex];
        const yearStart = Math.max(start, site.yearStart);
        const yearEnd = Math.min(end, site.yearEnd);
        return yearStart <= yearEnd ? { siteId: site.id, yearStart, yearEnd } : null;
      }).filter(Boolean);

      const firstPoint = sitePoints[siteAIndex];
      const secondPoint = sitePoints[siteBIndex];
      const centerX = (firstPoint.x + secondPoint.x) / 2;
      const centerY = (firstPoint.y + secondPoint.y) / 2;
      const shift = (zoneIndex % 3 - 1) * 12;
      const points = [
        [centerX - 115, centerY - 30 + shift],
        [centerX - 55, centerY - 78],
        [centerX + 55, centerY - 70 - shift],
        [centerX + 122, centerY - 12],
        [centerX + 88, centerY + 58 + shift],
        [centerX - 18, centerY + 80],
        [centerX - 100, centerY + 38],
        [centerX - 115, centerY - 30 + shift]
      ].map(([x, y]) => [Math.max(35, Math.min(885, x)), Math.max(35, Math.min(465, y))]);
      const languageName = `Demo ${familySeed.name.replace(' demo family', '').replace(' branch', '')} language ${branchIndex + 1}`;

      zones.push({
        id,
        type: 'zone',
        code: `zzzz${String(1001 + zoneIndex).padStart(4, '0')}`,
        languageName,
        title: languageName,
        languageFamilyId: familyId,
        familyColor: familySeed.color,
        dialect: branchIndex === 0 ? `North ${languageName} dialect` : `South ${languageName} dialect`,
        writingSystemUri: `https://example.invalid/skos/writing-system/demo-${scriptIndex + 1}`,
        writingSystemLabel: scriptNames[scriptIndex],
        scriptUnicodeBlock: scriptRanges[scriptIndex],
        status,
        validTimeEdtf: `${start}/${end}`,
        yearStart: start,
        yearEnd: end,
        geometry: {
          type: 'Polygon',
          coordinateSpace: 'local_schematic_svg',
          points,
          status: 'fictional_schematic_not_georeferenced',
          note: 'Local SVG points only; not WGS 84 longitude/latitude or a historical boundary.'
        },
        siteLinks,
        summary: `Synthetic ${status} distribution fixture for ${languageName}; the polygon is illustrative and not based on linguistic evidence.`,
        certaintyScore: [0.83, 0.67, 0.48, 0.33, 0.22, 0.74, 0.58, 0.42, 0.31, 0.86, 0.55, 0.28, 0.62, 0.38][zoneIndex],
        bibliographySlot: makeCitation(`ZONE-${zoneIndex + 1}`),
        mediaGallery: makeGallery(`ZONE-${zoneIndex + 1}`),
        publicationStatus: 'draft',
        trustFixture: makeTrust(zoneIndex + 1),
        auditHistory: makeAudit(id, 'linguistic zone')
      });
    }
  });

  window.PLEROMA_LINGUISTICS_DEMO = {
    demoOnly: true,
    glottologRelease: 'not connected; all codes are unverified fixtures',
    families,
    zones,
    sites: archaeology.sites,
    sitePoints
  };
})();
