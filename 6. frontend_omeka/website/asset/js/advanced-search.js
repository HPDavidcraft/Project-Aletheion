// Advanced Search — Vanilla JS (ES6+)
(() => {
    const form = document.getElementById('advanced-search-form');
    if (!form) return;

    const buildQuery = (data) => {
        // Build a simple query string suitable for Omeka S or custom endpoint.
        const params = new URLSearchParams();
        for (const [k,v] of Object.entries(data)){
            if (v === null || v === undefined) continue;
            if (Array.isArray(v)){
                v.filter(Boolean).forEach(val => params.append(k, val));
            } else if (String(v).trim() !== ''){
                params.set(k, v);
            }
        }
        return params.toString();
    };

    const readForm = () => {
        const fd = new FormData(form);
        const obj = {};
        for (const [k,v] of fd.entries()){
            if (obj[k]){
                // convert to array
                if (!Array.isArray(obj[k])) obj[k] = [obj[k]];
                obj[k].push(v);
            } else obj[k] = v;
        }
        return obj;
    };

    form.addEventListener('submit', (ev) => {
        ev.preventDefault();
        const data = readForm();
        const query = buildQuery(data);

        // Default Omeka endpoint base (user can override by setting data-endpoint attribute)
        const endpoint = form.dataset.endpoint || window.ALETHEION_OMEKA_ENDPOINT || '/omeka-s/api';

        // Build a simple items query — adaptable for Omeka S modules
        const url = endpoint + (endpoint.includes('?') ? '&' : '?') + query;

        // Emit a custom event for host integration
        const event = new CustomEvent('advancedSearch:submit', {detail:{data, url}});
        window.dispatchEvent(event);

        // Default behaviour: open search in new tab so integration can be inspected
        window.open(url, '_blank');
    });

    form.addEventListener('reset', () => {
        // small visual reset hook
        const details = document.querySelector('.results-hint');
        if (details) details.textContent = 'Filters cleared.';
    });

    // Quick-pill behaviour
    document.querySelectorAll('.pill').forEach(p => {
        p.addEventListener('click', (e) => {
            const target = e.currentTarget;
            const field = target.dataset.field;
            const value = target.dataset.value;
            if (!field) return;
            // try to find control
            const control = form.querySelector(`[name="${field}"]`);
            if (!control) return;
            if (control.tagName === 'SELECT'){
                // set select value if exists
                for (const opt of control.options) if (opt.value === value){ opt.selected = true; break; }
            } else {
                control.value = value;
            }
            // brief highlight
            target.animate([{transform:'scale(1)'},{transform:'scale(0.98)'},{transform:'scale(1)'}],{duration:200});
        });
    });

})();
