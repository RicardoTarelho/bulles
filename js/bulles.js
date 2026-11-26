/* Bulles — read comics in the language you're learning; tap a bubble to flip it. */
{
const LIB = window.BULLES_LIBRARY || {langs: {}, series: []};
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const store = {
  get(k, d){ try{ const v = localStorage.getItem('bulles:' + k); return v ? JSON.parse(v) : d; }catch(e){ return d; } },
  set(k, v){ try{ localStorage.setItem('bulles:' + k, JSON.stringify(v)); }catch(e){} }
};
const HELLO = {fr:'Bonjour !', en:'Hello!', pt:'Olá!', es:'¡Hola!', de:'Hallo!', it:'Ciao!'};
const root = document.documentElement;

/* ---------- data loading (script files, so it also works from disk) ---------- */
const cache = {}, waiting = {};
window.BULLES_LOAD = d => { const k = d.ep + ':' + d.part; cache[k] = d; (waiting[k] || []).forEach(f => f(d)); delete waiting[k]; };
window.BULLES_COVERS_LOAD = d => { cache.covers = d; (waiting.covers || []).forEach(f => f(d)); delete waiting.covers; };
function inject(key, src){
  if (cache[key]) return Promise.resolve(cache[key]);
  return new Promise((res, rej) => {
    const first = !waiting[key];
    (waiting[key] = waiting[key] || []).push(res);
    if (!first) return;
    const s = document.createElement('script'); s.src = src;
    s.onerror = () => { delete waiting[key]; rej(new Error('load ' + src)); };
    document.head.appendChild(s);
  });
}
const part = (ep, p) => inject(ep + ':' + p, 'data/episodes/' + ep + '/' + p + '.js');
const covers = () => inject('covers', 'data/covers.js');

/* ---------- theme ---------- */
const mq = window.matchMedia ? matchMedia('(prefers-color-scheme: dark)') : null;
const saved = store.get('theme', null);
if (saved) root.dataset.bulles = saved;
const effective = () => root.dataset.bulles || root.dataset.theme || (mq && mq.matches ? 'dark' : 'light');
function syncTheme(){
  const d = effective() === 'dark';
  root.classList.toggle('dark', d);
  $('#theme').setAttribute('aria-label', d ? 'Switch to light mode' : 'Switch to dark mode');
}
$('#theme').addEventListener('click', () => { root.dataset.bulles = effective() === 'dark' ? 'light' : 'dark'; store.set('theme', root.dataset.bulles); syncTheme(); });
if (mq && mq.addEventListener) mq.addEventListener('change', syncTheme);
new MutationObserver(syncTheme).observe(root, {attributes: true, attributeFilter: ['data-theme']});
syncTheme();

/* ---------- state ---------- */
let langs = store.get('langs', null);       // {learn, know}
let words = store.get('words', []);
let progress = store.get('progress', {});   // episodeId -> furthest page index
let lastEp = store.get('last', {});         // seriesId -> episodeId
const LN = l => LIB.langs[l] || l;
const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];
const LEVEL_HELP = {
  A1: 'Beginner: you know some words and very simple phrases.',
  A2: 'Elementary: you understand short, simple sentences about everyday things.',
  B1: 'Intermediate: you follow the main points of clear, everyday language.',
  B2: 'Upper intermediate: you read most texts, even with some complex language.',
  C1: 'Advanced: you read long, demanding texts without much trouble.',
  C2: 'Proficient: you understand almost everything you read.'};
/* how a piece of content compares with the reader's level; ranges like "A1–B1" count as fitting if they include it */
function fit(level){
  if (!langs || !langs.level || !level) return null;
  const parts = String(level).split('–'), lo = LEVELS.indexOf(parts[0]), hi = LEVELS.indexOf(parts[parts.length - 1]), u = LEVELS.indexOf(langs.level);
  const d = u >= lo && u <= hi ? 0 : hi < u ? hi - u : lo - u;
  return d <= -2 ? {k: 'easy', t: 'Easy for you'} : d <= 0 ? {k: 'good', t: 'Your level'} : d === 1 ? {k: 'stretch', t: 'A stretch'} : {k: 'hard', t: 'Hard for you'};
}
const lvTag = level => { const f = fit(level); return `<span class="lv">${esc(level)}</span>${f ? `<span class="fit fit-${f.k}">${f.t}</span>` : ''}`; };
const series = id => LIB.series.find(s => s.id === id);
const seriesOf = epId => LIB.series.find(s => s.episodes.some(e => e.id === epId));
/* the language bubbles flip into: yours if the episode has it, else English (or another it has) */
const knowFor = e => e.langs.includes(langs.know) ? langs.know
  : (e.langs.includes('en') && langs.learn !== 'en') ? 'en' : e.langs.find(l => l !== langs.learn);
