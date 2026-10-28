/* A small stand-in for the dashboard runtime the page was first written for.
   It loads each data file from /data, keeps the page's filter state, and re-runs
   every drawing (data-draw="name") that is on screen whenever data, a filter,
   a tab or the width changes. */
(() => {
  const SOURCES = ['chances', 'trend', 'polls', 'latest', 'leans_wide', 'eday', 'summary', 'history', 'parliament', 'maori', 'close_seats', 'markets'];
  const DEFAULTS = {range: '12m', pollview: 'adjusted', hv: 'stated'};
  const store = {};
  const calcs = {};
  const draws = new Map();
  const listeners = [];
  let params = {};
  let queued = false;

  const run = () => {
    queued = false;
    listeners.forEach((fn) => {
      try { fn(); } catch (e) { console.error(e); }
    });
    document.querySelectorAll('[data-draw]').forEach((el) => {
      if (el.closest('[hidden]')) return;
      const fn = draws.get(el.dataset.draw);
      if (!fn) return;
      try { fn(el); } catch (e) { console.error(e); }
    });
  };
  const schedule = () => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(run);
  };

  window.dash = {
    colors: ['#4a5fc1', '#d0743c', '#2f9e8f', '#b0478a', '#7a8b2f', '#8d5fd3', '#c0503f', '#3f8fc0'],
    data(id) {
      const c = calcs[id];
      if (c) {
        const ins = c.inputs.map((i) => window.dash.data(i));
        if (ins.some((x) => x.status === 'error' || x.status === 'missing')) return {status: 'error', data: []};
        if (ins.some((x) => x.status !== 'ok')) return {status: 'loading', data: []};
        try {
          return {status: 'ok', data: c.fn(...ins.map((x) => x.data))};
        } catch (e) {
          console.error(e);
          return {status: 'error', data: []};
        }
      }
      return store[id] || {status: 'missing', data: []};
    },
    draw(name, fn) {
      if (fn) draws.set(name, fn);
      schedule();
    },
    onData(fn) {
      listeners.push(fn);
      schedule();
    },
    calc(id, spec) { calcs[id] = spec; },
    params() { return {...DEFAULTS, ...params}; },
    setParams(p) {
      Object.assign(params, p);
      schedule();
    },
    resetParams() {
      params = {};
      schedule();
    },
    setLink(name) {
      try { history.replaceState(null, '', '#' + name); } catch (e) { /* ignore */ }
    },
    refresh() {},
  };

  SOURCES.forEach((id) => {
    store[id] = {status: 'loading', data: []};
    fetch(`data/${id}.json`, {cache: 'no-cache'})
      .then((r) => {
        if (!r.ok) throw new Error(r.status);
        return r.json();
      })
      .then((rows) => {
        store[id] = {status: 'ok', data: Array.isArray(rows) ? rows : (rows.rows || rows.data || [])};
        schedule();
      })
      .catch(() => {
        store[id] = {status: 'error', data: []};
        schedule();
      });
  });

  // Redraw when a tab is shown or hidden, and when the page width changes.
  const watch = () => {
    const mo = new MutationObserver(schedule);
    document.querySelectorAll('[data-panel]').forEach((el) => mo.observe(el, {attributes: true, attributeFilter: ['hidden']}));
    let lastW = 0;
    const root = document.querySelector('.nz') || document.body;
    new ResizeObserver(() => {
      const w = Math.round(root.clientWidth);
      if (w !== lastW) {
        lastW = w;
        schedule();
      }
    }).observe(root);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watch);
  else watch();
})();
