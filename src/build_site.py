"""Build the site (index.html, assets/site.css, assets/page.js) from src/dashboard.html,
the same page the Claude dashboard copy uses. Run from anywhere: python3 src/build_site.py"""
import re, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
src = (ROOT / 'src/dashboard.html').read_text()
css = re.search(r'<style>\n(.*?)</style>', src, re.S).group(1)
body = src[src.index('<div class="nz">'):src.index('<script>')].rstrip()
scripts = re.findall(r'<script>\n(.*?)</script>', src, re.S)
css = css.replace('--font-anthropic-sans', '--font-sans').replace('--font-anthropic-serif', '--font-serif')
LATIN = 'U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD'
LATEXT = 'U+0100-02AF,U+0304,U+0308,U+0329,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF'
faces = []
for fam, file, w in [('Source Sans 3', 'source-sans-3', 400), ('Source Sans 3', 'source-sans-3', 600), ('Source Serif 4', 'source-serif-4', 400)]:
    for sub, rng in [('latin', LATIN), ('latin-ext', LATEXT)]:
        faces.append(f'@font-face{{font-family:"{fam}";font-style:normal;font-weight:{w};font-display:swap;src:url(fonts/{file}-{sub}-{w}-normal.woff2) format("woff2");unicode-range:{rng}}}')
DARK = '''--color-bg:#121316;--color-panel:#1a1c20;--color-fg:#ebeae6;--color-fg-muted:#a1a4ad;--color-border-line:#2b2e34;--color-bad:#e5675a;
  --cds-chart-grid:#25282d;--cds-chart-axis:#5f636c;--cds-chart-reference:#7e828b;--cds-chart-muted:#4a4d55;
  --cds-surface-popover:#23262b;--cds-border:#363940;--cds-shadow-popover:0 6px 20px rgba(0,0,0,.5);--cds-text-secondary:#a1a4ad;
  --skel:#26292e;color-scheme:dark'''
base = '\n'.join(faces) + '''

:root{
  --font-sans:"Source Sans 3",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --font-serif:"Source Serif 4",Georgia,"Times New Roman",serif;
  --cds-font-size-caption:.8125rem;--cds-font-size-body:.9375rem;--cds-font-size-heading:1.125rem;--cds-font-size-title:1.75rem;
  --cds-font-weight-medium:600;
  --cds-gap-xs:4px;--cds-gap-sm:8px;--cds-gap-md:16px;--cds-gap-lg:24px;--cds-gap-xl:40px;
  --cds-pad-xs:4px;--cds-pad-sm:8px;--cds-pad-md:12px;--cds-pad-lg:20px;--cds-pad-xl:32px;
  --cds-radius:8px;--cds-dur-slow:.3s;
  --color-bg:#f5f4ef;--color-panel:#ffffff;--color-fg:#1b1d22;--color-fg-muted:#5c606c;--color-border-line:#e3e1d9;--color-bad:#c0392b;
  --cds-chart-grid:#ecebe4;--cds-chart-axis:#a3a5ad;--cds-chart-reference:#868a94;--cds-chart-muted:#cfcdc5;
  --cds-surface-popover:#ffffff;--cds-border:#dad8cf;--cds-shadow-popover:0 6px 20px rgba(20,22,30,.12);--cds-text-secondary:#5c606c;
  --skel:#e9e7e0;
  color-scheme:light;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){''' + DARK + '''}}
:root[data-theme="dark"]{''' + DARK + '''}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--color-bg);color:var(--color-fg);font-family:var(--font-sans);font-size:var(--cds-font-size-body);line-height:1.4;
  padding-block:max(24px,env(safe-area-inset-top,0px)) max(40px,env(safe-area-inset-bottom,0px));
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
@media (min-width:720px){body{padding-left:max(32px,env(safe-area-inset-left,0px));padding-right:max(32px,env(safe-area-inset-right,0px))}}
[hidden]{display:none!important}
img,svg{max-width:100%}
.dash-skeleton{color:transparent!important;background:var(--skel);border-radius:6px;animation:nz-pulse 1.4s ease-in-out infinite}
span.dash-skeleton,b.dash-skeleton{display:inline-block;min-width:2.6em;line-height:1}
p.nz-take.dash-skeleton{display:block;max-width:28em;height:1.45em}
.nz-chart.dash-skeleton{border-radius:var(--cds-radius)}
@keyframes nz-pulse{0%,100%{opacity:1}50%{opacity:.55}}
@media (prefers-reduced-motion:reduce){.dash-skeleton{animation:none}}
.nz-foot{font-size:var(--cds-font-size-caption);color:var(--color-fg-muted);line-height:1.5;max-width:74ch;padding-top:var(--cds-gap-sm);border-top:1px solid var(--color-border-line)}
.nz-foot a{color:inherit}
'''
phone = '''
@media (max-width:520px){
  .nz-tabs button{padding:var(--cds-pad-sm) 7px}
  .nz-card{padding:var(--cds-pad-lg) var(--cds-pad-md)}
}
@media (max-width:640px){
  .t-markets thead{display:none}
  .t-markets,.t-markets tbody,.t-markets tr{display:block;width:100%}
  .t-markets tr{padding:10px 0;border-bottom:1px solid var(--color-border-line)}
  .t-markets tbody tr:last-child{border-bottom:0}
  .t-markets td{display:grid;grid-template-columns:5.5rem minmax(0,1fr);gap:8px;border:0;padding:2px 0;white-space:normal;min-width:0!important;text-align:left!important}
  .t-markets td::before{color:var(--color-fg-muted)}
  .t-markets td:nth-child(1){display:block;font-weight:var(--cds-font-weight-medium);font-size:var(--cds-font-size-body);padding-bottom:4px}
  .t-markets td:nth-child(2)::before{content:"Where"}
  .t-markets td:nth-child(3)::before{content:"Reading"}
  .t-markets td:nth-child(4)::before{content:"Traded"}
  .t-markets td:nth-child(5)::before{content:"Counted"}
  .t-markets td:nth-child(6)::before{content:"Why"}
  .t-markets td:nth-child(7)::before{content:"Checked"}
}
'''
(ROOT / 'assets/site.css').write_text(base + '\n' + css + phone)
foot = '''
  <footer class="nz-foot">
    <p>Built by Claude for Cam Rodger from every published poll. The model re-runs each morning until election day. Not affiliated with any party, pollster or media outlet. Betting and prediction markets are shown on their own tab and never feed the forecast.</p>
  </footer>
</div>'''
assert body.endswith('</div>')
body = body[:-len('</div>')].rstrip() + '\n' + foot
html = '''<!doctype html>
<html lang="en-NZ">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>NZ Election Tracker 2026</title>
<meta name="description" content="Every 2026 New Zealand poll on one trend line with each pollster's lean taken out, simulated seats including overhangs, and the chance each side can form a government.">
<meta property="og:title" content="NZ Election Tracker 2026">
<meta property="og:description" content="Every poll on one trend line, each pollster's lean taken out, and the chance each side can form a government.">
<meta property="og:type" content="website">
<meta name="theme-color" content="#f5f4ef" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#121316" media="(prefers-color-scheme: dark)">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preload" href="assets/fonts/source-serif-4-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="assets/site.css">
</head>
<body>
''' + body + '''

<script src="assets/d3.min.js"></script>
<script src="assets/dash.js"></script>
<script src="assets/page.js"></script>
</body>
</html>
'''
(ROOT / 'index.html').write_text(html)
(ROOT / 'assets/page.js').write_text('\n'.join(s.rstrip() for s in scripts) + '\n')
print('built site', len(html))