const fits = e => e.langs.includes(langs.learn) && !!knowFor(e);
const short = t => t.replace(/^[^\d:]{0,24}\d+\s*[:.–-]\s*/, '');
const T = (obj, l) => (obj && (obj[l] || obj.en || Object.values(obj)[0])) || '';
function status(e){
  const at = progress[e.id] ?? -1;
  if (at < 0) return {pct: 0, label: 'New'};
  if (at + 1 >= e.pages) return {pct: 100, label: 'Read'};
  return {pct: Math.round((at + 1) / e.pages * 100), label: 'Page ' + (at + 1) + ' of ' + e.pages};
}

function views(id){
  if (id !== 'tale') { const sb = document.getElementById('sbub'); if (sb) sb.hidden = true; }
  document.querySelectorAll('.view').forEach(v => v.hidden = v.id !== id);
  $('#pair').hidden = !langs || id === 'setup';
  $('#wordsBtn').hidden = !langs || id === 'setup';
  window.scrollTo(0, 0);
}
function syncHeader(){
  if (langs) $('#pair').textContent = LN(langs.learn) + ' → ' + LN(langs.know) + (langs.level ? ' · ' + langs.level : '');
  $('#wc').textContent = words.length;
  $('#wc').classList.toggle('zero', !words.length);
}
$('#pair').addEventListener('click', () => { location.hash = 'setup'; });
$('#wordsBtn').addEventListener('click', () => { location.hash = 'words'; });

/* ---------- setup ---------- */
let pick = langs ? {level: 'A2', ...langs} : {learn: 'fr', know: 'en', level: 'A2'};
function drawSetup(){
  const codes = Object.keys(LIB.langs);
  const chip = (role, l) => `<button class="chip" data-role="${role}" data-l="${l}" aria-pressed="${pick[role] === l}" ${role === 'know' && pick.learn === l ? 'disabled' : ''}>${esc(LN(l))}</button>`;
  $('#learnChips').innerHTML = codes.map(l => chip('learn', l)).join('');
  $('#knowChips').innerHTML = codes.map(l => chip('know', l)).join('');
  $('#levelChips').innerHTML = LEVELS.map(l => `<button class="chip" data-role="level" data-l="${l}" aria-pressed="${pick.level === l}">${l}</button>`).join('');
  $('#levelLegend').textContent = 'My level in ' + LN(pick.learn);
  $('#levelHelp').textContent = LEVEL_HELP[pick.level] || '';
  $('#heroL').textContent = HELLO[pick.learn] || '';
  $('#heroK').textContent = HELLO[pick.know] || '';
  $('#start').disabled = !pick.learn || !pick.know || pick.learn === pick.know;
}
document.querySelector('.pick').addEventListener('click', e => {
  const b = e.target.closest('.chip'); if (!b || b.disabled) return;
  pick[b.dataset.role] = b.dataset.l;
  if (pick.learn === pick.know) pick.know = Object.keys(LIB.langs).find(l => l !== pick.learn);
  drawSetup();
});
$('#start').addEventListener('click', () => { langs = {...pick}; store.set('langs', langs); syncHeader(); location.hash = 'library'; });

