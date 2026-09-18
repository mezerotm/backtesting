#!/usr/bin/env python3
"""Post-process market report HTML: injects interpretation sidebar, badges, notes."""

import re, sys
from pathlib import Path

RULES = {
    "gdp": {"level": [(0.0, "\U0001f534", "Negative \u2014 recession"), (2.0, "\U0001f7e1", "Below trend \u2014 slowing"),
                       (3.0, "\U0001f7e2", "Healthy \u2014 Goldilocks"), (float("inf"), "\U0001f7e1", "Above trend")]},
    "inflation yoy": {"level": [(2.5, "\U0001f7e2", "At/near 2% target"), (3.0, "\U0001f7e1", "Slightly above"),
                                (float("inf"), "\U0001f534", "Above target \u2014 Fed constrained")]},
    "unemployment": {"level": [(4.0, "\U0001f7e2", "Low \u2014 tight labor"), (4.4, "\U0001f7e1", "Normal range"),
                               (float("inf"), "\U0001f534", "Elevated \u2014 recession risk")]},
}

def get_indicator(text):
    m = re.search(r'<div class="value-title">([^<]+)</div>', text)
    if not m: return None
    t = m.group(1).strip().lower()
    if 'gdp' in t: return 'gdp'
    if 'cpi' in t and 'inflation' not in t: return None  # Skip CPI - raw index level
    if 'inflation' in t: return 'inflation yoy'
    if 'unemployment' in t: return 'unemployment'
    return None

def extract_val(text):
    # Find the number in the font-bold value div specifically
    m = re.search(r'class="text-2xl font-bold mb-2">([\d.]+)', str(text))
    return float(m.group(1)) if m else None

def classify(v, rules):
    if not v or not rules: return ("--", "", "signal-yellow")
    for mx, sig, lbl in rules:
        if v < mx:
            css = {"\U0001f7e2": "signal-green", "\U0001f7e1": "signal-yellow", "\U0001f534": "signal-red"}.get(sig, "signal-yellow")
            return (sig, lbl, css)
    return ("\U0001f534", "Extreme", "signal-red")

SIDEBAR = """<div id="isidebar" class="fixed top-0 right-0 h-full w-80 bg-slate-900 border-l border-slate-700 shadow-2xl translate-x-full transition-transform duration-300 z-50 overflow-y-auto" style="display:none"><div class="p-4"><div class="flex justify-between items-center mb-4"><h3 class="text-lg font-bold text-white">Interpretation Guide</h3><button onclick="togS()" class="text-slate-400 hover:text-white text-xl">&times;</button></div>
<div class="space-y-3 text-sm">
<div class="bg-slate-800 p-3 rounded-lg"><h4 class="font-semibold text-blue-300 mb-2">Signal Legend</h4><div><span style="color:#4ade80">\U0001f7e2</span> Favorable</div><div><span style="color:#eab308">\U0001f7e1</span> Caution</div><div><span style="color:#f87171">\U0001f534</span> Warning</div></div>
<div class="bg-slate-800 p-3 rounded-lg"><h4 class="font-semibold text-blue-300 mb-2">How to Read</h4><ul class="ml-4 list-disc text-slate-300"><li><strong>1st derivative:</strong> going up or down?</li><li><strong>2nd derivative:</strong> accelerating or fading?</li><li><strong>Clusters:</strong> 2+ indicators same direction = thesis forming</li></ul></div>
<div class="bg-slate-800 p-3 rounded-lg"><h4 class="font-semibold text-blue-300 mb-2">Common Clusters</h4><div class="border-l-2 border-green-500 pl-2 my-1"><span style="color:#4ade80">\U0001f7e2 Risk-On</span><br><span class="text-xs">CPI falling + 10Y rolling + Dollar weak</span></div><div class="border-l-2 border-red-500 pl-2 my-1"><span style="color:#f87171">\U0001f534 Risk-Off</span><br><span class="text-xs">UE rising + Curve un-inverting + VIX high</span></div><div class="border-l-2 border-yellow-500 pl-2 my-1"><span style="color:#eab308">\U0001f7e1 Stagflation</span><br><span class="text-xs">Oil spiking + CPI sticky + GDP slowing</span></div></div>
<div class="bg-slate-800 p-3 rounded-lg"><h4 class="font-semibold text-blue-300 mb-2">Quick Rules</h4><ul class="text-slate-400 text-xs ml-4 list-disc"><li>Sahm: 3mo avg UE >0.5% above 12mo low = recession</li><li>10Y >5% = distress zone</li><li>Curve un-inverting = recession typically follows</li><li>Oil >$100 = supply shock, sticky CPI</li><li>VIX >30 = panic, often near bottoms</li></ul></div>
</div></div></div>
<style>
.signal-badge{display:inline-block;font-size:.7rem;padding:1px 6px;border-radius:4px;margin-left:6px;font-weight:600}
.signal-green{background:rgba(74,222,128,0.15);color:#4ade80;border:1px solid rgba(74,222,128,0.3)}
.signal-yellow{background:rgba(234,179,8,0.15);color:#eab308;border:1px solid rgba(234,179,8,0.3)}
.signal-red{background:rgba(248,113,113,0.15);color:#f87171;border:1px solid rgba(248,113,113,0.3)}
.card-green{border-left:3px solid #4ade80!important}.card-yellow{border-left:3px solid #eab308!important}.card-red{border-left:3px solid #f87171!important}
.itog{cursor:pointer;color:#60a5fa;font-size:.8rem;margin-top:6px;display:inline-block}.itog:hover{color:#93c5fd}
.icont{font-size:.78rem;color:#94a3b8;margin-top:4px;padding:6px 8px;background:rgba(15,23,42,0.5);border-radius:4px;display:none}
.icont.show{display:block}
#sbtn{position:fixed;top:80px;right:0;z-index:40;background:#1e293b;border:1px solid #334155;border-right:none;border-radius:8px 0 0 8px;padding:10px 6px;cursor:pointer;color:#94a3b8;font-size:.75rem;writing-mode:vertical-lr;text-orientation:mixed}
#sbtn:hover{background:#334155;color:#60a5fa}
</style>
<script>
function togS(){var s=document.getElementById('isidebar'),b=document.getElementById('sbtn');if(s.style.display==='none'){s.style.display='block';setTimeout(function(){s.style.transform='translateX(0)'},10);b.style.display='none'}else{s.style.transform='translateX(100%)';setTimeout(function(){s.style.display='none';b.style.display='block'},300)}}
document.addEventListener('click',function(e){var t=e.target.closest('.itog');if(t){var c=t.nextElementSibling;if(c)c.classList.toggle('show')}});
</script>"""

