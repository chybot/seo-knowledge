#!/usr/bin/env python3
"""
Build static GitHub Pages site from knowledge base JSON data.

Generates:
  docs/index.html                           — dashboard
  docs/signals/2026-03-14.html              — daily signal detail (all 30 topics)
  docs/opportunities/run-ai-locally.html    — opportunity detail page

Usage:
    python3 build_site.py              # build all pages
    python3 build_site.py --open       # build and open in browser
"""
from __future__ import annotations

import argparse
import glob
import json
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"

CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",system-ui,sans-serif;
  background:#0a0a0a; color:#e0e0e0; -webkit-font-smoothing:antialiased; }
a { color:#60a5fa; text-decoration:none; } a:hover { text-decoration:underline; }
.container { max-width:940px; margin:0 auto; padding:20px 16px; }
.header { text-align:center; padding:40px 0 24px; border-bottom:1px solid #1a1a1a; margin-bottom:28px; }
.header h1 { font-size:24px; font-weight:700; color:#fff; letter-spacing:-.3px; }
.header p { color:#555; font-size:13px; margin-top:6px; }
.breadcrumb { font-size:12px; color:#555; margin-bottom:20px; }
.breadcrumb a { color:#666; }
.stats { display:flex; justify-content:center; gap:10px; margin-top:14px; flex-wrap:wrap; }
.stat { font-size:12px; color:#666; background:#111; padding:4px 12px; border-radius:16px; border:1px solid #1a1a1a; }
.stat strong { color:#aaa; }
.pipeline { display:flex; align-items:center; justify-content:center; gap:6px; margin:20px 0 30px; flex-wrap:wrap; }
.pipeline .step { font-size:11px; color:#555; background:#111; padding:4px 10px; border-radius:6px; border:1px solid #1a1a1a; }
.pipeline .arrow { color:#333; font-size:12px; }
section { margin-bottom:36px; }
section h2 { font-size:16px; font-weight:600; color:#888; margin-bottom:14px; display:flex; align-items:center; gap:8px; }
section h2 .dot { width:6px; height:6px; border-radius:50%; }
section h3 { font-size:14px; color:#aaa; margin:18px 0 10px; }

/* Cards */
.card { background:#0d0d0d; border:1px solid #1a1a1a; border-radius:12px;
  padding:16px 18px; margin-bottom:10px; transition:border-color .15s; cursor:pointer; display:block; text-decoration:none !important; color:inherit; }
.card:hover { border-color:#333; }
.card.go { border-left:3px solid #22c55e; }
.card.watch { border-left:3px solid #eab308; }
.card.pass { border-left:3px solid #555; }
.card-header { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
.badge { font-size:10px; padding:2px 8px; border-radius:4px; font-weight:600; }
.badge.go { background:#052e16; color:#4ade80; }
.badge.watch { background:#2a1f00; color:#facc15; }
.badge.pass { background:#1a1a1a; color:#666; }
.slug { font-size:12px; color:#555; font-family:monospace; }
.date { font-size:11px; color:#444; margin-left:auto; }
.card-title { font-size:15px; font-weight:600; color:#eee; line-height:1.4; margin-bottom:6px; }
.card-meta { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px; }
.tag { font-size:10px; padding:2px 8px; border-radius:10px; background:#1a1a1a; color:#888; border:1px solid #252525; }
.card-detail { font-size:12px; color:#666; line-height:1.6; }
.card-kw { font-size:12px; color:#777; margin-top:6px; }
.card-kw code { background:#111; padding:1px 5px; border-radius:3px; color:#aaa; font-size:11px; }
.card-arrow { float:right; color:#333; font-size:14px; margin-top:4px; }

/* Tables */
.kw-table { width:100%; font-size:12px; border-collapse:collapse; margin:10px 0; }
.kw-table th { text-align:left; color:#555; font-weight:500; padding:6px 10px; border-bottom:1px solid #1a1a1a; }
.kw-table td { padding:6px 10px; color:#aaa; border-bottom:1px solid #111; }
.kw-table td.kw { color:#ddd; font-family:monospace; }
.kw-table tr:last-child td { border-bottom:none; }
.kw-table td.good { color:#4ade80; }
.kw-table td.warn { color:#facc15; }
.kw-table td.bad { color:#f87171; }

/* Filter checklist */
.filter-list { list-style:none; margin:10px 0; }
.filter-list li { font-size:13px; color:#888; padding:6px 10px; border-bottom:1px solid #111; line-height:1.5; }
.filter-list li:last-child { border:none; }
.filter-list .pass-icon { color:#4ade80; }
.filter-list .fail-icon { color:#f87171; }
.filter-list .warn-icon { color:#facc15; }

/* Suggest cloud */
.suggest-cloud { display:flex; flex-wrap:wrap; gap:5px; margin:10px 0; }
.suggest-cloud span { font-size:11px; padding:3px 8px; background:#111; border:1px solid #1a1a1a;
  border-radius:6px; color:#888; }

/* Trend sparkline (simple CSS bars) */
.trend-bars { display:flex; align-items:flex-end; gap:2px; height:30px; margin:4px 0; }
.trend-bars .bar { width:8px; background:#333; border-radius:1px; min-height:2px; }

/* Signal list on daily page */
.sig-row { display:flex; align-items:center; gap:10px; padding:8px 12px;
  border-bottom:1px solid #111; font-size:13px; }
.sig-row:last-child { border:none; }
.sig-row .sig-rank { color:#444; font-size:11px; min-width:24px; }
.sig-row .sig-verdict { min-width:50px; }
.sig-row .sig-title { flex:1; color:#bbb; }
.sig-row .sig-source { color:#555; font-size:11px; min-width:80px; }
.sig-row .sig-reason { color:#555; font-size:11px; flex:1; max-width:300px; }
.sig-row.is-go .sig-title { color:#4ade80; font-weight:600; }
.sig-row.is-watch .sig-title { color:#facc15; }
.sig-row a { color:inherit; text-decoration:none; }
.sig-row a:hover .sig-title { color:#fff; }

/* Detail blocks */
.detail-block { background:#0d0d0d; border:1px solid #1a1a1a; border-radius:10px; padding:16px; margin-bottom:14px; }
.detail-block h4 { font-size:13px; color:#666; margin-bottom:10px; text-transform:uppercase; letter-spacing:.5px; }
.detail-text { font-size:13px; color:#999; line-height:1.7; }
.detail-text strong { color:#ccc; }
.next-steps { list-style:none; }
.next-steps li { font-size:13px; color:#888; padding:4px 0; }
.next-steps li::before { content:"→ "; color:#444; }

.empty { text-align:center; color:#444; padding:30px; font-size:13px; }
.empty code { background:#1a1a1a; padding:2px 6px; border-radius:4px; color:#888; }
.footer { text-align:center; padding:20px 0; margin-top:20px; border-top:1px solid #111; }
.footer p { font-size:10px; color:#333; }
@media(max-width:640px) { .container { padding:12px 10px; } .card { padding:12px 14px; } }
"""


def _esc(s):
    if not s: return ""
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")


def _trend_bars(trend):
    if not trend: return ""
    mx = max(trend) or 1
    bars = "".join(f'<div class="bar" style="height:{max(2, int(v/mx*28))}px"></div>' for v in trend)
    return f'<div class="trend-bars">{bars}</div>'


def _kd_class(kd):
    if kd is None: return ""
    if kd <= 25: return "good"
    if kd <= 40: return "warn"
    return "bad"


def _vol_class(vol):
    if vol is None: return ""
    if vol >= 200: return "good"
    if vol >= 50: return "warn"
    return "bad"


def _page(title, body, breadcrumbs=None):
    bc = ""
    if breadcrumbs:
        bc = '<div class="breadcrumb">' + " / ".join(breadcrumbs) + '</div>'
    return f'''<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)} — SEO Knowledge Base</title>
<style>{CSS}</style>
</head><body><div class="container">{bc}{body}
<div class="footer"><p>seo-knowledge · auto-generated by build_site.py</p></div>
</div></body></html>'''


# ── Loaders ────────────────────────────────────────────────────

def load_json_files(pattern):
    results = []
    for f in sorted(glob.glob(str(ROOT / pattern)), reverse=True):
        try:
            data = json.loads(Path(f).read_text("utf-8"))
            data["_file"] = str(Path(f).relative_to(ROOT))
            results.append(data)
        except (json.JSONDecodeError, OSError):
            pass
    return results


# ── Index page ─────────────────────────────────────────────────

def build_index(opps, signals):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    go_count = sum(1 for o in opps if o.get("verdict") == "GO")
    watch_count = sum(len(s.get("watch", [])) for s in signals)
    total_scanned = sum(s.get("total_scanned", 0) for s in signals)

    # Opportunity cards (clickable)
    opp_html = ""
    if not opps:
        opp_html = '<div class="empty">暂无机会。运行 <code>挖需求</code> 开始。</div>'
    for opp in opps:
        slug = opp.get("slug", "")
        v = opp.get("verdict", "?")
        vc = {"GO":"go","CAUTIOUS":"watch","WATCH":"watch"}.get(v,"pass")
        vi = {"GO":"🟢","CAUTIOUS":"🟡","WATCH":"🟡"}.get(v,"🔴")
        sig = opp.get("signal", {})
        act = opp.get("action", {})
        metrics = opp.get("metrics", [])
        top_kw = metrics[0] if metrics else {}
        kd = top_kw.get("kd", "—")
        vol = top_kw.get("volume", "—")
        cpc = top_kw.get("cpc", "—")

        kw_tags = ""
        for m in metrics[:3]:
            kw_tags += f' <code>{_esc(m.get("keyword",""))}</code>'

        opp_html += f'''
        <a class="card {vc}" href="opportunities/{slug}.html">
          <span class="card-arrow">→</span>
          <div class="card-header">
            <span class="badge {vc}">{vi} {v}</span>
            <span class="slug">{_esc(slug)}</span>
            <span class="date">{_esc(opp.get("discovered_at",""))}</span>
          </div>
          <div class="card-title">{_esc(sig.get("topic_title", slug))}</div>
          <div class="card-meta">
            <span class="tag">{_esc(sig.get("demand_type",""))}</span>
            <span class="tag">{_esc(act.get("site_type",""))}</span>
            <span class="tag">KD:{kd} Vol:{vol} CPC:${cpc}</span>
          </div>
          <div class="card-kw">{kw_tags}</div>
        </a>'''

    # WATCH cards from signals
    watch_html = ""
    all_watches = []
    for sig in signals:
        for w in sig.get("watch", []):
            w["_date"] = sig.get("date", "")
            all_watches.append(w)
    if not all_watches:
        watch_html = '<div class="empty">暂无观察中的机会。</div>'
    for w in all_watches:
        slug = _esc(w.get("slug", ""))
        kw = _esc(w.get("keyword", ""))
        kd = w.get("kd", "—")
        vol = w.get("volume", "—")
        cpc = w.get("cpc", "—")
        reason = _esc(w.get("reason", ""))
        kd_s = str(kd) if kd is not None else "—"
        vol_s = f"{vol:,}" if isinstance(vol, (int, float)) else "—"
        cpc_s = f"${cpc}" if cpc and cpc != "—" else "—"
        watch_html += f'''
        <div class="card watch">
          <div class="card-header">
            <span class="badge watch">🟡 WATCH</span>
            <span class="slug">{slug}</span>
            <span class="date">{_esc(w.get("_date",""))}</span>
          </div>
          <div class="card-title" style="font-size:14px"><code>{kw}</code></div>
          <div class="card-meta">
            <span class="tag">KD:{kd_s}</span>
            <span class="tag">Vol:{vol_s}</span>
            <span class="tag">CPC:{cpc_s}</span>
          </div>
          <div class="card-detail">{reason}</div>
        </div>'''

    # Signal daily cards (clickable)
    sig_html = ""
    if not signals:
        sig_html = '<div class="empty">暂无信号数据。</div>'
    for sig in signals:
        date = sig.get("date", "")
        r = sig.get("results", {})
        topics = sig.get("topics", [])
        go_topics = [t for t in topics if t.get("verdict") == "GO"]
        watch_topics = [t for t in topics if t.get("verdict") == "WATCH"]

        items_preview = ""
        for t in go_topics:
            items_preview += f'<div style="font-size:12px;color:#4ade80;padding:2px 0">🟢 {_esc(t.get("title",""))}</div>'
        for t in watch_topics:
            items_preview += f'<div style="font-size:12px;color:#facc15;padding:2px 0">🟡 {_esc(t.get("title",""))}</div>'

        sig_html += f'''
        <a class="card" href="signals/{date}.html" style="border-left:3px solid #3b82f6">
          <span class="card-arrow">→</span>
          <div class="card-header">
            <span class="badge" style="background:#0c1f3f;color:#60a5fa">📡 {date}</span>
            <span class="date">扫描 {r.get("go",0)+r.get("watch",0)+r.get("pass",0)} 条</span>
          </div>
          <div class="card-meta">
            <span class="tag" style="border-color:#22c55e40;color:#4ade80">{r.get("go",0)} GO</span>
            <span class="tag" style="border-color:#eab30840;color:#facc15">{r.get("watch",0)} WATCH</span>
            <span class="tag">{r.get("pass",0)} PASS</span>
          </div>
          {items_preview}
        </a>'''

    body = f'''
    <div class="header">
      <h1>SEO Knowledge Base</h1>
      <p>需求挖掘 → 机会验证 → 建站 → 反馈闭环</p>
      <div class="stats">
        <span class="stat">🟢 <strong>{go_count}</strong> GO</span>
        <span class="stat">🟡 <strong>{watch_count}</strong> WATCH</span>
        <span class="stat">📡 <strong>{total_scanned}</strong> 信号扫描</span>
        <span class="stat">🕐 {now}</span>
      </div>
    </div>
    <div class="pipeline">
      <span class="step">📡 RSS/Reddit/HN</span><span class="arrow">→</span>
      <span class="step">🔍 信号提取</span><span class="arrow">→</span>
      <span class="step">⚡ 5问过滤</span><span class="arrow">→</span>
      <span class="step">📊 SEMrush验证</span><span class="arrow">→</span>
      <span class="step">✅ GO / ❌ PASS</span><span class="arrow">→</span>
      <span class="step">🚀 建站</span>
    </div>
    <section><h2><span class="dot" style="background:#22c55e"></span>🟢 GO — 立即行动</h2>{opp_html}</section>
    <section><h2><span class="dot" style="background:#eab308"></span>🟡 WATCH — 观察中</h2>{watch_html}</section>
    <section><h2><span class="dot" style="background:#3b82f6"></span>📡 信号日志</h2>{sig_html}</section>'''

    return _page("Dashboard", body)


# ── Opportunity detail page ────────────────────────────────────

def build_opportunity_page(opp):
    slug = opp.get("slug", "")
    v = opp.get("verdict", "?")
    vc = {"GO":"go","CAUTIOUS":"watch","WATCH":"watch"}.get(v,"pass")
    vi = {"GO":"🟢","CAUTIOUS":"🟡","WATCH":"🟡"}.get(v,"🔴")
    sig = opp.get("signal", {})
    filt = opp.get("filter", {})
    sug = opp.get("suggest", {})
    metrics = opp.get("metrics", [])
    act = opp.get("action", {})

    # Filter checklist
    filter_html = ""
    if filt:
        filter_html = '<ul class="filter-list">'
        labels = {
            "search_intent": "搜索意图存在？",
            "keywords_exist": "能想到关键词？",
            "small_site_can_rank": "小站能排？",
            "sustainable": "需求可持续？",
            "monetizable": "能变现？"
        }
        for key, label in labels.items():
            item = filt.get(key, {})
            if isinstance(item, dict):
                passed = item.get("pass", False)
                detail = _esc(item.get("detail", ""))
                icon_cls = "pass-icon" if passed else "fail-icon"
                icon = "✅" if passed else "❌"
            else:
                detail = _esc(str(item))
                icon = "✅" if detail.startswith("✅") else ("❌" if detail.startswith("❌") else "⚠️")
                icon_cls = "pass-icon" if "✅" in detail else "fail-icon"
                detail = detail.lstrip("✅❌⚠️ ")
            filter_html += f'<li><span class="{icon_cls}">{icon}</span> <strong>{label}</strong> {detail}</li>'
        filter_html += '</ul>'

    # Suggest cloud
    suggest_html = ""
    suggest_words = sug.get("top_30", sug.get("sample", []))
    if suggest_words:
        count = sug.get("count", len(suggest_words))
        suggest_html = f'<div class="detail-block"><h4>Google Suggest ({count} 个补全)</h4><div class="suggest-cloud">'
        for w in suggest_words:
            suggest_html += f'<span>{_esc(w)}</span>'
        suggest_html += '</div></div>'

    # Metrics table with trend
    metrics_html = ""
    if metrics:
        rows = ""
        for m in metrics:
            kd = m.get("kd")
            vol = m.get("volume")
            cpc = m.get("cpc", 0)
            trend = m.get("trend", [])
            note = _esc(m.get("trend_note", ""))
            kd_str = str(kd) if kd is not None else "—"
            vol_str = f"{vol:,}" if isinstance(vol, (int,float)) else "—"
            cpc_str = f"${cpc}" if cpc else "—"
            rows += f'''<tr>
              <td class="kw">{_esc(m.get("keyword",""))}</td>
              <td class="{_kd_class(kd)}">{kd_str}</td>
              <td class="{_vol_class(vol)}">{vol_str}</td>
              <td>{cpc_str}</td>
              <td>{_trend_bars(trend)}</td>
              <td style="font-size:11px;color:#555">{note}</td>
            </tr>'''
        metrics_html = f'''<div class="detail-block"><h4>SEMrush 指标</h4>
          <table class="kw-table"><thead><tr>
            <th>Keyword</th><th>KD</th><th>Vol</th><th>CPC</th><th>12M Trend</th><th>备注</th>
          </tr></thead><tbody>{rows}</tbody></table></div>'''

    # Action plan
    action_html = ""
    if act:
        steps = ""
        for s in act.get("next_steps", []):
            steps += f'<li>{_esc(s)}</li>'
        prim = ", ".join(f'<code>{_esc(k)}</code>' for k in act.get("primary_keywords", []))
        sec = ", ".join(f'<code>{_esc(k)}</code>' for k in act.get("secondary_keywords", []))
        action_html = f'''<div class="detail-block"><h4>行动计划</h4><div class="detail-text">
          <p><strong>站点类型:</strong> {_esc(act.get("site_type",""))}</p>
          {f"<p><strong>主攻词:</strong> {prim}</p>" if prim else ""}
          {f"<p><strong>辅助词:</strong> {sec}</p>" if sec else ""}
          <p><strong>内容计划:</strong> {_esc(act.get("content_plan",""))}</p>
          <p><strong>变现方式:</strong> {_esc(act.get("monetization",""))}</p>
          {f"<p><strong>预估页面:</strong> {act.get('estimated_pages','')} 页</p>" if act.get("estimated_pages") else ""}
          {f"<ul class='next-steps'>{steps}</ul>" if steps else ""}
        </div></div>'''

    # SERP analysis
    serp = opp.get("serp_analysis", {})
    serp_html = ""
    if serp:
        # Organic results table
        organic_rows = ""
        top_domains = serp.get("top_domains", [])
        for i, d in enumerate(top_domains[:10]):
            domain = _esc(d)
            is_small = not any(big in d for big in ["forbes", "techradar", "nytimes", "wikipedia", "amazon", "google"])
            cls = "good" if ("reddit" in d or is_small) else ""
            organic_rows += f'<tr><td>#{i+1}</td><td class="{cls}">{domain}</td></tr>'

        # Flags
        flags = []
        if serp.get("small_site_in_top10"):
            flags.append('<span class="tag" style="border-color:#22c55e40;color:#4ade80">✅ 小站能排</span>')
        if serp.get("reddit_ranking"):
            flags.append('<span class="tag" style="border-color:#ff450040;color:#ff6b6b">🔥 Reddit 在排名</span>')
        if serp.get("ai_overview"):
            flags.append('<span class="tag" style="border-color:#a855f740;color:#c084fc">⚡ AI Overview</span>')
        else:
            flags.append('<span class="tag" style="border-color:#22c55e40;color:#4ade80">✅ 无 AI Overview</span>')

        intent = _esc(serp.get("intent", ""))
        intent_icon = {"comparison": "⚖️", "tool": "🛠️", "informational": "📖", "commercial": "💰"}.get(intent, "🔍")
        note = _esc(serp.get("opportunity_note", ""))

        # Related searches
        related = serp.get("related_searches", [])
        related_html = ""
        if related:
            related_html = '<div style="margin-top:10px"><strong>Related Searches:</strong><div class="suggest-cloud" style="margin-top:6px">'
            for r in related:
                related_html += f'<span>{_esc(r)}</span>'
            related_html += '</div></div>'

        serp_html = f'''<div class="detail-block"><h4>🔍 SERP 分析（Google 搜索结果）</h4>
          <div class="detail-text">
            <p><strong>搜索意图:</strong> {intent_icon} {intent}</p>
            <div style="margin:8px 0">{" ".join(flags)}</div>
            {f'<p style="color:#aaa;margin:8px 0">💡 {note}</p>' if note else ''}
          </div>
          <table class="kw-table" style="max-width:300px"><thead><tr><th>#</th><th>Domain</th></tr></thead><tbody>{organic_rows}</tbody></table>
          {related_html}
        </div>'''

    # Trends analysis
    trends = opp.get("trends", {})
    trends_html = ""
    if trends:
        lc = trends.get("lifecycle", "")
        avg = trends.get("avg_interest", trends.get("avg", ""))
        peak = trends.get("peak", trends.get("peak_interest", ""))
        note = _esc(trends.get("note", ""))
        icon = {"new": "🆕", "sustained_growth": "📈", "stable": "➡️",
                "declining": "📉", "flash": "⚡", "seasonal": "🔄"}.get(lc, "❓")
        lc_color = {"new": "#4ade80", "sustained_growth": "#4ade80", "stable": "#888",
                    "declining": "#f87171", "flash": "#facc15", "seasonal": "#60a5fa"}.get(lc, "#888")
        trends_html = f'''<div class="detail-block"><h4>📈 Google Trends</h4>
          <div class="detail-text">
            <p><strong>生命周期:</strong> <span style="color:{lc_color}">{icon} {lc}</span></p>
            {f'<p><strong>平均热度:</strong> {avg} | <strong>峰值:</strong> {peak}</p>' if avg else ''}
            {f'<p style="color:#666">{note}</p>' if note else ''}
          </div>
        </div>'''

    # Reddit analysis
    reddit = opp.get("reddit", {})
    reddit_html = ""
    if reddit:
        rd_query = _esc(reddit.get("query", ""))
        rd_posts = reddit.get("posts_found", "")
        rd_top = _esc(reddit.get("top_post", ""))
        rd_pain = _esc(reddit.get("key_pain_point", ""))
        rd_insight = _esc(reddit.get("key_insight", ""))
        reddit_html = f'''<div class="detail-block"><h4>💬 Reddit 需求验证</h4>
          <div class="detail-text">
            {f'<p><strong>搜索词:</strong> {rd_query}</p>' if rd_query else ''}
            {f'<p><strong>找到帖子:</strong> {rd_posts} 篇</p>' if rd_posts else ''}
            {f'<p><strong>热帖:</strong> {rd_top}</p>' if rd_top else ''}
            {f'<p><strong>用户痛点:</strong> <span style="color:#facc15">{rd_pain}</span></p>' if rd_pain else ''}
            {f'<p><strong>关键洞察:</strong> <span style="color:#60a5fa">{rd_insight}</span></p>' if rd_insight else ''}
          </div>
        </div>'''

    # Signal source
    source_html = ""
    platforms = sig.get("platforms", [])
    urgency = sig.get("urgency", "")
    urgency_reason = sig.get("urgency_reason", "")
    urgency_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(urgency, "")
    if platforms or urgency:
        source_html = f'''<div class="detail-block"><h4>📡 信号来源</h4>
          <div class="detail-text">
            <p><strong>来源平台:</strong> {", ".join(platforms)}</p>
            <p><strong>需求类型:</strong> {_esc(sig.get("demand_type",""))}</p>
            {f'<p><strong>紧急度:</strong> {urgency_icon} {urgency} — {_esc(urgency_reason)}</p>' if urgency else ''}
            <p><strong>证据:</strong> {_esc(sig.get("evidence",""))}</p>
          </div>
        </div>'''

    body = f'''
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
      <span class="badge {vc}" style="font-size:14px;padding:4px 12px">{vi} {v}</span>
      <h1 style="font-size:22px;color:#fff">{_esc(sig.get("topic_title", slug))}</h1>
    </div>
    <div class="card-meta" style="margin-bottom:20px">
      <span class="tag">{_esc(sig.get("demand_type",""))}</span>
      <span class="tag">{_esc(act.get("site_type",""))}</span>
      <span class="tag">{", ".join(platforms)}</span>
      <span class="tag">{_esc(opp.get("discovered_at",""))}</span>
    </div>

    {source_html}
    <section><h3>5 问过滤</h3>{filter_html}</section>
    {suggest_html}
    {metrics_html}
    {trends_html}
    {serp_html}
    {reddit_html}
    {action_html}'''

    bc = ['<a href="../index.html">首页</a>', f'{slug}']
    return _page(slug, body, bc)


# ── Signal daily detail page ───────────────────────────────────

def build_signal_page(sig):
    date = sig.get("date", "")
    topics = sig.get("topics", [])
    r = sig.get("results", {})

    rows_html = ""
    for t in topics:
        v = t.get("verdict", "PASS")
        vc = {"GO":"go","WATCH":"watch"}.get(v,"pass")
        vi = {"GO":"🟢","WATCH":"🟡"}.get(v,"❌")
        row_cls = {"GO":"is-go","WATCH":"is-watch"}.get(v,"")

        decision = _esc(t.get("decision", ""))
        slug = t.get("slug", "")
        link_start = f'<a href="../opportunities/{slug}.html">' if slug and v in ("GO","WATCH") else ""
        link_end = "</a>" if link_start else ""

        # If GO/WATCH with filter data, show expandable detail
        extra = ""
        if v in ("GO", "WATCH") and t.get("filter"):
            filt = t["filter"]
            checks = ""
            for key, val in filt.items():
                checks += f'<span style="margin-right:12px">{_esc(val)}</span>'
            sug = t.get("suggest", {})
            sug_count = sug.get("count", 0)
            metrics = t.get("metrics", [])
            met_summary = " | ".join(
                f'{_esc(m.get("keyword",""))} KD:{m.get("kd","?")} Vol:{m.get("volume","?")}'
                for m in metrics[:3]
            )
            extra = f'''<div style="padding:8px 12px 4px 36px;font-size:11px;color:#555;line-height:1.8;border-bottom:1px solid #111">
              <div>{checks}</div>
              {f'<div>Google Suggest: {sug_count} 个补全</div>' if sug_count else ''}
              {f'<div>Metrics: {met_summary}</div>' if met_summary else ''}
            </div>'''

        rows_html += f'''
        <div class="sig-row {row_cls}">
          {link_start}
          <span class="sig-rank">#{t.get("rank","")}</span>
          <span class="sig-verdict"><span class="badge {vc}">{vi} {v}</span></span>
          <span class="sig-title">{_esc(t.get("title",""))}</span>
          <span class="sig-source">{_esc(t.get("source",""))}</span>
          {link_end}
        </div>
        <div class="sig-row" style="padding-left:36px;padding-top:0;padding-bottom:2px">
          <span style="font-size:11px;color:#555">{decision}</span>
        </div>
        {extra}'''

    body = f'''
    <h1 style="font-size:20px;color:#fff;margin-bottom:6px">📡 信号日报 {date}</h1>
    <div class="card-meta" style="margin-bottom:20px">
      <span class="tag" style="border-color:#22c55e40;color:#4ade80">{r.get("go",0)} GO</span>
      <span class="tag" style="border-color:#eab30840;color:#facc15">{r.get("watch",0)} WATCH</span>
      <span class="tag">{r.get("pass",0)} PASS</span>
      <span class="tag">共扫描 {sig.get("total_scanned",0)} 条</span>
    </div>
    <div class="detail-block" style="padding:0">
      {rows_html}
    </div>'''

    bc = ['<a href="../index.html">首页</a>', f'信号 {date}']
    return _page(f"Signal {date}", body, bc)


# ── Main ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build GitHub Pages site")
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()

    opps = load_json_files("opportunities/*.json")
    signals = load_json_files("signals/*/*.json")

    DOCS.mkdir(exist_ok=True)
    (DOCS / "opportunities").mkdir(exist_ok=True)
    (DOCS / "signals").mkdir(exist_ok=True)

    # Index
    idx = DOCS / "index.html"
    idx.write_text(build_index(opps, signals), "utf-8")

    # Opportunity detail pages
    for opp in opps:
        slug = opp.get("slug", "unknown")
        p = DOCS / "opportunities" / f"{slug}.html"
        p.write_text(build_opportunity_page(opp), "utf-8")

    # Signal daily pages
    for sig in signals:
        date = sig.get("date", "unknown")
        p = DOCS / "signals" / f"{date}.html"
        p.write_text(build_signal_page(sig), "utf-8")

    total = 1 + len(opps) + len(signals)
    print(f"Built {total} pages:")
    print(f"  docs/index.html")
    for opp in opps:
        print(f"  docs/opportunities/{opp.get('slug','?')}.html")
    for sig in signals:
        print(f"  docs/signals/{sig.get('date','?')}.html")

    if args.open:
        subprocess.run(["open", str(idx)])


if __name__ == "__main__":
    main()