/* ---------- library: one card per series ---------- */
function drawLibrary(){
  $('#libSub').innerHTML = esc('Reading in ' + LN(langs.learn) + ', flipping into ' + LN(langs.know) + '.') + (langs.level ? '' : ' <a href="#setup">Set your level</a> to see what suits you.');
  $('#shelf').innerHTML = LIB.series.map(s => {
    const eps = s.episodes.filter(fits), read = eps.filter(e => status(e).pct === 100).length;
    return `<a class="card scard" href="#series-${esc(s.id)}">
      <div class="stack3" data-series="${esc(s.id)}">${eps.slice(0, 3).map(e => `<div class="sc" data-cover="${esc(e.id)}"></div>`).join('')}</div>
      <div class="cbody"><h2>${esc(s.name)}</h2><p class="k">${esc(T(s.blurb, langs.know))}</p>
      <div class="meta">${lvTag(s.level)}<span>by ${esc(s.author)}</span><span>${eps.length} episodes</span><span>${read} read</span></div>
      <div class="prog"><i style="width:${eps.length ? Math.round(read / eps.length * 100) : 0}%"></i></div></div></a>`;
  }).join('');
  const books = (LIB.books || []).filter(b => b.lang === langs.learn);
  $('#bookshelf').innerHTML = books.map(b => {
    const done = b.chapters.filter(c => chapterPct(b, c) >= 100).length;
    return `<a class="card" href="#book-${esc(b.id)}">
      <div class="cover">${bookCover(b)}</div>
      <div class="cbody"><h2 lang="${esc(b.lang)}">${esc(b.title[b.lang])}</h2><p class="k">${esc(T(b.title, langs.know))} · ${esc(b.author)}</p>
      <div class="meta">${lvTag(b.level)}<span>${unitText(b)}</span><span>${done} read</span></div>
      <div class="prog"><i style="width:${Math.round(done / b.chapters.length * 100)}%"></i></div></div></a>`;
  }).join('');
  const others = (LIB.books || []).filter(b => b.lang !== langs.learn);
  $('#bookNote').textContent = books.length ? '' : others.length ? 'The first book, ' + others[0].title[others[0].lang] + ', is in ' + LN(others[0].lang) + '. Choose ' + LN(others[0].lang) + ' as the language you\'re learning to read it.' : '';
  fillCovers();
}
const unitText = b => b.chapters.length + (b.total > b.chapters.length ? ' of ' + b.total : '') + ' ' + (b.unit || 'tales');
function bookCover(b){
  const t = b.title[b.lang], m = t.match(/^(.*?)\s(de |d’)(.*)$/);
  const l1 = m ? m[1] : t, l2 = m ? m[2] + m[3] : '';
  return `<svg viewBox="0 0 288 200" role="img" aria-label="${esc(t)}"><rect width="288" height="200" fill="${esc(b.color || '#7b1e2c')}"/><rect x="12" y="12" width="264" height="176" fill="none" stroke="#e7c77d" stroke-width="2"/><rect x="19" y="19" width="250" height="162" fill="none" stroke="#e7c77d" stroke-width="1" opacity=".55"/>
    <path d="M144 34l5 9 10 1-7 7 2 10-10-5-10 5 2-10-7-7 10-1z" fill="#e7c77d"/>
    <text x="144" y="${l2 ? 104 : 116}" text-anchor="middle" font-family="Literata, Georgia, serif" font-size="30" font-weight="600" fill="#f6e7bf">${esc(l1)}</text>
    ${l2 ? `<text x="144" y="138" text-anchor="middle" font-family="Literata, Georgia, serif" font-size="24" fill="#f6e7bf">${esc(l2)}</text>` : ''}
    <text x="144" y="170" text-anchor="middle" font-family="Inter, sans-serif" font-size="${b.author.length > 20 ? 9 : 11}" letter-spacing="2" fill="#e7c77d">${esc(b.author.toUpperCase())} · ${b.year}</text></svg>`;
}
function fillCovers(){
  covers().then(c => document.querySelectorAll('[data-cover]').forEach(el => {
    if (el.querySelector('img') || !c[el.dataset.cover]) return;
    const i = new Image(); i.alt = ''; i.src = c[el.dataset.cover]; el.prepend(i);
  })).catch(() => {});
}

