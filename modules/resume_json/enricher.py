import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import concurrent.futures
import html
import requests

from utils.search import SearchClient
from utils.llm import LLMClient
from utils.person_disambiguation import (
    PersonDisambiguator,
    PersonProfile,
    extract_profile_from_resume_json
)
from infra.social_adapter import SocialProviderAdapter
from infra.scholar_metrics import ScholarMetricsFetcher
from infra.scholar_metrics_enhanced import AcademicMetricsFetcher
from infra.social_content_crawler import SocialContentCrawler

# Phase 1 enhancements: Benchmarking, Journal Quality, Risk Assessment
from utils.benchmark_data import AcademicBenchmarker, benchmark_researcher
from utils.journal_quality_db import JournalQualityDatabase, classify_publication_venue
from utils.risk_assessment import RiskAssessor, assess_candidate_risks

# Phase 2 enhancements: Authorship Analysis, Evidence Chain, Cross-Validation
from utils.authorship_analyzer import AuthorshipAnalyzer, analyze_authorship
from utils.evidence_chain import EvidenceChainBuilder, build_evidence_chains_for_evaluation
from utils.cross_validator import CrossValidator, cross_validate_evaluation

# Phase 3 enhancements: Research Lineage and Productivity Timeline
from utils.research_lineage import ResearchLineageAnalyzer
from utils.productivity_timeline import ProductivityTimelineAnalyzer


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
    """Extract date from text using multiple patterns."""
    s = text or ""
    # Priority 1: YYYY-MM-DD or YYYY/MM/DD
    m = re.search(r"((?:19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2})", s)
    if m:
        return m.group(1)
    # Priority 2: Chinese date format (2024年12月)
    m = re.search(r"((?:19|20)\d{2})年(\d{1,2})月(?:(\d{1,2})日)?", s)
    if m:
        year = m.group(1)
        month = m.group(2).zfill(2)
        day = m.group(3).zfill(2) if m.group(3) else "01"
        return f"{year}-{month}-{day}"
    # Priority 3: English month format (Dec 2024, December 2024)
    m = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+((?:19|20)\d{2})", s, re.I)
    if m:
        month_map = {"Jan":"01","Feb":"02","Mar":"03","Apr":"04","May":"05","Jun":"06",
                     "Jul":"07","Aug":"08","Sep":"09","Oct":"10","Nov":"11","Dec":"12"}
        month = month_map.get(m.group(1)[:3].capitalize(), "01")
        return f"{m.group(2)}-{month}"
    # Priority 4: Year only (19XX or 20XX)
    m = re.search(r"((?:19|20)\d{2})", s)
    if m:
        return m.group(1)
    return ""


