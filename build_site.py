#!/usr/bin/env python3
"""
Build static GitHub Pages site from knowledge base JSON data.

Usage:
    python3 build_site.py              # build docs/index.html
    python3 build_site.py --open       # build and open in browser
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"


def load_opportunities() -> list[dict]:
    """Load all opportunity JSON files."""
    opps = []
    for f in sorted(glob.glob(str(ROOT / "opportunities" / "*.json")), reverse=True):
        try:
            data = json.loads(Path(f).read_text("utf-8"))
            data["_file"] = Path(f).name
            opps.append(data)
        except (json.JSONDecodeError, OSError):
            pass
    return opps


def load_signals() -> list[dict]:
    """Load all signal archive files."""
    sigs = []
    for f in sorted(glob.glob(str(ROOT / "signals" / "*" / "*.json")), reverse=True):
        try:
            data = json.loads(Path(f).read_text("utf-8"))
            data["_file"] = "/".join(Path(f).parts[-2:])
            sigs.append(data)
        except (json.JSONDecodeError, OSError):
            pass
    return sigs


def load_niches() -> list[dict]:
    """Load niche evaluation files."""
    niches = []
    for f in sorted(glob.glob(str(ROOT / "niches" / "*.json")), reverse=True):
        try:
            data = json.loads(Path(f).read_text("utf-8"))
            niches.append(data)
        except (json.JSONDecodeError, OSError):
            pass
    return niches


def load_sites() -> list[dict]:
    """Load deployed site tracking files."""
    sites = []
    for f in sorted(glob.glob(str(ROOT / "sites" / "*.json")), reverse=True):
        try:
            data = json.loads(Path(f).read_text("utf-8"))
            sites.append(data)
        except (json.JSONDecodeError, OSError):
            pass
    return sites


def _esc(s):
    if not s:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def build_opportunity_cards(opps: list[dict]) -> str:
    """Generate HTML for opportunity cards."""
    if not opps:
        return '<div class="empty">暂无机会数据。运行 <code>挖需求</code> 开始发现机会。</div>'

    html = ""
    for opp in opps:
        slug = _esc(opp.get("slug", ""))
        date = _esc(opp.get("discovered_at", ""))
        verdict = opp.get("verdict", "?")
        signal = opp.get("signal", {})
        validation = opp.get("validation", {})
        action = opp.get("action", {})

        verdict_class = {
            "GO": "go", "CAUTIOUS": "watch", "RISKY": "risky", "PASS": "pass"
        }.get(verdict, "")
        verdict_icon = {
            "GO": "🟢", "CAUTIOUS": "🟡", "RISKY": "🟠", "PASS": "🔴"
        }.get(verdict, "❓")

        # Top keywords
        kw_rows = ""
        for kw in validation.get("top_keywords", [])[:5]:
            keyword = _esc(kw.get("keyword", ""))
            kd = kw.get("kd", "—")
            vol = kw.get("volume", "—")
            cpc = kw.get("cpc", "—")
            kd_display = f"{kd}" if kd is not None else "—"
            vol_display = f"{vol:,}" if isinstance(vol, (int, float)) and vol is not None else "—"
            cpc_display = f"${cpc}" if cpc and cpc != "—" else "—"
            kw_rows += f'<tr><td class="kw">{keyword}</td><td>{kd_display}</td><td>{vol_display}</td><td>{cpc_display}</td></tr>\n'

        platforms = ", ".join(signal.get("platforms", []))
        demand_type = _esc(signal.get("demand_type", ""))
        evidence = _esc(signal.get("evidence", ""))
        site_type = _esc(action.get("site_type", ""))
        content_plan = _esc(action.get("content_plan", ""))
        monetization = _esc(action.get("monetization", ""))

        html += f'''
        <div class="card {verdict_class}">
          <div class="card-header">
            <span class="verdict-badge {verdict_class}">{verdict_icon} {verdict}</span>
            <span class="slug">{slug}</span>
            <span class="date">{date}</span>
          </div>
          <div class="card-title">{_esc(signal.get("topic_title", slug))}</div>
          <div class="card-meta">
            <span class="tag">{demand_type}</span>
            <span class="tag">{site_type}</span>
            <span class="platforms">{platforms}</span>
          </div>
          {f'<div class="evidence">{evidence}</div>' if evidence else ''}
          {f'<table class="kw-table"><thead><tr><th>Keyword</th><th>KD</th><th>Vol</th><th>CPC</th></tr></thead><tbody>{kw_rows}</tbody></table>' if kw_rows else ''}
          {f'<div class="plan"><strong>内容计划:</strong> {content_plan}</div>' if content_plan else ''}
          {f'<div class="plan"><strong>变现:</strong> {monetization}</div>' if monetization else ''}
        </div>'''

    return html


def build_signal_summary(signals: list[dict]) -> str:
    """Generate HTML for signal history."""
    if not signals:
        return '<div class="empty">暂无信号数据。</div>'

    html = ""
    for sig in signals:
        date = _esc(sig.get("date", ""))
        results = sig.get("results", {})
        go_count = results.get("go", 0)
        watch_count = results.get("watch", 0)
        pass_count = results.get("pass", 0)
        total = sig.get("total_scanned", go_count + watch_count + pass_count)

        go_items = ""
        for item in sig.get("go", []):
            go_items += f'<div class="sig-item go">🟢 <strong>{_esc(item.get("keyword",""))}</strong> KD:{item.get("kd","?")} Vol:{item.get("volume","?")} — {_esc(item.get("reason",""))}</div>'

        watch_items = ""
        for item in sig.get("watch", []):
            watch_items += f'<div class="sig-item watch">🟡 <strong>{_esc(item.get("keyword",""))}</strong> KD:{item.get("kd","?")} Vol:{item.get("volume","?")} — {_esc(item.get("reason",""))}</div>'

        html += f'''
        <div class="signal-day">
          <div class="signal-header">
            <span class="signal-date">{date}</span>
            <span class="signal-stats">
              扫描 {total} · <span class="go-text">{go_count} GO</span> · <span class="watch-text">{watch_count} WATCH</span> · {pass_count} PASS
            </span>
          </div>
          {go_items}{watch_items}
        </div>'''

    return html


def build_html(opps, signals, niches, sites) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    opp_html = build_opportunity_cards(opps)
    sig_html = build_signal_summary(signals)

    total_opps = len(opps)
    go_count = sum(1 for o in opps if o.get("verdict") == "GO")
    total_signals = sum(s.get("total_scanned", 0) for s in signals)

    return f'''<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SEO Knowledge Base</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",system-ui,sans-serif;
  background:#0a0a0a; color:#e0e0e0; -webkit-font-smoothing:antialiased; }}
.container {{ max-width:900px; margin:0 auto; padding:20px 16px; }}

/* Header */
.header {{ text-align:center; padding:40px 0 30px; border-bottom:1px solid #1a1a1a; margin-bottom:30px; }}
.header h1 {{ font-size:24px; font-weight:700; color:#fff; letter-spacing:-.3px; }}
.header p {{ color:#555; font-size:13px; margin-top:6px; }}
.stats {{ display:flex; justify-content:center; gap:10px; margin-top:14px; }}
.stats .stat {{ font-size:12px; color:#666; background:#111; padding:4px 12px; border-radius:16px; border:1px solid #1a1a1a; }}
.stats .stat strong {{ color:#aaa; }}

/* Section */
section {{ margin-bottom:40px; }}
section h2 {{ font-size:16px; font-weight:600; color:#888; margin-bottom:16px;
  display:flex; align-items:center; gap:8px; }}
section h2 .dot {{ width:6px; height:6px; border-radius:50%; }}

/* Cards */
.card {{ background:#0d0d0d; border:1px solid #1a1a1a; border-radius:12px;
  padding:16px 18px; margin-bottom:12px; transition:border-color .15s; }}
.card:hover {{ border-color:#2a2a2a; }}
.card.go {{ border-left:3px solid #22c55e; }}
.card.watch {{ border-left:3px solid #eab308; }}
.card.risky {{ border-left:3px solid #f97316; }}
.card.pass {{ border-left:3px solid #ef4444; }}

.card-header {{ display:flex; align-items:center; gap:8px; margin-bottom:8px; }}
.verdict-badge {{ font-size:11px; padding:2px 8px; border-radius:4px; font-weight:600; }}
.verdict-badge.go {{ background:#052e16; color:#4ade80; }}
.verdict-badge.watch {{ background:#2a1f00; color:#facc15; }}
.verdict-badge.pass {{ background:#2a0000; color:#f87171; }}
.slug {{ font-size:12px; color:#666; font-family:monospace; }}
.date {{ font-size:11px; color:#444; margin-left:auto; }}

.card-title {{ font-size:16px; font-weight:600; color:#eee; line-height:1.4; margin-bottom:8px; }}
.card-meta {{ display:flex; gap:6px; flex-wrap:wrap; margin-bottom:10px; }}
.tag {{ font-size:10px; padding:2px 8px; border-radius:10px; background:#1a1a1a; color:#888; border:1px solid #252525; }}
.platforms {{ font-size:11px; color:#555; }}
.evidence {{ font-size:13px; color:#777; margin-bottom:10px; line-height:1.5; }}

/* Keyword table */
.kw-table {{ width:100%; font-size:12px; border-collapse:collapse; margin:8px 0; }}
.kw-table th {{ text-align:left; color:#555; font-weight:500; padding:4px 8px; border-bottom:1px solid #1a1a1a; }}
.kw-table td {{ padding:4px 8px; color:#aaa; border-bottom:1px solid #111; }}
.kw-table td.kw {{ color:#ddd; font-family:monospace; font-size:12px; }}
.kw-table tr:last-child td {{ border-bottom:none; }}

.plan {{ font-size:12px; color:#666; margin-top:6px; line-height:1.5; }}
.plan strong {{ color:#888; }}

/* Signals */
.signal-day {{ background:#0d0d0d; border:1px solid #1a1a1a; border-radius:10px;
  padding:14px 16px; margin-bottom:10px; }}
.signal-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }}
.signal-date {{ font-size:14px; font-weight:600; color:#ccc; }}
.signal-stats {{ font-size:12px; color:#555; }}
.go-text {{ color:#4ade80; }}
.watch-text {{ color:#facc15; }}
.sig-item {{ font-size:12px; color:#888; padding:3px 0; line-height:1.5; }}
.sig-item strong {{ color:#ccc; font-family:monospace; }}

/* Empty */
.empty {{ text-align:center; color:#444; padding:30px; font-size:13px; }}
.empty code {{ background:#1a1a1a; padding:2px 6px; border-radius:4px; color:#888; }}

/* Footer */
.footer {{ text-align:center; padding:20px 0; margin-top:20px; border-top:1px solid #111; }}
.footer p {{ font-size:10px; color:#333; }}

/* Pipeline */
.pipeline {{ display:flex; align-items:center; justify-content:center; gap:6px;
  margin:20px 0 30px; flex-wrap:wrap; }}
.pipeline .step {{ font-size:11px; color:#555; background:#111; padding:4px 10px;
  border-radius:6px; border:1px solid #1a1a1a; }}
.pipeline .arrow {{ color:#333; font-size:12px; }}

@media(max-width:640px) {{
  .container {{ padding:12px 10px; }}
  .card {{ padding:12px 14px; }}
  .card-title {{ font-size:14px; }}
  .stats {{ flex-wrap:wrap; }}
}}
</style>
</head><body>
<div class="container">

<div class="header">
  <h1>SEO Knowledge Base</h1>
  <p>需求挖掘 → 机会验证 → 建站 → 反馈闭环</p>
  <div class="stats">
    <span class="stat">🎯 <strong>{go_count}</strong> GO</span>
    <span class="stat">📊 <strong>{total_opps}</strong> 机会</span>
    <span class="stat">📡 <strong>{total_signals}</strong> 信号扫描</span>
    <span class="stat">🕐 {now}</span>
  </div>
</div>

<div class="pipeline">
  <span class="step">📡 RSS/Reddit/HN</span>
  <span class="arrow">→</span>
  <span class="step">🔍 信号提取</span>
  <span class="arrow">→</span>
  <span class="step">⚡ 5问过滤</span>
  <span class="arrow">→</span>
  <span class="step">📊 SEMrush验证</span>
  <span class="arrow">→</span>
  <span class="step">✅ GO / ❌ PASS</span>
  <span class="arrow">→</span>
  <span class="step">🚀 建站</span>
</div>

<section>
  <h2><span class="dot" style="background:#22c55e"></span>机会 Opportunities</h2>
  {opp_html}
</section>

<section>
  <h2><span class="dot" style="background:#3b82f6"></span>信号日志 Signal Log</h2>
  {sig_html}
</section>

<div class="footer">
  <p>seo-knowledge · auto-generated by build_site.py</p>
</div>

</div>
</body></html>'''


def main():
    parser = argparse.ArgumentParser(description="Build GitHub Pages site")
    parser.add_argument("--open", action="store_true", help="Open in browser after build")
    args = parser.parse_args()

    opps = load_opportunities()
    signals = load_signals()
    niches = load_niches()
    sites = load_sites()

    DOCS.mkdir(exist_ok=True)
    html = build_html(opps, signals, niches, sites)
    out = DOCS / "index.html"
    out.write_text(html, "utf-8")

    print(f"Built: {out}")
    print(f"  Opportunities: {len(opps)}")
    print(f"  Signals: {len(signals)}")
    print(f"  Niches: {len(niches)}")
    print(f"  Sites: {len(sites)}")

    if args.open:
        subprocess.run(["open", str(out)])


if __name__ == "__main__":
    main()