/* ---------- series: the episode list ---------- */
function drawSeries(id){
  const s = series(id); if (!s) { location.hash = 'library'; return; }
  const all = s.episodes.filter(fits), missing = s.episodes.length - all.length;
  $('#onlyWrap').hidden = !langs.level;
  const only = !!langs.level && $('#onlyMine').checked;
  const eps = only ? all.filter(e => { const f = fit(e.level); return f && (f.k === 'good' || f.k === 'easy'); }) : all;
  $('#sLevel').innerHTML = lvTag(s.level) + '<span class="sub small">Estimated level for each episode below</span>';
  const swapped = all.filter(e => knowFor(e) !== langs.know);
  $('#sName').textContent = s.name;
  $('#sBlurb').textContent = T(s.blurb, langs.know) + ' By ' + s.author + '.';
  const cont = all.find(e => e.id === lastEp[s.id] && status(e).pct < 100) || all.find(e => status(e).pct < 100) || all[0];
  $('#sGo').href = '#read-' + (cont ? cont.id : '');
  $('#sGo').textContent = cont && (progress[cont.id] ?? -1) >= 0 ? 'Continue episode ' + cont.n : 'Start episode ' + (cont ? cont.n : 1);
  const notes = [];
  if (swapped.length) notes.push((swapped.length === 1 ? 'Episode ' + swapped[0].n + ' isn\'t' : 'Episodes ' + swapped.map(e => e.n).join(', ') + ' aren\'t') + ' translated into ' + LN(langs.know) + ' yet, so ' + (swapped.length === 1 ? 'its' : 'their') + ' bubbles flip to ' + LN(knowFor(swapped[0])) + '.');
  if (missing) notes.push(missing + (missing === 1 ? ' episode isn\'t' : ' episodes aren\'t') + ' available in ' + LN(langs.learn) + ' yet, so ' + (missing === 1 ? 'it is' : 'they are') + ' hidden.');
  $('#sNote').textContent = notes.join(' ');
  $('#eps').innerHTML = eps.map(e => {
    const st = status(e);
    return `<li><a class="ep" href="#read-${esc(e.id)}">
      <div class="thumb" data-cover="${esc(e.id)}"><span class="num">${e.n}</span>${st.pct === 100 ? '<span class="done">Read</span>' : ''}</div>
      <div class="einfo"><h3 lang="${esc(langs.learn)}">${esc(short(T(e.title, langs.learn)))}</h3>
      <p class="k">${esc(short(T(e.title, knowFor(e))))}</p>${knowFor(e) !== langs.know ? `<p class="swap">Flips to ${esc(LN(knowFor(e)))}</p>` : ''}
      <p class="meta">${lvTag(e.level)}<span>${e.pages} pages</span><span>${esc(st.label)}</span></p>
      <div class="prog"><i style="width:${st.pct}%"></i></div></div></a></li>`;
  }).join('') || '<li class="empty">Every episode here is above your level. Switch the filter off to see them all.</li>';
  fillCovers();
}

/* ---------- reader ---------- */
let cur = null, lastTap = null, pageObs = null, openToken = 0;
const load = src => new Promise(r => { const i = new Image(); i.onload = () => r(i); i.onerror = () => r(null); i.src = src; });

async function openEpisode(id){
  const s = seriesOf(id), e = s && s.episodes.find(x => x.id === id);
  if (!e || !fits(e)) { location.hash = 'library'; return; }
  const token = ++openToken, learn = langs.learn, know = knowFor(e);
  lastEp[s.id] = id; store.set('last', lastEp);
  $('#rBack').href = '#series-' + s.id;
  $('#rTitle').textContent = T(e.title, learn); $('#rTitle').lang = learn;
  $('#hint').textContent = 'Tap a bubble you don\'t understand to see it in ' + LN(know) + '. Tap it again to go back.';
  $('#revealAll').checked = false;
  hidePhrase();
  const holder = $('#pages');
  holder.innerHTML = '<p class="loading"><span class="spin"></span>Opening episode ' + e.n + '…</p>';
  $('#credits').innerHTML = '';
  let P, LL, KL;
  try { [P, LL, KL] = await Promise.all([part(id, 'pages'), part(id, learn), part(id, know)]); }
  catch(err) { holder.innerHTML = '<p class="loading">This episode could not be loaded. Check your connection and try again.</p>'; return; }
  if (token !== openToken) return;
  holder.innerHTML = '';
  cur = {ep: e, series: s, pages: [], know};
  P.pages.forEach((p, i) => {
    const el = document.createElement('div');
    el.className = 'page'; el.style.aspectRatio = p.w + ' / ' + p.h; el.dataset.i = i;
    const n = (p.items[learn] || []).length;
    el.setAttribute('role', 'img');
    el.setAttribute('aria-label', 'Page ' + (i + 1) + (n ? ', ' + n + ' bubbles' : ''));
    const lsrc = LL.layers[p.id], ksrc = KL.layers[p.id];
    el.innerHTML = `<img alt="" decoding="async">${lsrc ? '<img alt="" decoding="async">' : ''}<canvas width="${p.w}" height="${p.h}"></canvas>`;
    const imgs = el.querySelectorAll('img');
    imgs[0].src = p.img; if (lsrc) imgs[1].src = lsrc;
    holder.appendChild(el);
    const pg = {data: p, el, canvas: el.querySelector('canvas'), shown: new Set(), lImg: null, kImg: null};
    pg.ready = lsrc && ksrc ? Promise.all([load(lsrc), load(ksrc)]).then(([l, k]) => { pg.lImg = l; pg.kImg = k; }) : Promise.resolve();
    el.addEventListener('click', ev => tapPage(pg, ev));
    cur.pages.push(pg);
  });
  drawCredits(s, e);
  if (pageObs) pageObs.disconnect();
  pageObs = new IntersectionObserver(ents => {
    for (const en of ents) if (en.isIntersecting) {
      const i = +en.target.dataset.i;
      if ((progress[id] ?? -1) < i) { progress[id] = i; store.set('progress', progress); }
    }
  }, {threshold: 0.6});
  cur.pages.forEach(pg => pageObs.observe(pg.el));
}

