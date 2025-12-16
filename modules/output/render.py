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
    return (str(s or "")).replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def _url_link(url: str, text: str = None, max_length: int = 80) -> str:
    """Convert URL to clickable link with optional text truncation.
    
    Args:
        url: The URL to link to
        text: Optional display text (if None, shows truncated URL)
        max_length: Maximum length for URL display before truncation
    
    Returns:
        HTML anchor tag with proper attributes for security and styling
    """
    if not url:
        return ""
    
    # Normalize URL - strip whitespace and ensure proper format
    url = str(url).strip()
    if not url:
        return ""
    
    # Security: Validate URL scheme to prevent javascript: injection and other attacks
    url_lower = url.lower()
    if not url_lower.startswith(('http://', 'https://', '//', 'mailto:')):
        # For non-standard URLs, just return escaped text without link
        return _esc(url)
    
    # Escape URL for safe HTML embedding
    url_clean = _esc(url)
    
    # Determine display text
    if text:
        display_text = _esc(str(text).strip())
    else:
        # Show shortened URL with ellipsis if too long
        if len(url_clean) > max_length:
            # Try to preserve protocol and domain
            display_text = url_clean[:max_length - 3] + "..."
        else:
            display_text = url_clean
    
    # Return formatted link with security attributes
    return f'<a href="{url_clean}" target="_blank" rel="noopener noreferrer" class="link" title="{url_clean}">{display_text}</a>'

def _kv(label: str, value: str, is_url: bool = False) -> str:
    """Render a key-value line if value is present.
    
    Args:
        label: The label/key to display
        value: The value to display
        is_url: Whether the value should be rendered as a clickable link
    
    Returns:
        HTML div with key-value pair, or empty string if value is empty
    """
    if not value or str(value).strip() == "":
        return ""
    
    lab = _esc(str(label).strip())
    
    if is_url:
        v = _url_link(str(value).strip())
    else:
        v = _esc(str(value).strip())
    
    return f'<div class="kv"><span class="k">{lab}：</span><span class="v">{v}</span></div>'

