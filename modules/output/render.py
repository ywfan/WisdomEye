import json
import re
import string
import shutil
import subprocess
from pathlib import Path
try:
    import markdown as _mdlib  # type: ignore
except Exception:
    _mdlib = None

def _read_json(path: str) -> dict:
    """Load JSON file with UTF-8 encoding."""
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))

def _esc(s: str) -> str:
    """HTML-escape minimal characters for safe rendering."""
    return (str(s or "")).replace("<", "&lt;").replace(">", "&gt;")

def _kv(label: str, value: str) -> str:
    """Render a key-value line if value is present."""
    v = _esc(value)
    lab = _esc(label)
    return f"<div class='kv'><span class='k'>{lab}：</span><span class='v'>{v}</span></div>" if v else ""

def _li_row(left: str, right: str) -> str:
    """Render a two-column list row used by timeline sections."""
    l = _esc(left)
    r = _esc(right)
    return f"<li class='edu-row'><span class='school'>{l}</span> <span class='meta'>{r}</span></li>"

def _period_key(s: str) -> int:
    """Extract latest year for sorting; return 0 if none."""
    try:
        ys = re.findall(r"(19|20)\d{2}", str(s or ""))
        if ys:
            return int(ys[-1])
    except Exception:
        pass
    return 0

def _label_cn(key: str) -> str:
    """Map internal keys to Chinese labels used in cards."""
    m = {
        "role": "角色",
        "funding_source": "资助来源",
        "time_period": "时间段",
        "project_name": "项目名称",
        "description": "描述",
        "repo_name": "仓库",
        "metrics": "指标",
        "url": "链接",
        "status": "状态",
        "number": "编号",
        "activity_name": "活动",
    }
    return m.get(key, key)

def _cards(items: list, title_key: str, fields: list) -> str:
    """Render list of card items with title and selected fields."""
    out = []
    for it in items or []:
        title = _esc(it.get(title_key, ""))
        parts = []
        for f in fields:
            v = it.get(f, "")
            parts.append(_kv(_label_cn(f), v))
        body = "".join([p for p in parts if p])
        if title or body:
            out.append(f"<li class='card'><div class='card-title'>{title}</div>{body}</li>")
    return "".join(out)


def _md(text: str) -> str:
    """Render markdown via library or a lightweight fallback HTML renderer."""
    s = str(text or "")
    s = re.sub(r"\n\s*\n+", "\n\n", s)
    if _mdlib:
        try:
            return _mdlib.markdown(s)
        except Exception:
            pass
    # Fallback renderer
    lines = s.splitlines()
    out = []
    in_ul = False
    in_ol = False
    in_code = False
    code_buf = []
    def fmt_inline(x: str) -> str:
        y = _esc(x)
        y = re.sub(r"\*\*(.*?)\*\*", r"<strong>\\1</strong>", y)
        y = re.sub(r"`([^`]+)`", r"<code>\\1</code>", y)
        y = re.sub(r"\[(.+?)\]\((https?://[^\s]+)\)", r"<a href='\\2' target='_blank'>\\1</a>", y)
        return y
    for ln in lines:
        if ln.strip().startswith("```"):
            if not in_code:
                in_code = True; code_buf = []
                # start code block
            else:
                # end code block
                out.append("<pre><code>" + _esc("\n".join(code_buf)) + "</code></pre>")
                in_code = False
            continue
        if in_code:
            code_buf.append(ln)
            continue
        if re.match(r"^---+$", ln.strip()):
            if in_ul:
                out.append("</ul>"); in_ul = False
            if in_ol:
                out.append("</ol>"); in_ol = False
            out.append("<hr/>"); continue
        if ln.startswith("> "):
            if in_ul:
                out.append("</ul>"); in_ul = False
            if in_ol:
                out.append("</ol>"); in_ol = False
            out.append("<blockquote>" + fmt_inline(ln[2:]) + "</blockquote>"); continue
        if ln.startswith("### "):
            if in_ul:
                out.append("</ul>"); in_ul = False
            if in_ol:
                out.append("</ol>"); in_ol = False
            out.append(f"<h3>{fmt_inline(ln[4:])}</h3>"); continue
        if ln.startswith("## "):
            if in_ul:
                out.append("</ul>"); in_ul = False
            if in_ol:
                out.append("</ol>"); in_ol = False
            out.append(f"<h2>{fmt_inline(ln[3:])}</h2>"); continue
        if ln.startswith("# "):
            if in_ul:
                out.append("</ul>"); in_ul = False
            if in_ol:
                out.append("</ol>"); in_ol = False
            out.append(f"<h1>{fmt_inline(ln[2:])}</h1>"); continue
        if re.match(r"^\d+\. ", ln):
            if in_ul:
                out.append("</ul>"); in_ul = False
            if not in_ol:
                out.append("<ol>"); in_ol = True
            out.append(f"<li>{fmt_inline(re.sub(r'^\d+\.\s*', '', ln))}</li>"); continue
        if ln.startswith("- "):
            if in_ol:
                out.append("</ol>"); in_ol = False
            if not in_ul:
                out.append("<ul>"); in_ul = True
            out.append(f"<li>{fmt_inline(ln[2:].strip())}</li>"); continue
        if ln.strip() == "":
            # paragraph break
            if in_ul:
                out.append("</ul>"); in_ul = False
            if in_ol:
                out.append("</ol>"); in_ol = False
            continue
        # normal paragraph
        out.append(f"<p>{fmt_inline(ln)}</p>")
    if in_ul:
        out.append("</ul>")
    if in_ol:
        out.append("</ol>")
    if in_code:
        out.append("<pre><code>" + _esc("\n".join(code_buf)) + "</code></pre>")
    return "".join(out)