class ResumeJSONEnricher:
    """Augments resume JSON with web signals, evaluations and final aggregation."""
    def __init__(self, search: Optional[SearchClient] = None, llm: Optional[LLMClient] = None, social: Optional[SocialProviderAdapter] = None, scholar: Optional[ScholarMetricsFetcher] = None, use_enhanced_scholar: bool = True):
        self.search = search or SearchClient.from_env(dotenv_path=".env")
        self.llm = llm or LLMClient.from_env(dotenv_path=".env", temperature=0.0)
        self.social = social or SocialProviderAdapter()
        # Use enhanced scholar fetcher if enabled
        if use_enhanced_scholar:
            self.scholar = AcademicMetricsFetcher().scholar_fetcher
        else:
            self.scholar = scholar or ScholarMetricsFetcher()
        # Initialize person disambiguator
        self.disambiguator = PersonDisambiguator(min_confidence=0.75)  # Raised from 0.60 to reduce false positives
        # Initialize social content crawler for deep analysis
        self.content_crawler = SocialContentCrawler(timeout=10.0, max_posts=10)
        # Phase 1 enhancements: Initialize benchmarker, journal quality DB, and risk assessor
        self.benchmarker = AcademicBenchmarker()
        self.journal_db = JournalQualityDatabase()
        self.risk_assessor = RiskAssessor()
        # Phase 2 enhancements: Initialize authorship analyzer, evidence chain builder, cross-validator
        self.evidence_builder = EvidenceChainBuilder(llm_client=self.llm)
        self.cross_validator = CrossValidator()

    def enrich_publications(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Search publications, attach URL/abstract/summary and sources/evidence."""
        pubs = data.get("publications") or []
        if not isinstance(pubs, list):
            return data
        
        # Input validation: limit publication count
        MAX_PUBS = 50
        try:
            import os as _os
            MAX_PUBS = int(_os.getenv("MAX_ENRICH_PUBS", "50"))
        except Exception:
            pass
        if len(pubs) > MAX_PUBS:
            print(f"[富化-论文警告] 论文数量 {len(pubs)} 超过限制 {MAX_PUBS}，仅处理前 {MAX_PUBS} 条")
            pubs = pubs[:MAX_PUBS]
        
        def safe_task(p: Dict[str, Any]) -> Dict[str, Any]:
            """Wrapper with exception handling to prevent thread pool failures."""
            try:
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
                
                # Phase 1: Add journal quality tagging
                venue = p.get("journal") or p.get("conference") or ""
                if venue:
                    quality_info = self.journal_db.classify_venue(venue)
                    out["venue_quality"] = quality_info
                    print(f"[富化-论文质量] {venue}: {quality_info.get('quality_flag', 'Unknown')}")
                
                return out
            except Exception as e:
                print(f"[富化-论文错误] {p.get('title', '')}: {e}")
                return p  # Return original data on failure
        
        max_workers = 8
        try:
            import os as _os
            max_workers = min(16, int(_os.getenv("ENRICH_MAX_WORKERS", "8")))  # Cap at 16
        except Exception:
            pass
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            results = list(ex.map(safe_task, pubs))
        data["publications"] = results
        return data

    def enrich_awards(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Search awards and add concise intro plus sources/evidence."""
        awards = data.get("awards") or []
        if not isinstance(awards, list):
            return data
        
        def safe_task(a: Dict[str, Any]) -> Dict[str, Any]:
            """Wrapper with exception handling to prevent thread pool failures."""
            try:
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
            except Exception as e:
                print(f"[富化-奖项错误] {a.get('name', '')}: {e}")
                return a  # Return original data on failure
        
        max_workers = 8
        try:
            import os as _os
            max_workers = min(16, int(_os.getenv("ENRICH_MAX_WORKERS", "8")))  # Cap at 16
        except Exception:
            pass
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            results = list(ex.map(safe_task, awards))
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
            with requests.get(url, timeout=10, stream=False) as r:
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
        def _normalize_url(url: str) -> str:
            """Normalize URL for deduplication."""
            u = url.strip().rstrip('/')
            u = u.replace('http://', 'https://')
            # Remove common tracking parameters
            u = re.sub(r'[?&](utm_[^&]+|ref=[^&]+|source=[^&]+)', '', u)
            return u.lower()
        
        seen = set()
        merged = []
        for r in results:
            u = r.get("url") or ""
            if u:
                norm_url = _normalize_url(u)
                if norm_url not in seen:
                    seen.add(norm_url)
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
        items = self._filter_social_items(name=name, education=(data.get("education") or []), items=items, resume_data=data)
        
        # Perform deep content analysis on filtered profiles
        items = self._enrich_with_deep_analysis(items)
        
        presence = self.social.normalize(items, platform="mixed")
        data["social_presence"] = presence
        
        # Generate comprehensive social analysis and persona profile
        social_analysis = self._generate_comprehensive_social_analysis(
            candidate_name=name,
            social_presence=presence,
            resume_data=data
        )
        data["social_influence"] = social_analysis
        
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

    def _extract_candidate_profile_from_social_item(self, item: Dict[str, Any]) -> PersonProfile:
        """
        Extract PersonProfile from a social media item.
        
        Args:
            item: Social media item with title, url, content, platform
            
        Returns:
            PersonProfile instance
        """
        # Extract name from title or content
        title = item.get("title", "")
        content = item.get("content", "")
        url = item.get("url", "")
        platform = item.get("platform", "")
        
        # Try to extract name (usually in title for profiles)
        name = ""
        if title:
            # Remove platform names
            name = title
            for plat in ["LinkedIn", "ResearchGate", "Google Scholar", "GitHub", "知乎"]:
                name = name.replace(plat, "").replace("|", "").replace("-", "")
            name = name.strip()
        
        # Extract affiliations and research interests from content
        affiliations = []
        research_interests = []
        
        # Simple keyword extraction for affiliations
        affiliation_keywords = ["University", "大学", "College", "学院", "Institute", "研究所", "Lab", "实验室"]
        for keyword in affiliation_keywords:
            if keyword in content:
                # Extract surrounding context (simple approach)
                idx = content.find(keyword)
                if idx != -1:
                    # Get surrounding words
                    start = max(0, idx - 30)
                    end = min(len(content), idx + 50)
                    snippet = content[start:end].strip()
                    affiliations.append(snippet)
        
        # Extract email domain if present
        email = ""
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', content)
        if email_match:
            email = email_match.group(0)
        
        return PersonProfile(
            name=name,
            affiliations=list(set(affiliations))[:3],  # Limit to top 3
            research_interests=research_interests,
            email=email
        )
    
    def _filter_social_items(self, name: str, education: List[Dict[str, Any]], items: List[Dict[str, Any]], custom_neg_keywords: Optional[List[str]] = None, resume_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Filter likely self-related social items using heuristics, person disambiguation, and optional LLM.
        
        Args:
            name: Candidate name
            education: List of education entries
            items: Social media items to filter
            custom_neg_keywords: Optional list of negative keywords to exclude specific profiles
            resume_data: Full resume data for person disambiguation (optional)
        
        Returns:
            Filtered list of social items with disambiguation metadata
        """
        nm = (name or "").strip()
        schools = [str((e or {}).get("school", "")) for e in (education or [])]
        
        # Extract target profile for disambiguation
        target_profile = None
        use_disambiguation = True
        try:
            import os as _os
            use_disambiguation = _os.getenv("FEATURE_PERSON_DISAMBIGUATION", "1") == "1"
        except Exception:
            use_disambiguation = True
        
        if use_disambiguation and resume_data:
            try:
                target_profile = extract_profile_from_resume_json(resume_data)
            except Exception as e:
                print(f"[人物消歧-错误] 无法提取目标画像: {e}")
        
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
            # STRICTER: Raised from 3 to 4 to reduce false positives
            return score >= 4
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
            disambiguation_result = None
            
            # Apply person disambiguation for profiles
            if use_disambiguation and target_profile and it.get("kind") == "profile":
                try:
                    # Extract candidate profile from social item
                    candidate_profile = self._extract_candidate_profile_from_social_item(it)
                    
                    # Disambiguate
                    disambiguation_result = self.disambiguator.disambiguate(target_profile, candidate_profile)
                    
                    # Update keep decision based on disambiguation
                    # Use HIGH threshold (0.75) to reduce false positives
                    if disambiguation_result.confidence >= 0.75:
                        keep = disambiguation_result.is_match
                        print(f"[人物消歧-高置信度] {it.get('platform','')} - {it.get('url','')[:80]}: 置信度={disambiguation_result.confidence:.3f}, 匹配={keep}")
                    elif disambiguation_result.confidence >= 0.60:
                        # Medium confidence: be conservative, reject by default
                        keep = False
                        print(f"[人物消歧-中置信度-拒绝] {it.get('platform','')}: 置信度={disambiguation_result.confidence:.3f}")
                    else:
                        # Low confidence: reject
                        keep = False
                        print(f"[人物消歧-低置信度-拒绝] {it.get('platform','')}: 置信度={disambiguation_result.confidence:.3f}")
                except Exception as e:
                    print(f"[人物消歧-错误] {it.get('platform','')}: {e}")
            
            # Only call LLM for borderline cases
            borderline = not keep
            if (llm is not None) and borderline and not disambiguation_result:
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
                # Add disambiguation metadata if available
                if disambiguation_result:
                    it["disambiguation"] = {
                        "confidence": disambiguation_result.confidence,
                        "explanation": disambiguation_result.explanation,
                        "evidence": {k: round(v, 3) for k, v in disambiguation_result.evidence.items()}
                    }
                out.append(it)
        return out
    
    def _enrich_with_deep_analysis(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Perform deep content analysis on social profiles.
        
        This adds sentiment analysis, topic extraction, and engagement metrics
        to provide truly deep insights into the candidate's social presence.
        
        Args:
            items: Filtered social items
            
        Returns:
            Items with deep analysis metadata
        """
        # Check if deep analysis is enabled
        use_deep_analysis = True
        try:
            import os as _os
            use_deep_analysis = _os.getenv("FEATURE_DEEP_SOCIAL_ANALYSIS", "1") == "1"
        except Exception:
            use_deep_analysis = True
        
        if not use_deep_analysis:
            return items
        
        enriched_items = []
        for item in items:
            try:
                platform = item.get("platform", "").lower()
                url = item.get("url", "")
                
                # Only analyze profile pages (not search results)
                if item.get("kind") != "profile":
                    enriched_items.append(item)
                    continue
                
                # Crawl profile for recent posts/content
                print(f"[深度分析] 正在分析 {platform} 个人主页: {url[:80]}")
                posts = self.content_crawler.crawl_profile(platform, url, max_posts=5)
                
                if not posts:
                    enriched_items.append(item)
                    continue
                
                # Analyze each post
                analyses = []
                total_engagement = 0
                for post in posts:
                    analysis = self.content_crawler.analyze(post)
                    analyses.append(analysis)
                    total_engagement += post.engagement_score()
                
                # Aggregate analysis
                sentiments = [a.sentiment for a in analyses]
                all_topics = []
                all_keywords = []
                for a in analyses:
                    all_topics.extend(a.topics)
                    all_keywords.extend(a.keywords)
                
                # Calculate sentiment distribution
                sentiment_dist = {
                    "positive": sentiments.count("positive") / len(sentiments) if sentiments else 0,
                    "neutral": sentiments.count("neutral") / len(sentiments) if sentiments else 0,
                    "negative": sentiments.count("negative") / len(sentiments) if sentiments else 0,
                }
                
                # Get top topics and keywords (by frequency)
                topic_counts = {}
                for topic in all_topics:
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1
                top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                
                keyword_counts = {}
                for kw in all_keywords:
                    keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
                top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                
                # Calculate average technical depth
                depth_map = {"shallow": 1, "medium": 2, "deep": 3}
                avg_depth = sum(depth_map.get(a.technical_depth, 1) for a in analyses) / len(analyses) if analyses else 0
                technical_depth = "shallow" if avg_depth < 1.5 else "medium" if avg_depth < 2.5 else "deep"
                
                # Add deep analysis metadata
                item["deep_analysis"] = {
                    "posts_analyzed": len(posts),
                    "total_engagement": round(total_engagement, 2),
                    "avg_engagement": round(total_engagement / len(posts), 2) if posts else 0,
                    "sentiment_distribution": {k: round(v, 3) for k, v in sentiment_dist.items()},
                    "top_topics": [{"topic": t, "count": c} for t, c in top_topics],
                    "top_keywords": [{"keyword": k, "count": c} for k, c in top_keywords],
                    "technical_depth": technical_depth,
                    "analysis_summary": self._generate_deep_analysis_summary(
                        platform, sentiment_dist, top_topics, technical_depth, total_engagement
                    )
                }
                
                print(f"[深度分析-完成] {platform}: 分析{len(posts)}篇内容, 技术深度={technical_depth}, 总互动={total_engagement:.0f}")
                
            except Exception as e:
                print(f"[深度分析-错误] {item.get('platform', '')}: {e}")
            
            enriched_items.append(item)
        
        return enriched_items
    
    def _generate_deep_analysis_summary(
        self,
        platform: str,
        sentiment_dist: Dict[str, float],
        top_topics: List[tuple],
        technical_depth: str,
        total_engagement: float
    ) -> str:
        """Generate a natural language summary of deep analysis."""
        sentiment_str = "积极" if sentiment_dist.get("positive", 0) > 0.5 else "中立" if sentiment_dist.get("neutral", 0) > 0.4 else "多样"
        topics_str = "、".join([t[0] for t in top_topics[:3]]) if top_topics else "多个领域"
        depth_str = {"shallow": "入门级", "medium": "中等深度", "deep": "深度技术"}[technical_depth]
        engagement_str = "高" if total_engagement > 1000 else "中" if total_engagement > 100 else "一般"
        
        return f"该{platform}账号发布内容以{sentiment_str}为主，主要涉及{topics_str}等主题，技术深度为{depth_str}，社区影响力{engagement_str}。"
    
    def _generate_comprehensive_social_analysis(
        self,
        candidate_name: str,
        social_presence: List[Dict[str, Any]],
        resume_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive social media analysis with persona profiling.
        
        This replaces the shallow "signals" list with deep insights including:
        - Multi-platform activity summary
        - Content quality assessment
        - Influence and reach metrics
        - Persona profile (professional identity, expertise areas, engagement style)
        - Key themes and focus areas
        - Community standing
        - Comprehensive synthesis using LLM
        
        Args:
            candidate_name: Candidate's name
            social_presence: List of social media profiles with deep_analysis
            resume_data: Full resume data for context
            
        Returns:
            Comprehensive social influence analysis
        """
        # Check if comprehensive analysis is enabled
        use_comprehensive = True
        try:
            import os as _os
            use_comprehensive = _os.getenv("FEATURE_COMPREHENSIVE_SOCIAL_ANALYSIS", "1") == "1"
        except Exception:
            use_comprehensive = True
        
        # Fallback to simple signals if disabled
        if not use_comprehensive:
            inf_signals = []
            for it in social_presence:
                if it.get("topics"):
                    inf_signals.append(it.get("topics"))
            return {"summary": "", "signals": inf_signals[:5]}
        
        # Aggregate metrics across all platforms
        total_platforms = len(social_presence)
        platforms_with_deep_analysis = sum(1 for p in social_presence if p.get("deep_analysis"))
        
        # Collect all deep analysis data
        all_topics = []
        all_keywords = []
        all_sentiments = []
        total_engagement = 0
        technical_depths = []
        platform_summaries = []
        
        for profile in social_presence:
            platform = profile.get("platform", "Unknown")
            deep = profile.get("deep_analysis")
            
            if deep:
                # Aggregate topics
                for topic_entry in deep.get("top_topics", []):
                    all_topics.append({
                        "topic": topic_entry.get("topic"),
                        "count": topic_entry.get("count", 0),
                        "platform": platform
                    })
                
                # Aggregate keywords
                for kw_entry in deep.get("top_keywords", []):
                    all_keywords.append({
                        "keyword": kw_entry.get("keyword"),
                        "count": kw_entry.get("count", 0),
                        "platform": platform
                    })
                
                # Sentiment
                sentiment_dist = deep.get("sentiment_distribution", {})
                all_sentiments.append(sentiment_dist)
                
                # Engagement
                total_engagement += deep.get("total_engagement", 0)
                
                # Technical depth
                tech_depth = deep.get("technical_depth", "medium")
                technical_depths.append(tech_depth)
                
                # Platform summary
                platform_summaries.append({
                    "platform": platform,
                    "summary": deep.get("analysis_summary", ""),
                    "posts_analyzed": deep.get("posts_analyzed", 0),
                    "engagement": deep.get("total_engagement", 0)
                })
        
        # Calculate aggregate sentiment
        avg_sentiment = {
            "positive": sum(s.get("positive", 0) for s in all_sentiments) / len(all_sentiments) if all_sentiments else 0,
            "neutral": sum(s.get("neutral", 0) for s in all_sentiments) / len(all_sentiments) if all_sentiments else 0,
            "negative": sum(s.get("negative", 0) for s in all_sentiments) / len(all_sentiments) if all_sentiments else 0
        }
        
        # Get most common topics (cross-platform)
        topic_aggregation = {}
        for t in all_topics:
            topic_name = t["topic"]
            topic_aggregation[topic_name] = topic_aggregation.get(topic_name, 0) + t["count"]
        top_topics_overall = sorted(topic_aggregation.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Get most common keywords
        keyword_aggregation = {}
        for k in all_keywords:
            kw_name = k["keyword"]
            keyword_aggregation[kw_name] = keyword_aggregation.get(kw_name, 0) + k["count"]
        top_keywords_overall = sorted(keyword_aggregation.items(), key=lambda x: x[1], reverse=True)[:15]
        
        # Calculate overall technical depth
        depth_map = {"shallow": 1, "medium": 2, "deep": 3}
        avg_depth_score = sum(depth_map.get(d, 2) for d in technical_depths) / len(technical_depths) if technical_depths else 2
        overall_technical_depth = "shallow" if avg_depth_score < 1.5 else "medium" if avg_depth_score < 2.5 else "deep"
        
        # Generate persona profile using LLM
        persona_profile = self._generate_persona_profile(
            candidate_name=candidate_name,
            resume_data=resume_data,
            social_data={
                "platforms": [p.get("platform") for p in social_presence],
                "top_topics": top_topics_overall[:5],
                "top_keywords": top_keywords_overall[:10],
                "sentiment": avg_sentiment,
                "technical_depth": overall_technical_depth,
                "total_engagement": total_engagement,
                "platform_summaries": platform_summaries
            }
        )
        
        # Generate comprehensive synthesis using LLM
        comprehensive_summary = self._generate_social_synthesis(
            candidate_name=candidate_name,
            resume_data=resume_data,
            persona_profile=persona_profile,
            social_metrics={
                "total_platforms": total_platforms,
                "platforms_analyzed": platforms_with_deep_analysis,
                "top_topics": top_topics_overall[:5],
                "sentiment": avg_sentiment,
                "technical_depth": overall_technical_depth,
                "total_engagement": total_engagement
            },
            platform_summaries=platform_summaries
        )
        
        # Build comprehensive result
        return {
            "summary": comprehensive_summary,
            "persona_profile": persona_profile,
            "metrics": {
                "total_platforms": total_platforms,
                "platforms_with_analysis": platforms_with_deep_analysis,
                "total_engagement": round(total_engagement, 2),
                "avg_sentiment": {k: round(v, 3) for k, v in avg_sentiment.items()},
                "technical_depth": overall_technical_depth
            },
            "key_topics": [{"topic": t, "frequency": c} for t, c in top_topics_overall[:10]],
            "key_keywords": [{"keyword": k, "frequency": c} for k, c in top_keywords_overall[:15]],
            "platform_insights": platform_summaries
        }
    
    def _generate_persona_profile(
        self,
        candidate_name: str,
        resume_data: Dict[str, Any],
        social_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive persona profile based on social media presence.
        
        Uses LLM to synthesize:
        - Professional identity
        - Expertise areas
        - Engagement style
        - Community standing
        - Thought leadership indicators
        """
        # Build context for LLM
        education = resume_data.get("education", [])
        work_exp = resume_data.get("work_experience", [])
        
        edu_str = "; ".join([
            f"{e.get('degree', '')} from {e.get('school', '')}" 
            for e in education[:2] if isinstance(e, dict)
        ]) if education else "N/A"
        
        work_str = "; ".join([
            f"{w.get('title', '')} at {w.get('company', '')}"
            for w in work_exp[:2] if isinstance(w, dict)
        ]) if work_exp else "N/A"
        
        platforms = ", ".join(social_data.get("platforms", []))
        topics = ", ".join([t[0] for t in social_data.get("top_topics", [])[:5]])
        keywords = ", ".join([k[0] for k in social_data.get("top_keywords", [])[:8]])
        
        sentiment = social_data.get("sentiment", {})
        sentiment_str = f"积极({sentiment.get('positive', 0):.1%}), 中立({sentiment.get('neutral', 0):.1%}), 消极({sentiment.get('negative', 0):.1%})"
        
        tech_depth = social_data.get("technical_depth", "medium")
        tech_depth_cn = {"shallow": "入门级", "medium": "中等深度", "deep": "深度技术"}[tech_depth]
        
        engagement = social_data.get("total_engagement", 0)
        engagement_str = "高" if engagement > 1000 else "中" if engagement > 100 else "一般"
        
        prompt = f"""# 角色
你是一名资深的人才评估专家，擅长通过社交媒体数据分析候选人的专业画像。

# 任务
基于以下候选人的履历和社交媒体数据，生成一份**结构化的人物画像**。

# 输入信息
## 候选人基本信息
- 姓名: {candidate_name}
- 教育背景: {edu_str}
- 工作经历: {work_str}

## 社交媒体数据
- 活跃平台: {platforms}
- 主要讨论主题: {topics}
- 高频关键词: {keywords}
- 内容情感倾向: {sentiment_str}
- 技术深度: {tech_depth_cn}
- 社区影响力: {engagement_str}

# 输出要求
请以**JSON格式**输出，包含以下字段（每个字段用1-2句话，50-80字）：

1. **professional_identity** (专业身份): 候选人的核心专业定位和角色
2. **expertise_areas** (专业领域): 主要技术专长和研究方向（数组，3-5个）
3. **engagement_style** (参与风格): 在社交媒体上的互动和内容分享风格
4. **community_standing** (社区地位): 在技术社区中的影响力和认可度
5. **thought_leadership** (思想领导力): 是否展现出行业洞见和引领能力
6. **key_strengths** (核心优势): 从社交媒体表现看出的关键优势（数组，3-5个）

# 重要约束
- 严格基于提供的数据，不要编造
- 如果信息不足，使用"数据有限"或"待观察"表述
- 输出必须是合法的JSON格式
- 每个字段保持简洁专业

请输出JSON："""

        try:
            msgs = [
                {"role": "system", "content": "你是一名专业的人才评估专家，擅长生成结构化的候选人画像。输出必须是合法的JSON格式。"},
                {"role": "user", "content": prompt}
            ]
            response = self.llm.chat(msgs)
            
            # Try to parse JSON
            import json
            response_clean = response.strip()
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]
            response_clean = response_clean.strip()
            
            persona = json.loads(response_clean)
            return persona
            
        except Exception as e:
            print(f"[人物画像生成-错误] {e}")
            # Fallback to simple structure
            return {
                "professional_identity": f"活跃于{platforms}等平台的技术从业者",
                "expertise_areas": [t[0] for t in social_data.get("top_topics", [])[:3]],
                "engagement_style": f"内容情感以{sentiment_str}为主",
                "community_standing": f"社区影响力{engagement_str}",
                "thought_leadership": "数据有限，待进一步观察",
                "key_strengths": [k[0] for k in social_data.get("top_keywords", [])[:3]]
            }
    
    def _generate_social_synthesis(
        self,
        candidate_name: str,
        resume_data: Dict[str, Any],
        persona_profile: Dict[str, Any],
        social_metrics: Dict[str, Any],
        platform_summaries: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a comprehensive synthesis of social media presence using LLM.
        
        This creates a 200-300 word narrative that ties together:
        - Resume background
        - Social media activity
        - Persona insights
        - Community influence
        """
        # Build context
        platforms = [p["platform"] for p in platform_summaries]
        platforms_str = "、".join(platforms)
        
        topics = [t[0] for t in social_metrics.get("top_topics", [])[:5]]
        topics_str = "、".join(topics) if topics else "多个技术领域"
        
        sentiment = social_metrics.get("sentiment", {})
        sentiment_main = "积极" if sentiment.get("positive", 0) > 0.5 else "中立" if sentiment.get("neutral", 0) > 0.4 else "多样化"
        
        tech_depth = social_metrics.get("technical_depth", "medium")
        tech_depth_cn = {"shallow": "入门级", "medium": "中等深度", "deep": "深度技术"}[tech_depth]
        
        engagement = social_metrics.get("total_engagement", 0)
        
        # Platform-specific insights
        platform_insights_str = "\n".join([
            f"- {p['platform']}: {p.get('summary', '暂无详情')}"
            for p in platform_summaries[:3]
        ])
        
        # Persona highlights
        prof_id = persona_profile.get("professional_identity", "")
        expertise = ", ".join(persona_profile.get("expertise_areas", [])[:3])
        thought_lead = persona_profile.get("thought_leadership", "")
        
        prompt = f"""# 角色
你是一名资深的人才评估报告撰写专家，擅长将碎片化的社交媒体数据综合成连贯、深刻的人物评估。

# 任务
基于候选人的社交媒体数据和人物画像，撰写一段**200-300字的综合评估**。

# 输入信息
## 候选人
- 姓名: {candidate_name}

## 社交媒体概况
- 活跃平台: {platforms_str}
- 主要讨论领域: {topics_str}
- 内容情感基调: {sentiment_main}
- 技术深度: {tech_depth_cn}
- 总互动量: {engagement:.0f}

## 各平台表现
{platform_insights_str}

## 人物画像
- 专业身份: {prof_id}
- 专长领域: {expertise}
- 思想领导力: {thought_lead}

# 输出要求
1. **篇幅**: 严格控制在200-300字之间
2. **结构**: 
   - 第1段(80-100字): 整体社交媒体活跃度和专业定位
   - 第2段(60-80字): 内容质量和技术深度评估
   - 第3段(60-80字): 社区影响力和未来潜力
3. **风格**: 
   - 客观专业，避免过度夸赞或批评
   - 数据支撑，每个判断基于具体指标
   - 洞察深刻，揭示表象背后的专业特质
4. **禁止**: 
   - 不要使用"本文"、"作者"、"该候选人"等生硬表述
   - 直接使用候选人姓名或"其"
   - 不要编造数据

请直接输出评估文本（纯文本，不要Markdown格式）："""

        try:
            msgs = [
                {"role": "system", "content": "你是一名专业的人才评估报告撰写专家。输出简洁、深刻、数据驱动的评估文本。"},
                {"role": "user", "content": prompt}
            ]
            synthesis = self.llm.chat(msgs)
            return synthesis.strip()
            
        except Exception as e:
            print(f"[社交综合分析-错误] {e}")
            # Fallback to simple summary
            return f"{candidate_name}在{platforms_str}等平台保持活跃，主要关注{topics_str}等领域。内容以{sentiment_main}为主，技术深度达到{tech_depth_cn}水平，累计获得{engagement:.0f}互动量，展现出一定的社区影响力。"

    def enrich_scholar_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Attach scholar metrics using enhanced fetcher with active crawling."""
        basic = data.get("basic_info") or {}
        name = basic.get("name") or data.get("name") or ""
        english_name = basic.get("english_name") or data.get("english_name") or ""
        if not name:
            return data
        
        # Try to get affiliation for better search results
        affiliation = None
        edu = data.get("education") or []
        if edu:
            # Use most recent education (first in list)
            affiliation = edu[0].get("school", "") if edu else None
        
        # Generate name variants for better Scholar profile search
        # Import helper from authorship_analyzer
        from utils.authorship_analyzer import AuthorshipAnalyzer
        name_analyzer = AuthorshipAnalyzer(name, english_name=english_name if english_name else None)
        name_variants = name_analyzer.name_variants
        
        print(f"[学术指标-搜索] 使用 {len(name_variants)} 个姓名变体搜索Google Scholar profile:")
        for i, variant in enumerate(name_variants, 1):
            print(f"  {i}. '{variant}'")
        
        # Try searching with each name variant
        profile_url = None
        for variant in name_variants:
            print(f"[学术指标-搜索] 尝试搜索: '{variant} Google Scholar'")
            rs = self.search.search(f"{variant} Google Scholar", max_results=5, engines=["tavily", "bocha"]) or []
            for r in rs:
                u = r.get("url") or ""
                if "scholar.google" in u and "citations" in u:
                    profile_url = u
                    print(f"[学术指标-成功] 找到Google Scholar profile: {profile_url}")
                    break
            if profile_url:
                break  # Found profile, stop searching
        
        if not profile_url:
            print(f"[学术指标-警告] 未找到Google Scholar profile，将尝试直接搜索爬取")
        
        # Fetch metrics using enhanced fetcher
        # The enhanced fetcher will:
        # 1. Try direct URL if provided
        # 2. Fall back to search-and-crawl if no URL
        # 3. Parse with multiple strategies
        print(f"[学术指标-获取] 开始获取学术指标 (profile_url={profile_url or '无'}, affiliation={affiliation or '无'})")
        metrics = self.scholar.run(
            name=name,
            profile_url=profile_url,
            affiliation=affiliation
        )
        
        # Update basic_info with metrics
        am = ((data.setdefault("basic_info", {})).setdefault("academic_metrics", {}))
        for k, v in metrics.items():
            if v:  # Only add non-empty values
                am[k] = v
        
        # Add profile URL to sources if found
        if profile_url:
            am["profile_url"] = profile_url  # Store in academic_metrics for later aggregation
            srcs = data.get("profile_sources") or []
            srcs.append(profile_url)
            data["profile_sources"] = list(dict.fromkeys(srcs))
            print(f"[学术指标-来源] 已添加Google Scholar profile到参考来源")
        
        # Phase 1: Add academic benchmarking
        if metrics.get("h_index") and metrics.get("citations_total"):
            benchmark_result = self._add_academic_benchmark(data, metrics)
            if benchmark_result:
                am["benchmark"] = benchmark_result
                print(f"[学术对标] 完成对标分析: h-index percentile={benchmark_result.get('h_index_analysis', {}).get('percentile', 'N/A')}")
        
        # Log results
        if any(metrics.values()):
            print(f"[学术指标-成功] h-index={metrics.get('h_index','N/A')}, citations={metrics.get('citations_total','N/A')}")
        else:
            print(f"[学术指标-警告] 未能从Google Scholar获取学术指标，尝试从论文数据推断...")
            # Fallback: Infer basic metrics from publication data
            inferred_metrics = self._infer_metrics_from_publications(data)
            if inferred_metrics:
                for k, v in inferred_metrics.items():
                    if v and not am.get(k):  # Only set if not already present
                        am[k] = v
                print(f"[学术指标-推断] 从论文推断: h-index={inferred_metrics.get('h_index','N/A')}, "
                      f"总论文={inferred_metrics.get('publications_count','N/A')}")
                am["data_source"] = "推断自论文列表"
            else:
                print(f"[学术指标-失败] 无法从Google Scholar或论文数据获取学术指标")
                am["data_source"] = "无法获取"
        
        return data
    
    def _infer_metrics_from_publications(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Infer basic academic metrics from publication list when Scholar data is unavailable.
        
        This provides a rough estimation to avoid showing completely empty metrics.
        
        Args:
            data: Resume data with publications
            
        Returns:
            Dictionary with inferred metrics (h_index, citations_total, publications_count)
        """
        publications = data.get("publications", [])
        if not publications:
            return {}
        
        # Count publications
        pub_count = len(publications)
        
        # Estimate h-index using simplified formula
        # h-index is the largest number h such that h publications have at least h citations each
        # Without citation data, we use a conservative estimation based on publication count:
        # - Rough formula: h-index ≈ sqrt(total_pubs) for early career researchers
        # - This is very conservative but better than showing nothing
        
        import math
        estimated_h_index = max(1, int(math.sqrt(pub_count)))
        
        # For conservative estimation, cap at reasonable values based on pub count
        if pub_count < 5:
            estimated_h_index = min(estimated_h_index, 2)
        elif pub_count < 10:
            estimated_h_index = min(estimated_h_index, 4)
        elif pub_count < 20:
            estimated_h_index = min(estimated_h_index, 6)
        
        # Note: We don't estimate citations_total as it's too unreliable
        # Better to show publication count instead
        
        return {
            "h_index": str(estimated_h_index),
            "publications_count": str(pub_count),
            # Note: citations_total intentionally omitted - too unreliable to estimate
        }
    
    def _aggregate_reference_sources(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregate all reference sources from different parts of the resume data.
        
        Collects URLs from:
        - Existing profile_sources
        - Publications (urls, venues)
        - Awards and honors
        - Social media profiles
        - Projects and grants
        - Any other sources with URLs
        
        Args:
            data: Complete resume data
            
        Returns:
            Dictionary with aggregated sources and statistics
        """
        all_sources = []
        
        # 1. Existing profile_sources
        existing_sources = data.get("profile_sources", [])
        if existing_sources:
            all_sources.extend([s for s in existing_sources if s])
        
        # 2. Publications
        publications = data.get("publications", [])
        pub_count = 0
        for pub in publications:
            if not isinstance(pub, dict):
                continue
            # Publication URL
            url = pub.get("url", "")
            if url:
                all_sources.append(url)
                pub_count += 1
            # Venue/conference URL (if different)
            venue_url = pub.get("venue_url", "")
            if venue_url and venue_url != url:
                all_sources.append(venue_url)
        
        # 3. Social media profiles
        social_presence = data.get("social_presence", [])
        social_count = 0
        for profile in social_presence:
            if not isinstance(profile, dict):
                continue
            url = profile.get("url", "")
            if url:
                all_sources.append(url)
                social_count += 1
        
        # 4. Awards and honors
        awards = data.get("awards", [])
        for award in awards:
            if not isinstance(award, dict):
                continue
            url = award.get("url", "") or award.get("source", "")
            if url:
                all_sources.append(url)
        
        honors = data.get("honors", [])
        for honor in honors:
            if not isinstance(honor, dict):
                continue
            url = honor.get("url", "") or honor.get("source", "")
            if url:
                all_sources.append(url)
        
        # 5. Projects
        projects = data.get("projects", [])
        for project in projects:
            if not isinstance(project, dict):
                continue
            url = project.get("url", "")
            if url:
                all_sources.append(url)
        
        # 6. Grants
        grants = data.get("grants", [])
        for grant in grants:
            if not isinstance(grant, dict):
                continue
            url = grant.get("url", "")
            if url:
                all_sources.append(url)
        
        # 7. Open source contributions
        open_source = data.get("open_source", [])
        for contrib in open_source:
            if not isinstance(contrib, dict):
                continue
            url = contrib.get("url", "")
            if url:
                all_sources.append(url)
        
        # 8. Academic metrics source (Google Scholar profile)
        basic_info = data.get("basic_info", {})
        academic_metrics = basic_info.get("academic_metrics", {})
        scholar_profile = academic_metrics.get("profile_url", "")
        if scholar_profile:
            all_sources.append(scholar_profile)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_sources = []
        for source in all_sources:
            # Clean and normalize URL
            source_clean = str(source).strip()
            if source_clean and source_clean not in seen:
                seen.add(source_clean)
                unique_sources.append(source_clean)
        
        # Calculate statistics
        other_count = len(unique_sources) - pub_count - social_count
        
        return {
            "urls": unique_sources,
            "statistics": {
                "total_sources": len(unique_sources),
                "publication_sources": pub_count,
                "social_sources": social_count,
                "other_sources": max(0, other_count)
            }
        }
    
    def _add_academic_benchmark(self, data: Dict[str, Any], metrics: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Add academic benchmarking analysis
        
        Args:
            data: Resume data
            metrics: Scholar metrics
            
        Returns:
            Benchmark analysis or None if insufficient data
        """
        try:
            # Extract necessary data
            h_index = metrics.get("h_index", 0)
            citations = metrics.get("citations_total", 0)
            
            if not h_index or not citations:
                return None
            
            # Get publication count
            pubs = data.get("publications", [])
            pub_count = len(pubs)
            
            # Extract PhD year for career stage calculation
            phd_year = None
            education = data.get("education", [])
            for edu in education:
                degree = edu.get("degree", "")
                if "PhD" in degree or "博士" in degree:
                    year_str = edu.get("end_date", "") or edu.get("year", "")
                    match = re.search(r"(19|20)\d{2}", str(year_str))
                    if match:
                        phd_year = int(match.group(0))
                        break
            
            if not phd_year:
                print("[学术对标-警告] 无法确定PhD毕业年份，使用默认career stage")
                years_since_phd = 5  # Default to mid-career
            else:
                years_since_phd = self.risk_assessor.current_year - phd_year
            
            # Determine research field
            # Try to infer from education or use a default
            field = "Computational Mathematics"  # Default
            for edu in education:
                major = edu.get("major", "")
                if major:
                    # Simple field mapping
                    if "计算机" in major or "Computer" in major:
                        field = "Computer Science"
                    elif "数学" in major or "Math" in major:
                        if "应用" in major or "Applied" in major:
                            field = "Applied Mathematics"
                        else:
                            field = "Computational Mathematics"
                    break
            
            # Perform benchmarking
            benchmark_result = self.benchmarker.benchmark_candidate(
                h_index=int(h_index),
                citations=int(citations),
                pub_count=pub_count,
                field=field,
                years_since_phd=years_since_phd
            )
            
            return benchmark_result
            
        except Exception as e:
            print(f"[学术对标-错误] {e}")
            return None

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
        
        # Phase 1: Add comprehensive risk assessment
        print("[风险评估] 开始全面风险分析...")
        risk_assessment = self.risk_assessor.assess_all_risks(data)
        final_obj["risk_assessment"] = risk_assessment
        print(f"[风险评估-完成] 识别风险: {risk_assessment['summary']['total_risks']} 个 "
              f"(严重: {risk_assessment['summary']['critical_count']}, "
              f"高: {risk_assessment['summary']['high_count']}, "
              f"中: {risk_assessment['summary']['medium_count']})")
        
        # Phase 2: Add authorship pattern analysis
        print("[作者贡献分析] 开始分析作者模式...")
        candidate_name = data.get("basic_info", {}).get("name", "") or data.get("name", "")
        english_name = data.get("basic_info", {}).get("english_name", "") or data.get("english_name", "")
        if candidate_name:
            print(f"[作者贡献分析-姓名] 候选人: {candidate_name}, 英文名: {english_name or '(未提供)'}")
            authorship_report = analyze_authorship(
                candidate_name, 
                data.get("publications", []),
                english_name=english_name if english_name else None
            )
            final_obj["authorship_analysis"] = authorship_report
            independence_score = authorship_report.get("metrics", {}).get("independence_score", 0)
            print(f"[作者贡献分析-完成] 独立性得分: {independence_score:.2f}, "
                  f"第一作者率: {authorship_report.get('metrics', {}).get('first_author', {}).get('rate', 0):.1%}")
        
        # Phase 2: Add evidence chains for multi-dimension evaluation
        print("[证据链追溯] 开始构建证据链...")
        enhanced_evaluation = build_evidence_chains_for_evaluation(
            evaluation_dict=dims,
            resume_data=data,
            llm_client=self.llm
        )
        final_obj["enhanced_evaluation"] = enhanced_evaluation
        print(f"[证据链追溯-完成] 为 {len(enhanced_evaluation)} 个维度构建了证据链")
        
        # Phase 2: Add academic-social cross-validation
        print("[交叉验证] 开始学术-社交信号交叉验证...")
        social_data = data.get("social_influence", {})
        # Type validation: ensure dims is a dict before cross-validation
        if social_data and isinstance(dims, dict) and isinstance(social_data, dict):
            try:
                cross_validation = cross_validate_evaluation(
                    academic_evaluation=dims,
                    social_analysis=social_data
                )
                final_obj["cross_validation"] = cross_validation
                consistency = cross_validation.get("consistency_score", 0)
                inconsistencies = len(cross_validation.get("inconsistencies", []))
                print(f"[交叉验证-完成] 一致性得分: {consistency:.1%}, 发现矛盾: {inconsistencies} 个")
            except Exception as e:
                print(f"[交叉验证-错误] {str(e)}")
                final_obj["cross_validation"] = {"error": str(e), "consistency_score": 0, "inconsistencies": []}
        elif not isinstance(dims, dict):
            print(f"[交叉验证-跳过] dims 类型错误: {type(dims).__name__}, 期望 dict")
        else:
            print("[交叉验证-跳过] 缺少社交数据")
        
        # Phase 3: Add research lineage analysis
        print("[研究脉络分析] 开始分析学术谱系和研究轨迹...")
        try:
            lineage_analyzer = ResearchLineageAnalyzer(llm_client=self.llm)
            research_lineage = lineage_analyzer.analyze(data)
            if isinstance(research_lineage, dict):
                final_obj["research_lineage"] = research_lineage
                continuity_score = research_lineage.get("continuity_score", 0)
                coherence = research_lineage.get("coherence_assessment", "Unknown")
                maturity = research_lineage.get("research_maturity", "Unknown")
                print(f"[研究脉络分析-完成] 连续性得分: {continuity_score:.2f}, 一致性: {coherence[:30]}..., 成熟度: {maturity[:30]}...")
            else:
                print(f"[研究脉络分析-错误] 返回类型错误: {type(research_lineage).__name__}, 期望 dict")
                final_obj["research_lineage"] = {"error": f"Invalid return type: {type(research_lineage).__name__}"}
        except Exception as e:
            print(f"[研究脉络分析-错误] {str(e)}")
            final_obj["research_lineage"] = {"error": str(e)}
        
        # Phase 3: Add productivity timeline analysis
        print("[产出时间线分析] 开始分析生产力趋势和时间线...")
        try:
            timeline_analyzer = ProductivityTimelineAnalyzer()
            productivity_timeline = timeline_analyzer.analyze(data)
            if isinstance(productivity_timeline, dict):
                final_obj["productivity_timeline"] = productivity_timeline
                productivity_score = productivity_timeline.get("productivity_score", 0)
                trend = productivity_timeline.get("trend_assessment", "Unknown")
                recent_trend = productivity_timeline.get("recent_trend", "Unknown")
                print(f"[产出时间线分析-完成] 生产力得分: {productivity_score:.1f}/10, 整体趋势: {trend[:40]}..., 近期趋势: {recent_trend[:40]}...")
            else:
                print(f"[产出时间线分析-错误] 返回类型错误: {type(productivity_timeline).__name__}, 期望 dict")
                final_obj["productivity_timeline"] = {"error": f"Invalid return type: {type(productivity_timeline).__name__}"}
        except Exception as e:
            print(f"[产出时间线分析-错误] {str(e)}")
            final_obj["productivity_timeline"] = {"error": str(e)}
        
        # Aggregate all reference sources
        print("[参考来源汇总] 开始收集所有参考来源...")
        aggregated_sources = self._aggregate_reference_sources(final_obj)
        final_obj["profile_sources"] = aggregated_sources["urls"]
        final_obj["source_statistics"] = aggregated_sources["statistics"]
        print(f"[参考来源汇总-完成] 共收集 {aggregated_sources['statistics']['total_sources']} 个来源 "
              f"(论文: {aggregated_sources['statistics']['publication_sources']}, "
              f"社交: {aggregated_sources['statistics']['social_sources']}, "
              f"其他: {aggregated_sources['statistics']['other_sources']})")
        
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

    
