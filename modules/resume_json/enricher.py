import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import concurrent.futures
import html
import requests

from utils.search import SearchClient
from utils.llm import LLMClient
from infra.social_adapter import SocialProviderAdapter
from infra.scholar_metrics import ScholarMetricsFetcher


def _score(title: str, candidate: Dict[str, Any]) -> int:
    t = (title or "").lower()
    ct = (candidate.get("title") or "").lower()
    cu = (candidate.get("url") or "").lower()
    s = 0
    for w in re.findall(r"[a-zA-Z0-9]+", t):
        if w and w in ct:
            s += 3
        if w and w in cu:
            s += 1
    if t and t in ct:
        s += 5
    return s


def _best_result(results: List[Dict[str, Any]], title: str) -> Dict[str, Any]:
    if not results:
        return {}
    scored = sorted(results, key=lambda r: _score(title, r), reverse=True)
    return scored[0]


def _extract_date(text: str) -> str:
    s = text or ""
    m = re.search(r"(20\d{2}-\d{1,2}-\d{1,2})", s)
    if m:
        return m.group(1)
    m = re.search(r"(20\d{2}/\d{1,2}/\d{1,2})", s)
    if m:
        return m.group(1)
    m = re.search(r"(20\d{2})", s)
    if m:
        return m.group(1)
    return ""