def _li_row(left: str, right: str) -> str:
    """Render a two-column list row used by timeline sections.
    
    Args:
        left: Left column content (typically title/organization)
        right: Right column content (typically metadata like dates)
    
    Returns:
        HTML list item with timeline styling
    """
    l = _esc(str(left or "").strip())
    r = _esc(str(right or "").strip())
    return f'<li class="timeline-item"><span class="timeline-title">{l}</span><span class="timeline-meta">{r}</span></li>'

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
            if v:
                is_url = (f == "url")
                parts.append(_kv(_label_cn(f), str(v), is_url=is_url))
        body = "".join(parts)
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
        """Format inline markdown elements (bold, code, links)."""
        if not x:
            return ""
        y = _esc(x)
        # Bold: **text**
        y = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", y)
        # Inline code: `code`
        y = re.sub(r"`([^`]+)`", r"<code>\1</code>", y)
        # Links: [text](url) - enhanced with title attribute
        y = re.sub(
            r"\[(.+?)\]\((https?://[^\s\)]+)\)",
            r'<a href="\2" target="_blank" rel="noopener noreferrer" class="link" title="\2">\1</a>',
            y
        )
        # Auto-link bare URLs (http:// or https://)
        y = re.sub(
            r'(?<!href=")(?<!src=")(https?://[^\s<>"]+)',
            r'<a href="\1" target="_blank" rel="noopener noreferrer" class="link" title="\1">\1</a>',
            y
        )
        return y
    
    for ln in lines:
        if ln.strip().startswith("```"):
            if not in_code:
                in_code = True
                code_buf = []
            else:
                out.append("<pre><code>" + _esc("\n".join(code_buf)) + "</code></pre>")
                in_code = False
            continue
        if in_code:
            code_buf.append(ln)
            continue
        if re.match(r"^---+$", ln.strip()):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False
            out.append("<hr/>")
            continue
        if ln.startswith("> "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False
            out.append("<blockquote>" + fmt_inline(ln[2:]) + "</blockquote>")
            continue
        if ln.startswith("### "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False
            out.append(f"<h3>{fmt_inline(ln[4:])}</h3>")
            continue
        if ln.startswith("## "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False
            out.append(f"<h2>{fmt_inline(ln[3:])}</h2>")
            continue
        if ln.startswith("# "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False
            out.append(f"<h1>{fmt_inline(ln[2:])}</h1>")
            continue
        if re.match(r"^\d+\. ", ln):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{fmt_inline(re.sub(r'^\d+\.\s*', '', ln))}</li>")
            continue
        if ln.startswith("- "):
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{fmt_inline(ln[2:].strip())}</li>")
            continue
        if ln.strip() == "":
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False
            continue
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
    
    # Extract data
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
    
    # Phase 1-3 enhancements
    risk_assessment = data.get("risk_assessment") or {}
    authorship_analysis = data.get("authorship_analysis") or {}
    enhanced_evaluation = data.get("enhanced_evaluation") or {}
    cross_validation = data.get("cross_validation") or {}
    research_lineage = data.get("research_lineage") or {}
    productivity_timeline = data.get("productivity_timeline") or {}

    # Build basic info HTML
    bi_html = "".join([
        _kv("姓名", name),
        _kv("学历", degree),
        _kv("邮箱", contact.get("email", "")),
        _kv("电话", contact.get("phone", "")),
        _kv("位置", contact.get("location", "")),
        _kv("主页", contact.get("homepage", ""), is_url=True),
    ])

    # Education timeline
    edu_rows = []
    for e in education:
        school = e.get("school", "")
        degree_info = e.get("degree", "")
        major = e.get("major", "")
        period = e.get("time_period", "")
        meta_parts = [x for x in [degree_info, major, period] if x]
        meta = " • ".join(meta_parts)
        if school or meta:
            edu_rows.append(_li_row(school, meta))
    edu_list_html = "".join(edu_rows)

    # Work experience timeline
    work_rows = []
    for w in work:
        company = w.get("company", "")
        title = w.get("title", "")
        period = w.get("time_period", "")
        meta_parts = [x for x in [title, period] if x]
        meta = " • ".join(meta_parts)
        if company or meta:
            work_rows.append(_li_row(company, meta))
    work_list_html = "".join(work_rows)

    # Internships timeline
    intern_rows = []
    for i in internships:
        comp = i.get("company", "")
        title = i.get("title", "")
        period = i.get("time_period", "")
        meta_parts = [x for x in [title, period] if x]
        meta = " • ".join(meta_parts)
        if comp or meta:
            intern_rows.append(_li_row(comp, meta))
    internships_list_html = "".join(intern_rows)

    # Publications with enhanced display and proper link handling
    pubs_html = ""
    for idx, p in enumerate(publications, 1):
        title = _esc(p.get('title', ''))
        venue = p.get('venue', '')
        url = p.get('url', '')
        date = p.get('date', '')
        summary = p.get('summary', '')
        abstract = p.get('abstract', '')
        authors = p.get('authors', '')
        
        card_html = f"<li class='card publication-card'>"
        
        # Title with optional numbering
        if title:
            card_html += f"<div class='card-title'><span class='pub-number'>#{idx}</span> {title}</div>"
        
        # Metadata line
        meta_items = []
        if authors and str(authors).strip():
            # Truncate long author lists
            authors_str = str(authors).strip()
            if len(authors_str) > 100:
                authors_str = authors_str[:97] + "..."
            meta_items.append(f"<span class='authors'>{_esc(authors_str)}</span>")
        if venue:
            meta_items.append(f"<span class='venue'>{_esc(venue)}</span>")
        if date:
            meta_items.append(f"<span class='date'>{_esc(date)}</span>")
        
        if meta_items:
            card_html += f"<div class='pub-meta'>{' • '.join(meta_items)}</div>"
        
        # URL as a button-style link
        if url:
            card_html += f"<div class='pub-actions'>{_url_link(url, '📄 查看论文')} {_url_link(url, '🔗 复制链接', max_length=0)}</div>"
        
        # Summary section
        if summary:
            card_html += f"<div class='summary'><div class='chip'>📝 AI总结</div><div class='content'>{_md(summary)}</div></div>"
        
        # Collapsible abstract
        if abstract:
            card_html += f"<details class='abstract-details'><summary>📖 查看完整摘要</summary><div class='abstract-content'>{_esc(abstract)}</div></details>"
        
        card_html += "</li>"
        pubs_html += card_html

    # Awards
    awards_html = ""
    for a in awards:
        name_val = _esc(a.get('name', ''))
        date_val = a.get('date', '')
        intro = a.get('intro', '')
        
        if name_val or date_val or intro:
            awards_html += f"<li class='card'>"
            if name_val:
                awards_html += f"<div class='card-title'>{name_val}</div>"
            if date_val:
                awards_html += f"<div class='meta'>{_esc(date_val)}</div>"
            if intro:
                awards_html += f"<div class='content'>{_esc(intro)}</div>"
            awards_html += "</li>"

    # Evaluation cards
    eval_cards = []
    order = ["学术创新力", "工程实战力", "行业影响力", "合作协作", "综合素质"]
    for k in order:
        v = md_eval.get(k)
        if isinstance(v, dict):
            text = str(v.get("evaluation") or v.get("desc") or "")
            srcs = v.get("evidence_sources") or []
        else:
            text = str(v or "")
            srcs = []
        score = scores.get(k, "")
        
        card = f"<div class='card eval-card'>"
        card += f"<div class='card-title'>{_esc(k)}"
        if score:
            card += f"<span class='score-badge'>{_esc(str(score))}</span>"
        card += "</div>"
        if text:
            card += f"<div class='eval-content'>{_md(text)}</div>"
        if srcs:
            src_list = "<br>".join([_esc(str(x)) for x in srcs[:3]])
            card += f"<details class='evidence'><summary>证据来源</summary><div class='evidence-content'>{src_list}</div></details>"
        card += "</div>"
        eval_cards.append(card)
    eval_html = "".join(eval_cards)

    # Social presence cards
    sp_cards = []
    for sp in social_presence:
        plat = sp.get("platform", "")
        acct = sp.get("account", "")
        url = sp.get("url", "")
        foll = sp.get("followers", "")
        freq = sp.get("posts_per_month", "")
        topics = sp.get("topics", "")
        
        if plat or acct or url:
            card = f"<div class='card social-card'>"
            if plat:
                card += f"<div class='card-title'>{_esc(plat)}</div>"
            if acct:
                card += _kv("账号", acct)
            if url:
                card += f"<div class='kv'><span class='k'>链接：</span><span class='v'>{_url_link(url)}</span></div>"
            if foll:
                card += _kv("粉丝", foll)
            if freq:
                card += _kv("频率", freq + "/月")
            if topics:
                card += f"<div class='topics'><div class='chip'>话题</div><div class='content'>{_esc(topics)}</div></div>"
            card += "</div>"
            sp_cards.append(card)
    social_cards = "".join(sp_cards)
    
    # Social influence block
    si_summary = social_influence.get("summary", "") if isinstance(social_influence, dict) else ""
    si_signals = social_influence.get("signals", []) if isinstance(social_influence, dict) else []
    si_block = ""
    if si_summary or si_signals:
        si_block = "<div class='card'><div class='card-title'>影响力</div>"
        if si_summary:
            si_block += f"<div class='content'>{_esc(si_summary)}</div>"
        if si_signals:
            sig_html = "".join([f"<li>{_esc(str(s))}</li>" for s in si_signals[:5]])
            si_block += f"<ul class='signal-list'>{sig_html}</ul>"
        si_block += "</div>"

    # Network graph
    ng_nodes = (network_graph.get("nodes") if isinstance(network_graph, dict) else []) or []
    ng_tags = (network_graph.get("circle_tags") if isinstance(network_graph, dict) else []) or []
    ng_metrics = (network_graph.get("centrality_metrics") if isinstance(network_graph, dict) else {}) or {}
    
    nodes_html = ""
    for n in ng_nodes[:6]:
        nm = n.get("name", "")
        rl = n.get("role", "")
        aff = n.get("affiliation", "")
        if nm:
            parts = [_esc(nm)]
            if rl:
                parts.append(f"({_esc(rl)})")
            if aff:
                parts.append(f"• {_esc(aff)}")
            nodes_html += f"<li class='network-node'>{' '.join(parts)}</li>"
    
    tags_html = "".join([f"<span class='tag'>{_esc(t)}</span>" for t in ng_tags[:8]])
    
    network_cards = ""
    if nodes_html:
        network_cards += f"<div class='card'><div class='card-title'>核心成员</div><ul class='network-list'>{nodes_html}</ul></div>"
    if tags_html:
        network_cards += f"<div class='card'><div class='card-title'>圈层标签</div><div class='tags-container'>{tags_html}</div></div>"
    if ng_metrics:
        deg = ng_metrics.get("degree", "")
        cw = ng_metrics.get("coauthor_weight", "")
        if deg or cw:
            network_cards += f"<div class='card'><div class='card-title'>中心性指标</div>{_kv('度', str(deg))}{_kv('合著权重', str(cw))}</div>"

    # Skills
    skills_html = ""
    if skills.get('tech_stack'):
        skills_html += f"<li class='card'><div class='card-title'>技术栈</div><div class='content'>{_esc(', '.join(skills['tech_stack']))}</div></li>"
    if skills.get('languages'):
        skills_html += f"<li class='card'><div class='card-title'>语言能力</div><div class='content'>{_esc(', '.join(skills['languages']))}</div></li>"
    if skills.get('general'):
        skills_html += f"<li class='card'><div class='card-title'>其他技能</div><div class='content'>{_esc(', '.join(skills['general']))}</div></li>"

    # Honors
    honors_html = ""
    if honors:
        for h in honors:
            h_name = h.get('name', '')
            h_date = h.get('date', '')
            if h_name or h_date:
                honors_html += f"<li class='card'>"
                if h_name:
                    honors_html += f"<div class='card-title'>{_esc(h_name)}</div>"
                if h_date:
                    honors_html += f"<div class='meta'>{_esc(h_date)}</div>"
                honors_html += "</li>"
    else:
        honors_html = "<li class='card empty-card'><div class='content'>暂无</div></li>"

    # Others
    others_html = f"<div class='card'><div class='content'>{_esc(others)}</div></div>" if others else "<div class='card empty-card'><div class='content'>暂无</div></div>"

    # ========== Phase 1: Risk Assessment HTML ==========
    risk_html = ""
    if risk_assessment:
        summary = risk_assessment.get("summary", {})
        risks_by_severity = risk_assessment.get("risks", {})
        
        # Summary card
        risk_html += "<div class='card risk-summary-card'>"
        risk_html += "<div class='card-title'>🚨 风险总览</div>"
        risk_html += f"<div class='risk-stats'>"
        risk_html += f"<div class='risk-stat critical'><span class='num'>{summary.get('critical_count', 0)}</span><span class='label'>严重</span></div>"
        risk_html += f"<div class='risk-stat high'><span class='num'>{summary.get('high_count', 0)}</span><span class='label'>高风险</span></div>"
        risk_html += f"<div class='risk-stat medium'><span class='num'>{summary.get('medium_count', 0)}</span><span class='label'>中风险</span></div>"
        risk_html += f"<div class='risk-stat low'><span class='num'>{summary.get('low_count', 0)}</span><span class='label'>低风险</span></div>"
        risk_html += "</div></div>"
        
        # Display risks by severity level
        severity_labels = {
            "critical": ("🔴 严重风险", "CRITICAL"),
            "high": ("🟠 高风险", "HIGH"),
            "medium": ("🟡 中风险", "MEDIUM"),
            "low": ("🟢 低风险", "LOW")
        }
        
        for severity_key, (severity_label, severity_val) in severity_labels.items():
            risk_list = risks_by_severity.get(severity_key, [])
            if risk_list:
                risk_html += f"<div class='card risk-category-card'>"
                risk_html += f"<div class='card-title'>{severity_label}</div>"
                
                for risk in risk_list[:5]:  # Show top 5 per severity
                    title = risk.get("title", "")
                    detail = risk.get("detail", "")
                    implication = risk.get("implication", "")
                    mitigation = risk.get("mitigation", [])
                    category = risk.get("category", "")
                    
                    risk_html += f"<div class='risk-item {severity_key}'>"
                    risk_html += f"<div class='risk-header'>"
                    risk_html += f"<span class='badge'>{severity_val}</span>"
                    if category:
                        risk_html += f"<span class='category-tag'>{_esc(category)}</span>"
                    risk_html += f"</div>"
                    risk_html += f"<div class='risk-title'><strong>{_esc(title)}</strong></div>"
                    if detail:
                        risk_html += f"<div class='risk-desc'>📊 {_esc(detail)}</div>"
                    if implication:
                        risk_html += f"<div class='risk-implication'>⚠️ {_esc(implication)}</div>"
                    if mitigation:
                        risk_html += "<div class='risk-mitigation'>💡 <strong>建议措施:</strong><ul>"
                        for m in mitigation[:3]:
                            risk_html += f"<li>{_esc(m)}</li>"
                        risk_html += "</ul></div>"
                    risk_html += "</div>"
                
                risk_html += "</div>"
    
    # ========== Phase 2: Authorship Analysis HTML ==========
    authorship_html = ""
    if authorship_analysis:
        metrics = authorship_analysis.get("metrics", {})
        patterns = authorship_analysis.get("patterns", {})
        
        # Metrics card
        authorship_html += "<div class='card authorship-metrics-card'>"
        authorship_html += "<div class='card-title'>📊 作者贡献指标</div>"
        authorship_html += f"<div class='metric-row'>"
        authorship_html += f"<div class='metric-item'><div class='label'>独立性得分</div><div class='value score-{int(metrics.get('independence_score', 0) * 10)}'>{metrics.get('independence_score', 0):.2f}</div></div>"
        
        first_author = metrics.get("first_author", {})
        authorship_html += f"<div class='metric-item'><div class='label'>第一作者</div><div class='value'>{first_author.get('count', 0)} ({first_author.get('rate', 0):.1%})</div></div>"
        
        corresponding = metrics.get("corresponding_author", {})
        authorship_html += f"<div class='metric-item'><div class='label'>通讯作者</div><div class='value'>{corresponding.get('count', 0)} ({corresponding.get('rate', 0):.1%})</div></div>"
        
        solo = metrics.get("solo_authored", {})
        authorship_html += f"<div class='metric-item'><div class='label'>独著论文</div><div class='value'>{solo.get('count', 0)} ({solo.get('rate', 0):.1%})</div></div>"
        authorship_html += f"</div></div>"
        
        # Patterns card
        if patterns:
            authorship_html += "<div class='card authorship-patterns-card'>"
            authorship_html += "<div class='card-title'>📈 合作模式</div>"
            
            collab_pattern = patterns.get("collaboration_pattern", "")
            if collab_pattern:
                authorship_html += f"<div class='pattern-item'><strong>合作模式:</strong> {_esc(collab_pattern)}</div>"
            
            career_trajectory = patterns.get("career_trajectory", "")
            if career_trajectory:
                authorship_html += f"<div class='pattern-item'><strong>职业轨迹:</strong> {_esc(career_trajectory)}</div>"
            
            authorship_html += "</div>"
    
    # ========== Phase 2: Evidence Chain HTML ==========
    evidence_html = ""
    if enhanced_evaluation:
        for dim_name, dim_data in list(enhanced_evaluation.items())[:5]:  # Show top 5 dimensions
            if isinstance(dim_data, dict):
                evidence_html += f"<div class='card evidence-card'>"
                evidence_html += f"<div class='card-title'>🔍 {_esc(dim_name)}</div>"
                
                claims = dim_data.get("claims", [])
                for claim in claims[:3]:  # Show top 3 claims per dimension
                    claim_text = claim.get("claim", "")
                    confidence = claim.get("confidence_score", 0)
                    evidence_list = claim.get("evidence", [])
                    
                    evidence_html += f"<div class='claim-item'>"
                    evidence_html += f"<div class='claim-text'>{_esc(claim_text)}</div>"
                    evidence_html += f"<div class='confidence-bar'><div class='confidence-fill' style='width: {confidence * 100}%'></div><span class='confidence-text'>{confidence:.0%}</span></div>"
                    
                    if evidence_list:
                        evidence_html += "<ul class='evidence-list'>"
                        for ev in evidence_list[:3]:
                            ev_type = ev.get("type", "")
                            ev_desc = ev.get("description", "")
                            ev_url = ev.get("url", "")
                            
                            evidence_html += f"<li class='evidence-item'>"
                            evidence_html += f"<span class='ev-type'>{_esc(ev_type)}</span>: {_esc(ev_desc)}"
                            if ev_url:
                                evidence_html += f" {_url_link(ev_url, '🔗')}"
                            evidence_html += "</li>"
                        evidence_html += "</ul>"
                    evidence_html += "</div>"
                
                evidence_html += "</div>"
    
    # ========== Phase 2: Cross Validation HTML ==========
    cross_val_html = ""
    if cross_validation:
        consistency_score = cross_validation.get("consistency_score", 0)
        inconsistencies = cross_validation.get("inconsistencies", [])
        
        # Consistency card
        cross_val_html += "<div class='card cross-val-summary-card'>"
        cross_val_html += "<div class='card-title'>✅ 一致性检验</div>"
        cross_val_html += f"<div class='consistency-meter'>"
        cross_val_html += f"<div class='meter-fill' style='width: {consistency_score * 100}%'></div>"
        cross_val_html += f"<span class='meter-text'>{consistency_score:.0%}</span>"
        cross_val_html += "</div>"
        
        if inconsistencies:
            cross_val_html += f"<div class='inconsistency-count'>⚠️ 发现 {len(inconsistencies)} 处潜在矛盾</div>"
        else:
            cross_val_html += "<div class='all-consistent'>✨ 学术与社交信号高度一致</div>"
        cross_val_html += "</div>"
        
        # Inconsistencies
        if inconsistencies:
            cross_val_html += "<div class='card inconsistencies-card'>"
            cross_val_html += "<div class='card-title'>⚠️ 矛盾分析</div>"
            for incons in inconsistencies[:5]:
                cross_val_html += f"<div class='inconsistency-item'>"
                cross_val_html += f"<div class='incons-type'>{_esc(incons.get('type', ''))}</div>"
                cross_val_html += f"<div class='incons-desc'>{_esc(incons.get('description', ''))}</div>"
                cross_val_html += "</div>"
            cross_val_html += "</div>"
    
    # ========== Phase 3: Research Lineage HTML ==========
    lineage_html = ""
    if research_lineage:
        # Summary card
        lineage_html += "<div class='card lineage-summary-card'>"
        lineage_html += "<div class='card-title'>🎓 研究脉络总览</div>"
        lineage_html += f"<div class='lineage-metrics'>"
        lineage_html += f"<div class='metric-item'><span class='label'>连续性得分</span><span class='value'>{research_lineage.get('continuity_score', 0):.2f}</span></div>"
        lineage_html += f"<div class='metric-item'><span class='label'>研究成熟度</span><span class='value'>{_esc(research_lineage.get('research_maturity', 'Unknown')[:30])}</span></div>"
        lineage_html += "</div>"
        lineage_html += f"<div class='coherence-assessment'>{_esc(research_lineage.get('coherence_assessment', ''))}</div>"
        lineage_html += "</div>"
        
        # Academic lineage
        academic_lineage = research_lineage.get("academic_lineage", {})
        if academic_lineage:
            phd_sup = academic_lineage.get("phd_supervisor")
            if phd_sup:
                lineage_html += "<div class='card supervisor-card'>"
                lineage_html += "<div class='card-title'>👨‍🏫 PhD 导师</div>"
                lineage_html += f"<div class='supervisor-info'>"
                lineage_html += f"<div class='sup-name'>{_esc(phd_sup.get('name', ''))}</div>"
                lineage_html += f"<div class='sup-inst'>{_esc(phd_sup.get('institution', ''))}</div>"
                if phd_sup.get('year'):
                    lineage_html += f"<div class='sup-year'>{phd_sup.get('year')}</div>"
                lineage_html += "</div>"
                lineage_html += f"<div class='influence'>影响力: {_esc(academic_lineage.get('supervisor_influence', 'Unknown'))}</div>"
                lineage_html += f"<div class='prestige'>谱系声望: {_esc(academic_lineage.get('lineage_prestige', 'Unknown'))}</div>"
                lineage_html += "</div>"
        
        # Research trajectory
        trajectory = research_lineage.get("research_trajectory", {})
        if trajectory:
            stages = trajectory.get("career_stages", [])
            lineage_html += "<div class='card trajectory-card'>"
            lineage_html += "<div class='card-title'>📈 研究轨迹</div>"
            lineage_html += f"<div class='evolution-text'>{_esc(trajectory.get('research_evolution', ''))}</div>"
            
            if stages:
                lineage_html += "<div class='stages-timeline'>"
                for stage in stages:
                    lineage_html += f"<div class='stage-item'>"
                    lineage_html += f"<div class='stage-header'><strong>{_esc(stage.get('stage', ''))}</strong> <span class='years'>({_esc(stage.get('years', ''))})</span></div>"
                    lineage_html += f"<div class='stage-stats'>{stage.get('publication_count', 0)} 篇论文</div>"
                    topics = stage.get('main_topics', [])
                    if topics:
                        lineage_html += f"<div class='stage-topics'>主题: {', '.join([_esc(t) for t in topics[:3]])}</div>"
                    lineage_html += "</div>"
                lineage_html += "</div>"
            lineage_html += "</div>"
        
        # Topic evolution
        topic_evo = research_lineage.get("topic_evolution", {})
        if topic_evo:
            lineage_html += "<div class='card topic-evolution-card'>"
            lineage_html += "<div class='card-title'>🔬 主题演变</div>"
            
            sustained = topic_evo.get("sustained_topics", [])
            if sustained:
                lineage_html += f"<div class='topic-group sustained'>"
                lineage_html += f"<div class='topic-label'>🟢 持续主题</div>"
                lineage_html += f"<div class='topic-tags'>{', '.join([_esc(t) for t in sustained])}</div>"
                lineage_html += "</div>"
            
            emerging = topic_evo.get("emerging_topics", [])
            if emerging:
                lineage_html += f"<div class='topic-group emerging'>"
                lineage_html += f"<div class='topic-label'>🆕 新兴主题</div>"
                lineage_html += f"<div class='topic-tags'>{', '.join([_esc(t) for t in emerging])}</div>"
                lineage_html += "</div>"
            
            abandoned = topic_evo.get("abandoned_topics", [])
            if abandoned:
                lineage_html += f"<div class='topic-group abandoned'>"
                lineage_html += f"<div class='topic-label'>⏸️ 放弃主题</div>"
                lineage_html += f"<div class='topic-tags'>{', '.join([_esc(t) for t in abandoned])}</div>"
                lineage_html += "</div>"
            
            lineage_html += f"<div class='diversity-trend'>{_esc(topic_evo.get('topic_diversity_trend', ''))}</div>"
            lineage_html += "</div>"
    
    # ========== Phase 3: Productivity Timeline HTML ==========
    productivity_html = ""
    if productivity_timeline:
        # Summary card
        productivity_html += "<div class='card productivity-summary-card'>"
        productivity_html += "<div class='card-title'>📊 生产力总览</div>"
        prod_score = productivity_timeline.get("productivity_score", 0)
        productivity_html += f"<div class='prod-score'><span class='score-num'>{prod_score:.1f}</span><span class='score-max'>/10</span></div>"
        productivity_html += f"<div class='trend-assessment'>{_esc(productivity_timeline.get('trend_assessment', ''))}</div>"
        productivity_html += f"<div class='recent-trend'>近期趋势: {_esc(productivity_timeline.get('recent_trend', ''))}</div>"
        productivity_html += "</div>"
        
        # Publication timeline
        pub_timeline = productivity_timeline.get("publication_timeline", {})
        if pub_timeline:
            annual_counts = pub_timeline.get("annual_counts", [])
            if annual_counts:
                productivity_html += "<div class='card pub-timeline-card'>"
                productivity_html += "<div class='card-title'>📅 年度发表统计</div>"
                productivity_html += "<div class='timeline-chart'>"
                max_count = max([item.get("count", 0) for item in annual_counts]) if annual_counts else 1
                for item in annual_counts[-10:]:  # Show last 10 years
                    year = item.get("year", "")
                    count = item.get("count", 0)
                    height_pct = (count / max_count * 100) if max_count > 0 else 0
                    productivity_html += f"<div class='timeline-bar-wrapper'>"
                    productivity_html += f"<div class='timeline-bar' style='height: {height_pct}%' title='{year}: {count} 篇'></div>"
                    productivity_html += f"<div class='timeline-year'>{year}</div>"
                    productivity_html += "</div>"
                productivity_html += "</div>"
                productivity_html += f"<div class='timeline-stats'>"
                productivity_html += f"<span>总计: {pub_timeline.get('total_publications', 0)} 篇</span> • "
                productivity_html += f"<span>年均: {pub_timeline.get('avg_per_year', 0):.1f} 篇</span> • "
                productivity_html += f"<span>增长率: {pub_timeline.get('growth_rate', 'Unknown')}</span>"
                productivity_html += "</div>"
                productivity_html += "</div>"
        
        # Quality-quantity balance
        balance = productivity_timeline.get("quality_quantity_balance", {})
        if balance:
            productivity_html += "<div class='card balance-card'>"
            productivity_html += "<div class='card-title'>⚖️ 质量-数量平衡</div>"
            productivity_html += f"<div class='balance-metrics'>"
            productivity_html += f"<div class='balance-item'><span class='label'>质量得分</span><span class='value'>{balance.get('quality_score', 0):.1f}</span></div>"
            productivity_html += f"<div class='balance-item'><span class='label'>数量得分</span><span class='value'>{balance.get('quantity_score', 0):.1f}</span></div>"
            productivity_html += f"<div class='balance-item'><span class='label'>平衡得分</span><span class='value'>{balance.get('balance_score', 0):.1f}</span></div>"
            productivity_html += "</div>"
            productivity_html += f"<div class='balance-assessment'>{_esc(balance.get('balance_assessment', ''))}</div>"
            productivity_html += "</div>"
        
        # Peak period
        peak = productivity_timeline.get("peak_productivity_period")
        if peak:
            productivity_html += "<div class='card peak-period-card'>"
            productivity_html += "<div class='card-title'>🌟 高峰生产力期</div>"
            years = peak.get("years", [])
            if years:
                productivity_html += f"<div class='peak-years'>{', '.join([str(y) for y in years])}</div>"
            productivity_html += f"<div class='peak-stats'>{peak.get('publication_count', 0)} 篇论文</div>"
            productivity_html += f"<div class='peak-assessment'>{_esc(peak.get('assessment', ''))}</div>"
            productivity_html += "</div>"
        
        # Future prediction
        prediction = productivity_timeline.get("prediction", {})
        if prediction:
            productivity_html += "<div class='card prediction-card'>"
            productivity_html += "<div class='card-title'>🔮 未来预测</div>"
            productivity_html += f"<div class='prediction-trend'>{_esc(prediction.get('expected_trend', ''))}</div>"
            productivity_html += f"<div class='prediction-confidence'>置信度: {_esc(prediction.get('confidence', ''))}</div>"
            recommendations = prediction.get("recommendations", [])
            if recommendations:
                productivity_html += "<div class='recommendations'>"
                productivity_html += "<div class='rec-title'>💡 建议</div>"
                for rec in recommendations:
                    productivity_html += f"<div class='rec-item'>• {_esc(rec)}</div>"
                productivity_html += "</div>"
            productivity_html += "</div>"

    # Metrics
    metrics_html = f"""
        <div class='metric-card'>
            <div class='metric-num'>{len(publications)}</div>
            <div class='metric-label'>论文</div>
        </div>
        <div class='metric-card'>
            <div class='metric-num'>{len(awards)}</div>
            <div class='metric-label'>奖项</div>
        </div>
        <div class='metric-card'>
            <div class='metric-num'>{len(prof_sources)}</div>
            <div class='metric-label'>来源</div>
        </div>
    """

    # Modern CSS with enhanced styling and better visual hierarchy
    style = """
    :root {
        --color-primary: #3b82f6;
        --color-primary-dark: #2563eb;
        --color-primary-light: #60a5fa;
        --color-success: #10b981;
        --color-warning: #f59e0b;
        --color-bg: #f8fafc;
        --color-surface: #ffffff;
        --color-text: #0f172a;
        --color-text-secondary: #64748b;
        --color-text-muted: #94a3b8;
        --color-border: #e2e8f0;
        --color-border-light: #f1f5f9;
        --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
        --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
        --shadow-hover: 0 12px 24px -8px rgb(0 0 0 / 0.15);
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
        --transition-fast: 150ms ease;
        --transition-normal: 250ms ease;
    }

    * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
        background: var(--color-bg);
        color: var(--color-text);
        line-height: 1.6;
        overflow-x: hidden;
    }

    .page {
        max-width: 1400px;
        margin: 0 auto;
    }

    .layout {
        display: grid;
        grid-template-columns: 280px 1fr;
        min-height: 100vh;
        gap: 0;
    }

    /* Sidebar */
    .sidebar {
        background: var(--color-surface);
        border-right: 1px solid var(--color-border);
        padding: 32px 24px;
        position: sticky;
        top: 0;
        height: 100vh;
        overflow-y: auto;
        overflow-x: hidden;
    }
    
    .sidebar::-webkit-scrollbar {
        width: 6px;
    }
    
    .sidebar::-webkit-scrollbar-track {
        background: var(--color-bg);
    }
    
    .sidebar::-webkit-scrollbar-thumb {
        background: var(--color-border);
        border-radius: 3px;
    }
    
    .sidebar::-webkit-scrollbar-thumb:hover {
        background: var(--color-text-muted);
    }

    .title {
        font-size: 22px;
        font-weight: 700;
        color: var(--color-text);
        margin-bottom: 8px;
    }

    .subtitle {
        font-size: 14px;
        color: var(--color-text-secondary);
        margin-bottom: 24px;
        padding-bottom: 24px;
        border-bottom: 1px solid var(--color-border-light);
    }

    .nav {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .nav a {
        display: block;
        padding: 10px 14px;
        color: var(--color-text-secondary);
        text-decoration: none;
        border-radius: var(--radius-sm);
        font-size: 14px;
        transition: all 0.2s ease;
    }

    .nav a:hover {
        background: var(--color-bg);
        color: var(--color-primary);
        transform: translateX(2px);
    }

    /* Main content */
    .content {
        padding: 48px 40px;
        background: var(--color-bg);
    }

    .section {
        margin-bottom: 48px;
    }

    h2 {
        font-size: 24px;
        font-weight: 700;
        color: var(--color-text);
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 12px;
        padding-bottom: 12px;
        border-bottom: 2px solid var(--color-border-light);
    }
    
    h3 {
        font-size: 18px;
        font-weight: 600;
        color: var(--color-text);
        margin: 16px 0 12px 0;
    }
    
    h1, h2, h3 {
        line-height: 1.3;
    }

    /* Card system - Enhanced with better shadows and hover effects */
    .card {
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-md);
        padding: 24px;
        box-shadow: var(--shadow-sm);
        transition: all var(--transition-normal);
        overflow: hidden;
    }

    .card:hover {
        box-shadow: var(--shadow-hover);
        border-color: var(--color-primary-light);
        transform: translateY(-2px);
    }
    
    .card > *:last-child {
        margin-bottom: 0;
    }

    .card-title {
        font-size: 18px;
        font-weight: 600;
        color: var(--color-text);
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .cards {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
        gap: 20px;
        list-style: none;
    }

    /* Key-value pairs - Enhanced word wrapping */
    .kv {
        display: flex;
        gap: 8px;
        margin-bottom: 12px;
        font-size: 14px;
        line-height: 1.6;
        align-items: flex-start;
    }

    .kv .k {
        color: var(--color-text-secondary);
        font-weight: 500;
        min-width: 80px;
        flex-shrink: 0;
    }

    .kv .v {
        color: var(--color-text);
        flex: 1;
        word-wrap: break-word;
        word-break: break-word;
        overflow-wrap: break-word;
        min-width: 0;
    }
    
    .kv:last-child {
        margin-bottom: 0;
    }

    /* Links - Enhanced with better word breaking and hover effects */
    .link {
        color: var(--color-primary);
        text-decoration: none;
        word-wrap: break-word;
        word-break: break-word;
        overflow-wrap: break-word;
        hyphens: auto;
        transition: all var(--transition-fast);
        display: inline;
        position: relative;
    }

    .link:hover {
        color: var(--color-primary-dark);
        text-decoration: underline;
    }
    
    .link:active {
        color: var(--color-primary-dark);
    }
    
    /* Ensure long URLs don't overflow containers */
    .link[href*="://"] {
        max-width: 100%;
        overflow-wrap: anywhere;
    }

    /* Timeline */
    .timeline-item {
        display: flex;
        justify-content: space-between;
        gap: 16px;
        padding: 16px 0 16px 20px;
        position: relative;
        border-left: 2px solid var(--color-border);
    }

    .timeline-item::before {
        content: "";
        position: absolute;
        left: -6px;
        top: 20px;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: var(--color-primary);
        border: 2px solid var(--color-surface);
    }

    .timeline-title {
        font-weight: 600;
        color: var(--color-text);
        flex: 1;
    }

    .timeline-meta {
        color: var(--color-text-secondary);
        font-size: 14px;
        text-align: right;
    }

    /* Publications - Enhanced styling */
    .publication-card {
        padding: 20px;
        border-left: 3px solid var(--color-primary);
    }
    
    .publication-card .card-title {
        font-size: 16px;
        line-height: 1.5;
        display: flex;
        align-items: flex-start;
        gap: 8px;
    }
    
    .pub-number {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 32px;
        height: 24px;
        padding: 0 8px;
        border-radius: 12px;
        background: var(--color-primary);
        color: white;
        font-size: 12px;
        font-weight: 600;
        flex-shrink: 0;
    }

    .pub-meta {
        color: var(--color-text-secondary);
        font-size: 13px;
        margin: 12px 0;
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        line-height: 1.6;
    }
    
    .authors {
        color: var(--color-text);
        font-weight: 500;
    }

    .venue {
        font-style: italic;
        color: var(--color-primary);
    }
    
    .date {
        color: var(--color-text-muted);
    }
    
    .pub-actions {
        display: flex;
        gap: 12px;
        margin: 12px 0;
        flex-wrap: wrap;
    }
    
    .pub-actions .link {
        display: inline-block;
        padding: 8px 16px;
        background: var(--color-primary);
        color: white;
        border-radius: var(--radius-sm);
        font-size: 13px;
        font-weight: 500;
        transition: all var(--transition-fast);
    }
    
    .pub-actions .link:hover {
        background: var(--color-primary-dark);
        transform: translateY(-1px);
        box-shadow: var(--shadow-md);
        text-decoration: none;
    }

    .summary {
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid var(--color-border-light);
    }

    .summary .content {
        margin-top: 8px;
        color: var(--color-text-secondary);
        font-size: 14px;
        line-height: 1.7;
    }

    .abstract-details {
        margin-top: 12px;
        cursor: pointer;
    }

    .abstract-details summary {
        color: var(--color-primary);
        font-size: 14px;
        font-weight: 500;
        list-style: none;
        cursor: pointer;
        user-select: none;
        padding: 8px 12px;
        background: var(--color-bg);
        border-radius: var(--radius-sm);
        transition: all var(--transition-fast);
    }
    
    .abstract-details summary:hover {
        background: var(--color-border-light);
    }

    .abstract-details summary::-webkit-details-marker {
        display: none;
    }

    .abstract-content {
        margin-top: 12px;
        padding: 16px;
        background: var(--color-bg);
        border-radius: var(--radius-sm);
        color: var(--color-text-secondary);
        font-size: 14px;
        line-height: 1.7;
        white-space: pre-wrap;
        word-wrap: break-word;
        word-break: break-word;
        overflow-wrap: break-word;
        max-height: 400px;
        overflow-y: auto;
    }
    
    .abstract-content::-webkit-scrollbar {
        width: 6px;
    }
    
    .abstract-content::-webkit-scrollbar-track {
        background: var(--color-border-light);
        border-radius: 3px;
    }
    
    .abstract-content::-webkit-scrollbar-thumb {
        background: var(--color-border);
        border-radius: 3px;
    }

    /* Chips and badges */
    .chip {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 999px;
        background: var(--color-bg);
        color: var(--color-text-secondary);
        font-size: 12px;
        font-weight: 500;
    }

    .score-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 48px;
        height: 32px;
        padding: 0 12px;
        border-radius: 999px;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        font-size: 16px;
        font-weight: 700;
    }

    .hbadge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: var(--radius-sm);
        background: var(--color-bg);
        color: var(--color-text-secondary);
        font-weight: 600;
        font-size: 14px;
    }

    /* Metrics */
    .metrics {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 16px;
        margin-top: 20px;
    }

    .metric-card {
        background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
        padding: 24px;
        border-radius: var(--radius-md);
        text-align: center;
        color: white;
        box-shadow: var(--shadow-md);
    }

    .metric-num {
        font-size: 36px;
        font-weight: 700;
        line-height: 1;
        margin-bottom: 8px;
    }

    .metric-label {
        font-size: 14px;
        opacity: 0.9;
    }

    /* Evaluation cards */
    .eval-card {
        border-left: 4px solid var(--color-primary);
    }

    .eval-content {
        color: var(--color-text-secondary);
        font-size: 14px;
        line-height: 1.8;
    }

    .evidence {
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid var(--color-border-light);
    }

    .evidence summary {
        color: var(--color-text-secondary);
        font-size: 13px;
        cursor: pointer;
        user-select: none;
    }

    .evidence-content {
        margin-top: 12px;
        padding: 12px;
        background: var(--color-bg);
        border-radius: var(--radius-sm);
        font-size: 13px;
        color: var(--color-text-secondary);
        line-height: 1.6;
    }

    /* Social cards */
    .social-card {
        border-left: 4px solid var(--color-success);
    }

    .topics {
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid var(--color-border-light);
    }

    .topics .content {
        margin-top: 8px;
        color: var(--color-text-secondary);
        font-size: 14px;
    }

    /* Network */
    .network-list {
        list-style: none;
        display: flex;
        flex-direction: column;
        gap: 12px;
    }

    .network-node {
        padding: 12px;
        background: var(--color-bg);
        border-radius: var(--radius-sm);
        font-size: 14px;
        color: var(--color-text);
    }

    .tags-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 12px;
    }

    .tag {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 999px;
        background: var(--color-bg);
        color: var(--color-text);
        font-size: 13px;
        border: 1px solid var(--color-border);
    }

    /* Sources list - Enhanced styling */
    .sources {
        list-style: none;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }

    .sources li {
        padding: 14px 16px;
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-sm);
        font-size: 14px;
        display: flex;
        align-items: flex-start;
        gap: 10px;
        transition: all var(--transition-fast);
    }
    
    .sources li:hover {
        border-color: var(--color-primary);
        box-shadow: var(--shadow-sm);
    }
    
    .source-number {
        color: var(--color-text-muted);
        font-weight: 600;
        min-width: 24px;
        flex-shrink: 0;
    }

    .signal-list {
        list-style: disc;
        padding-left: 24px;
        margin-top: 12px;
        color: var(--color-text-secondary);
        font-size: 14px;
    }

    .signal-list li {
        margin-bottom: 8px;
    }

    /* Details/Summary */
    details summary {
        cursor: pointer;
        user-select: none;
        transition: color 0.2s ease;
    }

    details summary:hover {
        color: var(--color-primary);
    }

    details[open] summary {
        margin-bottom: 12px;
    }

    /* Markdown content - Enhanced readability */
    .md {
        color: var(--color-text-secondary);
        font-size: 14px;
        line-height: 1.8;
    }

    .md p {
        margin-bottom: 12px;
    }
    
    .md p:last-child {
        margin-bottom: 0;
    }

    .md strong {
        color: var(--color-text);
        font-weight: 600;
    }
    
    .md em {
        font-style: italic;
        color: var(--color-text);
    }

    .md code {
        padding: 3px 8px;
        background: var(--color-bg);
        border: 1px solid var(--color-border-light);
        border-radius: 4px;
        font-family: "Monaco", "Menlo", "Courier New", "Consolas", monospace;
        font-size: 13px;
        color: var(--color-text);
    }

    .md pre {
        padding: 16px;
        background: var(--color-bg);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-sm);
        overflow-x: auto;
        margin: 12px 0;
    }

    .md pre code {
        padding: 0;
        background: none;
        border: none;
        font-size: 13px;
    }
    
    .md ul, .md ol {
        padding-left: 24px;
        margin: 12px 0;
    }
    
    .md li {
        margin-bottom: 6px;
    }
    
    .md blockquote {
        border-left: 3px solid var(--color-primary);
        padding-left: 16px;
        margin: 12px 0;
        color: var(--color-text);
        font-style: italic;
    }
    
    .md hr {
        border: none;
        border-top: 1px solid var(--color-border);
        margin: 20px 0;
    }

    /* Text content - Enhanced wrapping and readability */
    .content {
        color: var(--color-text-secondary);
        font-size: 14px;
        line-height: 1.7;
        word-wrap: break-word;
        word-break: break-word;
        overflow-wrap: break-word;
    }

    .text {
        white-space: pre-wrap;
        word-wrap: break-word;
        word-break: break-word;
        overflow-wrap: break-word;
        color: var(--color-text-secondary);
        font-size: 14px;
        line-height: 1.7;
    }
    
    /* Ensure all text content respects container boundaries */
    p, div, span, li {
        overflow-wrap: break-word;
        word-wrap: break-word;
    }

    /* Empty state */
    .empty-card {
        text-align: center;
        color: var(--color-text-muted);
        font-style: italic;
    }

    /* Footer */
    footer {
        margin-top: 48px;
        padding-top: 24px;
        border-top: 1px solid var(--color-border);
        color: var(--color-text-muted);
        font-size: 13px;
        text-align: center;
    }

    /* Responsive design - Enhanced for better mobile experience */
    @media (max-width: 1200px) {
        .cards {
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        }
    }
    
    @media (max-width: 1024px) {
        .layout {
            grid-template-columns: 1fr;
        }
        
        .sidebar {
            position: relative;
            height: auto;
            border-right: none;
            border-bottom: 1px solid var(--color-border);
        }
        
        .cards {
            grid-template-columns: 1fr;
        }
        
        .content {
            padding: 32px 24px;
        }
    }

    @media (max-width: 640px) {
        .content {
            padding: 20px 16px;
        }
        
        .sidebar {
            padding: 20px 16px;
        }
        
        .card {
            padding: 16px;
        }
        
        h2 {
            font-size: 20px;
            margin-bottom: 16px;
        }
        
        .title {
            font-size: 18px;
        }
        
        .timeline-item {
            flex-direction: column;
            gap: 6px;
        }
        
        .timeline-meta {
            text-align: left;
            font-size: 13px;
        }
        
        .kv {
            flex-direction: column;
            gap: 4px;
        }
        
        .kv .k {
            min-width: auto;
        }
        
        .metric-num {
            font-size: 28px;
        }
    }

    /* Print styles */
    @media print {
        body {
            background: white;
        }
        
        .layout {
            grid-template-columns: 1fr;
        }
        
        .sidebar {
            display: none;
        }
        
        .card {
            break-inside: avoid;
            box-shadow: none;
        }
        
        .cards {
            grid-template-columns: 1fr;
        }
        
        .link {
            color: #000;
            text-decoration: underline;
        }
    }
    
    /* ========== Phase 1-3 Enhanced Styles ========== */
    
    /* Risk Assessment Styles */
    .risk-summary-card {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border-left: 4px solid #f59e0b;
    }
    
    .risk-stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
        gap: 1rem;
        margin-top: 1rem;
    }
    
    .risk-stat {
        text-align: center;
        padding: 1rem;
        border-radius: var(--radius-sm);
        background: rgba(255, 255, 255, 0.7);
    }
    
    .risk-stat.critical { border-left: 3px solid #dc2626; }
    .risk-stat.high { border-left: 3px solid #f59e0b; }
    .risk-stat.medium { border-left: 3px solid #fbbf24; }
    .risk-stat.low { border-left: 3px solid #10b981; }
    
    .risk-stat .num {
        display: block;
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    
    .risk-stat .label {
        font-size: 0.875rem;
        color: var(--color-text-secondary);
    }
    
    .risk-category-card {
        border-left: 3px solid #f59e0b;
    }
    
    .risk-item {
        padding: 1rem;
        margin: 0.75rem 0;
        border-radius: var(--radius-sm);
        background: #fafafa;
    }
    
    .risk-item.critical { background: #fee2e2; border-left: 3px solid #dc2626; }
    .risk-item.high { background: #fef3c7; border-left: 3px solid #f59e0b; }
    .risk-item.medium { background: #fef9c3; border-left: 3px solid #fbbf24; }
    .risk-item.low { background: #d1fae5; border-left: 3px solid #10b981; }
    
    .risk-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    .risk-header .badge {
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.9);
    }
    
    .risk-title {
        font-weight: 600;
        color: var(--color-text);
        margin-bottom: 0.5rem;
    }
    
    .risk-desc {
        color: var(--color-text);
        line-height: 1.5;
        margin-bottom: 0.5rem;
    }
    
    .risk-implication {
        margin-top: 0.5rem;
        padding: 0.5rem;
        border-radius: 4px;
        background: rgba(255, 140, 0, 0.1);
        font-size: 0.875rem;
        color: #c05621;
        line-height: 1.5;
    }
    
    .risk-mitigation {
        margin-top: 0.75rem;
        padding: 0.5rem;
        border-radius: 4px;
        background: rgba(34, 197, 94, 0.1);
        font-size: 0.875rem;
    }
    
    .risk-mitigation ul {
        margin: 0.5rem 0 0 1.25rem;
        padding: 0;
    }
    
    .risk-mitigation li {
        margin: 0.25rem 0;
        line-height: 1.5;
    }
    
    .category-tag {
        font-size: 0.75rem;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        background: rgba(99, 102, 241, 0.1);
        color: #4f46e5;
        margin-left: 0.5rem;
    }
    
    .risk-evidence {
        margin-top: 0.5rem;
        padding: 0.5rem;
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.5);
        font-size: 0.875rem;
        color: var(--color-text-secondary);
    }
    
    /* Authorship Analysis Styles */
    .authorship-metrics-card {
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        border-left: 4px solid var(--color-primary);
    }
    
    .metric-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 1rem;
        margin-top: 1rem;
    }
    
    .metric-item {
        text-align: center;
        padding: 1rem;
        border-radius: var(--radius-sm);
        background: rgba(255, 255, 255, 0.8);
    }
    
    .metric-item .label {
        display: block;
        font-size: 0.875rem;
        color: var(--color-text-secondary);
        margin-bottom: 0.5rem;
    }
    
    .metric-item .value {
        display: block;
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--color-primary);
    }
    
    .authorship-patterns-card {
        border-left: 3px solid var(--color-primary);
    }
    
    .pattern-item {
        padding: 0.75rem 0;
        line-height: 1.6;
    }
    
    .pattern-item strong {
        color: var(--color-primary);
    }
    
    /* Evidence Chain Styles */
    .evidence-card {
        border-left: 3px solid #8b5cf6;
    }
    
    .claim-item {
        padding: 1rem;
        margin: 0.75rem 0;
        border-radius: var(--radius-sm);
        background: #fafafa;
    }
    
    .claim-text {
        font-weight: 600;
        color: var(--color-text);
        margin-bottom: 0.75rem;
    }
    
    .confidence-bar {
        position: relative;
        height: 24px;
        background: #e5e7eb;
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 0.75rem;
    }
    
    .confidence-fill {
        height: 100%;
        background: linear-gradient(90deg, #8b5cf6 0%, #a78bfa 100%);
        transition: width 0.3s ease;
    }
    
    .confidence-text {
        position: absolute;
        right: 0.75rem;
        top: 50%;
        transform: translateY(-50%);
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--color-text);
    }
    
    .evidence-list {
        list-style: none;
        padding-left: 0;
    }
    
    .evidence-item {
        padding: 0.5rem 0;
        font-size: 0.875rem;
        color: var(--color-text-secondary);
        line-height: 1.5;
    }
    
    .ev-type {
        font-weight: 600;
        color: #8b5cf6;
    }
    
    /* Cross Validation Styles */
    .cross-val-summary-card {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        border-left: 4px solid var(--color-success);
    }
    
    .consistency-meter {
        position: relative;
        height: 32px;
        background: #e5e7eb;
        border-radius: 16px;
        overflow: hidden;
        margin: 1rem 0;
    }
    
    .meter-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--color-success) 0%, #34d399 100%);
        transition: width 0.3s ease;
    }
    
    .meter-text {
        position: absolute;
        right: 1rem;
        top: 50%;
        transform: translateY(-50%);
        font-size: 1rem;
        font-weight: 700;
        color: var(--color-text);
    }
    
    .inconsistency-count {
        margin-top: 0.75rem;
        padding: 0.75rem;
        border-radius: var(--radius-sm);
        background: rgba(251, 191, 36, 0.2);
        color: #92400e;
        font-weight: 600;
    }
    
    .all-consistent {
        margin-top: 0.75rem;
        padding: 0.75rem;
        border-radius: var(--radius-sm);
        background: rgba(16, 185, 129, 0.2);
        color: #065f46;
        font-weight: 600;
    }
    
    .inconsistencies-card {
        border-left: 3px solid #f59e0b;
    }
    
    .inconsistency-item {
        padding: 1rem;
        margin: 0.75rem 0;
        border-radius: var(--radius-sm);
        background: #fef3c7;
        border-left: 3px solid #f59e0b;
    }
    
    .incons-type {
        font-weight: 700;
        color: #92400e;
        margin-bottom: 0.5rem;
    }
    
    .incons-desc {
        color: var(--color-text-secondary);
        line-height: 1.5;
    }
    
    /* Research Lineage Styles */
    .lineage-summary-card {
        background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
        border-left: 4px solid #6366f1;
    }
    
    .lineage-metrics {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .lineage-metrics .metric-item {
        background: rgba(255, 255, 255, 0.8);
        padding: 1rem;
        border-radius: var(--radius-sm);
    }
    
    .coherence-assessment {
        margin-top: 1rem;
        padding: 1rem;
        border-radius: var(--radius-sm);
        background: rgba(255, 255, 255, 0.7);
        font-style: italic;
        color: var(--color-text-secondary);
    }
    
    .supervisor-card {
        border-left: 3px solid #6366f1;
    }
    
    .supervisor-info {
        padding: 1rem;
        margin: 1rem 0;
        border-radius: var(--radius-sm);
        background: #fafafa;
    }
    
    .sup-name {
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--color-text);
        margin-bottom: 0.5rem;
    }
    
    .sup-inst {
        color: var(--color-text-secondary);
        margin-bottom: 0.25rem;
    }
    
    .sup-year {
        color: var(--color-text-muted);
        font-size: 0.875rem;
    }
    
    .influence, .prestige {
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: var(--radius-sm);
        background: #f5f5f5;
        font-size: 0.875rem;
    }
    
    .trajectory-card {
        border-left: 3px solid #8b5cf6;
    }
    
    .evolution-text {
        padding: 1rem;
        margin: 1rem 0;
        border-radius: var(--radius-sm);
        background: #fafafa;
        line-height: 1.6;
        font-style: italic;
    }
    
    .stages-timeline {
        margin-top: 1rem;
    }
    
    .stage-item {
        padding: 1rem;
        margin: 0.75rem 0;
        border-radius: var(--radius-sm);
        background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
        border-left: 3px solid #8b5cf6;
    }
    
    .stage-header {
        margin-bottom: 0.5rem;
    }
    
    .stage-header strong {
        color: #6b21a8;
    }
    
    .stage-header .years {
        color: var(--color-text-muted);
        font-size: 0.875rem;
    }
    
    .stage-stats {
        font-size: 0.875rem;
        color: var(--color-text-secondary);
        margin: 0.25rem 0;
    }
    
    .stage-topics {
        font-size: 0.875rem;
        color: var(--color-text-secondary);
        margin-top: 0.5rem;
        padding-top: 0.5rem;
        border-top: 1px solid rgba(139, 92, 246, 0.2);
    }
    
    .topic-evolution-card {
        border-left: 3px solid #10b981;
    }
    
    .topic-group {
        padding: 1rem;
        margin: 0.75rem 0;
        border-radius: var(--radius-sm);
    }
    
    .topic-group.sustained {
        background: #d1fae5;
        border-left: 3px solid #10b981;
    }
    
    .topic-group.emerging {
        background: #dbeafe;
        border-left: 3px solid #3b82f6;
    }
    
    .topic-group.abandoned {
        background: #fee2e2;
        border-left: 3px solid #ef4444;
    }
    
    .topic-label {
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .topic-tags {
        color: var(--color-text-secondary);
        line-height: 1.6;
    }
    
    .diversity-trend {
        margin-top: 1rem;
        padding: 1rem;
        border-radius: var(--radius-sm);
        background: #fafafa;
        font-style: italic;
        color: var(--color-text-secondary);
    }
    
    /* Productivity Timeline Styles */
    .productivity-summary-card {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border-left: 4px solid #f59e0b;
        text-align: center;
    }
    
    .prod-score {
        font-size: 3rem;
        font-weight: 800;
        color: #92400e;
        margin: 1rem 0;
    }
    
    .prod-score .score-num {
        color: #f59e0b;
    }
    
    .prod-score .score-max {
        font-size: 1.5rem;
        color: var(--color-text-muted);
    }
    
    .trend-assessment {
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: var(--radius-sm);
        background: rgba(255, 255, 255, 0.7);
        font-weight: 600;
        color: var(--color-text);
    }
    
    .recent-trend {
        padding: 0.75rem;
        border-radius: var(--radius-sm);
        background: rgba(255, 255, 255, 0.5);
        font-size: 0.875rem;
        color: var(--color-text-secondary);
    }
    
    .pub-timeline-card {
        border-left: 3px solid #3b82f6;
    }
    
    .timeline-chart {
        display: flex;
        align-items: flex-end;
        justify-content: space-around;
        height: 200px;
        margin: 1.5rem 0;
        padding: 0 1rem;
        border-bottom: 2px solid var(--color-border);
    }
    
    .timeline-bar-wrapper {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        max-width: 60px;
    }
    
    .timeline-bar {
        width: 100%;
        min-height: 4px;
        background: linear-gradient(180deg, #3b82f6 0%, #60a5fa 100%);
        border-radius: 4px 4px 0 0;
        transition: all 0.3s ease;
    }
    
    .timeline-bar-wrapper:hover .timeline-bar {
        background: linear-gradient(180deg, #2563eb 0%, #3b82f6 100%);
        transform: scaleY(1.05);
    }
    
    .timeline-year {
        margin-top: 0.5rem;
        font-size: 0.75rem;
        color: var(--color-text-muted);
        transform: rotate(-45deg);
        white-space: nowrap;
    }
    
    .timeline-stats {
        padding: 1rem;
        border-radius: var(--radius-sm);
        background: #fafafa;
        text-align: center;
        font-size: 0.875rem;
        color: var(--color-text-secondary);
    }
    
    .balance-card {
        border-left: 3px solid #8b5cf6;
    }
    
    .balance-metrics {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .balance-item {
        text-align: center;
        padding: 1rem;
        border-radius: var(--radius-sm);
        background: #fafafa;
    }
    
    .balance-item .label {
        display: block;
        font-size: 0.875rem;
        color: var(--color-text-secondary);
        margin-bottom: 0.5rem;
    }
    
    .balance-item .value {
        display: block;
        font-size: 1.5rem;
        font-weight: 700;
        color: #8b5cf6;
    }
    
    .balance-assessment {
        padding: 1rem;
        border-radius: var(--radius-sm);
        background: #fafafa;
        font-style: italic;
        color: var(--color-text-secondary);
    }
    
    .peak-period-card {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border-left: 4px solid #f59e0b;
    }
    
    .peak-years {
        font-size: 1.5rem;
        font-weight: 700;
        color: #92400e;
        margin: 0.75rem 0;
    }
    
    .peak-stats {
        font-size: 1.125rem;
        color: var(--color-text-secondary);
        margin: 0.5rem 0;
    }
    
    .peak-assessment {
        padding: 1rem;
        margin-top: 0.75rem;
        border-radius: var(--radius-sm);
        background: rgba(255, 255, 255, 0.7);
        font-style: italic;
    }
    
    .prediction-card {
        background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
        border-left: 4px solid #6366f1;
    }
    
    .prediction-trend {
        padding: 1rem;
        margin: 0.75rem 0;
        border-radius: var(--radius-sm);
        background: rgba(255, 255, 255, 0.8);
        font-weight: 600;
        color: var(--color-text);
    }
    
    .prediction-confidence {
        padding: 0.75rem;
        border-radius: var(--radius-sm);
        background: rgba(255, 255, 255, 0.6);
        font-size: 0.875rem;
        color: var(--color-text-secondary);
    }
    
    .recommendations {
        margin-top: 1rem;
        padding: 1rem;
        border-radius: var(--radius-sm);
        background: rgba(255, 255, 255, 0.7);
    }
    
    .rec-title {
        font-weight: 700;
        color: #4338ca;
        margin-bottom: 0.5rem;
    }
    
    .rec-item {
        padding: 0.5rem 0;
        color: var(--color-text-secondary);
        line-height: 1.5;
    }
    
    """

    # Sidebar navigation
    nav_items = [
        ("basic", "基本信息"),
        ("education", "教育经历"),
        ("work", "工作经历"),
        ("internships", "实习经历"),
        ("overview", "综合评价"),
        ("review", "学术评价"),
        ("evaluation", "维度评价"),
        ("scholar", "学术指标"),
        ("risk-assessment", "风险评估"),
        ("authorship", "作者贡献分析"),
        ("evidence-chain", "证据链追溯"),
        ("cross-validation", "交叉验证"),
        ("research-lineage", "研究脉络分析"),
        ("productivity-timeline", "产出时间线分析"),
        ("publications", "论文"),
        ("awards-honors", "奖项与荣誉"),
        ("projects", "项目经验"),
        ("grants", "研究资助"),
        ("open_source", "开源贡献"),
        ("patents", "专利"),
        ("activities", "学术活动"),
        ("memberships", "组织会员"),
        ("social", "社交声量"),
        ("network", "人脉图谱"),
        ("skills", "技能"),
        ("others", "其他"),
        ("sources", "参考来源"),
    ]
    
    nav_html = "".join([f"<a href='#{anchor}'>{title}</a>" for anchor, title in nav_items])

    # Build blocks conditionally
    internships_block = f"<h2>实习经历</h2><div class='card'><ul>{internships_list_html}</ul></div>" if internships_list_html else ""
    work_block = f"<h2>工作经历</h2><div class='card'><ul>{work_list_html}</ul></div>" if work_list_html else ""
    projects_block = f"<h2>项目经验</h2><ul class='cards'>{_cards(project_experience, 'project_name', ['role', 'description'])}</ul>" if project_experience else ""
    grants_block = f"<h2>研究资助</h2><ul class='cards'>{_cards(research_grants, 'title', ['role', 'funding_source', 'time_period'])}</ul>" if research_grants else ""
    open_source_block = f"<h2>开源贡献</h2><ul class='cards'>{_cards(open_source, 'repo_name', ['role', 'metrics', 'url', 'description'])}</ul>" if open_source else ""
    patents_block = f"<h2>专利</h2><ul class='cards'>{_cards(patents, 'title', ['status', 'number'])}</ul>" if patents else ""
    activities_block = f"<h2>学术活动</h2><ul class='cards'>{_cards(academic_activities, 'activity_name', ['role', 'description'])}</ul>" if academic_activities else ""
    
    memberships_block = ""
    if memberships:
        ms_list = "".join([f"<li class='timeline-item'><span class='timeline-title'>{_esc(str(m))}</span></li>" for m in memberships if m])
        if ms_list:
            memberships_block = f"<h2>组织会员</h2><div class='card'><ul>{ms_list}</ul></div>"

    # Sources - Improved display with proper link handling
    sources_html = ""
    for idx, u in enumerate(prof_sources, 1):
        if u:
            # Extract domain for display
            try:
                from urllib.parse import urlparse
                domain = urlparse(str(u)).netloc or "链接"
                domain = domain.replace('www.', '')
            except:
                domain = "链接"
            sources_html += f"<li><span class='source-number'>{idx}.</span> {_url_link(u, f'{domain}', max_length=60)}</li>"

    # HTML template
    html_template = f"""<!doctype html>
<html lang='zh-CN'>
<head>
    <meta charset='utf-8'/>
    <meta name='viewport' content='width=device-width,initial-scale=1'/>
    <title>综合评价 - {_esc(name)}</title>
    <style>{style}</style>
</head>
<body>
<div class='page'>
<div class='layout'>
    <aside class='sidebar'>
        <div class='title'>候选人综合评价</div>
        <div class='subtitle'>姓名：{_esc(name)}{("｜学历：" + _esc(degree)) if degree else ""}</div>
        <nav class='nav'>{nav_html}</nav>
    </aside>
    <main class='content'>
        <section id='basic' class='section'>
            <h2>基本信息</h2>
            <div class='card'>{bi_html}</div>
        </section>
        
        <section id='education' class='section'>
            <h2>教育经历</h2>
            <div class='card'><ul>{edu_list_html}</ul></div>
        </section>
        
        {("<section id='work' class='section'>" + work_block + "</section>") if work_block else ""}
        {("<section id='internships' class='section'>" + internships_block + "</section>") if internships_block else ""}
        
        <section id='overview' class='section'>
            <h2>综合评价</h2>
            <div class='card'><div class='md'>{_md(overall)}</div></div>
            <div class='metrics'>{metrics_html}</div>
        </section>
        
        <section id='review' class='section'>
            <h2>学术评价</h2>
            <details class='card' open>
                <summary>点击展开/收起</summary>
                <div class='text'>{_esc(review) if review else "暂无"}</div>
            </details>
        </section>
        
        <section id='evaluation' class='section'>
            <h2>多维度评价</h2>
            <div class='cards'>{eval_html if eval_html else "<div class='card empty-card'><div class='content'>暂无</div></div>"}</div>
        </section>
        
        <section id='scholar' class='section'>
            <h2>学术指标</h2>
            <div class='cards'>
                <div class='card'>
                    <div class='card-title'>学术指标</div>
                    {_kv("h-index", str(academic_metrics.get("h_index", "")))}
                    {_kv("h10-index", str(academic_metrics.get("h10_index", "")))}
                    {_kv("总引用", str(academic_metrics.get("citations_total", "")))}
                    {_kv("近五年引用", str(academic_metrics.get("citations_recent", "")))}
                    {_kv("论文总数", str(academic_metrics.get("publications_count", ""))) if academic_metrics.get("publications_count") else ""}
                    {("<div style='margin-top: 12px; padding: 8px; background: #fff3cd; border-radius: 4px; font-size: 13px; color: #856404;'>ℹ️ 数据来源: " + str(academic_metrics.get("data_source", "")) + "</div>") if academic_metrics.get("data_source") else ""}
                </div>
            </div>
        </section>
        
        {("<section id='risk-assessment' class='section'><h2>🚨 风险评估</h2><div class='cards'>" + risk_html + "</div></section>") if risk_html else ""}
        
        {("<section id='authorship' class='section'><h2>📊 作者贡献分析</h2><div class='cards'>" + authorship_html + "</div></section>") if authorship_html else ""}
        
        {("<section id='evidence-chain' class='section'><h2>🔍 证据链追溯</h2><div class='cards'>" + evidence_html + "</div></section>") if evidence_html else ""}
        
        {("<section id='cross-validation' class='section'><h2>✅ 交叉验证</h2><div class='cards'>" + cross_val_html + "</div></section>") if cross_val_html else ""}
        
        {("<section id='research-lineage' class='section'><h2>🎓 研究脉络分析</h2><div class='cards'>" + lineage_html + "</div></section>") if lineage_html else ""}
        
        {("<section id='productivity-timeline' class='section'><h2>📊 产出时间线分析</h2><div class='cards'>" + productivity_html + "</div></section>") if productivity_html else ""}
        
        <section id='publications' class='section'>
            <h2>论文 <span class='hbadge'>{len(publications)}</span></h2>
            <ul class='cards'>{pubs_html if pubs_html else "<li class='card empty-card'><div class='content'>暂无</div></li>"}</ul>
        </section>
        
        <section id='awards-honors' class='section'>
            <h2>奖项与荣誉 <span class='hbadge'>{len(awards) + len(honors)}</span></h2>
            <ul class='cards'>{awards_html}{honors_html if honors_html and honors_html != "<li class='card empty-card'><div class='content'>暂无</div></li>" else ""}{("<li class='card empty-card'><div class='content'>暂无</div></li>" if not awards_html and (not honors_html or honors_html == "<li class='card empty-card'><div class='content'>暂无</div></li>") else "")}</ul>
        </section>
        
        {("<section id='projects' class='section'>" + projects_block + "</section>") if projects_block else ""}
        {("<section id='grants' class='section'>" + grants_block + "</section>") if grants_block else ""}
        {("<section id='open_source' class='section'>" + open_source_block + "</section>") if open_source_block else ""}
        {("<section id='patents' class='section'>" + patents_block + "</section>") if patents_block else ""}
        {("<section id='activities' class='section'>" + activities_block + "</section>") if activities_block else ""}
        {("<section id='memberships' class='section'>" + memberships_block + "</section>") if memberships_block else ""}
        
        <section id='social' class='section'>
            <h2>社交声量</h2>
            <div class='cards'>{social_cards if social_cards else "<div class='card empty-card'><div class='content'>暂无</div></div>"}</div>
            {si_block}
        </section>
        
        <section id='network' class='section'>
            <h2>人脉图谱</h2>
            <div class='cards'>{network_cards if network_cards else "<div class='card empty-card'><div class='content'>暂无</div></div>"}</div>
        </section>
        
        <section id='skills' class='section'>
            <h2>技能</h2>
            <ul class='cards'>{skills_html if skills_html else "<li class='card empty-card'><div class='content'>暂无</div></li>"}</ul>
        </section>
        
        <section id='others' class='section'>
            <h2>其他</h2>
            {others_html}
        </section>
        
        <section id='sources' class='section'>
            <h2>参考来源 <span class='hbadge'>{len(prof_sources)}</span></h2>
            <ul class='sources'>{sources_html if sources_html else "<li class='empty-card'>暂无</li>"}</ul>
        </section>
        
        <footer>自动生成报告 • {_esc(name)}</footer>
    </main>
</div>
</div>
</body>
</html>"""

    out_html = Path(final_json_path).parent / "resume_final.html"
    out_html.write_text(html_template, encoding="utf-8")
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
            subprocess.run([wk, html_path, str(out_pdf)], check=True, timeout=300)
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
        content_stream += f"BT /F1 12 Tf 72 {y-14*(i+1)} Td (" + ln.replace("(", "[").replace(")", "]") + ") Tj ET\n"
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