function overlap(a, b){
  const x = Math.max(0, Math.min(a[0] + a[2], b[0] + b[2]) - Math.max(a[0], b[0]));
  const y = Math.max(0, Math.min(a[1] + a[3], b[1] + b[3]) - Math.max(a[1], b[1]));
  return x * y / Math.min(a[2] * a[3], b[2] * b[3]);
}
function region(pg, idx){
  const p = pg.data, L = p.items[langs.learn][idx];
  const K = (p.items[cur.know] || []).filter(k => overlap(L.b, k.b) > 0.2);
  let [x0, y0, x1, y1] = [L.b[0], L.b[1], L.b[0] + L.b[2], L.b[1] + L.b[3]];
  for (const k of K) { x0 = Math.min(x0, k.b[0]); y0 = Math.min(y0, k.b[1]); x1 = Math.max(x1, k.b[0] + k.b[2]); y1 = Math.max(y1, k.b[1] + k.b[3]); }
  return {L, K, r: [x0 * p.w, y0 * p.h, (x1 - x0) * p.w, (y1 - y0) * p.h]};
}
/* hide the learned text under a soft white patch, then draw the known language on top */
function paintItem(pg, idx, ctx){
  const {r} = region(pg, idx);
  const pad = 14, [x, y, w, h] = r.map(Math.round);
  const sx = Math.max(0, x - pad), sy = Math.max(0, y - pad);
  const sw = Math.min(pg.data.w - sx, w + pad * 2), sh = Math.min(pg.data.h - sy, h + pad * 2);
  if (sw <= 0 || sh <= 0) return;
  const o = document.createElement('canvas'); o.width = sw; o.height = sh;
  const oc = o.getContext('2d');
  for (let a = 0; a < 24; a++) for (const rad of [4, 8, 12]) {
    oc.drawImage(pg.lImg, sx, sy, sw, sh, Math.cos(a / 24 * Math.PI * 2) * rad, Math.sin(a / 24 * Math.PI * 2) * rad, sw, sh);
  }
  oc.globalCompositeOperation = 'source-in';
  oc.fillStyle = '#ffffff'; oc.fillRect(0, 0, sw, sh);
  ctx.drawImage(o, sx, sy);
  ctx.drawImage(pg.kImg, sx, sy, sw, sh, sx, sy, sw, sh);
}
function repaint(pg){
  const ctx = pg.canvas.getContext('2d');
  ctx.clearRect(0, 0, pg.canvas.width, pg.canvas.height);
  if (!pg.lImg || !pg.kImg) return;
  for (const i of pg.shown) paintItem(pg, i, ctx);
}
async function tapPage(pg, e){
  const items = pg.data.items[langs.learn] || [];
  const rect = pg.el.getBoundingClientRect();
  const px = (e.clientX - rect.left) / rect.width, py = (e.clientY - rect.top) / rect.height, m = 0.012;
  let best = -1, area = Infinity;
  items.forEach((it, i) => {
    const [x, y, w, h] = it.b;
    if (px >= x - m && px <= x + w + m && py >= y - m && py <= y + h + m && w * h < area) { best = i; area = w * h; }
  });
  if (best < 0) { hidePhrase(); return; }
  await pg.ready;
  if (!pg.lImg || !pg.kImg) return;
  if (pg.shown.has(best)) { pg.shown.delete(best); hidePhrase(); }
  else { pg.shown.add(best); showPhrase(pg, best); }
  repaint(pg);
}
$('#onlyMine').addEventListener('change', () => { const h = location.hash.slice(1); if (h.startsWith('series-')) drawSeries(h.slice(7)); });
$('#revealAll').addEventListener('change', async e => {
  if (!cur) return;
  hidePhrase();
  for (const pg of cur.pages) {
    await pg.ready;
    pg.shown = e.target.checked ? new Set((pg.data.items[langs.learn] || []).map((_, i) => i)) : new Set();
    repaint(pg);
  }
});