def enhance(path):
    html = Path(path).read_text("utf-8")
    # Only inject sidebar once
    if 'id="isidebar"' not in html:
        html = html.replace("</body>", f"\n{SIDEBAR}\n<button id=\"sbtn\" onclick=\"togS()\">Guide</button>\n</body>")
    else:
        # Remove any old duplicate buttons/injections from prior runs
        # Count existing sidebars
        import re as re2
        side_count = len(re2.findall(r'id="isidebar"', html))
        if side_count > 1:
            # Strip duplicates - keep the first one
            parts = html.split('<div id="isidebar"')
            html = parts[0] + '<div id="isidebar"' + '<div id="isidebar"'.join(parts[2:])
        btn_count = len(re2.findall(r'id="sbtn"', html))
        if btn_count > 1:
            parts = html.split('<button id="sbtn"')
            html = parts[0] + '<button id="sbtn"' + '<button id="sbtn"'.join(parts[2:])

    
    # Process economic indicator cards
    out = []
    buf = []
    in_card = False
    in_style = False
    for line in html.split("\n"):
        if "<style" in line.lower() and "</style>" not in line: in_style = True
        if "</style>" in line: in_style = False
        
        if not in_style and 'class="value-card"' in line and 'value-card {' not in line:
            in_card = True; buf = [line]; continue
        if in_card:
            buf.append(line)
            if line.strip() == "</div>" and len(buf) > 3:
                card = "\n".join(buf)
                ind = get_indicator(card)
                if ind:
                    rules = RULES[ind]
                    val = extract_val(card)
                    if val and rules["level"]:
                        sig, lbl, css = classify(val, rules["level"])
                        badge = f'<span class="signal-badge {css}">{sig} {lbl}</span>'
                        card = re.sub(r'(<div class="text-2xl font-bold mb-2">[^<]+</div>)',
                                      lambda m: m.group(0).rstrip("</div>") + f" {badge}</div>", card)
                        bc = {"\U0001f7e2":"card-green","\U0001f7e1":"card-yellow","\U0001f534":"card-red"}.get(sig,"")
                        if bc: card = card.replace('class="value-card"', f'class="value-card {bc}"', 1)
                        interp = f'<div class="itog"><i class="fa-solid fa-circle-info"></i> What this means</div><div class="icont">Level: {sig} {lbl}</div>'
                        parts = card.split('<div class="text-xs text-slate-500 mt-2">', 1)
                        if len(parts) > 1:
                            card = parts[0] + interp + '\n                <div class="text-xs text-slate-500 mt-2">' + parts[1]
                out.append(card); in_card = False; buf = []
                continue
        if not in_card: out.append(line)
    
    Path(path).write_text("\n".join(out), "utf-8")
    print(f"Enhanced: {path}")

if __name__ == "__main__":
    if len(sys.argv) < 2: print("Usage: python3 enhance_market_report.py <path>"); sys.exit(1)
    enhance(sys.argv[1])
