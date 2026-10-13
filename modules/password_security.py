"""Build the offline browser-only password checker component.

The password input and analysis remain in this local iframe. The value is never
sent to Streamlit/Python, session state, logs, or persistent storage.
"""
from pathlib import Path

ANALYZER_PATH = Path(__file__).with_name("password_analyzer.js")

def build_password_checker_html():
    analyzer = ANALYZER_PATH.read_text(encoding="utf-8")
    script = """
    const password = document.getElementById('password');
    const compare = document.getElementById('compare');
    const result = document.getElementById('result');
    const meter = document.getElementById('meter');
    const reset = document.getElementById('reset');
    const visibility = document.getElementById('visibility');
    const colors = {'Very Weak':'#ef5350','Weak':'#ff8a3d','Fair':'#ffc247','Strong':'#45a4ff','Very Strong':'#3bd39e'};
    function render() {
      const value = password.value;
      if (!value) {
        result.innerHTML = '<div class="empty">Enter a password to see its analysis. Nothing is sent to the app server.</div>';
      meter.style.width = '0%'; meter.style.background = '#30434d';
        password.setAttribute('aria-describedby','privacy'); return;
      }
      const report = window.SnakbitePasswordAnalyzer.analyzePassword(value, compare.value);
      const color = colors[report.classification];
      meter.style.width = report.score + '%'; meter.style.background = color;
      const patterns = report.patterns.length ? report.patterns.map(p => '<li><b>'+escapeHtml(p.label)+'</b><span>'+escapeHtml(p.reason)+'</span></li>').join('') : '<li class="good"><b>No listed weak patterns found</b><span>This is an educational local check, not a breach-database lookup.</span></li>';
      const checks = report.checks.map(c => '<li><span class="mark '+(c.ok?'yes':'no')+'">'+(c.ok?'✓':'•')+'</span><span><b>'+escapeHtml(c.label)+'</b><small>'+escapeHtml(c.detail)+'</small></span></li>').join('');
      const tips = report.recommendations.map(t => '<li>'+escapeHtml(t)+'</li>').join('');
      result.innerHTML = '<div class="score-row"><div><div class="eyebrow">EDUCATIONAL STRENGTH ESTIMATE</div><div class="grade" style="color:'+color+'">'+report.classification+'</div></div><div class="score"><strong>'+report.score+'</strong><small>/ 100</small></div></div>'+
        '<div class="stats"><span><b>'+report.length+'</b> characters</span><span><b>'+report.groups+'</b> character groups</span><span><b>≤ '+report.entropy+' bits</b> theoretical entropy*</span></div>'+
        '<div class="grid"><section><h3>Password checklist</h3><ul class="checks">'+checks+'</ul></section><section><h3>Weakness analysis</h3><ul class="findings">'+patterns+'</ul></section></div>'+
        '<section class="tips"><h3>Improvement suggestions</h3><ul>'+tips+'</ul></section>'+
        '<div class="note">*Entropy is an upper-bound estimate assuming a uniformly random choice from the observed character groups. Real guessing risk depends on how the password was created, attacker strategy, hashing, and other context. Categories are educational estimates, not certification.</div>';
      password.setAttribute('aria-describedby','privacy');
    }
    function escapeHtml(text) { return String(text).replace(/[&<>\"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[ch])); }
    password.addEventListener('input', render); compare.addEventListener('input', render);
    visibility.addEventListener('click', () => { const show = password.type === 'password'; password.type = show ? 'text' : 'password'; visibility.textContent = show ? 'Hide' : 'Show'; visibility.setAttribute('aria-pressed', String(show)); password.focus(); });
    reset.addEventListener('click', () => { password.value = ''; compare.value = ''; password.type = 'password'; visibility.textContent = 'Show'; visibility.setAttribute('aria-pressed','false'); render(); password.focus(); });
    render();
    """
    html = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box}body{margin:0;background:transparent;color:#e4edf1;font-family:Segoe UI,Arial,sans-serif}.wrap{background:linear-gradient(145deg,#10212a,#0b1821);border:1px solid #20343d;border-radius:16px;padding:20px 22px}.eyebrow{font-size:11px;letter-spacing:.15em;color:#42d3a2;font-weight:800}.title{font-size:21px;font-weight:800;margin:6px 0}.copy{color:#96aab3;font-size:13px;line-height:1.5}.field-label{display:block;font-weight:700;font-size:13px;margin:14px 0 7px}.entry{display:flex;gap:8px}.entry input,.compare{min-width:0;width:100%;border:1px solid #30444e;border-radius:9px;background:#08141b;color:#eff8f6;padding:11px 12px;font-size:15px;outline:none}.entry input:focus,.compare:focus{border-color:#3bd39e;box-shadow:0 0 0 2px #3bd39e24}.entry button,.reset{border-radius:9px;border:1px solid #30444e;background:#142832;color:#e8f4f2;padding:0 15px;font-weight:700;cursor:pointer}.entry button:hover,.reset:hover{border-color:#3bd39e}.privacy{margin-top:12px;padding:10px 12px;border:1px solid #2b514b;background:#102a26;border-radius:9px;color:#bdebd7;font-size:12px;line-height:1.45}.meter-track{height:8px;background:#20343d;border-radius:20px;overflow:hidden;margin:14px 0 10px}.meter-track>div{height:100%;border-radius:20px;transition:width .18s,background .18s}.score-row{display:flex;align-items:end;justify-content:space-between;margin-top:18px}.grade{font-size:23px;font-weight:800;margin-top:3px}.score{display:flex;align-items:baseline;gap:3px}.score strong{font-size:27px}.score small,.stats,.empty{color:#91a6af}.stats{display:flex;gap:20px;flex-wrap:wrap;font-size:12px;padding-bottom:8px}.stats b{color:#eaf4f3}.grid{display:grid;grid-template-columns:1fr 1fr;gap:13px;margin-top:10px}.grid section,.tips{background:#0b1820;border:1px solid #20343d;border-radius:11px;padding:13px 14px}h3{font-size:14px;margin:0 0 10px}.checks,.findings,.tips ul{padding:0;margin:0;list-style:none}.checks li{display:flex;gap:9px;align-items:flex-start;padding:6px 0;border-bottom:1px solid #1b2b33;font-size:12px}.checks li:last-child{border:0}.mark{font-size:15px;width:16px}.yes{color:#3bd39e}.no{color:#ffb84c}.checks small{display:block;color:#8fa4ad;margin-top:2px}.findings li{padding:7px 0;border-bottom:1px solid #1b2b33;font-size:12px;color:#ffca81}.findings li:last-child{border:0}.findings li span{display:block;color:#93a8b0;margin-top:3px;line-height:1.4}.findings .good{color:#63dfad}.tips{margin-top:12px}.tips li{font-size:12px;color:#bfd1d6;padding:4px 0 4px 15px;position:relative}.tips li:before{content:'→';position:absolute;left:0;color:#42d3a2}.note{margin:11px 2px 0;color:#8299a3;font-size:11px;line-height:1.5}.empty{padding:25px 8px;text-align:center;border:1px dashed #2b404a;border-radius:10px;margin-top:16px}.reset-row{display:flex;justify-content:flex-end;margin-top:8px}.reset{min-height:36px}.comparison-copy{font-size:11px!important;margin-top:5px}@media(max-width:650px){.wrap{padding:16px 13px}.grid{grid-template-columns:1fr}.stats{gap:10px}.entry input{font-size:14px}}
</style></head><body><main class="wrap"><div class="eyebrow">LOCAL · PRIVATE · EDUCATIONAL</div><div class="title">Password strength analysis</div><div class="copy">Type to see a live estimate and the patterns that affect it. Analysis runs in this page's local browser component.</div>
<label class="field-label" for="password">Password</label><div class="entry"><input id="password" type="password" autocomplete="off" autocapitalize="off" spellcheck="false" aria-label="Password to analyze"><button id="visibility" type="button" aria-pressed="false">Show</button></div>
<label class="field-label" for="compare">Optional comparison value</label><input class="compare" id="compare" type="text" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="A username or name fragment you choose"><div class="copy comparison-copy">Only checked in this browser component; it is not retained or sent to the app.</div>
<div class="privacy" id="privacy">Privacy: the password and optional comparison stay in this browser component. They are not sent to Python, external services, analytics, logs, SQLite, CSV, or browser storage. Only enter a password if you trust this computer and the app source.</div><div class="meter-track"><div id="meter"></div></div><div id="result" aria-live="polite"></div><div class="reset-row"><button id="reset" class="reset" type="button">Reset / clear</button></div></main><script>__ANALYZER__
__UI_SCRIPT__</script></body></html>"""
    return html.replace("__ANALYZER__", analyzer).replace("__UI_SCRIPT__", script)