function showPhrase(pg, idx){
  const {L, K} = region(pg, idx);
  if (!L.t) { hidePhrase(); return; }
  const kt = K.map(k => k.t).filter(Boolean).join(' ');
  lastTap = {ep: cur.ep, pg, L: L.t, K: kt, who: L.s || ''};
  $('#pWho').textContent = L.s || ''; $('#pWho').hidden = !L.s;
  $('#pL').textContent = L.t; $('#pL').lang = langs.learn;
  $('#pK').textContent = kt; $('#pK').lang = cur.know;
  const has = words.some(w => w.l === L.t && w.lang === langs.learn);
  $('#pSave').textContent = has ? 'Saved' : 'Save'; $('#pSave').disabled = has;
  $('#phrase').hidden = false;
}
function hidePhrase(){ $('#phrase').hidden = true; lastTap = null; }
$('#pClose').addEventListener('click', hidePhrase);
$('#pSave').addEventListener('click', () => {
  if (!lastTap) return;
  const t = lastTap;
  words.unshift({l: t.L, k: t.K, who: t.who, lang: langs.learn, klang: cur.know,
    src: 'Episode ' + t.ep.n + ', page ' + (+t.pg.el.dataset.i + 1)});
  store.set('words', words); syncHeader();
  $('#pSave').textContent = 'Saved'; $('#pSave').disabled = true;
});

function drawCredits(s, e){
  const names = l => {
    const x = (e.translation || {})[l] || {};
    const tr = (x.translation || []).filter(n => n !== 'original version');
    const pr = x.proofreading || [];
    return (tr.length ? tr.join(', ') : 'original version') + (pr.length ? ' · proofreading: ' + pr.join(', ') : '');
  };
  const c = e.credits || {};
  const extra = Object.entries(c).filter(([k]) => !['art', 'scenario'].includes(k));
  const eps = s.episodes.filter(fits), i = eps.indexOf(e), next = eps[i + 1];
  $('#credits').innerHTML = `<h2>Credits</h2>
    <dl><dt>Art</dt><dd>${esc((c.art || [s.author]).join(', '))}</dd>
    <dt>Story</dt><dd>${esc((c.scenario || [s.author]).join(', '))}</dd>
    ${extra.map(([k, v]) => `<dt>${esc(k[0].toUpperCase() + k.slice(1))}</dt><dd>${esc(v.join(', '))}</dd>`).join('')}
    <dt>${esc(LN(langs.learn))}</dt><dd>${esc(names(langs.learn))}</dd>
    <dt>${esc(LN(knowFor(e)))}</dt><dd>${esc(names(knowFor(e)))}</dd>
    <dt>Licence</dt><dd><a href="${esc(s.licenseUrl)}">${esc(s.license)}</a> · <a href="${esc(s.site)}">peppercarrot.com</a></dd></dl>
    <div class="next"><a href="#series-${esc(s.id)}">All episodes</a>${next ? `<a class="go" href="#read-${esc(next.id)}">Next: episode ${next.n}</a>` : ''}</div>`;
}

/* ---------- books ---------- */
const bookById = id => (LIB.books || []).find(b => b.id === id);
const bookKnow = b => b.langs.includes(langs.know) && langs.know !== b.lang ? langs.know : 'en';
const chapterPct = (b, c) => { const p = progress['book:' + b.id + '/' + c.id]; return p ? p.pct : 0; };
const chapterFile = (b, c) => inject(b.id + '/' + c.id + ':text', 'data/books/' + b.id + '/' + c.id + '.js');

function drawBook(id){
  const b = bookById(id);
  if (!b || b.lang !== langs.learn) { location.hash = 'library'; return; }
  const know = bookKnow(b);
  $('#bTitle').textContent = b.title[b.lang]; $('#bTitle').lang = b.lang;
  $('#bBlurb').innerHTML = esc(T(b.blurb, langs.know) + ' ' + b.author + (b.translator ? ', translated into French by ' + b.translator : '') + ', ' + b.year + '.')
    + (b.total > b.chapters.length ? ' <em>' + esc(unitText(b)) + ' so far, more coming.</em>' : '') + '<br>' + lvTag(b.level)
    + (know !== langs.know ? `<span class="swap">Sentences flip to ${esc(LN(know))}</span>` : '');
  const cont = b.chapters.find(c => { const p = chapterPct(b, c); return p > 0 && p < 100; }) || b.chapters.find(c => chapterPct(b, c) < 100) || b.chapters[0];
  $('#bGo').href = '#tale-' + b.id + '-' + cont.id;
  $('#bGo').textContent = (chapterPct(b, cont) > 0 ? 'Continue: ' : 'Start: ') + T(cont.title, b.lang);
  $('#chaps').innerHTML = b.chapters.map((c, i) => {
    const p = chapterPct(b, c);
    return `<li><a class="chap" href="#tale-${esc(b.id)}-${esc(c.id)}">
      <span class="cn">${i + 1}</span>
      <div class="einfo"><h3 lang="${esc(b.lang)}">${esc(T(c.title, b.lang))}</h3><p class="k">${esc(T(c.title, know))}</p>
      <p class="meta">${lvTag(c.level)}<span>about ${c.minutes} min</span><span>${p >= 100 ? 'Read' : p > 0 ? p + '% read' : 'New'}</span></p>
      <div class="prog"><i style="width:${p}%"></i></div></div></a></li>`;
  }).join('');
  $('#bFoot').innerHTML = `<p>Text: <a href="${esc(b.source)}">${esc(b.sourceName)}</a>. ${esc(b.license)}. ${esc(b.translations)} Levels are estimates: ${b.chapters.map(c => esc(T(c.title, 'en')) + ' (' + c.level + ', ' + esc(c.levelWhy) + ')').join('; ')}.</p>`;
}