def render_html(final_json_path: str) -> str:
    """Build the HTML report from `resume_final.json` and write to disk."""
    data = _read_json(final_json_path)
    basic = data.get("basic_info") or {}
    name = (basic.get("name") or data.get("name") or "").strip()
    degree = (basic.get("highest_degree") or "").strip()
    contact = basic.get("contact") or {}
    academic_metrics = basic.get("academic_metrics") or {}
    education = sorted((data.get("education") or []), key=lambda e: _period_key(e.get("time_period")), reverse=True)
    internships = sorted((data.get("internships") or []), key=lambda i: _period_key(i.get("time_period")), reverse=True)
    work = sorted((data.get("work_experience") or []), key=lambda w: _period_key(w.get("time_period")), reverse=True)
    research_grants = data.get("research_grants") or []
    project_experience = data.get("project_experience") or []
    open_source = data.get("open_source_contributions") or []
    patents = data.get("patents") or []
    academic_activities = data.get("academic_activities") or []
    memberships = data.get("memberships") or []
    publications = data.get("publications") or []
    awards = data.get("awards") or []
    md_eval = data.get("multi_dimension_evaluation") or {}
    scores = data.get("multi_dimension_scores") or {}
    overall = data.get("overall_summary") or ""
    review = data.get("academic_review") or ""
    prof_sources = data.get("profile_sources") or []
    social_presence = data.get("social_presence") or []
    social_influence = data.get("social_influence") or {}
    network_graph = data.get("network_graph") or {}
    skills = data.get("skills") or {}
    honors = data.get("honors") or []
    others = data.get("others") or ""

    bi_html = "".join([
        _kv("姓名", name),
        _kv("学历", degree),
        _kv("邮箱", contact.get("email", "")),
        _kv("电话", contact.get("phone", "")),
        _kv("位置", contact.get("location", "")),
        _kv("主页", contact.get("homepage", "")),
    ])

    edu_rows = []
    for e in education:
        school = _esc(e.get("school", ""))
        meta = " • ".join([_esc(e.get("degree", "")), _esc(e.get("major", "")), _esc(e.get("time_period", ""))]).strip(" • ")
        edu_rows.append(_li_row(school, meta))
    edu_list_html = "".join([r for r in edu_rows if r])

    work_rows = []
    for w in work:
        company = _esc(w.get("company", ""))
        meta = " • ".join([_esc(w.get("title", "")), _esc(w.get("time_period", ""))]).strip(" • ")
        work_rows.append(_li_row(company, meta))
    work_list_html = "".join([r for r in work_rows if r])

    intern_rows = []
    for i in internships:
        comp = _esc(i.get("company", ""))
        meta = " • ".join([_esc(i.get("title", "")), _esc(i.get("time_period", ""))]).strip(" • ")
        intern_rows.append(_li_row(comp, meta))
    internships_list_html = "".join([r for r in intern_rows if r])

    pubs_html = "".join([
        f"<li class='card'><div class='card-title'>{_esc(p.get('title'))}</div>"
        + (f"<div class='meta'>{_esc(p.get('venue',''))}</div>" if p.get('venue') else "")
        + (f"<div class='meta'><a href='{_esc(p.get('url'))}' target='_blank'>链接</a></div>" if p.get('url') else "")
        + (f"<div class='meta'>{_esc(p.get('date'))}</div>" if p.get('date') else "")
        + (f"<div class='chip'>总结</div><div class='md'>{_md(p.get('summary'))}</div>" if p.get('summary') else "")
        + (f"<details class='card'><summary>摘要</summary><div class='text'>{_esc(p.get('abstract'))}</div></details>" if p.get('abstract') else "")
        + "</li>" for p in publications
    ])

    awards_html = "".join([
        f"<li class='card'><div class='card-title'>{_esc(a.get('name'))}</div>"
        + (f"<div class='meta'>{_esc(a.get('date',''))}</div>" if a.get('date') else "")
        + (f"<div class='text'>{_esc(a.get('intro',''))}</div>" if a.get('intro') else "")
        + "</li>" for a in awards
    ])

    eval_cards = []
    order = ["学术创新力", "工程实战力", "行业影响力", "合作协作", "综合素质"]
    for k in order:
        v = md_eval.get(k)
        if isinstance(v, dict):
            text = str(v.get("evaluation") or v.get("desc") or "")
            srcs = v.get("evidence_sources") or []
        else:
            text = _esc(str(v or ""))
            srcs = []
        score = scores.get(k, "")
        src_block = ""
        if srcs:
            src_block = "<div class='chip'>证据来源</div><div class='text'>" + _esc("\n".join([str(x) for x in srcs])) + "</div>"
        eval_cards.append(f"<div class='card'><div class='card-title'>{_esc(k)}<span class='badge'>{_esc(score)}</span></div><div class='md'>{_md(text)}</div>{src_block}</div>")
    eval_html = "".join(eval_cards)

    sp_cards = []
    for sp in social_presence:
        plat = _esc(sp.get("platform",""))
        acct = _esc(sp.get("account",""))
        url = _esc(sp.get("url",""))
        foll = _esc(sp.get("followers",""))
        freq = _esc(sp.get("posts_per_month",""))
        topics = _esc(sp.get("topics",""))
        sp_cards.append(
            f"<div class='card'><div class='card-title'>{plat}</div>"
            + _kv("账号", acct)
            + (f"<div class='kv'><span class='k'>链接</span><span class='v'><a href='{url}' target='_blank'>{url}</a></span></div>" if url else "")
            + _kv("粉丝", foll)
            + (_kv("频率", freq + "/月") if freq else "")
            + (f"<div class='chip'>话题</div><div class='text'>{topics}</div>" if topics else "")
            + "</div>"
        )
    social_cards = "".join(sp_cards)
    si_summary = _esc(social_influence.get("summary","")) if isinstance(social_influence, dict) else ""
    si_signals = social_influence.get("signals") if isinstance(social_influence, dict) else []
    si_block = ""
    if si_summary or si_signals:
        sig_html = "".join([f"<li class='edu-row'><span class='meta'>{_esc(s)}</span></li>" for s in (si_signals or [])])
        si_block = f"<div class='card'><div class='card-title'>影响力</div><div class='text'>{si_summary}</div>{('<ul class=\'edu-list\'>'+sig_html+'</ul>') if sig_html else ''}</div>"

    ng_nodes = (network_graph.get("nodes") if isinstance(network_graph, dict) else []) or []
    ng_tags = (network_graph.get("circle_tags") if isinstance(network_graph, dict) else []) or []
    ng_metrics = (network_graph.get("centrality_metrics") if isinstance(network_graph, dict) else {}) or {}
    top_nodes = []
    for n in ng_nodes[:6]:
        nm = _esc(n.get("name",""))
        rl = _esc(n.get("role",""))
        aff = _esc(n.get("affiliation",""))
        line = " ".join([x for x in [nm, rl and f"({rl})", aff and f" • {aff}"] if x])
        if line:
            top_nodes.append(f"<li class='edu-row'><span class='school'>{line}</span></li>")
    nodes_html = "".join(top_nodes)
    tags_html = "".join([f"<span class='chip'>{_esc(t)}</span>" for t in ng_tags])
    deg = _esc(ng_metrics.get("degree",""))
    cw = _esc(ng_metrics.get("coauthor_weight",""))
    network_cards = (
        f"<div class='card'><div class='card-title'>成员</div><ul class='edu-list'>{nodes_html}</ul></div>" if nodes_html else ""
    ) + (
        f"<div class='card'><div class='card-title'>圈层标签</div>{tags_html}</div>" if tags_html else ""
    ) + (
        f"<div class='card'><div class='card-title'>中心性</div>{_kv('度',deg)}{_kv('合著权重',cw)}</div>"
    )

    style = """
    :root{--bg:#f7f8fa;--panel:#f9fafb;--text:#0f172a;--muted:#64748b;--accent:#2563eb;--accent-2:#16a34a;--card:#ffffff;--border:#e2e8f0}
    *{box-sizing:border-box}
    body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;overflow-x:hidden}
    .page{max-width:1200px;margin:0 auto}
    .layout{display:grid;grid-template-columns:280px 1fr;min-height:100vh}
    .sidebar{padding:20px;border-right:1px solid var(--border);background:var(--panel);position:sticky;top:0;height:100vh;overflow:auto}
    .content{padding:24px}
    .title{font-size:24px;font-weight:700;margin:0}
    .subtitle{color:var(--muted);margin-top:6px}
    .nav{margin:16px 0;display:grid;gap:8px}
    .nav a{display:block;padding:10px 12px;border:1px solid var(--border);border-radius:10px;color:var(--text);text-decoration:none;background:#ffffff}
    .section{margin:24px 0}
    h2{font-size:20px;margin:0 0 14px;display:flex;align-items:center;gap:10px}
    .cards{display:grid;grid-template-columns: repeat(auto-fill,minmax(320px,1fr));gap:16px}
    @media (max-width:1024px){.page{max-width:96vw}.layout{grid-template-columns:1fr}.sidebar{position:relative;height:auto}.cards{grid-template-columns:1fr}}
    @media (max-width:640px){.page{max-width:96vw}.content{padding:18px}.sidebar{padding:16px}}
    .card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px;box-shadow:0 1px 2px rgba(15,23,42,0.06)}
    .card-title{font-weight:600;margin-bottom:10px;display:flex;align-items:center;justify-content:space-between}
    .badge{display:inline-block;padding:2px 10px;border-radius:999px;background:#fff;border:1px solid var(--border);color:var(--accent-2);font-weight:600}
    .hbadge{display:inline-block;padding:2px 8px;border-radius:8px;background:#eef2ff;border:1px solid #c7d2fe;color:#334155;font-weight:600}
    .chip{display:inline-block;padding:3px 10px;border-radius:8px;background:#fff;border:1px solid var(--border);margin:8px 0;color:var(--muted)}
    .text{white-space:pre-wrap;line-height:1.75}
    .md{white-space:normal;line-height:1.8}
    ul{list-style:none;padding:0;margin:0}
    .edu-list .edu-row{display:flex;gap:10px;align-items:center;margin:6px 0}
    .edu-list .school{font-weight:600}
    .edu-list .meta{color:var(--muted)}
    .sources a{color:var(--accent)}
    .metrics{display:grid;grid-template-columns: repeat(3,1fr);gap:12px;margin-top:12px}
    .metric{background:#fff;border:1px solid var(--border);border-radius:12px;padding:10px 12px;text-align:center}
    .metric .num{font-size:22px;font-weight:700;color:#1f2937}
    .metric .label{color:#64748b}
    footer{margin-top:20px;color:var(--muted);font-size:12px}
    .timeline{border-left:2px solid var(--border);padding-left:14px}
    .timeline .edu-row{position:relative;padding-left:10px}
    .timeline .edu-row::before{content:"";position:absolute;left:-8px;top:8px;width:8px;height:8px;background:var(--accent);border-radius:50%}
    details.card>summary{cursor:pointer;list-style:none;font-weight:600}
    details.card>summary::-webkit-details-marker{display:none}
    details.card[open]{border-color:#cbd5e1}
    @media print{body{background:#fff;color:#000}.layout{grid-template-columns:1fr}.sidebar{display:none}.page{max-width:100%}.card{background:#fff;border:1px solid #ccc;box-shadow:none}a{color:#000;text-decoration:underline}.cards{grid-template-columns:1fr}.card{break-inside:avoid}}
    """

    sidebar_sections = "".join([
        "<div class='card'><div class='card-title'>导航</div><div class='nav'>"
        + "".join([f"<a href='#{anchor}'>{title}</a>" for anchor, title in [
            ("basic","基本信息"),("education","教育经历"),("internships","实习经历"),("work","工作经历"),("projects","项目经验"),("grants","研究资助"),("open_source","开源贡献"),("patents","专利"),("activities","学术活动"),("memberships","组织会员"),("overview","综合评价"),("review","学术综述"),("evaluation","维度评价"),("scholar","学术指标"),("social","社交声量"),("network","人脉图谱概要"),("publications","论文"),("awards","奖项"),("skills","技能"),("honors","荣誉"),("others","其他"),("sources","来源")
        ]])
        + "</div></div>"
    ])

    skills_html = "".join([
        f"<li class='card'><div class='card-title'>技术栈</div><div class='text'>{_esc(', '.join(skills.get('tech_stack',[]) or []))}</div></li>",
        f"<li class='card'><div class='card-title'>语言能力</div><div class='text'>{_esc(', '.join(skills.get('languages',[]) or []))}</div></li>",
        f"<li class='card'><div class='card-title'>其他技能</div><div class='text'>{_esc(', '.join(skills.get('general',[]) or []))}</div></li>",
    ])

    honors_html = "".join([
        f"<li class='card'><div class='card-title'>{_esc(h.get('name'))}</div><div class='meta'>{_esc(h.get('date',''))}</div></li>" for h in (honors or [])
    ]) or "<li class='card'><div class='text'>暂无</div></li>"

    others_html = f"<div class='card'><div class='text'>{_esc(others)}</div></div>" if others else "<div class='card'><div class='text'>暂无</div></div>"

    metrics_html = "".join([
        f"<div class='metric'><div class='num'>{len(publications)}</div><div class='label'>论文</div></div>",
        f"<div class='metric'><div class='num'>{len(awards)}</div><div class='label'>奖项</div></div>",
        f"<div class='metric'><div class='num'>{len(prof_sources)}</div><div class='label'>来源</div></div>",
    ])

    tpl = """
<!doctype html>
<html lang='zh-CN'>
<meta charset='utf-8'/>
<meta name='viewport' content='width=device-width,initial-scale=1'/>
<title>综合评价 - $NAME</title>
<style>$STYLE</style>
<body>
<div class='page'>
<div class='layout'>
  <aside class='sidebar'>
    <div class='title'>候选人综合评价</div>
    <div class='subtitle'>姓名：$NAME$DEGREE</div>
    $SIDEBAR_SECTIONS
  </aside>
  <main class='content'>
    <section id='basic' class='section'>
      <h2>基本信息</h2>
      <div class='card'><div class='card-title'>个人信息</div>$BI_HTML</div>
    </section>
    <section id='education' class='section'><h2>教育经历</h2><div class='card'><ul class='edu-list timeline'>$EDU_LIST</ul></div></section>
    <section id='internships' class='section'>$INTERNSHIPS_BLOCK</section>
    <section id='work' class='section'>$WORK_BLOCK</section>
    <section id='projects' class='section'>$PROJECTS_BLOCK</section>
    <section id='grants' class='section'>$GRANTS_BLOCK</section>
    <section id='open_source' class='section'>$OPEN_SOURCE_BLOCK</section>
    <section id='patents' class='section'>$PATENTS_BLOCK</section>
    <section id='activities' class='section'>$ACTIVITIES_BLOCK</section>
    <section id='memberships' class='section'>$MEMBERSHIPS_BLOCK</section>
    <section id='overview' class='section'>
      <h2>总览</h2>
      <div class='card'><div class='md'>$SUMMARY_HTML</div></div>
      <div class='metrics'>$METRICS_HTML</div>
    </section>
    <section id='review' class='section'>
      <h2>学术综述（全文）</h2>
      <details class='card'><summary>展开/收起全文</summary><div class='text'>$REVIEW_FULL</div></details>
    </section>
    <section id='evaluation' class='section'>
      <h2>多维度评价</h2>
      <div class='cards'>$EVAL_HTML</div>
    </section>
    <section id='scholar' class='section'>
      <h2>学术指标</h2>
      <div class='cards'>
        <div class='card'><div class='card-title'>指标</div>
          $HINDEX
          $H10INDEX
          $CITATIONS_TOTAL
          $CITATIONS_RECENT
        </div>
      </div>
    </section>
    <section id='social' class='section'>
      <h2>社交声量</h2>
      <div class='cards'>$SOCIAL_CARDS</div>
      $SOCIAL_INFLUENCE
    </section>
    <section id='network' class='section'>
      <h2>人脉图谱概要</h2>
      <div class='cards'>$NETWORK_CARDS</div>
    </section>
    <section id='publications' class='section'>
      <h2>论文 <span class='hbadge'>${PUB_COUNT}</span></h2>
      <ul class='cards'>$PUBS_HTML</ul>
    </section>
    <section id='awards' class='section'>
      <h2>奖项 <span class='hbadge'>${AWARD_COUNT}</span></h2>
      <ul class='cards'>$AWARDS_HTML</ul>
    </section>
    <section id='skills' class='section'><h2>技能</h2><ul class='cards'>$SKILLS_HTML</ul></section>
    <section id='honors' class='section'><h2>荣誉</h2><ul class='cards'>$HONORS_HTML</ul></section>
    <section id='others' class='section'><h2>其他</h2>$OTHERS_HTML</section>
    <section id='sources' class='section'>
      <h2>参考来源 <span class='hbadge'>${SRC_COUNT}</span></h2>
      <ul class='sources'>$SRC_HTML</ul>
    </section>
    <footer>自动生成报告</footer>
  </main>
</div>
</div>
</body>
</html>
"""

    internships_block = f"<h2>实习经历</h2><ul class='edu-list timeline'>{internships_list_html}</ul>" if internships_list_html else ""
    work_block = f"<h2>工作经历</h2><ul class='edu-list timeline'>{work_list_html}</ul>" if work_list_html else ""
    projects_block = f"<h2>项目经验</h2><ul class='cards'>{_cards(project_experience,'project_name',['role','description'])}</ul>" if project_experience else ""
    grants_block = f"<h2>研究资助</h2><ul class='cards'>{_cards(research_grants,'title',['role','funding_source','time_period'])}</ul>" if research_grants else ""
    open_source_block = f"<h2>开源贡献</h2><ul class='cards'>{_cards(open_source,'repo_name',['role','metrics','url','description'])}</ul>" if open_source else ""
    patents_block = f"<h2>专利</h2><ul class='cards'>{_cards(patents,'title',['status','number'])}</ul>" if patents else ""
    activities_block = f"<h2>学术活动</h2><ul class='cards'>{_cards(academic_activities,'activity_name',['role','description'])}</ul>" if academic_activities else ""
    memberships_block = ""
    if memberships:
        ms_list = "".join([f"<li class='edu-row'><span class='school'>{_esc(m)}</span></li>" for m in memberships])
        memberships_block = f"<h2>组织会员</h2><div class='card'><ul class='edu-list'>{ms_list}</ul></div>"

    html = string.Template(tpl).safe_substitute({
        "STYLE": style,
        "NAME": _esc(name),
        "DEGREE": ("｜学历："+_esc(degree)) if degree else "",
        "SIDEBAR_SECTIONS": sidebar_sections,
        "BI_HTML": bi_html,
        "EDU_LIST": edu_list_html,
        "INTERNSHIPS_BLOCK": internships_block,
        "WORK_BLOCK": work_block,
        "PROJECTS_BLOCK": projects_block,
        "GRANTS_BLOCK": grants_block,
        "OPEN_SOURCE_BLOCK": open_source_block,
        "PATENTS_BLOCK": patents_block,
        "ACTIVITIES_BLOCK": activities_block,
        "MEMBERSHIPS_BLOCK": memberships_block,
        "SUMMARY_HTML": _md(overall),
        "REVIEW_FULL": _esc(review),
        "EVAL_HTML": eval_html,
        "HINDEX": _kv("h-index", academic_metrics.get("h_index","")),
        "H10INDEX": _kv("h10-index", academic_metrics.get("h10_index","")),
        "CITATIONS_TOTAL": _kv("总引用", academic_metrics.get("citations_total","")),
        "CITATIONS_RECENT": _kv("近五年引用", academic_metrics.get("citations_recent","")),
        "SOCIAL_CARDS": social_cards,
        "SOCIAL_INFLUENCE": si_block,
        "NETWORK_CARDS": network_cards,
        "PUBS_HTML": pubs_html,
        "AWARDS_HTML": awards_html,
        "SKILLS_HTML": skills_html,
        "HONORS_HTML": honors_html,
        "OTHERS_HTML": others_html,
        "SRC_HTML": "".join([f"<li><a href='{_esc(u)}' target='_blank'>{_esc(u)}</a></li>" for u in prof_sources]),
        "METRICS_HTML": "".join([
            f"<div class='metric'><div class='num'>{len(publications)}</div><div class='label'>论文</div></div>",
            f"<div class='metric'><div class='num'>{len(awards)}</div><div class='label'>奖项</div></div>",
            f"<div class='metric'><div class='num'>{len(prof_sources)}</div><div class='label'>来源</div></div>",
        ]),
        "PUB_COUNT": str(len(publications)),
        "AWARD_COUNT": str(len(awards)),
        "SRC_COUNT": str(len(prof_sources)),
    })

    out_html = Path(final_json_path).parent / "resume_final.html"
    out_html.write_text(html, encoding="utf-8")
    return str(out_html)

