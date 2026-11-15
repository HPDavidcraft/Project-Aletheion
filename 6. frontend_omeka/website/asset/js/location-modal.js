/* LocationModal
   Injects a full-screen modal overlay with a skeuomorphic window and
   header controls (minimize, maximize - cosmetic, and close - removes modal).
   Vanilla JS (ES6+). No external deps.
*/
(function(){
    class LocationModal {
        constructor(opts = {}){
            this.opts = opts;
            this._styleId = 'aletheion-location-modal-style';
            this._mask = null;
            this._previousFocus = document.activeElement;
            this._onClose = this._onClose.bind(this);
            this._create();
        }

        _create(){
            // Inject styles (if not already present)
            if (!document.getElementById(this._styleId)){
                const style = document.createElement('style');
                style.id = this._styleId;
                style.textContent = `
                    .aletheion-location-modal-mask{background-color: rgba(0,0,0,0.6);position:fixed;inset:0;z-index:99990;display:flex;align-items:center;justify-content:center}
                    .aletheion-location-window{background:#f4f4f0; border:4px solid #C5A059; box-shadow:0 4px 15px rgba(197,160,89,0.3); width:840px; max-width:92%; height:80vh; border-radius:10px; overflow:hidden; font-family:system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif; display:flex; flex-direction:column;z-index:99991}
                    .aletheion-location-header{background-color:#342e18;color:#ffffff;padding:12px 16px;position:relative;display:flex;align-items:center;justify-content:space-between;flex:0 0 auto;z-index:2}
                    .aletheion-location-title{font-size:1.05rem;font-weight:700;margin:0;color:#ffffff}
                    .aletheion-window-controls{display:flex;gap:10px;align-items:center}
                    .aletheion-window-controls button{background:transparent;border:0;padding:4px;display:inline-flex;align-items:center;justify-content:center}
                    .aletheion-window-controls svg{width:16px;height:16px;display:block}
                    .aletheion-control-cosmetic{cursor:default;opacity:0.5}
                    .aletheion-control-close{cursor:pointer;opacity:0.95}
                    .aletheion-location-body{flex:1 1 auto;display:flex;align-items:stretch;overflow:hidden;padding:0;position:relative}
                    .aletheion-left-partition{width:25%;min-width:200px;background-color:#f4f4f0;overflow-y:auto;border-right:1px solid #cccccc;padding:12px;box-sizing:border-box;height:100%;z-index:1}
                    .aletheion-right-partition{width:75%;flex:1 1 auto;overflow:hidden;position:relative;display:flex;flex-direction:column;padding:0;box-sizing:border-box;background:linear-gradient(180deg,#fffdfa,#f4f2ec);height:100%;z-index:1}
                    .aletheion-map{flex:1;min-height:0;position:relative;z-index:1;overflow:hidden}
                `;
                document.head.appendChild(style);
            }

            // Mask
            const mask = document.createElement('div');
            mask.className = 'aletheion-location-modal-mask';
            mask.setAttribute('role','dialog');
            mask.setAttribute('aria-modal','true');

            // Window
            const win = document.createElement('div');
            win.className = 'aletheion-location-window';

            // Header
            const header = document.createElement('header');
            header.className = 'aletheion-location-header';

            const title = document.createElement('h2');
            title.className = 'aletheion-location-title';
            title.textContent = this.opts.title || 'Location Selection';

            const controls = document.createElement('div');
            controls.className = 'aletheion-window-controls';

            // Close (active)
            const btnClose = document.createElement('button');
            btnClose.type = 'button';
            btnClose.className = 'aletheion-control-close';
            btnClose.setAttribute('aria-label','Close location modal');
            btnClose.innerHTML = `
                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                    <line x1="6" y1="6" x2="18" y2="18" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round" />
                    <line x1="6" y1="18" x2="18" y2="6" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round" />
                </svg>`;

            // Append controls
            controls.appendChild(btnClose);

            header.appendChild(title);
            header.appendChild(controls);

            // Body container with left/right partitions (25% / 75%)
            const body = document.createElement('div');
            body.className = 'aletheion-location-body';

            const left = document.createElement('aside');
            left.className = 'aletheion-left-partition';
            left.setAttribute('role','region');
            left.setAttribute('aria-label','Location controls');

            const right = document.createElement('div');
            right.className = 'aletheion-right-partition';
            right.setAttribute('role','region');
            right.setAttribute('aria-label','Map and details');

            let hasRegionCatalog = false;
            // Populate left with provided leftContent or defaults
            if (this.opts.leftContent instanceof Node){
                left.appendChild(this.opts.leftContent);
            } else if (typeof this.opts.leftContent === 'string'){
                left.textContent = this.opts.leftContent;
            } else {
                // Create CSS for tree view (insert once)
                const treeStyleId = this._styleId + '-tree';
                if (!document.getElementById(treeStyleId)){
                    const ts = document.createElement('style');
                    ts.id = treeStyleId;
                    ts.textContent = `
                        .aletheion-tree{list-style:none;margin:0;padding:6px 0 12px 0;color:#333333;font-size:0.95rem}
                        .aletheion-tree ul{list-style:none;margin:0;padding-left:14px;display:none}
                        .aletheion-tree li{padding:6px 8px;border-radius:6px;cursor:default}
                        .aletheion-tree li:hover{background:rgba(197,160,89,0.15);color:#342e18}
                        .aletheion-tree .node-row{display:flex;align-items:center;gap:8px}
                        .aletheion-tree .node-toggle{display:inline-flex;width:18px;height:18px;align-items:center;justify-content:center}
                        .aletheion-tree .chev{width:12px;height:12px;transition:transform 200ms ease;fill:none;stroke:#333333;stroke-width:2;stroke-linecap:round}
                        .aletheion-tree li.expanded > .node-row .chev{transform:rotate(90deg);stroke:#342e18}
                        .aletheion-tree li.expanded > ul{display:block}
                        .aletheion-tree .leaf{padding-left:18px;color:#333333}
                        .aletheion-tree li[data-state="excluded"] .leaf{ text-decoration: line-through; color: #b33939 }
                        .aletheion-tree li.contained > .node-row{background:rgba(197,160,89,0.12)}
                    `;
                    document.head.appendChild(ts);
                }

                const regions = this.opts.regions;
                const regionIds = new Set();
                const validRegion = (node) => {
                    if (!node || typeof node.name !== 'string' || !node.name.trim()) return false;
                    if (Array.isArray(node.children) && node.children.length) {
                        return node.children.every(validRegion);
                    }
                    if (typeof node.uuid !== 'string' ||
                        !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(node.uuid) ||
                        regionIds.has(node.uuid.toLowerCase())) {
                        return false;
                    }
                    regionIds.add(node.uuid.toLowerCase());
                    return true;
                };
                hasRegionCatalog = Array.isArray(regions) &&
                    regions.length > 0 &&
                    regions.every(validRegion);

                const renderTree = (node) => {
                    const ul = document.createElement('ul');
                    ul.className = 'aletheion-tree-root';
                    ul.setAttribute('role','tree');

                    const build = (n, container) => {
                        const li = document.createElement('li');
                        li.setAttribute('role','treeitem');
                        li.tabIndex = 0;
                        const row = document.createElement('div');
                        row.className = 'node-row';

                        const toggle = document.createElement('span');
                        toggle.className = 'node-toggle';
                        // inline SVG chevron
                        toggle.innerHTML = `
                            <svg class="chev" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                                <polyline points="8 6 16 12 8 18" />
                            </svg>`;

                        const label = document.createElement('span');
                        label.textContent = n.name;

                        row.appendChild(toggle);
                        row.appendChild(label);
                        li.appendChild(row);

                        if (Array.isArray(n.children) && n.children.length){
                            const childUl = document.createElement('ul');
                            childUl.setAttribute('role', 'group');
                            n.children.forEach(ch => build(ch, childUl));
                            li.appendChild(childUl);

                            // click toggles expanded state
                            // parent node initial aria state
                            li.setAttribute('aria-expanded', 'false');
                            row.addEventListener('click', (e) => {
                                e.stopPropagation();
                                const isExpanded = li.classList.toggle('expanded');
                                li.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
                            });
                        } else {
                            // leaf styling and boolean masking toggle
                            label.className = 'leaf';
                            // assign a region id (slug)
                            const uuid = n.uuid;
                            li.dataset.uuid = uuid;
                            li.dataset.state = 'included';

                            row.addEventListener('click', (e) => {
                                e.stopPropagation();
                                // toggle included/excluded
                                const current = li.dataset.state === 'excluded' ? 'included' : 'excluded';
                                li.dataset.state = current;
                                const isExcluded = current === 'excluded';
                                // visual brief highlight
                                li.animate([{background:isExcluded? 'rgba(179,57,57,0.06)':'rgba(197,160,89,0.12)'},{background:'transparent'}],{duration:260});
                                // call map masking update (use strict UUID)
                                try{ self.updateMapMasking(uuid, isExcluded); } catch(err){ console.warn('updateMapMasking error', err); }
                            });
                        }

                        container.appendChild(li);
                    };

                    // root may have children
                    if (node.children && node.children.length){
                        node.children.forEach(ch => build(ch, ul));
                    } else {
                        build(node, ul);
                    }
                    ul.classList.add('aletheion-tree');

                    // keyboard support for tree: Enter/Space to toggle
                    ul.addEventListener('keydown', (ev) => {
                        const key = ev.key;
                        if (key !== 'Enter' && key !== ' ' && key !== 'Spacebar') return;
                        // determine focused li
                        const active = document.activeElement;
                        const li = active && active.closest ? active.closest('li') : null;
                        if (!li) return;
                        ev.preventDefault();
                        // if parent node (has child UL)
                        const childUl = li.querySelector('ul');
                        if (childUl){
                            const isExpanded = li.classList.toggle('expanded');
                            li.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
                            return;
                        }
                        // else leaf: toggle included/excluded
                        const current = li.dataset.state === 'excluded' ? 'included' : 'excluded';
                        li.dataset.state = current;
                        const isExcluded = current === 'excluded';
                        li.animate([{background:isExcluded? 'rgba(179,57,57,0.06)':'rgba(197,160,89,0.12)'},{background:'transparent'}],{duration:260});
                        try{ self.updateMapMasking(li.dataset.uuid, isExcluded); } catch(err){ console.warn('updateMapMasking error', err); }
                    });
                    return ul;
                };

                if (hasRegionCatalog) {
                    regions.forEach(region => left.appendChild(renderTree(region)));
                } else {
                    const unavailable = document.createElement('p');
                    unavailable.setAttribute('role', 'status');
                    unavailable.textContent = 'The region catalog is not configured. Location selection is unavailable.';
                    left.appendChild(unavailable);
                }
            }

            // Clear right partition completely for proper flex layout
            right.innerHTML = '';

            // Populate right with main content or defaults (append AFTER clearing)
            let contentContainer = null;
            if (this.opts.content instanceof Node){
                contentContainer = this.opts.content;
                right.appendChild(contentContainer);
            } else if (typeof this.opts.content === 'string'){
                contentContainer = document.createElement('div');
                contentContainer.textContent = this.opts.content;
                right.appendChild(contentContainer);
            }
            // NOTE: Do NOT create placeholder here. Map container will be added by initMap()

            // Footer control panel injected into right partition (AFTER content, so it sits at bottom)
            const footerId = this._styleId + '-footer';
            if (!document.getElementById(footerId)){
                const fs = document.createElement('style');
                fs.id = footerId;
                fs.textContent = `
                    .aletheion-footer{height:60px;flex-shrink:0;position:relative;z-index:10;background-color:#f4f4f0;display:flex;align-items:center;justify-content:flex-end;padding:0 20px;border-top:1px solid #cccccc;gap:15px;box-sizing:border-box}
                    .aletheion-footer .btn-reset{background:transparent;color:#666666;border:1px solid #666666;padding:6px 12px;border-radius:6px;cursor:pointer}
                    .aletheion-footer .btn-save{background-color:#979e88;color:#ffffff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer}
                    .aletheion-footer .btn-save:hover{background-color:#687965}
                `;
                document.head.appendChild(fs);
            }

            const footer = document.createElement('div');
            footer.className = 'aletheion-footer';

            const btnReset = document.createElement('button');
            btnReset.type = 'button';
            btnReset.className = 'btn-reset';
            btnReset.textContent = 'Reset View';

            const btnSave = document.createElement('button');
            btnSave.type = 'button';
            btnSave.className = 'btn-save';
            btnSave.textContent = 'Save';
            btnSave.disabled = !hasRegionCatalog;
            this._hasRegionCatalog = hasRegionCatalog;

            footer.appendChild(btnReset);
            footer.appendChild(btnSave);
            right.appendChild(footer);

            // expose save button for other methods (enable/disable during fetch)
            this._btnSave = btnSave;

            // create overlays container for loader and errors inside right partition
            const overlayId = this._styleId + '-overlays';
            if (!document.getElementById(overlayId)){
                const os = document.createElement('style');
                os.id = overlayId;
                os.textContent = `
                    .aletheion-map-overlay{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;pointer-events:none;z-index:100;width:100%;height:100%;top:0;left:0;right:0;bottom:0}
                    .aletheion-spinner{width:48px;height:48px;border-radius:50%;border:4px solid rgba(197,160,89,0.2);border-top-color:#C5A059;animation:aletheion-spin 900ms linear infinite;box-sizing:border-box}
                    @keyframes aletheion-spin{to{transform:rotate(360deg)}}
                    .aletheion-error{position:absolute;left:12px;right:12px;top:50%;transform:translateY(-50%);padding:16px;background:rgba(255,255,255,0.95);border-radius:8px;border:1px solid #f0d7d7;color:#b33939;font-weight:600;box-shadow:0 4px 12px rgba(0,0,0,0.15);text-align:center;z-index:105}
                `;
                document.head.appendChild(os);
            }

            // helper: show/hide loader and error overlays
            this._showLoader = () => {
                try{
                    const mapEl = this._mask.querySelector('.aletheion-map');
                    if (!mapEl) return;
                    if (!mapEl.querySelector('.aletheion-map-overlay')){
                        const ov = document.createElement('div');
                        ov.className = 'aletheion-map-overlay';
                        ov.innerHTML = '<div class="aletheion-spinner" aria-hidden="true"></div>';
                        mapEl.appendChild(ov);
                    }
                    if (this._btnSave) { this._btnSave.style.opacity = '0.5'; this._btnSave.style.cursor = 'not-allowed'; this._btnSave.disabled = true; }
                }catch(e){/* ignore */}
            };
            this._hideLoader = () => {
                try{
                    const mapEl = this._mask.querySelector('.aletheion-map');
                    if (!mapEl) return;
                    const ov = mapEl.querySelector('.aletheion-map-overlay');
                    if (ov && ov.parentNode) ov.parentNode.removeChild(ov);
                    if (this._btnSave) {
                        this._btnSave.style.opacity = '';
                        this._btnSave.style.cursor = '';
                        this._btnSave.disabled = !this._hasRegionCatalog;
                    }
                }catch(e){/* ignore */}
            };
            this._showError = (msg) => {
                try{
                    const mapEl = this._mask.querySelector('.aletheion-map');
                    if (!mapEl) return;
                    const prev = mapEl.querySelector('.aletheion-error'); if (prev && prev.parentNode) prev.parentNode.removeChild(prev);
                    const err = document.createElement('div'); err.className = 'aletheion-error'; err.textContent = msg;

                    // create Retry Connection button with exact required styles
                    const retryBtn = document.createElement('button');
                    retryBtn.type = 'button';
                    retryBtn.className = 'aletheion-error-retry';
                    retryBtn.textContent = 'Retry Connection';
                    retryBtn.style.cssText = 'background-color: transparent; color: #b33939; border: 1px solid #b33939; padding: 6px 12px; margin-top: 10px; cursor: pointer; transition: background-color 0.2s ease;';

                    // inject hover style if not present
                    const hoverId = this._styleId + '-retry-hover';
                    if (!document.getElementById(hoverId)){
                        const hs = document.createElement('style'); hs.id = hoverId;
                        hs.textContent = `.aletheion-error-retry:hover{ background-color: rgba(179,57,57,0.08); }`;
                        document.head.appendChild(hs);
                    }

                    // click handler: hide error, show loader, and re-fire the fetch via updateMapMasking
                    retryBtn.addEventListener('click', (ev) => {
                        ev.stopPropagation();
                        try{ this._hideError(); } catch(e){}
                        try{ this._showLoader(); } catch(e){}
                        const last = this._lastFailed || {};
                        if (last && last.uuid){
                            try{ this.updateMapMasking(last.uuid, last.isExcluded); } catch(e){ console.warn('Retry updateMapMasking failed', e); }
                        }
                    });

                    err.appendChild(retryBtn);
                    mapEl.appendChild(err);
                    if (this._btnSave) {
                        this._btnSave.style.opacity = '';
                        this._btnSave.style.cursor = '';
                        this._btnSave.disabled = !this._hasRegionCatalog;
                    }
                }catch(e){/* ignore */}
            };
            this._hideError = () => { try{ const mapEl = this._mask.querySelector('.aletheion-map'); if (!mapEl) return; const prev = mapEl.querySelector('.aletheion-error'); if (prev && prev.parentNode) prev.parentNode.removeChild(prev); }catch(e){} };

            // Map sizing now handled by CSS flex layout (flex: 1; min-height: 0)

            // Reset View: remove all exclusions and clear mask overlays
            btnReset.addEventListener('click', () => {
                try {
                    const excluded = left.querySelectorAll('li[data-state="excluded"]');
                        excluded.forEach(li => {
                            const uuid = li.dataset.uuid;
                            li.dataset.state = 'included';
                            if (uuid) this.updateMapMasking(uuid, false);
                    });
                } catch (err){ console.warn('Reset View error', err); }
            });

            // Save selected region UUIDs for the search integration.
            btnSave.addEventListener('click', () => {
                try {
                    const roots = Array.from(left.querySelectorAll('.aletheion-tree-root'));
                    if (!roots.length){
                        // nothing to save
                        this._onClose();
                        return;
                    }

                    const selectedRegions = roots.flatMap(root => Array.from(root.querySelectorAll('li[data-uuid]')))
                        .filter(region => region.dataset.state !== 'excluded')
                        .map(region => ({
                            uuid: region.dataset.uuid,
                            name: region.querySelector('.leaf')?.textContent.trim() || region.dataset.uuid
                        }));
                    const out = JSON.stringify(selectedRegions.map(region => region.uuid));
                    const input = document.querySelector('#advanced-search-location-input');
                    if (input) {
                        input.value = out;
                    }
                    const output = document.querySelector('#location-output');
                    if (output) {
                        output.textContent = selectedRegions.length
                            ? selectedRegions.map(region => region.name).join(', ')
                            : 'No locations selected.';
                    }

                    // close modal
                    this._onClose();

                } catch (err){ console.error('Save error', err); }
            });

            body.appendChild(left);
            body.appendChild(right);

            win.appendChild(header);
            win.appendChild(body);
            mask.appendChild(win);

            // Wire close button: strictly remove modal from DOM
            btnClose.addEventListener('click', this._onClose);
            mask.addEventListener('keydown', event => {
                if (event.key === 'Escape') this._onClose();
            });

            // Keep references for cleanup
            this._mask = mask;
            this._btnClose = btnClose;

            // Auto-insert into DOM
            (this.opts.appendTo || document.body).appendChild(mask);
            btnClose.focus();

            // Initialize map after DOM insertion to avoid Leaflet sizing issues
            this.initMap();
        }

        _onClose(e){
            // Remove modal and all related nodes/styles. No data-saving logic executed.
            try {
                if (this._btnClose) this._btnClose.removeEventListener('click', this._onClose);
                if (this._map) {
                    this._map.remove();
                    this._map = null;
                }
                if (this._mask && this._mask.parentNode) this._mask.parentNode.removeChild(this._mask);
                const style = document.getElementById(this._styleId);
                if (style && style.parentNode) style.parentNode.removeChild(style);
            } finally {
                if (this._previousFocus instanceof HTMLElement && this._previousFocus.isConnected) {
                    this._previousFocus.focus();
                }
                // clear references
                this._mask = null;
                this._btnClose = null;
            }
        }

        // Public API: close the modal programmatically
        close(){
            this._onClose();
        }

        // Initialize Leaflet map inside the right partition. Ensures assets loaded.
        initMap(){
            try {
                const right = this._mask && this._mask.querySelector('.aletheion-right-partition');
                if (!right) return;

                // Create container element for Leaflet
                let mapEl = right.querySelector('.aletheion-map');
                if (!mapEl){
                    mapEl = document.createElement('div');
                    mapEl.className = 'aletheion-map';
                    // Insert map as first child, BEFORE footer (footer is last child)
                    const footer = right.querySelector('.aletheion-footer');
                    if (footer){
                        right.insertBefore(mapEl, footer);
                    } else {
                        right.insertBefore(mapEl, right.firstChild);
                    }
                }

                let configuredWms;
                try {
                    configuredWms = new URL(this.opts.wmsUrl);
                } catch {
                    mapEl.textContent = 'GeoServer WMS is not configured.';
                    return;
                }
                if (!['https:', 'http:'].includes(configuredWms.protocol) ||
                    configuredWms.username ||
                    configuredWms.password ||
                    !this.opts.wmsLayer ||
                    !Array.isArray(this.opts.center) ||
                    this.opts.center.length !== 2 ||
                    !Number.isFinite(this.opts.center[0]) ||
                    !Number.isFinite(this.opts.center[1]) ||
                    this.opts.center[0] < -90 ||
                    this.opts.center[0] > 90 ||
                    this.opts.center[1] < -180 ||
                    this.opts.center[1] > 180) {
                    mapEl.textContent = 'GeoServer WMS is not configured.';
                    return;
                }
                if (this.opts.zoom !== undefined &&
                    (!Number.isFinite(this.opts.zoom) || this.opts.zoom < 0 || this.opts.zoom > 20)) {
                    mapEl.textContent = 'The configured map zoom is invalid.';
                    return;
                }

                const ensureCss = (href) => {
                    if (document.querySelector(`link[href="${href}"]`)) return;
                    const l = document.createElement('link');
                    l.rel = 'stylesheet';
                    l.href = href;
                    document.head.appendChild(l);
                };

                const ensureScript = (src) => new Promise((resolve, reject) => {
                    if (window.L) return resolve();
                    // check if script already present
                    const existing = Array.from(document.scripts).find(s => s.src && s.src.indexOf(src) !== -1);
                    if (existing){
                        existing.addEventListener('load', () => resolve());
                        existing.addEventListener('error', () => reject(new Error('Leaflet script failed to load')));
                        if (window.L) resolve();
                        return;
                    }
                    const s = document.createElement('script');
                    s.src = src;
                    s.async = true;
                    s.onload = () => resolve();
                    s.onerror = () => reject(new Error('Leaflet script failed to load'));
                    document.head.appendChild(s);
                });

                // Load Leaflet only when a configured GeoServer layer is available.
                const leafletCss = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
                const leafletJs = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';

                ensureCss(leafletCss);

                ensureScript(leafletJs).then(() => {
                    // create map instance
                    if (!window.L) return;
                    // avoid double init
                    if (this._map) return;

                    // Ensure mapEl has proper computed dimensions before Leaflet initializes
                    const right = this._mask && this._mask.querySelector('.aletheion-right-partition');
                    const mapEl = this._mask && this._mask.querySelector('.aletheion-map');
                    
                    if (mapEl && right) {
                        // Force reflow to ensure flexbox has laid out the map element
                        void mapEl.offsetHeight;
                        
                        // Set explicit minimum width to prevent Leaflet collapse
                        if (!mapEl.style.width) mapEl.style.width = '100%';
                        if (!mapEl.style.height) mapEl.style.minHeight = '300px';
                    }

                    const leaflet = window.L;
                    if (!leaflet) {
                        mapEl.textContent = 'The map library could not be loaded. Region selection remains available.';
                        return;
                    }
                    this._map = leaflet.map(mapEl, { preferCanvas: true })
                        .setView(this.opts.center, this.opts.zoom ?? 4);

                    leaflet.tileLayer.wms(configuredWms.href, {
                        layers: this.opts.wmsLayer,
                        format: 'image/png',
                        transparent: true,
                        version: '1.1.1',
                        attribution: 'GeoServer WMS'
                    }).addTo(this._map);

                    // CRITICAL: Leaflet must recalculate container size after DOM injection
                    // First invalidation with no animation to establish initial bounds
                    setTimeout(() => {
                        try {
                            if (this._map && this._map.invalidateSize) {
                                this._map.invalidateSize(false);
                            }
                        } catch (err){}
                    }, 50);

                    // Second invalidation after CSS paint completes (200ms is typical for modern browsers)
                    // This ensures any flexbox reflow has settled
                    setTimeout(() => {
                        try {
                            if (this._map && this._map.invalidateSize) {
                                this._map.invalidateSize();
                            }
                        } catch (err){}
                    }, 250);
                }).catch(err => {
                    console.warn('Leaflet failed to load:', err);
                    mapEl.textContent = 'The map library could not be loaded. Region selection remains available.';
                });

            } catch (err){
                // eslint-disable-next-line no-console
                console.error('initMap error', err);
            }
        }

        // Renders/removes a GeoJSON overlay using strict Entity_UUID binding.
        updateMapMasking(uuid, isExcluded){
            try {
                if (!this._map || !window.L) return;
                this._maskLayers = this._maskLayers || {};

                // Store last failed attempt for retry
                this._lastFailed = { uuid: uuid, isExcluded: !!isExcluded };

                // if disabling exclusion (included) remove layer
                if (!isExcluded){
                    const existing = this._maskLayers[uuid];
                    if (existing){ this._map.removeLayer(existing); delete this._maskLayers[uuid]; }
                    return;
                }

                // build polygon with required excluded styling (fallback)
                const styleExcluded = { fillColor: '#000000', fillOpacity: 0.85, color: '#C5A059', weight: 2 };
                const styleIncluded = { fillColor: 'transparent', fillOpacity: 0, color: '#C5A059', weight: 1 };

                // remove existing layer if present
                if (this._maskLayers[uuid]){
                    try{ this._map.removeLayer(this._maskLayers[uuid]); } catch(e){}
                    delete this._maskLayers[uuid];
                }

                // If WFS/WFS helper is provided, attempt to fetch real geometry.
                const fetchGeo = (uid) => {
                    // prefer user-supplied function
                    if (typeof this.opts.getGeoJsonForRegion === 'function'){
                        return Promise.resolve(this.opts.getGeoJsonForRegion(uid));
                    }
                    // try layer map (uuid -> typename)
                    if (this.opts.wfsUrl && this.opts.wfsLayerMap && this.opts.wfsLayerMap[uid]){
                        const layer = this.opts.wfsLayerMap[uid];
                        const url = `${this.opts.wfsUrl}?service=WFS&version=2.0.0&request=GetFeature&typeNames=${encodeURIComponent(layer)}&outputFormat=application/json`;
                        return fetch(url).then(response => {
                            if (!response.ok) throw new Error(`WFS request failed with status ${response.status}`);
                            return response.json();
                        });
                    }
                    // fallback: no remote geometry available
                    return Promise.reject(new Error('No GeoJSON provider configured'));
                };

                // Attempt to fetch real GeoJSON for this uuid via middleware (or user-supplied provider)
                // Show loading overlay and disable Save while awaiting response
                this._hideError && this._hideError();
                this._showLoader && this._showLoader();

                fetchGeo(uuid).then(geojson => {
                    // done loading
                    this._hideLoader && this._hideLoader();
                    try{
                        const leftPartition = this._mask && this._mask.querySelector('.aletheion-left-partition');

                        // Strict filter: only keep features with properties.Entity_UUID that map to an existing li[data-uuid]
                        const feats = Array.isArray(geojson && geojson.features) ? geojson.features : [];
                        const regionElements = Array.from(leftPartition?.querySelectorAll('li[data-uuid]') || []);
                        const matched = feats.filter(f => {
                            const ent = f && f.properties ? f.properties.Entity_UUID : null;
                            if (!ent) return false;
                            return regionElements.some(region => region.dataset.uuid === ent);
                        });

                        if (!matched.length){
                            // per strict binding rules: drop polygon silently if no strict matches
                            return;
                        }

                        const filteredGeo = { type: 'FeatureCollection', features: matched };

                        const styleForFeature = (feature) => {
                            const ent = feature && feature.properties ? feature.properties.Entity_UUID : null;
                            const li = regionElements.find(region => region.dataset.uuid === ent);
                            const excluded = li && li.dataset && li.dataset.state === 'excluded';
                            return excluded ? styleExcluded : styleIncluded;
                        };

                        const layer = window.L.geoJSON(filteredGeo, { style: styleForFeature }).addTo(this._map);
                        this._maskLayers[uuid] = layer;
                        // if the requested operation was exclusion, fit to bounds to give feedback
                        if (isExcluded && layer.getBounds && !layer.getBounds().isEmpty()) this._map.fitBounds(layer.getBounds());
                    }catch(err){
                        // on render error: drop silently (do not draw fuzzy polygons)
                        console.warn('GeoJSON render error (strict binding)', err);
                    }
                }).catch(err => {
                    // remove loader, show inline error and allow retry (do not draw fuzzy polygons)
                    this._hideLoader && this._hideLoader();
                    this._lastFailed = { uuid: uuid, isExcluded: !!isExcluded };
                    this._showError && this._showError('System Error: Unable to retrieve spatial geometries from the Aletheion Middleware.');
                });

            } catch (err){
                console.warn('updateMapMasking error', err);
            }
        }
    }

    // Expose to global
    window.LocationModal = LocationModal;
})();