let tale = null, taleObs = null, sentTap = null;
async function openTale(bookId, chapId){
  const b = bookById(bookId), c = b && b.chapters.find(x => x.id === chapId);
  if (!c || b.lang !== langs.learn) { location.hash = 'library'; return; }
  const know = bookKnow(b), token = ++openToken;
  closeBubble();
  $('#tBack').href = '#book-' + b.id;
  $('#tTitle').textContent = T(c.title, b.lang); $('#tTitle').lang = b.lang;
  $('#tHint').textContent = 'Tap any sentence you don\'t understand to see it in ' + LN(know) + '.';
  $('#tAll').checked = false; $('#text').classList.remove('all');
  $('#text').innerHTML = '<p class="loading"><span class="spin"></span>Opening…</p>'; $('#tEnd').innerHTML = '';
  let d;
  try { d = await chapterFile(b, c); } catch(e) { $('#text').innerHTML = '<p class="loading">This tale could not be loaded. Check your connection and try again.</p>'; return; }
  if (token !== openToken) return;
  tale = {b, c, know, d, flat: []};
  $('#text').innerHTML = `<h2 class="ttl" lang="${esc(b.lang)}">${esc(T(c.title, b.lang))}</h2>` + d.paras.map((p, pi) =>
    `<p class="${p.poem ? 'poem' : 'para'}" data-p="${pi}" lang="${esc(b.lang)}">${p.s.map(s => {
      const k = tale.flat.push(s) - 1;
      return `<span class="s" data-i="${k}" tabindex="0" role="button">${esc(s[b.lang])}</span><span class="tr" lang="${esc(know)}">${esc(s[know] || s.en)}</span>`;
    }).join(' ')}</p>`.replace('">', '">' + (p.who ? (() => { const k = tale.flat.push(p.who) - 1; return `<span class="s wl" data-i="${k}" tabindex="0" role="button">${esc(p.who[b.lang])}</span><span class="tr wlt">${esc(p.who[know] || p.who.en)}</span>`; })() : ''))).join('');
  const i = b.chapters.indexOf(c), next = b.chapters[i + 1];
  $('#tEnd').innerHTML = `<h2>The end</h2><dl><dt>Text</dt><dd><a href="${esc(b.source)}">${esc(b.sourceName)}</a> · ${esc(b.license)}</dd>
    <dt>Author</dt><dd>${esc(b.author)}, ${b.year}${b.translator ? ' · French translation by ' + esc(b.translator) : ''}</dd><dt>${esc(LN(know))}</dt><dd>${esc(b.translations)}</dd></dl>
    <div class="next"><a href="#book-${esc(b.id)}">Contents</a>${next ? `<a class="go" href="#tale-${esc(b.id)}-${esc(next.id)}">Next: ${esc(T(next.title, b.lang))}</a>` : ''}</div>`;
  const key = 'book:' + b.id + '/' + c.id, paras = d.paras.length;
  if (taleObs) taleObs.disconnect();
  taleObs = new IntersectionObserver(ents => {
    for (const en of ents) if (en.isIntersecting) {
      const pi = +en.target.dataset.p, pct = Math.round((pi + 1) / paras * 100), old = progress[key];
      if (!old || old.pct < pct) { progress[key] = {pct}; store.set('progress', progress); }
    }
  }, {threshold: 0.9});
  document.querySelectorAll('#text p[data-p]').forEach(p => taleObs.observe(p));
}