class ResumeJSONEnricher:
    """Augments resume JSON with web signals, evaluations and final aggregation."""
    def __init__(self, search: Optional[SearchClient] = None, llm: Optional[LLMClient] = None, social: Optional[SocialProviderAdapter] = None, scholar: Optional[ScholarMetricsFetcher] = None):
        self.search = search or SearchClient.from_env(dotenv_path=".env")
        self.llm = llm or LLMClient.from_env(dotenv_path=".env", temperature=0.0)
        self.social = social or SocialProviderAdapter()
        self.scholar = scholar or ScholarMetricsFetcher()

    def enrich_publications(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Search publications, attach URL/abstract/summary and sources/evidence."""
        pubs = data.get("publications") or []
        if not isinstance(pubs, list):
            return data
        def task(p: Dict[str, Any]) -> Dict[str, Any]:
            title = p.get("title") or ""
            if not title:
                return p
            print(f"[富化-论文] 搜索: {title}")
            res = self.search.search(title, max_results=5, engines=["tavily", "bocha"]) or []
            best = _best_result(res, title)
            url = best.get("url") or ""
            abstract = self._build_abstract(best, res)
            date = _extract_date(abstract)
            out = dict(p)
            out["url"] = url
            out["abstract"] = abstract
            if date:
                out["date"] = date
            print(f"[富化-论文输出] url={url} date={date} 摘要预览={abstract[:400]}")
            if abstract:
                summ = self._summarize_text(abstract)
                out["summary"] = summ
            srcs = [r.get("url") for r in res if r.get("url")][:5]
            evid = [{"url": r.get("url"), "snippet": r.get("content") or ""} for r in res[:5]]
            if srcs:
                out["sources"] = srcs
            if evid:
                out["evidence"] = evid
            return out
        max_workers = 8
        try:
            import os as _os
            max_workers = int(_os.getenv("ENRICH_MAX_WORKERS", "8"))
        except Exception:
            pass
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            results = list(ex.map(task, pubs))
        data["publications"] = results
        return data

    def enrich_awards(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Search awards and add concise intro plus sources/evidence."""
        awards = data.get("awards") or []
        if not isinstance(awards, list):
            return data
        def task(a: Dict[str, Any]) -> Dict[str, Any]:
            name = a.get("name") or ""
            if not name:
                return a
            print(f"[富化-奖项] 搜索: {name}")
            res = self.search.search(name, max_results=3, engines=["tavily", "bocha"]) or []
            best = res[0] if res else {}
            intro_src = best.get("content") or ""
            intro = self._summarize_award(name, intro_src)
            out = dict(a)
            out["intro"] = intro
            print(f"[富化-奖项输出] {name} -> {intro}")
            srcs = [r.get("url") for r in res if r.get("url")][:5]
            evid = [{"url": r.get("url"), "snippet": r.get("content") or ""} for r in res[:5]]
            if srcs:
                out["sources"] = srcs
            if evid:
                out["evidence"] = evid
            return out
        max_workers = 8
        try:
            import os as _os
            max_workers = int(_os.getenv("ENRICH_MAX_WORKERS", "8"))
        except Exception:
            pass
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            results = list(ex.map(task, awards))
        data["awards"] = results
        return data

    def _summarize_text(self, text: str) -> str:
        """LLM short review of abstract using PSR structure in Chinese."""
        prompt = (
		"""# Role
你是一名资深的学术情报分析师。你擅长将晦涩的学术摘要“翻译”为极简练的中文短评，供繁忙的专家快速审阅。
# Task
读取提供的【论文标题】和【摘要】，输出一段 **100字以内** 的核心总结。
# Constraints
1.  **结构严格 (PSR)**：必须包含 **背景/痛点(Problem)** -> **创新方法(Solution)** -> **核心指标/贡献(Result)**。
2.  **字数限制**：严格控制在 80-120 字之间。
3.  **语言风格**：
    * **禁止**使用“本文提出了”、“作者认为”等废话，直接陈述事实。
    * 使用专业术语，保持高信息密度。
    * 输出为纯文本，不要Markdown标题。

# 输出示例：
"针对序列转换模型难以并行计算的痛点，提出了一种完全基于注意力机制的Transformer架构。该模型摒弃了循环和卷积结构，仅利用Self-Attention计算输入输出依赖。实验表明，该方法在WMT 2014英德翻译任务中达到28.4 BLEU，不仅刷新了SOTA，且训练并行度大幅提升。"
"""
	)
        msgs = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ]
        out = self.llm.chat(msgs)
        return (out or "").strip()

    def _summarize_award(self, name: str, source_text: str) -> str:
        """LLM one-sentence award introduction in Chinese (<=50 chars)."""
        prompt = f"奖项名称：{name}\n资料：{source_text}"
        msgs = [
            {"role": "system", "content": "请用中文对该奖项做一句话介绍（<=50字），聚焦奖项定位与含金量，不要编造。"},
            {"role": "user", "content": prompt},
        ]
        out = self.llm.chat(msgs)
        return (out or "").strip()

    def enrich_file(self, json_path: str) -> str:
        """Run concurrent enrichers and write `resume_rich.json`."""
        import time as _t
        t0 = _t.time()
        p = Path(json_path)
        obj = json.loads(p.read_text(encoding="utf-8"))
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            fut_pubs = ex.submit(self.enrich_publications, dict(obj))
            fut_awds = ex.submit(self.enrich_awards, dict(obj))
            fut_soc = ex.submit(self.enrich_social_pulse, dict(obj))
            fut_sch = ex.submit(self.enrich_scholar_metrics, dict(obj))
            pubs_res = fut_pubs.result()
            awds_res = fut_awds.result()
            soc_res = fut_soc.result()
            sch_res = fut_sch.result()
        if "publications" in pubs_res:
            obj["publications"] = pubs_res.get("publications")
        if "awards" in awds_res:
            obj["awards"] = awds_res.get("awards")
        if "social_presence" in soc_res:
            obj["social_presence"] = soc_res.get("social_presence")
        if "social_influence" in soc_res:
            obj["social_influence"] = soc_res.get("social_influence")
        if "basic_info" in sch_res:
            obj["basic_info"] = sch_res.get("basic_info")
        obj = self.enrich_profile_evaluation(obj)
        obj = self.enrich_network_graph(obj)
        out_json = p.parent / "resume_rich.json"
        out_json.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[富化-完成] 生成 {str(out_json)}")
        try:
            from pathlib import Path as _P
            import json as _J
            root = _P.cwd() / "output" / "logs"
            root.mkdir(parents=True, exist_ok=True)
            rec = {
                "kind": "enrich_json",
                "src_json": json_path,
                "out_json": str(out_json),
                "pubs": len(obj.get("publications", []) or []),
                "awards": len(obj.get("awards", []) or []),
                "social_presence": len(obj.get("social_presence", []) or []),
                "elapsed_sec": round(_t.time() - t0, 3),
            }
            with open(root / "trace.jsonl", "a", encoding="utf-8") as f:
                f.write(_J.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
        return str(out_json)

    def _build_abstract(self, best: Dict[str, Any], all_results: List[Dict[str, Any]]) -> str:
        """Combine snippets and optionally fetch page content to form abstract."""
        url = best.get("url") or ""
        snippet = best.get("content") or ""
        agg = " ".join([(r.get("content") or "") for r in all_results])
        merged = (snippet + "\n" + agg).strip()
        full = self._fetch_abstract_from_url(url) or merged
        return full.strip()

    def _fetch_abstract_from_url(self, url: str) -> Optional[str]:
        """Fetch HTML and try to extract abstract via site-specific/metadata rules."""
        if not url:
            return None
        try:
            r = requests.get(url, timeout=10)
            if not r.ok:
                return None
            text = r.text or ""
        except Exception:
            return None
        if "arxiv.org" in url:
            m = re.search(r"<blockquote[^>]*class=\"abstract\"[^>]*>([\s\S]*?)</blockquote>", text, re.I)
            if m:
                raw = m.group(1)
                raw = re.sub(r"<[^>]+>", " ", raw)
                raw = html.unescape(raw)
                raw = raw.replace("Abstract:", "").replace("摘要:", "").strip()
                return raw
        for pat in [r'<meta[^>]+name="description"[^>]+content="([^"]+)"', r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', r'<meta[^>]+name="twitter:description"[^>]+content="([^"]+)"']:
            m = re.search(pat, text, re.I)
            if m:
                return html.unescape(m.group(1)).strip()
        body = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
        body = re.sub(r"<style[\s\S]*?</style>", " ", body, flags=re.I)
        body = re.sub(r"<[^>]+>", " ", body)
        body = html.unescape(body)
        candidates: List[str] = []
        for kw in ["Abstract", "ABSTRACT", "摘要", "概要"]:
            m = re.search(kw + r"[\s\S]{0,4000}", body)
            if m:
                candidates.append(m.group(0))
        if candidates:
            return max(candidates, key=len).strip()
        return None

    def enrich_profile_evaluation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate web signals for profile evaluation text and collect sources."""
        basic = data.get("basic_info") or {}
        name = basic.get("name") or data.get("name") or ""
        if not name:
            return data
        degree = basic.get("highest_degree") or ""
        edu = data.get("education") or []
        if (not degree) and isinstance(edu, list) and edu:
            degree = edu[0].get("degree") or ""
        skills = data.get("skills") or {}
        tech = []
        if isinstance(skills, dict):
            tech = (skills.get("tech_stack") or []) + (skills.get("general") or [])
        interests = data.get("research_interests") or []
        fields = " ".join([str(x) for x in (interests if isinstance(interests, list) else [])])
        fields = fields or " ".join([str(x) for x in tech])
        queries = [f"{name} {degree} {fields}".strip(), f"{name} Google Scholar", f"{name} 学术主页", f"{name} {degree}"]
        print(f"[综合评估] 组合查询: {queries}")
        results: List[Dict[str, Any]] = []
        for q in queries:
            rs = self.search.search(q, max_results=5, engines=["tavily", "bocha"]) or []
            results.extend(rs)
        seen = set()
        merged = []
        for r in results:
            u = r.get("url") or ""
            if u and u not in seen:
                seen.add(u)
                merged.append(r)
        context = "\n\n".join([f"来源: {r.get('url','')}\n内容: {r.get('content','')}" for r in merged[:10]])
        msgs = [
            {"role": "system", "content": "你是一名资深评审。请基于提供的公开资料，给出中文综合评价（300-500字），客观、中立，强调学术水平、荣誉与潜力，避免夸张与臆测。"},
            {"role": "user", "content": f"姓名: {name}\n学历: {degree}\n领域: {fields}\n\n资料:\n{context}"},
        ]
        eval_text = self.llm.chat(msgs) or ""
        data["profile_evaluation"] = eval_text.strip()
        data["profile_sources"] = [r.get("url") for r in merged[:10] if r.get("url")]
        print(f"[综合评估输出] {data['profile_evaluation'][:200]}")
        return data

    def enrich_social_pulse(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect social presence across platforms; produce presence and signals."""
        basic = data.get("basic_info") or {}
        name = basic.get("name") or data.get("name") or ""
        if not name:
            return data
        qs = [
            f"{name} LinkedIn",
            f"{name} ResearchGate",
            f"{name} Google Scholar",
            f"{name} GitHub",
            f"{name} 知乎 个人主页",
        ]
        res: List[Dict[str, Any]] = []
        for q in qs:
            rs = self.search.search(q, max_results=5, engines=["tavily", "bocha"]) or []
            res.extend(rs)
        items: List[Dict[str, Any]] = []
        for r in res:
            u = r.get("url") or ""
            t = r.get("title") or ""
            c = r.get("content") or ""
            platform, kind = self._classify_social_url(u)
            if platform:
                items.append({"title": t, "url": u, "content": c, "platform": platform, "kind": kind})
        items = self._filter_social_items(name=name, education=(data.get("education") or []), items=items)
        presence = self.social.normalize(items, platform="mixed")
        data["social_presence"] = presence
        inf_signals = []
        for it in presence:
            if it.get("topics"):
                inf_signals.append(it.get("topics"))
        data["social_influence"] = {"summary": "", "signals": inf_signals[:5]}
        return data

    def _classify_social_url(self, url: str) -> tuple[str, str]:
        """Classify social URL into platform and item kind."""
        u = url or ""
        plat = ""
        kind = "other"
        if "linkedin.com" in u:
            plat = "LinkedIn"
            if "/in/" in u:
                kind = "profile"
            elif "/company/" in u:
                kind = "company"
        elif "researchgate.net" in u:
            plat = "ResearchGate"
            if "/profile/" in u:
                kind = "profile"
        elif "scholar.google" in u:
            plat = "Google Scholar"
            if "citations" in u:
                kind = "profile"
        elif "github.com" in u:
            plat = "GitHub"
            try:
                seg = u.split("github.com/")[-1].split("/")
                if seg and seg[0] and (len(seg) == 1 or seg[1] == ""):
                    kind = "profile"
                else:
                    kind = "repo"
            except Exception:
                kind = "repo"
        elif "zhihu.com" in u:
            plat = "知乎"
            if "/people/" in u:
                kind = "profile"
            elif "/topic/" in u:
                kind = "topic"
            elif "/question/" in u or "/zhuanlan/" in u:
                kind = "article"
        elif ("twitter.com" in u) or ("x.com" in u):
            plat = "X (Twitter)"
            if "/status/" in u:
                kind = "post"
        elif ("medium.com" in u) or ("dev.to" in u) or ("/blog" in u):
            plat = "Blog"
            kind = "article"
        return plat, kind

    def _filter_social_items(self, name: str, education: List[Dict[str, Any]], items: List[Dict[str, Any]], custom_neg_keywords: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Filter likely self-related social items using heuristics and optional LLM.
        
        Args:
            name: Candidate name
            education: List of education entries
            items: Social media items to filter
            custom_neg_keywords: Optional list of negative keywords to exclude specific profiles
        
        Returns:
            Filtered list of social items
        """
        nm = (name or "").strip()
        schools = [str((e or {}).get("school", "")) for e in (education or [])]
        
        def _signals() -> Dict[str, List[str]]:
            """Build signal keywords from education background."""
            sig = {
                "pos": [],  # Positive signals from education/background
                "tech": ["python", "c++", "java", "javascript", "machine learning", "deep learning", 
                         "ai", "data science", "algorithm", "software", "engineering"],  # General tech keywords
                "neg": custom_neg_keywords or [],  # User-provided negative keywords
            }
            # Add school-related keywords
            for s in schools:
                if s:
                    sig["pos"].append(s.lower())
            # Add name variations (simple approach)
            if nm:
                # Only add exact name, avoid hardcoding specific person's variants
                sig["pos"].append(nm.lower())
            return sig
        sig = _signals()
        def heur(it: Dict[str, Any]) -> bool:
            s = " ".join([str(it.get("title","")), str(it.get("url","")), str(it.get("content",""))]).lower()
            plat = str(it.get("platform",""))
            kind = str(it.get("kind","other"))
            # weighted scoring
            score = 0
            if any(kw in s for kw in sig["neg"]):
                return False
            # platform whitelist boosts
            if plat in {"LinkedIn","ResearchGate","Google Scholar","GitHub"}:
                score += 2
            # personal page boosts
            if kind == "profile":
                score += 2
            elif kind in {"topic","article","post","repo"}:
                score += 0
            if nm and nm.lower() in s:
                score += 1
            score += sum(1 for kw in sig["pos"] if kw in s)
            score += sum(1 for kw in sig["tech"] if kw in s)
            return score >= 3
        out: List[Dict[str, Any]] = []
        # LLM-assisted filtering when configured
        use_llm = True
        try:
            import os as _os
            use_llm = _os.getenv("FEATURE_SOCIAL_FILTER", "1") == "1"
        except Exception:
            use_llm = True
        llm = self.llm if use_llm else None
        for it in (items or []):
            keep = heur(it)
            # Only call LLM for borderline cases
            borderline = not keep
            if (llm is not None) and borderline:
                ctx = {
                    "name": nm,
                    "schools": schools,
                    "item": {"title": it.get("title",""), "url": it.get("url",""), "text": it.get("content","")},
                }
                prompt = "请判断下面社交条目是否属于同一位候选人。若属于，则返回JSON {\"keep\":true};否则返回 {\"keep\":false}。严格基于姓名、学校/学院、专业、邮箱域名、地区等线索，排除同名不同人。输入：" + json.dumps(ctx, ensure_ascii=False)
                try:
                    res = str(llm.chat(prompt) or "").strip()
                    obj = json.loads(res)
                    if isinstance(obj, dict) and ("keep" in obj):
                        keep = bool(obj.get("keep"))
                except Exception:
                    # ignore and fall back to heuristic
                    pass
            if keep:
                out.append(it)
        return out

    def enrich_scholar_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Attach scholar metrics, updating basic_info.academic_metrics and sources."""
        basic = data.get("basic_info") or {}
        name = basic.get("name") or data.get("name") or ""
        if not name:
            return data
        rs = self.search.search(f"{name} Google Scholar", max_results=5, engines=["tavily", "bocha"]) or []
        prof = None
        for r in rs:
            u = r.get("url") or ""
            if "scholar.google" in u and "citations" in u:
                prof = r
                break
        metrics = self.scholar.run(name=name, profile_url=(prof or {}).get("url"), content=(prof or {}).get("content"))
        am = ((data.setdefault("basic_info", {})).setdefault("academic_metrics", {}))
        for k, v in metrics.items():
            am[k] = v
        if prof and prof.get("url"):
            srcs = data.get("profile_sources") or []
            srcs.append(prof.get("url"))
            data["profile_sources"] = list(dict.fromkeys(srcs))
        return data

    def enrich_network_graph(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Build simple network graph from supervisors and coauthors."""
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        basic = data.get("basic_info") or {}
        cname = basic.get("name") or data.get("name") or ""
        if cname:
            nodes.append({"name": cname, "role": "candidate", "affiliation": ""})
        edu = data.get("education") or []
        pubs = data.get("publications") or []
        for e in edu:
            s = e.get("supervisor") or ""
            if s:
                nodes.append({"name": s, "role": "supervisor", "affiliation": e.get("school") or ""})
                if cname:
                    edges.append({"source": s, "target": cname, "relation": "mentor"})
        coauthors: Dict[str, int] = {}
        for p in pubs:
            auths = p.get("authors") or []
            for a in auths:
                if isinstance(a, str) and a and a != cname:
                    nodes.append({"name": a, "role": "coauthor", "affiliation": ""})
                    edges.append({"source": cname or a, "target": a if cname else a, "relation": "coauthor"})
                    coauthors[a] = coauthors.get(a, 0) + 1
        uniq_nodes = []
        seen = set()
        for n in nodes:
            key = (n.get("name") or "") + "|" + (n.get("role") or "")
            if key not in seen and n.get("name"):
                uniq_nodes.append(n)
                seen.add(key)
        degree = 0
        if cname:
            connected = {e.get("source") for e in edges if e.get("target") == cname} | {e.get("target") for e in edges if e.get("source") == cname}
            degree = len([x for x in connected if x and x != cname])
        circle_tags = []
        for e in edu:
            if e.get("school"):
                circle_tags.append(e.get("school"))
        data["network_graph"] = {
            "nodes": uniq_nodes,
            "edges": edges,
            "circle_tags": list(dict.fromkeys(circle_tags))[:5],
            "centrality_metrics": {"degree": str(degree), "coauthor_weight": str(sum(coauthors.values()))}
        }
        return data

    def _ensure_json_simple(self, content: str) -> Dict[str, Any]:
        """Best-effort JSON object parsing from free-form content."""
        s = (content or "").strip()
        if not s:
            return {}
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
        m = re.search(r"\{[\s\S]*\}", s)
        if m:
            try:
                obj = json.loads(m.group(0))
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass
        return {}

    def academic_review(self, data: Dict[str, Any]) -> str:
        """LLM-generated academic review (Chinese, 300–500 chars)."""
        name = ((data.get("basic_info") or {}).get("name") or data.get("name") or "").strip()
        interests = data.get("research_interests") or []
        pubs = data.get("publications") or []
        parts: List[str] = []
        if interests:
            parts.append("研究方向: " + ", ".join([str(x) for x in interests]))
        for p in pubs[:10]:
            title = p.get("title") or ""
            abstract = p.get("abstract") or ""
            summary = p.get("summary") or ""
            seg = f"标题: {title}\n摘要: {abstract}\n总结: {summary}"
            parts.append(seg)
        ctx = "\n\n".join(parts) or ""
        msgs = [
            {"role": "system", "content": "你是一名资深终身教职评审委员。请基于提供资料，用中文写一段300-500字的学术综述，严格、深刻、具技术洞察，评价候选人的研究方向、核心内容与学术价值，避免夸张与臆测。"},
            {"role": "user", "content": f"姓名: {name}\n\n资料:\n{ctx}"},
        ]
        out = self.llm.chat(msgs) or ""
        return out.strip()

    def overall_summary(self, data: Dict[str, Any]) -> str:
        """LLM final holistic summary using explicit signals."""
        payload = json.dumps(data, ensure_ascii=False)
        # extract explicit signals for summary emphasis
        basic = data.get("basic_info") or {}
        am = (basic.get("academic_metrics") or {})
        h_idx = str(am.get("h_index") or "")
        h10 = str(am.get("h10_index") or "")
        cit_tot = str(am.get("citations_total") or "")
        cit_rec = str(am.get("citations_recent") or "")
        sp = data.get("social_presence") or []
        sp_cnt = len(sp or [])
        sp_platforms = ", ".join(sorted({str((x or {}).get("platform") or "") for x in sp if isinstance(x, dict)} - {""}))
        ng = data.get("network_graph") or {}
        deg = str(((ng.get("centrality_metrics") or {}).get("degree")) or "")
        tags = ", ".join((ng.get("circle_tags") or [])[:5])
        prompt = (
            f"""# Role
你是一名拥有20年招聘经验的首席技术评估官（Chief Talent Assessor）。你阅人无数，擅长基于简历、评分与外部信号做出客观、可执行的综合判断。

# Inputs (Signals)
- 学术指标：h-index={h_idx}，h10-index={h10}，总引用={cit_tot}，近五年引用={cit_rec}
- 社交声量：平台数={sp_cnt}（{sp_platforms}）
- 人脉图谱：中心性度={deg}，圈层标签={tags}

# Task
阅读输入的完整JSON（含上述信号），生成**终极综合评价报告**。

# Cognitive Steps
1. 画像定性：明确候选人类型（学术/工程/协作/潜力）。
2. 矛盾与一致性：指出强弱项的组合关系及风险与机会。
3. 证据引用：在描述中自然地融合学术指标、社交信号与人脉圈层，不夸张、不臆测。
4. 组织落地：给出入职后的建议定位与前3个月可执行目标。

# 输出
400字左右，中文，段落清晰，避免空话。
            """
        )
        msgs = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": payload},
        ]
        out = self.llm.chat(msgs) or ""
        return out.strip()

    def multi_dimension_evaluation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """LLM outputs five-dimension evaluations with evidence sources (no scores)."""
        d2 = json.loads(json.dumps(data))
        pubs = d2.get("publications") or []
        for p in pubs:
            if "abstract" in p:
                p["abstract"] = ""
        d2["publications"] = pubs
        # include profile_sources to help evidence mapping
        prof_src = d2.get("profile_sources") or []
        payload = json.dumps({"data": d2, "profile_sources": prof_src}, ensure_ascii=False)
        prompt = (
            """
# Role
你是一名拥有20年经验的技术专家面试官。你的特长是透过简历的字里行间，评估候选人的硬实力（学术/工程）与软素质（协作/领导力）。

# Goal
接收一份【标准化的简历JSON数据】，输出五个维度的定性评价文本（不包含分数），并附带证据来源引用。

# Dimensions
- 学术创新力
- 工程实战力
- 行业影响力
- 合作协作
- 综合素质

# Requirements
1. 严格输出JSON对象，键为上述中文维度名称，值为对象：{"evaluation": "...", "evidence_sources": ["url或来源"...]}
2. 文本为中文，客观中立，避免臆测；证据来源引用可来自输入中的 profile_sources 或 publications/awards 的来源。
3. 不要输出分数；评分在后续步骤单独计算。
            """
        )
        msgs = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": payload},
        ]
        out = self.llm.chat(msgs) or ""
        obj = self._ensure_json_simple(out)
        if not isinstance(obj, dict) or not obj:
            obj = {
                "学术创新力": {"evaluation": "", "evidence_sources": []},
                "工程实战力": {"evaluation": "", "evidence_sources": []},
                "行业影响力": {"evaluation": "", "evidence_sources": []},
                "合作协作": {"evaluation": "", "evidence_sources": []},
                "综合素质": {"evaluation": "", "evidence_sources": []},
            }
        # normalize values to expected shape
        def _to_obj(v: Any) -> Dict[str, Any]:
            if isinstance(v, dict):
                ev = str(v.get("evaluation") or v.get("desc") or "")
                srcs = v.get("evidence_sources") or []
                srcs = srcs if isinstance(srcs, list) else []
                return {"evaluation": ev, "evidence_sources": srcs}
            return {"evaluation": str(v or ""), "evidence_sources": []}
        canon: Dict[str, Any] = {}
        for k in ["学术创新力", "工程实战力", "行业影响力", "合作协作", "综合素质"]:
            canon[k] = _to_obj(obj.get(k))
        return canon

    def multi_dimension_scores(self, dims_text: Dict[str, Any]) -> Dict[str, float]:
        """LLM numeric scores (0–10) based on evaluation texts; defaults to 6.0."""
        def _extract_text(v: Any) -> str:
            if isinstance(v, dict):
                return str(v.get("evaluation") or v.get("desc") or "")
            return str(v or "")
        pure_text = {k: _extract_text(v) for k, v in (dims_text or {}).items()}
        prompt = "请基于以下五个维度的中文评价文本，分别给出0-10的评分，支持0.5刻度，输出JSON对象，键为维度中文名，值为评分数字。"
        payload = json.dumps(pure_text, ensure_ascii=False)
        msgs = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": payload},
        ]
        out = self.llm.chat(msgs) or ""
        obj = self._ensure_json_simple(out)
        scores: Dict[str, float] = {}
        for k, v in (obj or {}).items():
            try:
                scores[k] = max(0.0, min(10.0, float(v)))
            except Exception:
                continue
        if not scores:
            for k in dims_text.keys():
                scores[k] = 6.0
        return scores

    def generate_final(self, json_path: str) -> str:
        """Aggregate review/evaluations/scores/summary → write `resume_final.json`."""
        import time as _t
        t0 = _t.time()
        p = Path(json_path)
        data = json.loads(p.read_text(encoding="utf-8"))
        review = self.academic_review(data)
        dims = self.multi_dimension_evaluation(data)
        final_obj = json.loads(json.dumps(data))
        final_obj["academic_review"] = review
        final_obj["multi_dimension_evaluation"] = dims
        final_obj["multi_dimension_scores"] = self.multi_dimension_scores(dims)
        final_obj["overall_summary"] = self.overall_summary(data)
        out_path = p.parent / "resume_final.json"
        out_path.write_text(json.dumps(final_obj, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[终评-完成] 生成 {str(out_path)}")
        try:
            from pathlib import Path as _P
            import json as _J
            root = _P.cwd() / "output" / "logs"
            root.mkdir(parents=True, exist_ok=True)
            rec = {
                "kind": "finalize_json",
                "src_json": json_path,
                "out_json": str(out_path),
                "elapsed_sec": round(_t.time() - t0, 3),
            }
            with open(root / "trace.jsonl", "a", encoding="utf-8") as f:
                f.write(_J.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
        return str(out_path)

    