def render_pdf(final_json_path: str) -> str:
    """Generate PDF from HTML via WeasyPrint, fallback to wkhtmltopdf or plain PDF."""
    html_path = render_html(final_json_path)
    out_pdf = Path(final_json_path).parent / "resume_final.pdf"
    try:
        from weasyprint import HTML
        HTML(filename=html_path).write_pdf(str(out_pdf))
        return str(out_pdf)
    except Exception:
        pass
    wk = shutil.which("wkhtmltopdf")
    if wk:
        try:
            subprocess.run([wk, html_path, str(out_pdf)], check=True)
            return str(out_pdf)
        except Exception:
            pass
    content = f"Candidate Report\nPlease open HTML at: {html_path}\n"
    pdf_bytes = _simple_text_pdf(content)
    out_pdf.write_bytes(pdf_bytes)
    return str(out_pdf)

def _simple_text_pdf(text: str) -> bytes:
    """Create a minimal PDF with embedded text for ultimate fallback."""
    lines = text.splitlines()
    y = 750
    content_stream = "BT /F1 12 Tf 72 770 Td (" + (lines[0] if lines else "") + ") Tj ET\n"
    for i, ln in enumerate(lines[1:]):
        content_stream += f"BT /F1 12 Tf 72 {y-14*(i+1)} Td (" + ln.replace("(","[").replace(")","]") + ") Tj ET\n"
    b = content_stream.encode("latin-1", errors="ignore")
    objs = []
    objs.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objs.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objs.append(b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>endobj\n")
    objs.append(b"4 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")
    objs.append(b"5 0 obj<< /Length " + str(len(b)).encode() + b" >>stream\n" + b + b"endstream endobj\n")
    pdf = b"%PDF-1.4\n"
    offs = []
    for o in objs:
        offs.append(len(pdf))
        pdf += o
    xref_pos = len(pdf)
    pdf += b"xref\n0 6\n0000000000 65535 f \n"
    for off in offs:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += b"trailer<< /Size 6 /Root 1 0 R >>\nstartxref\n" + str(xref_pos).encode() + b"\n%%EOF\n"
    return pdf