/* tapping a sentence opens a speech bubble with its translation, pointing at the sentence */
function openBubble(span){
  if (!tale) return;
  const s = tale.flat[+span.dataset.i], bub = $('#sbub');
  document.querySelectorAll('#text .s.on').forEach(x => x.classList.remove('on'));
  span.classList.add('on');
  $('#sbK').textContent = s[tale.know] || s.en; $('#sbK').lang = tale.know;
  const has = words.some(w => w.l === s[tale.b.lang]);
  $('#sbSave').textContent = has ? 'Saved' : 'Save'; $('#sbSave').disabled = has;
  sentTap = s;
  bub.hidden = false; bub.classList.remove('below');
  const r = span.getClientRects()[0] || span.getBoundingClientRect(), W = document.documentElement.clientWidth;
  const bw = Math.min(520, W - 24); bub.style.width = bw + 'px';
  const left = Math.max(12, Math.min(W - bw - 12, r.left + r.width / 2 - bw / 2));
  const bh = bub.offsetHeight, topBar = 130;
  let top = r.top - bh - 14;
  if (top < topBar) { top = r.bottom + 14; bub.classList.add('below'); }
  bub.style.left = (left + window.scrollX) + 'px';
  bub.style.top = (top + window.scrollY) + 'px';
  bub.style.setProperty('--tx', Math.max(18, Math.min(bw - 18, r.left + Math.min(r.width, 120) / 2 - left)) + 'px');
}
function closeBubble(){ $('#sbub').hidden = true; sentTap = null; document.querySelectorAll('#text .s.on').forEach(x => x.classList.remove('on')); }
$('#text').addEventListener('click', e => {
  const s = e.target.closest('.s');
  if (!s) { closeBubble(); return; }
  if (s.classList.contains('on')) closeBubble(); else openBubble(s);
});
$('#text').addEventListener('keydown', e => { const s = e.target.closest('.s'); if (s && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); openBubble(s); } });
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeBubble(); });
window.addEventListener('resize', () => { if (!$('#sbub').hidden) closeBubble(); });
$('#sbClose').addEventListener('click', closeBubble);
$('#sbSave').addEventListener('click', () => {
  if (!sentTap || !tale) return;
  words.unshift({l: sentTap[tale.b.lang], k: sentTap[tale.know] || sentTap.en, who: '', lang: tale.b.lang, klang: tale.know,
    src: tale.b.title[tale.b.lang] + ', ' + T(tale.c.title, tale.b.lang)});
  store.set('words', words); syncHeader();
  $('#sbSave').textContent = 'Saved'; $('#sbSave').disabled = true;
});
$('#tAll').addEventListener('change', e => { closeBubble(); $('#text').classList.toggle('all', e.target.checked); });

/* ---------- saved phrases ---------- */
function drawWords(){
  $('#wlist').innerHTML = words.length ? words.map((w, i) => `<li><div class="wt">
      <p class="pl" lang="${esc(w.lang)}">${esc(w.l)}</p>
      <p class="pk" lang="${esc(w.klang)}">${esc(w.k)}</p>
      <small>${w.who ? esc(w.who) + ' · ' : ''}${esc(w.src)}</small></div>
      <button class="icon ghost" data-del="${i}" aria-label="Remove">×</button></li>`).join('')
    : '<li class="empty" style="border:0;padding:0">Nothing saved yet. While reading, tap a bubble, then press Save.</li>';
}
$('#wlist').addEventListener('click', e => {
  const b = e.target.closest('[data-del]'); if (!b) return;
  words.splice(+b.dataset.del, 1); store.set('words', words); syncHeader(); drawWords();
});
$('#copyW').addEventListener('click', async () => {
  const txt = words.map(w => w.l + ' — ' + w.k).join('\n');
  try { await navigator.clipboard.writeText(txt); $('#copied').textContent = 'Copied'; }
  catch(e) { $('#copied').textContent = 'Your browser blocked copying'; }
});

/* ---------- routing ---------- */
function route(){
  const h = location.hash.slice(1);
  if (!langs || h === 'setup') { pick = langs ? {...langs} : pick; drawSetup(); views('setup'); return; }
  if (h.startsWith('read-')) { views('reader'); openEpisode(h.slice(5)); return; }
  if (h.startsWith('series-')) { drawSeries(h.slice(7)); views('series'); return; }
  if (h.startsWith('book-')) { drawBook(h.slice(5)); views('book'); return; }
  if (h.startsWith('tale-')) { const [bk, ch] = h.slice(5).split('-'); views('tale'); openTale(bk, ch); return; }
  if (h === 'words') { drawWords(); views('words'); return; }
  drawLibrary(); views('library');
}
window.addEventListener('hashchange', route);
syncHeader(); route();
}
