(() => {
  const NZ = (window.NZ = {});
  NZ.K = {threshold: 5, band: 0.9, min_traded: 250000, max_gap: 2, close_lo: 0.05, close_hi: 0.95, default_n: 1000};
  NZ.DEF = {range: '12m', pollview: 'adjusted', hv: 'stated'};
  NZ.C = {NAT: '#2f6fd0', LAB: '#d63a3a', GRN: '#2f9e4f', NZF: '#7b8794', ACT: '#d9a300', OPP: '#11a39c', TPM: '#b3466b', TTT: '#9a7a4c', IND: '#9a9a9a'};
  NZ.ORDER = ['NAT', 'LAB', 'GRN', 'NZF', 'ACT', 'OPP', 'TPM', 'TTT', 'IND'];
  const f1 = d3.format('.1f');
  NZ.f = {
    pct: (v) => d3.format('.0%')(+v),
    pct1: (v) => d3.format('.1%')(+v),
    share: (v) => f1(+v) + '%',
    share0: (v) => d3.format('.0f')(+v) + '%',
    dec1: (v) => f1(+v),
    num: (v) => String(+v),
    int: (v) => d3.format(',')(Math.round(+v)),
    signed: (v) => d3.format('+.1f')(+v),
    usd: (v) => 'US$' + d3.format(',')(Math.round(+v)),
    date: (v) => d3.utcFormat('%-d %b')(new Date(String(v).slice(0, 10) + 'T00:00:00Z')),
    text: (v) => String(v),
  };
  NZ.isNum = (fmt) => fmt && fmt !== 'text' && fmt !== 'date';
  NZ.param = (k) => {
    const p = dash.params() || {};
    return p[k] ?? NZ.DEF[k];
  };
  NZ.status = (ids) => {
    let loading = false;
    for (const id of ids) {
      const s = dash.data(id).status;
      if (s === 'ok') continue;
      if (s === 'loading') loading = true;
      else return 'error';
    }
    return loading ? 'loading' : 'ok';
  };
  NZ.rows = (id) => {
    const g = dash.data(id);
    return g.status === 'ok' && Array.isArray(g.data) ? g.data : [];
  };
  NZ.find = (rows, where) => {
    if (!where) return rows[0];
    const conds = where.split('&').map((p) => {
      const i = p.indexOf('=');
      return [decodeURIComponent(p.slice(0, i)), decodeURIComponent(p.slice(i + 1))];
    });
    return rows.find((r) => conds.every(([k, v]) => String(r[k]) === v));
  };
  NZ.summary = () => {
    const S = {};
    NZ.rows('summary').forEach((r) => { S[r.metric] = r.value; });
    return S;
  };
  NZ.day = (s) => new Date(String(s).slice(0, 10) + 'T00:00:00Z');
  NZ.gate = (el, ids) => {
    const s = NZ.status(ids);
    if (s === 'ok') { el.classList.remove('dash-skeleton'); return true; }
    el.replaceChildren();
    if (s === 'error') {
      el.classList.remove('dash-skeleton');
      const line = document.createElement('div');
      line.className = 'nz-failed';
      const dot = document.createElement('span');
      dot.className = 'nz-dot';
      line.append(dot, document.createTextNode('Failed to load'));
      el.append(line);
    } else el.classList.add('dash-skeleton');
    return false;
  };
  NZ.svg = (el, W, H) => d3.select(el).append('svg').attr('class', 'nz-svg').attr('width', '100%').attr('height', H).attr('viewBox', `0 0 ${W} ${H}`);
  NZ.textH = 14;
  NZ.textW = (svg, strings, cls) => {
    const g = svg.append('g');
    const w = strings.map((s) => {
      const t = g.append('text').attr('class', cls).text(s);
      const n = t.node();
      const b = n.getBBox();
      if (b.height) NZ.textH = Math.max(12, b.height);
      return n.getComputedTextLength();
    });
    g.remove();
    return w;
  };
  NZ.dodge = (items, gap, lo, hi) => {
    items.sort((a, b) => a.y - b.y);
    items.forEach((it, i) => {
      it.ly = Math.max(it.y, lo);
      if (i && it.ly < items[i - 1].ly + gap) it.ly = items[i - 1].ly + gap;
    });
    const n = items.length;
    if (n && items[n - 1].ly > hi) {
      items[n - 1].ly = hi;
      for (let i = n - 2; i >= 0; i--) if (items[i].ly > items[i + 1].ly - gap) items[i].ly = items[i + 1].ly - gap;
    }
    return items;
  };
  NZ.thin = (svgNode, texts) => {
    const box = svgNode.getBoundingClientRect();
    let last = null;
    texts.forEach((t) => {
      const r = t.getBoundingClientRect();
      if (!r.width) return;
      const out = r.left < box.left - 0.5 || r.right > box.right + 0.5;
      const hit = last && r.left < last.right + 8;
      if (out || hit) t.remove();
      else last = r;
    });
  };
  NZ.axisStyle = (ax) => {
    ax.attr('font-size', null).attr('font-family', null);
    ax.select('.domain').style('stroke', 'var(--cds-chart-axis)');
    ax.selectAll('.tick line').style('stroke', 'var(--cds-chart-axis)');
    ax.selectAll('.tick text').attr('class', 'tick');
  };
  NZ.tip = (el) => {
    let t = el.querySelector(':scope > .tt');
    if (!t) {
      t = document.createElement('div');
      t.className = 'tt';
      t.hidden = true;
      el.append(t);
    }
    return t;
  };
  NZ.tipFill = (t, head, lines) => {
    const h = document.createElement('div');
    h.className = 'tt-h';
    h.textContent = head;
    t.replaceChildren(h, ...lines.map((l) => {
      const row = document.createElement('div');
      row.className = 'tt-r';
      if (l.color) {
        const s = document.createElement('span');
        s.className = 'tt-sw';
        s.style.background = l.color;
        row.append(s);
      }
      const a = document.createElement('span');
      a.textContent = l.label;
      row.append(a);
      if (l.value != null) {
        const b = document.createElement('span');
        b.className = 'tt-v';
        b.textContent = l.value;
        row.append(b);
      }
      return row;
    }));
  };
  NZ.tipAt = (el, t, x, y) => {
    t.hidden = false;
    const W = el.clientWidth, H = el.clientHeight, tw = t.offsetWidth, th = t.offsetHeight;
    let left = x + 14;
    if (left + tw > W) left = x - 14 - tw;
    if (left < 0) left = Math.max(0, (W - tw) / 2);
    let top = y - th - 10;
    if (top < 0) top = Math.max(0, Math.min(H - th, y + 14));
    t.style.left = left + 'px';
    t.style.top = top + 'px';
  };
  NZ.tipHide = (el) => {
    const t = el.querySelector(':scope > .tt');
    if (t) t.hidden = true;
  };
  NZ.local = (el, ev) => {
    const b = el.getBoundingClientRect();
    return [ev.clientX - b.left, ev.clientY - b.top];
  };
  const memo = new WeakMap();
  NZ.memo = (rows, key, make) => {
    let m = memo.get(rows);
    if (!m) { m = {}; memo.set(rows, m); }
    if (!(key in m)) m[key] = make(rows);
    return m[key];
  };
})();
(() => {
  const NZ = window.NZ;

  dash.draw('n', (el) => {
    const id = el.dataset.source;
    const s = NZ.status([id]);
    if (s !== 'ok') {
      el.textContent = '—';
      el.classList.toggle('dash-skeleton', s === 'loading');
      return;
    }
    el.classList.remove('dash-skeleton');
    const row = NZ.find(NZ.rows(id), el.dataset.where);
    const v = row ? row[el.dataset.field] : null;
    const fmtName = el.dataset.fmt || 'text';
    const fmt = NZ.f[fmtName] || NZ.f.text;
    const bad = v == null || v === '' || (NZ.isNum(fmtName) && !isFinite(+v));
    el.textContent = bad ? '—' : fmt(v);
  });

  dash.draw('k', (el) => {
    const v = NZ.K[el.dataset.k];
    const fmt = NZ.f[el.dataset.fmt] || NZ.f.text;
    el.textContent = v == null ? '—' : fmt(v);
  });

  dash.draw('rows', (tb) => {
    const table = tb.closest('table');
    if (!table) return;
    const id = table.dataset.source;
    if (NZ.status([id]) !== 'ok') { tb.replaceChildren(); return; }
    let rows = NZ.rows(id).slice();
    const need = table.dataset.need;
    if (need) rows = rows.filter((r) => r[need] != null && r[need] !== '');
    const sort = table.dataset.sort;
    if (sort) {
      const [k, dir] = sort.split(':');
      const sign = dir === 'asc' ? 1 : -1;
      rows.sort((a, b) => sign * ((+a[k] || 0) - (+b[k] || 0)));
    }
    const keys = (table.dataset.rowKey || '').split(',').filter(Boolean);
    const ths = [...table.querySelectorAll('thead th')];
    tb.replaceChildren(...rows.map((r) => {
      const tr = document.createElement('tr');
      if (keys.length === 1) tr.dataset.key = String(r[keys[0]]);
      else if (keys.length > 1) tr.dataset.key = keys.map((k) => encodeURIComponent(String(r[k]))).join(',');
      ths.forEach((th) => {
        const td = document.createElement('td');
        const v = r[th.dataset.field];
        const fmtName = th.dataset.fmt || 'text';
        const fmt = NZ.f[fmtName] || NZ.f.text;
        const bad = v == null || v === '' || (NZ.isNum(fmtName) && !isFinite(+v));
        td.textContent = bad ? '–' : fmt(v);
        tr.append(td);
      });
      return tr;
    }));
  });

  // Which headline sentence shows
  const MARGIN = 0.15;
  dash.onData(() => {
    const g = dash.data('chances');
    document.querySelectorAll('.nz-take').forEach((p) => p.classList.toggle('dash-skeleton', g.status === 'loading'));
    let pick = null;
    if (g.status === 'ok' && Array.isArray(g.data)) {
      const get = (v, o) => {
        const r = g.data.find((x) => x.view === v && x.outcome === o);
        return r ? +r.chance : 0;
      };
      const sL = get('stated', 'Luxon-led'), sH = get('stated', 'Hipkins-led');
      const oL = get('open', 'Luxon-led'), oH = get('open', 'Hipkins-led');
      if (sL > sH && oL > oH) pick = Math.min(sL - sH, oL - oH) > MARGIN ? 'luxon' : 'lean_l';
      else if (sH > sL && oH > oL) pick = Math.min(sH - sL, oH - oL) > MARGIN ? 'hipkins' : 'lean_h';
      else if (sH > sL && oL > oH) pick = 'split_h';
      else pick = 'close';
    }
    document.querySelectorAll('[data-tk]').forEach((s) => { s.hidden = s.dataset.tk !== pick; });
  });

  // Market sentence
  dash.onData(() => {
    const g = dash.data('market_count');
    const ok = g.status === 'ok' && Array.isArray(g.data) && g.data.length > 0;
    const n = ok ? +g.data[0].counted : NaN;
    document.querySelectorAll('[data-mk]').forEach((p) => {
      p.hidden = !ok || (p.dataset.mk === 'none' ? n !== 0 : !(n > 0));
    });
  });

  // Toggle buttons
  document.querySelectorAll('[data-set]').forEach((b) => b.addEventListener('click', () => {
    const [k, v] = b.dataset.set.split('=');
    dash.setParams({[k]: v});
  }));
  dash.onData(() => {
    document.querySelectorAll('[data-set]').forEach((b) => {
      const [k, v] = b.dataset.set.split('=');
      b.setAttribute('aria-pressed', String(NZ.param(k) === v));
    });
  });

  // Tabs
  const panels = () => [...document.querySelectorAll('[data-panel]')];
  const show = (id, link) => {
    const ids = panels().map((s) => s.id);
    if (!ids.includes(id)) id = ids[0];
    panels().forEach((s) => { s.hidden = s.id !== id; });
    document.querySelectorAll('[data-tab]').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.tab === id)));
    if (link) dash.setLink(id);
  };
  document.querySelectorAll('[data-tab]').forEach((b) => b.addEventListener('click', () => show(b.dataset.tab, true)));
  const named = location.hash.slice(1);
  const target = named ? document.getElementById(named) : null;
  const panel = target ? target.closest('[data-panel]') : null;
  show(panel ? panel.id : '', false);
  if (target && panel && target !== panel) requestAnimationFrame(() => requestAnimationFrame(() => target.scrollIntoView()));
})();
dash.calc('market_count', {
  inputs: ['markets'],
  title: 'Markets that pass the rule',
  description: 'How many of the markets checked are marked as counted.',
  fn: (markets) => [{counted: markets.filter((m) => m.counted === 'Yes').length}],
});
(() => {
  const NZ = window.NZ;
  const SEGS = [['Luxon-led', 'seg-l'], ['No clear majority', 'seg-s'], ['Hipkins-led', 'seg-h']];
  dash.draw('govbar', (el) => {
    if (!NZ.gate(el, ['chances'])) return;
    const rows = NZ.rows('chances').filter((r) => r.view === el.dataset.view);
    const W = el.clientWidth || 300;
    const bar = document.createElement('div');
    bar.className = 'gb';
    SEGS.forEach(([o, cls]) => {
      const r = rows.find((z) => z.outcome === o);
      if (!r) return;
      const v = +r.chance;
      if (!(v > 0)) return;
      const s = document.createElement('div');
      s.className = 'gb-seg ' + cls;
      s.style.flexBasis = (v * 100) + '%';
      const lab = NZ.f.pct(v);
      if (v * W >= lab.length * 8 + 14) {
        const t = document.createElement('span');
        t.textContent = lab;
        s.append(t);
      }
      s.addEventListener('pointermove', (ev) => {
        const tip = NZ.tip(el);
        NZ.tipFill(tip, o, [{label: 'Chance', value: NZ.f.pct1(v)}]);
        const [x, y] = NZ.local(el, ev);
        NZ.tipAt(el, tip, x, y);
      });
      s.addEventListener('pointerleave', () => NZ.tipHide(el));
      bar.append(s);
    });
    el.replaceChildren(bar);
  });
})();
(() => {
  const NZ = window.NZ;
  const truthy = (v) => v === true || v === 'true';
  const parseTrend = (rows) => {
    const pts = rows.map((r) => ({party: r.party, d: NZ.day(r.date), mid: +r.mid, lo: +r.lo, hi: +r.hi, ahead: truthy(r.ahead)}))
      .filter((p) => !isNaN(p.d) && isFinite(p.mid));
    const by = d3.group(pts, (p) => p.party);
    by.forEach((a) => a.sort((x, y) => x.d - y.d));
    const past = pts.filter((p) => !p.ahead);
    const end = d3.max(pts, (p) => p.d);
    return {by, start: d3.min(pts, (p) => p.d), end, today: d3.max(past, (p) => p.d) || end};
  };
  const parsePolls = (rows) => rows.map((r) => ({
    party: r.party, d: NZ.day(r.date), poll: r.poll,
    pub: r.published == null ? NaN : +r.published,
    adj: r.lean_removed == null ? NaN : +r.lean_removed,
  })).filter((p) => !isNaN(p.d));

  dash.draw('worm', (el) => {
    if (!NZ.gate(el, ['trend', 'polls', 'eday'])) return;
    const T = NZ.memo(NZ.rows('trend'), 'trend', parseTrend);
    const PL = NZ.memo(NZ.rows('polls'), 'polls', parsePolls);
    const info = new Map(NZ.rows('eday').map((r) => [r.party, r]));
    const range = NZ.param('range');
    const view = NZ.param('pollview');
    const val = (q) => (view === 'published' ? q.pub : q.adj);
    const start = range === 'all' ? T.start : d3.utcDay.offset(T.today, range === '3m' ? -92 : -365);
    const W = Math.max(280, el.clientWidth || 0), H = 320, narrow = W < 560;
    const fv = d3.format('.1f');
    const series = NZ.ORDER.filter((p) => T.by.has(p)).map((p) => {
      const all = T.by.get(p);
      const meta = info.get(p) || {};
      return {p, all, pts: all.filter((q) => q.d >= start), last: all[all.length - 1], color: NZ.C[p] || '#888',
        name: meta.name || p, label: narrow ? (meta.short || p) : (meta.name || p)};
    }).filter((s) => s.pts.length);
    series.forEach((s) => { s.text = `${s.label} ${fv(s.last.mid)}`; });
    const dots = PL.filter((q) => q.d >= start && q.d <= T.end && isFinite(val(q)) && T.by.has(q.party));

    el.replaceChildren();
    const svg = NZ.svg(el, W, H);
    const lw = NZ.textW(svg, series.map((s) => s.text), 'lbl');
    const yMax = d3.max([d3.max(series, (s) => d3.max(s.pts, (q) => q.hi)), d3.max(dots, val)].filter((v) => isFinite(v))) || 50;
    const y0 = d3.scaleLinear([0, yMax * 1.04], [0, 1]).nice();
    const yt = y0.ticks(5);
    const tw = NZ.textW(svg, yt.map((t) => t + '%'), 'tick');
    const ml = Math.ceil(d3.max(tw) || 20) + 11, mr = Math.ceil(d3.max(lw) || 40) + 28, mt = 20, mb = 26;
    const x = d3.scaleUtc([start, T.end], [ml, W - mr]);
    const y = d3.scaleLinear(y0.domain(), [H - mb, mt]);

    svg.append('g').selectAll('line').data(yt).join('line')
      .attr('x1', ml).attr('x2', W - mr).attr('y1', (t) => y(t)).attr('y2', (t) => y(t))
      .style('stroke', 'var(--cds-chart-grid)');
    svg.append('g').selectAll('text').data(yt).join('text').attr('class', 'tick')
      .attr('x', ml - 8).attr('y', (t) => y(t)).attr('dy', '0.32em').attr('text-anchor', 'end').text((t) => t + '%');

    svg.append('rect').attr('x', x(T.today)).attr('y', mt).attr('width', Math.max(0, x(T.end) - x(T.today))).attr('height', H - mb - mt)
      .style('fill', 'var(--cds-chart-grid)').style('opacity', 0.6);
    svg.append('line').attr('x1', ml).attr('x2', W - mr).attr('y1', y(NZ.K.threshold)).attr('y2', y(NZ.K.threshold))
      .style('stroke', 'var(--cds-chart-reference)').attr('stroke-dasharray', '4 3');

    const area = d3.area().x((q) => x(q.d)).y0((q) => y(q.lo)).y1((q) => y(q.hi));
    svg.append('g').selectAll('path').data(series).join('path').attr('d', (s) => area(s.pts))
      .style('fill', (s) => s.color).style('opacity', 0.1);

    svg.append('g').selectAll('circle').data(dots).join('circle')
      .attr('cx', (q) => x(q.d)).attr('cy', (q) => y(val(q))).attr('r', narrow ? 1.8 : 2.4)
      .style('fill', (q) => NZ.C[q.party] || '#888').style('opacity', 0.45);

    const line = d3.line().x((q) => x(q.d)).y((q) => y(q.mid));
    const lg = svg.append('g').attr('fill', 'none').attr('stroke-width', 2);
    series.forEach((s) => {
      const past = s.pts.filter((q) => !q.ahead);
      const ahead = s.pts.filter((q) => q.ahead);
      if (past.length && ahead.length) ahead.unshift(past[past.length - 1]);
      if (past.length > 1) lg.append('path').attr('d', line(past)).style('stroke', s.color).attr('stroke-linecap', 'round').attr('stroke-linejoin', 'round');
      if (ahead.length > 1) lg.append('path').attr('d', line(ahead)).style('stroke', s.color).attr('stroke-dasharray', '3 3');
    });

    svg.append('line').attr('x1', x(T.today)).attr('x2', x(T.today)).attr('y1', mt).attr('y2', H - mb).style('stroke', 'var(--cds-chart-axis)');
    svg.append('text').attr('class', 'tick').attr('x', x(T.today) - 4).attr('y', mt - 7).attr('text-anchor', 'end').text('Today');

    const every = range === 'all' ? d3.utcMonth.every(narrow ? 6 : 3) : range === '12m' ? d3.utcMonth.every(narrow ? 3 : 1) : d3.utcWeek.every(narrow ? 3 : 2);
    const fY = d3.utcFormat('%b %Y'), fM = d3.utcFormat('%b'), fD = d3.utcFormat('%-d %b');
    const fmtX = (d) => (range === '3m' ? fD(d) : range === 'all' || d.getUTCMonth() === 0 ? fY(d) : fM(d));
    const ax = svg.append('g').attr('transform', `translate(0,${H - mb})`)
      .call(d3.axisBottom(x).ticks(every).tickFormat(fmtX).tickSizeOuter(0));
    NZ.axisStyle(ax);
    NZ.thin(svg.node(), ax.selectAll('text').nodes());

    const items = series.map((s) => ({s, y: y(s.last.mid)}));
    NZ.dodge(items, Math.ceil(NZ.textH) + 2, mt + 6, H - mb - 6);
    const lx = W - mr + 8;
    const eg = svg.append('g');
    items.forEach((it) => {
      eg.append('path').attr('d', `M${x(it.s.last.d)},${it.y}L${lx + 2},${it.ly}`).attr('fill', 'none').style('stroke', it.s.color).style('opacity', 0.7);
      eg.append('rect').attr('x', lx + 4).attr('y', it.ly - 4).attr('width', 8).attr('height', 8).attr('rx', 2).style('fill', it.s.color);
      eg.append('text').attr('class', 'lbl').attr('x', lx + 16).attr('y', it.ly).attr('dy', '0.32em').text(it.s.text);
    });

    const hover = svg.append('g').style('display', 'none');
    const rule = hover.append('line').attr('y1', mt).attr('y2', H - mb).style('stroke', 'var(--cds-chart-axis)');
    const hd = hover.selectAll('circle').data(series).join('circle').attr('r', 4)
      .style('fill', (s) => s.color).style('stroke', 'var(--color-panel)').attr('stroke-width', 1.5);
    const fd = d3.utcFormat('%-d %b %Y');
    const bis = d3.bisector((q) => q.d).center;
    svg.append('rect').attr('x', ml).attr('y', mt).attr('width', Math.max(0, W - mr - ml)).attr('height', H - mb - mt)
      .style('fill', 'transparent').style('touch-action', 'pan-y')
      .on('pointermove', (ev) => {
        const [px, py] = d3.pointer(ev, svg.node());
        const d = x.invert(px);
        const at = new Map();
        series.forEach((s) => {
          const q = s.pts[bis(s.pts, d)];
          if (q) at.set(s, q);
        });
        if (!at.size) return;
        const q0 = at.values().next().value;
        hover.style('display', null);
        rule.attr('x1', x(q0.d)).attr('x2', x(q0.d));
        hd.attr('cx', (s) => (at.has(s) ? x(at.get(s).d) : -20)).attr('cy', (s) => (at.has(s) ? y(at.get(s).mid) : -20));
        const lines = [...at.entries()].sort((a, b) => b[1].mid - a[1].mid)
          .map(([s, q]) => ({color: s.color, label: s.name, value: fv(q.mid) + '%'}));
        const tip = NZ.tip(el);
        NZ.tipFill(tip, fd(q0.d) + (q0.ahead ? ', projected' : ''), lines);
        NZ.tipAt(el, tip, x(q0.d), py);
      })
      .on('pointerleave', () => {
        hover.style('display', 'none');
        NZ.tipHide(el);
      });
  });
})();
(() => {
  const NZ = window.NZ;
  dash.draw('hist', (el) => {
    if (!NZ.gate(el, ['history'])) return;
    const rows = NZ.rows('history').map((r) => ({
      d: NZ.day(r.asof), luxon: +r.luxon, hipkins: +r.hipkins, stuck: +r.stuck, open_luxon: +r.open_luxon, open_hipkins: +r.open_hipkins,
    })).filter((r) => !isNaN(r.d)).sort((a, b) => a.d - b.d);
    el.replaceChildren();
    if (rows.length < 2) return;
    const defs = NZ.param('hv') === 'open'
      ? [['open_luxon', 'Luxon-led', NZ.C.NAT], ['open_hipkins', 'Hipkins-led', NZ.C.LAB]]
      : [['luxon', 'Luxon-led', NZ.C.NAT], ['hipkins', 'Hipkins-led', NZ.C.LAB], ['stuck', 'No clear majority', 'var(--cds-chart-muted)']];
    const W = Math.max(280, el.clientWidth || 0), H = 240;
    const fp = d3.format('.0%');
    const lastRow = rows[rows.length - 1];
    const series = defs.map(([k, label, color]) => ({k, label, color, pts: rows.filter((r) => isFinite(r[k])), text: `${label} ${fp(lastRow[k])}`}))
      .filter((s) => s.pts.length > 1);
    const svg = NZ.svg(el, W, H);
    const lw = NZ.textW(svg, series.map((s) => s.text), 'lbl');
    const yt = [0, 0.25, 0.5, 0.75, 1];
    const tw = NZ.textW(svg, yt.map(fp), 'tick');
    const ml = Math.ceil(d3.max(tw) || 24) + 11, mr = Math.ceil(d3.max(lw) || 60) + 24, mt = 10, mb = 26;
    const x = d3.scaleUtc(d3.extent(rows, (r) => r.d), [ml, W - mr]);
    const y = d3.scaleLinear([0, 1], [H - mb, mt]);
    svg.append('g').selectAll('line').data(yt).join('line')
      .attr('x1', ml).attr('x2', W - mr).attr('y1', (t) => y(t)).attr('y2', (t) => y(t))
      .style('stroke', (t) => (t === 0.5 ? 'var(--cds-chart-reference)' : 'var(--cds-chart-grid)'))
      .attr('stroke-dasharray', (t) => (t === 0.5 ? '4 3' : null));
    svg.append('g').selectAll('text').data(yt).join('text').attr('class', 'tick')
      .attr('x', ml - 8).attr('y', (t) => y(t)).attr('dy', '0.32em').attr('text-anchor', 'end').text(fp);
    const line = d3.line().x((r) => x(r.d));
    const lg = svg.append('g').attr('fill', 'none').attr('stroke-width', 2).attr('stroke-linecap', 'round').attr('stroke-linejoin', 'round');
    series.forEach((s) => lg.append('path').attr('d', line.y((r) => y(r[s.k]))(s.pts)).style('stroke', s.color));
    const ax = svg.append('g').attr('transform', `translate(0,${H - mb})`)
      .call(d3.axisBottom(x).ticks(d3.utcMonth.every(1)).tickFormat(d3.utcFormat('%b')).tickSizeOuter(0));
    NZ.axisStyle(ax);
    NZ.thin(svg.node(), ax.selectAll('text').nodes());
    const items = series.map((s) => ({s, y: y(lastRow[s.k])}));
    NZ.dodge(items, Math.ceil(NZ.textH) + 2, mt + 6, H - mb - 6);
    const lx = W - mr + 8;
    items.forEach((it) => {
      svg.append('path').attr('d', `M${x(lastRow.d)},${it.y}L${lx + 2},${it.ly}`).attr('fill', 'none').style('stroke', it.s.color);
      svg.append('text').attr('class', 'lbl').attr('x', lx + 6).attr('y', it.ly).attr('dy', '0.32em').text(it.s.text);
    });
    const hover = svg.append('g').style('display', 'none');
    const rule = hover.append('line').attr('y1', mt).attr('y2', H - mb).style('stroke', 'var(--cds-chart-axis)');
    const hd = hover.selectAll('circle').data(series).join('circle').attr('r', 4)
      .style('fill', (s) => s.color).style('stroke', 'var(--color-panel)').attr('stroke-width', 1.5);
    const fd = d3.utcFormat('%-d %b %Y');
    const bis = d3.bisector((r) => r.d).center;
    svg.append('rect').attr('x', ml).attr('y', mt).attr('width', Math.max(0, W - mr - ml)).attr('height', H - mb - mt)
      .style('fill', 'transparent').style('touch-action', 'pan-y')
      .on('pointermove', (ev) => {
        const [px, py] = d3.pointer(ev, svg.node());
        const r = rows[bis(rows, x.invert(px))];
        if (!r) return;
        hover.style('display', null);
        rule.attr('x1', x(r.d)).attr('x2', x(r.d));
        hd.attr('cx', x(r.d)).attr('cy', (s) => y(r[s.k]));
        const tip = NZ.tip(el);
        NZ.tipFill(tip, fd(r.d), series.map((s) => ({color: s.color, label: s.label, value: NZ.f.pct1(r[s.k])})));
        NZ.tipAt(el, tip, x(r.d), py);
      })
      .on('pointerleave', () => {
        hover.style('display', 'none');
        NZ.tipHide(el);
      });
  });
})();
(() => {
  const NZ = window.NZ;
  const fi = d3.format('.0f');

  dash.draw('seats', (el) => {
    if (!NZ.gate(el, ['eday'])) return;
    const rows = NZ.rows('eday').map((r) => ({...r, mid: +r.seats_mid, lo: +r.seats_lo, hi: +r.seats_hi}))
      .filter((r) => isFinite(r.mid) && isFinite(r.lo) && isFinite(r.hi) && r.hi > 0)
      .sort((a, b) => b.mid - a.mid || b.hi - a.hi);
    const W = Math.max(280, el.clientWidth || 0), rowH = 30, mt = 4, mb = 26, H = mt + rows.length * rowH + mb;
    el.style.minHeight = H + 'px';
    el.replaceChildren();
    if (!rows.length) return;
    const narrow = W < 480;
    rows.forEach((r) => {
      r.lab = narrow ? (r.short || r.party) : (r.name || r.party);
      r.txt = `${fi(r.mid)} (${fi(r.lo)}–${fi(r.hi)})`;
    });
    const svg = NZ.svg(el, W, H);
    const nw = NZ.textW(svg, rows.map((r) => r.lab), 'lbl');
    const vw = NZ.textW(svg, rows.map((r) => r.txt), 'lbl-m');
    const ml = Math.ceil(d3.max(nw)) + 16, mr = Math.ceil(d3.max(vw)) + 16;
    const x = d3.scaleLinear([0, d3.max(rows, (r) => r.hi) || 10], [ml, W - mr]).nice();
    const xt = x.ticks(Math.max(2, Math.floor((W - ml - mr) / 60)));
    svg.append('g').selectAll('line').data(xt).join('line')
      .attr('x1', (t) => x(t)).attr('x2', (t) => x(t)).attr('y1', mt).attr('y2', H - mb).style('stroke', 'var(--cds-chart-grid)');
    const ax = svg.append('g').attr('transform', `translate(0,${H - mb})`).call(d3.axisBottom(x).tickValues(xt).tickFormat(fi).tickSizeOuter(0));
    NZ.axisStyle(ax);
    ax.select('.domain').remove();
    NZ.thin(svg.node(), ax.selectAll('text').nodes());
    const g = svg.append('g').selectAll('g').data(rows).join('g').attr('transform', (r, i) => `translate(0,${mt + i * rowH + rowH / 2})`);
    g.append('text').attr('class', 'lbl').attr('x', ml - 12).attr('dy', '0.32em').attr('text-anchor', 'end').text((r) => r.lab);
    g.append('rect').attr('x', (r) => x(r.lo)).attr('y', -5).attr('width', (r) => Math.max(2, x(r.hi) - x(r.lo))).attr('height', 10).attr('rx', 5)
      .style('fill', (r) => NZ.C[r.party] || '#888').style('opacity', 0.3);
    g.append('circle').attr('cx', (r) => x(r.mid)).attr('r', 6).style('fill', (r) => NZ.C[r.party] || '#888');
    g.append('text').attr('class', 'lbl-m').attr('x', W - mr + 10).attr('dy', '0.32em').text((r) => r.txt);
    g.append('rect').attr('x', 0).attr('y', -rowH / 2).attr('width', W).attr('height', rowH).style('fill', 'transparent')
      .on('pointermove', (ev, r) => {
        const tip = NZ.tip(el);
        const lines = [{color: NZ.C[r.party] || '#888', label: 'Seats', value: r.txt}];
        if (r.vote_mid != null && isFinite(+r.vote_mid)) lines.push({label: 'Party vote', value: `${NZ.f.share(r.vote_mid)} (${NZ.f.dec1(r.vote_lo)}–${NZ.f.dec1(r.vote_hi)})`});
        NZ.tipFill(tip, r.name || r.party, lines);
        const [px, py] = NZ.local(el, ev);
        NZ.tipAt(el, tip, px, py);
      })
      .on('pointerleave', () => NZ.tipHide(el));
  });

  dash.draw('bloc', (el) => {
    if (!NZ.gate(el, ['summary'])) return;
    const S = NZ.summary();
    const side = el.dataset.side === 'left' ? 'left' : 'right';
    const mid = +S[side + '_mid'], lo = +S[side + '_lo'], hi = +S[side + '_hi'], maj = +S.maj_mid;
    const oppAll = +S.opp_mid || 0;
    const opp = side === 'left' ? oppAll : 0;
    el.replaceChildren();
    if (![mid, lo, hi, maj].every((v) => isFinite(v))) return;
    const W = Math.max(280, el.clientWidth || 0), H = 46;
    const top = d3.max([+S.right_hi, +S.left_hi + oppAll, +S.left_mid + oppAll, maj].filter((v) => isFinite(v))) || 70;
    const tR = fi(+S.right_mid);
    const tL = `${fi(+S.left_mid)} + ${fi(oppAll)} TOP`;
    const svg = NZ.svg(el, W, H);
    const mr = Math.ceil(d3.max(NZ.textW(svg, [tR, tL], 'lbl'))) + 14;
    const x = d3.scaleLinear([0, top * 1.04], [0, W - mr]);
    const color = side === 'left' ? NZ.C.LAB : NZ.C.NAT;
    svg.append('rect').attr('x', 0).attr('y', 6).attr('width', Math.max(0, x(mid))).attr('height', 20).attr('rx', 3).style('fill', color);
    if (opp > 0) svg.append('rect').attr('x', x(mid) + 1).attr('y', 6).attr('width', Math.max(0, x(mid + opp) - x(mid) - 1)).attr('height', 20).attr('rx', 3)
      .style('fill', NZ.C.OPP).style('opacity', 0.65);
    svg.append('line').attr('x1', x(lo)).attr('x2', x(hi)).attr('y1', 36).attr('y2', 36).style('stroke', 'var(--color-fg-muted)');
    [lo, hi].forEach((v) => svg.append('line').attr('x1', x(v)).attr('x2', x(v)).attr('y1', 32).attr('y2', 40).style('stroke', 'var(--color-fg-muted)'));
    svg.append('line').attr('x1', x(maj)).attr('x2', x(maj)).attr('y1', 0).attr('y2', H).style('stroke', 'var(--color-fg)').attr('stroke-dasharray', '4 3');
    svg.append('text').attr('class', 'lbl').attr('x', W - mr + 10).attr('y', 16).attr('dy', '0.32em').text(side === 'left' ? tL : tR);
    svg.append('rect').attr('x', 0).attr('y', 0).attr('width', W).attr('height', H).style('fill', 'transparent')
      .on('pointermove', (ev) => {
        const tip = NZ.tip(el);
        const lines = [{color, label: 'Most likely', value: `${fi(mid)} seats`}, {label: 'Range', value: `${fi(lo)}–${fi(hi)}`}];
        if (opp > 0) lines.push({color: NZ.C.OPP, label: 'Opportunity adds', value: fi(opp)});
        lines.push({label: 'Majority', value: fi(maj)});
        NZ.tipFill(tip, 'Seats', lines);
        const [px, py] = NZ.local(el, ev);
        NZ.tipAt(el, tip, px, py);
      })
      .on('pointerleave', () => NZ.tipHide(el));
  });

  dash.draw('parl', (el) => {
    if (!NZ.gate(el, ['parliament', 'summary'])) return;
    const rows = NZ.rows('parliament').map((r) => ({n: +r.seats, p: +r.chance})).filter((r) => isFinite(r.n) && isFinite(r.p)).sort((a, b) => a.n - b.n);
    const med = +NZ.summary().total_mid;
    el.replaceChildren();
    if (!rows.length) return;
    const W = Math.max(280, el.clientWidth || 0), H = 200, mt = 8, mb = 26;
    const fp = d3.format('.0%');
    const y0 = d3.scaleLinear([0, d3.max(rows, (r) => r.p) || 0.1], [0, 1]).nice();
    const yt = y0.ticks(3);
    const svg = NZ.svg(el, W, H);
    const ml = Math.ceil(d3.max(NZ.textW(svg, yt.map(fp), 'tick')) || 24) + 11;
    const x = d3.scaleBand(rows.map((r) => r.n), [ml, W - 4]).padding(0.2);
    const y = d3.scaleLinear(y0.domain(), [H - mb, mt]);
    svg.append('g').selectAll('line').data(yt).join('line')
      .attr('x1', ml).attr('x2', W - 4).attr('y1', (t) => y(t)).attr('y2', (t) => y(t)).style('stroke', 'var(--cds-chart-grid)');
    svg.append('g').selectAll('text').data(yt).join('text').attr('class', 'tick')
      .attr('x', ml - 8).attr('y', (t) => y(t)).attr('dy', '0.32em').attr('text-anchor', 'end').text(fp);
    const bw = x.bandwidth();
    svg.append('g').selectAll('rect').data(rows).join('rect')
      .attr('x', (r) => x(r.n)).attr('y', (r) => y(r.p)).attr('width', bw).attr('height', (r) => Math.max(0, H - mb - y(r.p)))
      .attr('rx', Math.min(3, bw / 2))
      .style('fill', (r) => (r.n === med ? dash.colors[0] : 'var(--cds-chart-muted)'))
      .on('pointermove', (ev, r) => {
        const tip = NZ.tip(el);
        NZ.tipFill(tip, `${fi(r.n)} seats`, [{label: 'Chance', value: NZ.f.pct1(r.p)}]);
        const [px, py] = NZ.local(el, ev);
        NZ.tipAt(el, tip, px, py);
      })
      .on('pointerleave', () => NZ.tipHide(el));
    const ax = svg.append('g').attr('transform', `translate(0,${H - mb})`).call(d3.axisBottom(x).tickFormat(fi).tickSizeOuter(0));
    NZ.axisStyle(ax);
    NZ.thin(svg.node(), ax.selectAll('text').nodes());
  });
})();
