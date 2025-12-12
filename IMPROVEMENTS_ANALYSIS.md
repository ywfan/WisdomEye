# WisdomEye 系统改进分析与实施方案

## 日期
2025-12-12

## 概述
本文档详细分析了当前WisdomEye系统存在的5个核心问题，并提供系统性的改进方案。

---

## 问题 1: 论文解析遗漏预印本和已投稿论文

###  当前问题
- **现象**: 已投稿（Under Review）、预印本（ArXiv/bioRxiv）等状态的论文经常不被识别为publications
- **原因**: LLM在解析时可能将这些状态的论文误分类到其他字段或直接忽略
- **影响**: 学术成果不完整，降低候选人评估的准确性

### 根因分析

1. **Schema定义模糊**:
```json
{
  "publications": [
    {
      "status": "String, 状态",  // 未明确说明包含哪些状态
      ...
    }
  ]
}
```

2. **Prompt指导不足**:
```python
# formatter.py line 30-31
* **论文**：包含已发表、在投（Under Review）、预印本（ArXiv）等。
```
虽然提到了，但不够强调，LLM容易忽略

3. **关键词识别不全**:
- 缺少常见的投稿状态关键词识别
- 未处理预印本平台的多样性（arXiv, bioRxiv, medRxiv, SSRN等）

### 改进方案

#### 方案1: 增强Prompt（高优先级）

修改`formatter.py`的PROMPT_BASE:

```python
3.  **字段归类原则 (Strict Categorization)**：
    * **论文（CRITICAL）**：
        **必须包含**以下所有状态的学术成果：
        - ✅ 已发表（Published）: 在期刊、会议上正式发表
        - ✅ 已接收（Accepted）: 已被接收但未正式发表
        - ✅ 在投/审稿中（Under Review / In Review / Submitted）
        - ✅ 修订中（Revise and Resubmit / Major Revision / Minor Revision）
        - ✅ 预印本（Preprint）: 包括 arXiv, bioRxiv, medRxiv, SSRN, viXra等平台
        - ✅ 工作论文（Working Paper）
        - ✅ 技术报告（Technical Report）: 如果包含研究性内容
        
        **识别特征**：
        - 包含作者、标题、摘要或描述
        - 有明确的发表意图或已在线托管
        - DOI、arXiv ID、或URL链接
        
        **反例（不归入publications）**：
        - 纯课程作业/毕业论文（除非已发表或有明确投稿记录）
        - 内部技术文档（除非公开发表）
```

#### 方案2: 后处理验证（中优先级）

在`formatter.py`的`to_json`方法中添加验证逻辑:

```python
def _validate_publications(self, data: dict) -> dict:
    """Post-process to ensure preprints and submissions are captured."""
    text_lower = self._original_text.lower()
    
    # 关键词检测
    preprint_keywords = [
        'arxiv', 'biorxiv', 'medrxiv', 'ssrn', 'preprint',
        'under review', 'submitted', 'in review', 'revise',
        'working paper', 'technical report'
    ]
    
    # 如果文本中包含这些关键词但publications为空或很少
    if any(kw in text_lower for kw in preprint_keywords):
        pub_count = len(data.get('publications', []))
        if pub_count < 2:  # 阈值可调
            # 记录警告并可能触发重新解析
            print(f"[警告] 检测到预印本/投稿关键词，但publications只有{pub_count}条")
```

#### 方案3: 数据增强（低优先级）

使用训练数据微调或Few-shot示例:

```python
PROMPT_BASE += """

# 示例 (Few-shot Examples)

## 输入示例1: 预印本
文本: "...arXiv:2312.12345, Transformer Variants for Image Recognition, Under Review..."

正确输出:
{
  "publications": [
    {
      "title": "Transformer Variants for Image Recognition",
      "status": "Under Review (arXiv preprint)",
      "url": "https://arxiv.org/abs/2312.12345",
      ...
    }
  ]
}

## 输入示例2: 投稿中
文本: "...Submitted to NeurIPS 2024, Deep Reinforcement Learning for Robotics..."

正确输出:
{
  "publications": [
    {
      "title": "Deep Reinforcement Learning for Robotics",
      "venue": "NeurIPS 2024 (Submitted)",
      "status": "Under Review",
      ...
    }
  ]
}
"""
```

---

## 问题 2: 社交声量分析过于表面

### 当前问题
- **现象**: 只搜索到候选人的账号链接，没有深入分析发帖内容、互动数据等
- **原因**: 
  1. 只使用搜索引擎获取URL，未爬取页面内容
  2. 缺少平台特定的内容提取器
  3. 未对内容进行深度分析（主题、影响力、技术深度等）

### 当前实现分析

```python
# enricher.py line 357-390
def enrich_social_pulse(self, data: Dict[str, Any]) -> Dict[str, Any]:
    qs = [
        f"{name} LinkedIn",
        f"{name} ResearchGate",
        # ...
    ]
    # 仅搜索，获取URL
    for q in qs:
        rs = self.search.search(q, max_results=5, engines=["tavily", "bocha"])
        res.extend(rs)
    
    # 仅分类，未深入爬取
    for r in res:
        platform, kind = self._classify_social_url(r.get("url"))
        items.append({...})
```

**问题**: 只有URL和搜索snippet，没有实际内容

### 改进方案

#### 方案1: 平台内容爬取器（核心）

创建新文件`infra/social_content_crawler.py`:

```python
from typing import Dict, Any, List, Optional
import requests
from bs4 import BeautifulSoup
import re
import json


class SocialContentCrawler:
    """Deep crawler for social media platforms."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def crawl_zhihu_profile(self, url: str) -> Dict[str, Any]:
        """
        爬取知乎个人主页深度信息。
        
        返回:
        {
            "user_id": "用户ID",
            "nickname": "昵称",
            "headline": "一句话介绍",
            "description": "个人介绍",
            "follower_count": 粉丝数,
            "answer_count": 回答数,
            "article_count": 文章数,
            "column_count": 专栏数,
            "total_votes": 总赞同数,
            "recent_answers": [
                {
                    "question_title": "问题标题",
                    "answer_excerpt": "回答摘要",
                    "vote_count": 赞同数,
                    "comment_count": 评论数,
                    "created_time": "发布时间",
                    "topics": ["话题1", "话题2"]
                }
            ],
            "recent_articles": [
                {
                    "title": "文章标题",
                    "excerpt": "文章摘要",
                    "vote_count": 赞同数,
                    "comment_count": 评论数,
                    "read_count": 阅读数
                }
            ],
            "expertise_areas": ["领域1", "领域2"],  # 从话题和内容分析
            "activity_level": "活跃度评分",
            "influence_score": "影响力评分"
        }
        """
        try:
            resp = self.session.get(url, timeout=15)
            if not resp.ok:
                return {}
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 提取基本信息
            data = {
                "follower_count": self._extract_zhihu_follower_count(soup),
                "answer_count": self._extract_zhihu_answer_count(soup),
                "article_count": self._extract_zhihu_article_count(soup),
                # ... 更多提取逻辑
            }
            
            # 提取近期内容
            data["recent_answers"] = self._extract_zhihu_recent_answers(url, limit=10)
            data["recent_articles"] = self._extract_zhihu_recent_articles(url, limit=5)
            
            # 分析专业领域
            data["expertise_areas"] = self._analyze_expertise_areas(
                data["recent_answers"], 
                data["recent_articles"]
            )
            
            return data
        except Exception as e:
            print(f"[知乎爬取错误] {url}: {e}")
            return {}
    
    def crawl_github_profile(self, username: str, profile_url: str) -> Dict[str, Any]:
        """
        爬取GitHub个人主页和仓库信息。
        
        返回:
        {
            "username": "用户名",
            "name": "真实姓名",
            "bio": "简介",
            "location": "地理位置",
            "email": "邮箱",
            "blog": "博客地址",
            "company": "公司",
            "follower_count": 关注者数,
            "following_count": 关注数,
            "public_repos": 公开仓库数,
            "public_gists": 公开gist数,
            "total_stars_received": 总star数,
            "total_forks_received": 总fork数,
            "contribution_years": ["2023", "2024"],
            "primary_languages": {"Python": 45.2, "JavaScript": 30.1, ...},
            "top_repositories": [
                {
                    "name": "仓库名",
                    "description": "描述",
                    "stars": star数,
                    "forks": fork数,
                    "language": "主要语言",
                    "topics": ["topic1", "topic2"],
                    "is_fork": false,
                    "last_updated": "最后更新时间"
                }
            ],
            "contribution_summary": {
                "total_commits_last_year": "近一年提交数",
                "max_streak_days": "最长连续贡献天数",
                "avg_commits_per_week": "平均每周提交数"
            },
            "code_quality_indicators": {
                "has_tests": "是否有测试",
                "has_ci_cd": "是否有CI/CD",
                "documentation_quality": "文档质量评分",
                "code_review_participation": "代码审查参与度"
            }
        }
        """
        try:
            # GitHub API调用
            api_url = f"https://api.github.com/users/{username}"
            headers = {
                "Accept": "application/vnd.github.v3+json",
                # 可选: 添加GitHub token以提高速率限制
                # "Authorization": f"token {GITHUB_TOKEN}"
            }
            
            resp = self.session.get(api_url, headers=headers, timeout=15)
            if not resp.ok:
                return {}
            
            user_data = resp.json()
            
            # 获取仓库列表
            repos_url = user_data.get("repos_url")
            repos_resp = self.session.get(
                repos_url, 
                headers=headers, 
                params={"sort": "updated", "per_page": 100},
                timeout=15
            )
            repos = repos_resp.json() if repos_resp.ok else []
            
            # 分析仓库
            analysis = self._analyze_github_repos(repos, username)
            
            return {
                "username": user_data.get("login"),
                "name": user_data.get("name"),
                "bio": user_data.get("bio"),
                "location": user_data.get("location"),
                "email": user_data.get("email"),
                "blog": user_data.get("blog"),
                "company": user_data.get("company"),
                "follower_count": user_data.get("followers", 0),
                "following_count": user_data.get("following", 0),
                "public_repos": user_data.get("public_repos", 0),
                "public_gists": user_data.get("public_gists", 0),
                **analysis
            }
        except Exception as e:
            print(f"[GitHub爬取错误] {username}: {e}")
            return {}
    
    def _analyze_github_repos(self, repos: List[Dict], username: str) -> Dict[str, Any]:
        """分析GitHub仓库质量和影响力。"""
        if not repos:
            return {}
        
        total_stars = sum(r.get("stargazers_count", 0) for r in repos if not r.get("fork"))
        total_forks = sum(r.get("forks_count", 0) for r in repos if not r.get("fork"))
        
        # 语言统计
        languages = {}
        for r in repos:
            lang = r.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1
        
        # 排序取前N个仓库
        top_repos = sorted(
            [r for r in repos if not r.get("fork")],
            key=lambda x: x.get("stargazers_count", 0) + x.get("forks_count", 0),
            reverse=True
        )[:10]
        
        top_repos_data = [
            {
                "name": r.get("name"),
                "description": r.get("description", ""),
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "language": r.get("language", ""),
                "topics": r.get("topics", []),
                "is_fork": r.get("fork", False),
                "last_updated": r.get("updated_at", ""),
                "url": r.get("html_url", "")
            }
            for r in top_repos
        ]
        
        # 代码质量指标
        code_quality = self._assess_code_quality(top_repos)
        
        return {
            "total_stars_received": total_stars,
            "total_forks_received": total_forks,
            "primary_languages": dict(sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]),
            "top_repositories": top_repos_data,
            "code_quality_indicators": code_quality
        }
    
    def _assess_code_quality(self, repos: List[Dict]) -> Dict[str, Any]:
        """评估代码质量（基于仓库特征）。"""
        if not repos:
            return {}
        
        has_tests_count = 0
        has_ci_count = 0
        has_good_docs_count = 0
        
        for repo in repos:
            # 简单启发式判断（实际应该深入爬取README、CI配置等）
            desc = (repo.get("description") or "").lower()
            topics = [t.lower() for t in (repo.get("topics") or [])]
            
            # 测试关键词
            if any(kw in desc or kw in " ".join(topics) for kw in ["test", "testing", "ci", "coverage"]):
                has_tests_count += 1
            
            # CI/CD关键词
            if any(kw in desc or kw in " ".join(topics) for kw in ["ci", "cd", "github-actions", "travis", "circleci"]):
                has_ci_count += 1
            
            # 文档关键词
            if any(kw in desc or kw in " ".join(topics) for kw in ["docs", "documentation", "wiki"]):
                has_good_docs_count += 1
        
        total = len(repos)
        return {
            "has_tests": f"{has_tests_count}/{total}",
            "has_ci_cd": f"{has_ci_count}/{total}",
            "documentation_quality": f"{has_good_docs_count}/{total}",
            "quality_score": round((has_tests_count + has_ci_count + has_good_docs_count) / (total * 3) * 10, 1)
        }
```

#### 方案2: 内容深度分析（使用LLM）

修改`enricher.py`的`enrich_social_pulse`:

```python
def enrich_social_pulse_deep(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced social pulse with deep content analysis."""
    basic = data.get("basic_info") or {}
    name = basic.get("name") or data.get("name") or ""
    if not name:
        return data
    
    # 原有的URL发现逻辑
    items = self._discover_social_urls(name)
    
    # 新增: 深度内容爬取
    crawler = SocialContentCrawler()
    enriched_items = []
    
    for item in items:
        url = item.get("url", "")
        platform = item.get("platform", "")
        
        deep_data = {}
        if platform == "知乎" and "people" in url:
            deep_data = crawler.crawl_zhihu_profile(url)
        elif platform == "GitHub":
            username = self._extract_github_username(url)
            if username:
                deep_data = crawler.crawl_github_profile(username, url)
        
        # 合并数据
        enriched_item = {**item, **deep_data}
        
        # LLM分析内容影响力
        if deep_data:
            analysis = self._analyze_social_influence(name, platform, deep_data)
            enriched_item["influence_analysis"] = analysis
        
        enriched_items.append(enriched_item)
    
    data["social_presence"] = enriched_items
    return data

def _analyze_social_influence(self, name: str, platform: str, content_data: Dict) -> Dict[str, Any]:
    """Use LLM to analyze social influence from deep content."""
    prompt = f"""
    # 任务
    分析候选人{name}在{platform}平台的影响力和技术深度。
    
    # 输入数据
    {json.dumps(content_data, ensure_ascii=False, indent=2)}
    
    # 输出要求
    返回JSON对象:
    {{
        "activity_level": "高/中/低",
        "technical_depth": "深/中/浅",
        "influence_scope": "国际/国内/小圈子",
        "key_topics": ["话题1", "话题2", ...],
        "content_quality": "高/中/低",
        "engagement_quality": "高/中/低",  // 基于互动数据
        "summary": "一句话总结（50字内）"
    }}
    """
    
    try:
        response = self.llm.chat([
            {"role": "system", "content": "你是社交媒体分析专家。"},
            {"role": "user", "content": prompt}
        ])
        return json.loads(response)
    except Exception as e:
        print(f"[社交影响力分析错误] {e}")
        return {}
```

---

## 问题 3: 同名人物识别不准确

### 当前问题
- **现象**: 搜索结果中混入了其他同名人的信息
- **原因**: 
  1. 仅基于姓名搜索，缺少足够的辨识特征
  2. 过滤逻辑过于简单（只看关键词匹配）
  3. 未利用多维度信息交叉验证

### 当前实现分析

```python
# enricher.py line 438-522
def _filter_social_items(self, name, education, items, custom_neg_keywords):
    # 简单的启发式判断
    def heur(it):
        score = 0
        # 仅基于关键词匹配打分
        if nm and nm.lower() in s:
            score += 1
        score += sum(1 for kw in sig["pos"] if kw in s)
        return score >= 3  # 阈值过低
```

**问题**: 
- 没有利用年龄、工作经历、学位时间等强特征
- 没有交叉验证多个来源
- LLM判断是边界case，但prompt不够精确

### 改进方案

#### 方案1: 多维度特征匹配（核心）

创建`utils/person_disambiguation.py`:

```python
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import re
from datetime import datetime


@dataclass
class PersonProfile:
    """候选人特征画像"""
    name: str
    name_variants: List[str]  # 名字变体（如：Zhang San, San Zhang, 张三）
    education: List[Dict[str, Any]]
    work_history: List[Dict[str, Any]]
    research_interests: List[str]
    email_domains: List[str]  # 邮箱域名（强特征）
    locations: List[str]  # 地理位置
    age_range: Optional[tuple]  # 推测的年龄范围
    
    @classmethod
    def from_resume_data(cls, data: Dict[str, Any]) -> "PersonProfile":
        """从简历数据构建特征画像。"""
        basic = data.get("basic_info", {})
        name = basic.get("name", "")
        
        # 提取邮箱域名（强特征）
        email = (basic.get("contact", {}) or {}).get("email", "")
        email_domains = []
        if email and "@" in email:
            domain = email.split("@")[1].lower()
            email_domains.append(domain)
        
        # 推测年龄范围（基于教育经历）
        age_range = cls._estimate_age_range(data.get("education", []))
        
        # 提取地理位置
        locations = cls._extract_locations(data)
        
        # 生成名字变体
        name_variants = cls._generate_name_variants(name)
        
        return cls(
            name=name,
            name_variants=name_variants,
            education=data.get("education", []),
            work_history=data.get("work_experience", []),
            research_interests=data.get("research_interests", []),
            email_domains=email_domains,
            locations=locations,
            age_range=age_range
        )
    
    @staticmethod
    def _estimate_age_range(education: List[Dict]) -> Optional[tuple]:
        """基于教育经历推测年龄范围。"""
        if not education:
            return None
        
        # 找最近的学位时间
        latest_year = 0
        for edu in education:
            period = edu.get("time_period", "")
            years = re.findall(r"(19|20)\d{2}", period)
            if years:
                latest_year = max(latest_year, max(int(y) for y in years))
        
        if latest_year == 0:
            return None
        
        current_year = datetime.now().year
        
        # 假设博士毕业年龄约27-35岁
        # 硕士约24-30岁
        # 本科约22-26岁
        degree_type = education[0].get("degree", "").lower()
        if "博士" in degree_type or "phd" in degree_type or "doctor" in degree_type:
            graduation_age = 30  # 平均博士毕业年龄
        elif "硕士" in degree_type or "master" in degree_type:
            graduation_age = 26
        else:
            graduation_age = 23
        
        birth_year_estimate = latest_year - graduation_age
        current_age = current_year - birth_year_estimate
        
        # 给一个范围（±5年）
        return (current_age - 5, current_age + 5)
    
    @staticmethod
    def _extract_locations(data: Dict[str, Any]) -> List[str]:
        """提取候选人相关的地理位置。"""
        locations = []
        
        # 从联系方式
        contact_loc = (data.get("basic_info", {}).get("contact", {}) or {}).get("location", "")
        if contact_loc:
            locations.append(contact_loc.lower())
        
        # 从教育经历
        for edu in data.get("education", []):
            school = edu.get("school", "")
            if school:
                # 简单的城市提取（可以用NER模型改进）
                for city in ["北京", "上海", "深圳", "杭州", "广州", "成都", "西安", "武汉", 
                             "beijing", "shanghai", "shenzhen", "hangzhou", "guangzhou"]:
                    if city in school.lower():
                        locations.append(city)
        
        # 从工作经历
        for work in data.get("work_experience", []):
            company = work.get("company", "")
            if company:
                for city in ["北京", "上海", "深圳", "杭州", "广州", "成都", "西安", "武汉",
                             "beijing", "shanghai", "shenzhen", "hangzhou", "guangzhou"]:
                    if city in company.lower():
                        locations.append(city)
        
        return list(set(locations))
    
    @staticmethod
    def _generate_name_variants(name: str) -> List[str]:
        """生成名字变体（中英文、不同排列）。"""
        variants = [name.lower()]
        
        # 中文名处理
        if any('\u4e00' <= c <= '\u9fff' for c in name):
            # 去除空格
            variants.append(name.replace(" ", "").lower())
        
        # 英文名处理（First Last, Last First）
        if " " in name:
            parts = name.split()
            if len(parts) == 2:
                variants.append(f"{parts[1]} {parts[0]}".lower())
                variants.append(f"{parts[1]}, {parts[0]}".lower())
                # 首字母缩写
                variants.append(f"{parts[0][0]}. {parts[1]}".lower())
        
        return list(set(variants))


class PersonDisambiguator:
    """人物消歧类，用于判断搜索结果是否属于同一人。"""
    
    def __init__(self, profile: PersonProfile, llm_client: Optional[Any] = None):
        self.profile = profile
        self.llm = llm_client
    
    def match_score(self, item: Dict[str, Any]) -> float:
        """
        计算搜索结果与候选人的匹配分数（0-100）。
        
        评分维度:
        - 名字匹配: 0-20分
        - 邮箱域名: 0-25分（强特征）
        - 教育背景: 0-20分
        - 地理位置: 0-10分
        - 年龄一致性: 0-10分
        - 研究兴趣: 0-15分
        
        阈值:
        - >= 60分: 高置信度是同一人
        - 40-59分: 需要LLM辅助判断
        - < 40分: 不是同一人
        """
        score = 0.0
        text = " ".join([
            item.get("title", ""),
            item.get("url", ""),
            item.get("content", "")
        ]).lower()
        
        # 1. 名字匹配 (0-20分)
        name_score = self._match_name(text)
        score += name_score
        
        # 2. 邮箱域名匹配 (0-25分，强特征)
        email_score = self._match_email_domain(text)
        score += email_score
        
        # 3. 教育背景匹配 (0-20分)
        edu_score = self._match_education(text)
        score += edu_score
        
        # 4. 地理位置匹配 (0-10分)
        loc_score = self._match_location(text)
        score += loc_score
        
        # 5. 年龄一致性 (0-10分)
        age_score = self._match_age_consistency(text)
        score += age_score
        
        # 6. 研究兴趣匹配 (0-15分)
        interest_score = self._match_research_interests(text)
        score += interest_score
        
        return score
    
    def _match_name(self, text: str) -> float:
        """名字匹配评分"""
        for variant in self.profile.name_variants:
            if variant in text:
                # 完全匹配
                if f" {variant} " in f" {text} ":
                    return 20.0
                # 部分匹配
                return 15.0
        return 0.0
    
    def _match_email_domain(self, text: str) -> float:
        """邮箱域名匹配（强特征）"""
        for domain in self.profile.email_domains:
            if domain in text:
                return 25.0
        return 0.0
    
    def _match_education(self, text: str) -> float:
        """教育背景匹配"""
        score = 0.0
        for edu in self.profile.education:
            school = edu.get("school", "").lower()
            major = edu.get("major", "").lower()
            degree = edu.get("degree", "").lower()
            
            if school and school in text:
                score += 10.0
            if major and major in text:
                score += 5.0
            if degree and degree in text:
                score += 5.0
        
        return min(score, 20.0)
    
    def _match_location(self, text: str) -> float:
        """地理位置匹配"""
        for loc in self.profile.locations:
            if loc in text:
                return 10.0
        return 0.0
    
    def _match_age_consistency(self, text: str) -> float:
        """年龄一致性检查"""
        if not self.profile.age_range:
            return 5.0  # 无法判断，给中等分
        
        # 查找年龄信息
        age_patterns = [
            r"(\d{2})\s*岁",
            r"age\s*:?\s*(\d{2})",
            r"born\s+in\s+(19|20)\d{2}"
        ]
        
        for pattern in age_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                if pattern.endswith("d{2})"):  # 年份
                    birth_year = int(match.group(0))
                    age = datetime.now().year - birth_year
                else:  # 直接年龄
                    age = int(match.group(1))
                
                min_age, max_age = self.profile.age_range
                if min_age <= age <= max_age:
                    return 10.0
                else:
                    return 0.0  # 年龄不符，强烈否定信号
        
        return 5.0  # 未找到年龄信息
    
    def _match_research_interests(self, text: str) -> float:
        """研究兴趣匹配"""
        score = 0.0
        for interest in self.profile.research_interests:
            if interest.lower() in text:
                score += 5.0
        return min(score, 15.0)
    
    def is_same_person(self, item: Dict[str, Any], threshold: float = 60.0) -> bool:
        """判断是否为同一人（带LLM辅助）。"""
        score = self.match_score(item)
        
        if score >= threshold:
            return True
        elif score < 40.0:
            return False
        else:
            # 边界case，使用LLM辅助
            if self.llm:
                return self._llm_verify(item, score)
            else:
                # 无LLM时，保守策略
                return score >= 50.0
    
    def _llm_verify(self, item: Dict[str, Any], prelim_score: float) -> bool:
        """LLM辅助验证（更精确的prompt）。"""
        prompt = f"""
# 任务：人物消歧
判断以下搜索结果是否属于候选人{self.profile.name}。

# 候选人特征
- 姓名: {self.profile.name}
- 姓名变体: {", ".join(self.profile.name_variants)}
- 教育背景: {json.dumps(self.profile.education, ensure_ascii=False)}
- 工作经历: {json.dumps(self.profile.work_history, ensure_ascii=False)}
- 研究兴趣: {", ".join(self.profile.research_interests)}
- 邮箱域名: {", ".join(self.profile.email_domains)}
- 地理位置: {", ".join(self.profile.locations)}
- 推测年龄范围: {self.profile.age_range}

# 搜索结果
- 标题: {item.get("title", "")}
- URL: {item.get("url", "")}
- 内容片段: {item.get("content", "")[:500]}

# 初步匹配分数
{prelim_score:.1f}/100

# 判断标准
- **强否定信号**（直接返回false）:
  1. 年龄明显不符（相差>10岁）
  2. 学位/学校完全不同且无合理解释
  3. 明显不同的职业领域（如医生 vs 工程师）
  4. 地理位置完全无交集且时间线不合理

- **强肯定信号**（直接返回true）:
  1. 邮箱域名匹配
  2. 学校+专业+姓名完全匹配
  3. 独特的研究方向+姓名匹配

- **模糊情况**：
  综合考虑多个弱信号的累积效应

# 输出
严格返回JSON: {{"is_same_person": true/false, "confidence": 0.0-1.0, "reason": "简要理由"}}
        """
        
        try:
            response = self.llm.chat([
                {"role": "system", "content": "你是人物消歧专家，擅长通过多维度证据链判断是否为同一人。"},
                {"role": "user", "content": prompt}
            ])
            result = json.loads(response)
            return result.get("is_same_person", False)
        except Exception as e:
            print(f"[LLM验证错误] {e}")
            return prelim_score >= 50.0
```

#### 方案2: 集成到enricher.py

修改`enricher.py`的`_filter_social_items`:

```python
from utils.person_disambiguation import PersonProfile, PersonDisambiguator

def _filter_social_items_v2(self, name: str, education: List[Dict[str, Any]], items: List[Dict[str, Any]], resume_data: Dict[str, Any]) -> List[Dict[str, Any]:
    """Enhanced filtering with multi-dimensional disambiguation."""
    
    # 构建候选人特征画像
    profile = PersonProfile.from_resume_data(resume_data)
    disambiguator = PersonDisambiguator(profile, llm_client=self.llm)
    
    filtered = []
    for item in items:
        score = disambiguator.match_score(item)
        is_match = disambiguator.is_same_person(item, threshold=60.0)
        
        print(f"[人物消歧] URL={item.get('url')} Score={score:.1f} Match={is_match}")
        
        if is_match:
            # 附加匹配分数供后续分析
            item["disambiguation_score"] = score
            filtered.append(item)
    
    return filtered
```

---

## 问题 4: 工程实战力评价缺少GitHub分析

### 当前问题
- **现象**: "工程实战力"评价主要基于项目经历描述，缺少客观的代码分析
- **原因**: 未集成GitHub数据，无法评估代码质量、贡献度、项目影响力

### 改进方案

已在**问题2的方案1**中包含了`crawl_github_profile`方法，现在需要将其集成到评估流程。

#### 方案1: 增强GitHub数据采集

修改`enricher.py`:

```python
def enrich_engineering_capability(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich engineering capability assessment with GitHub data."""
    
    # 1. 寻找GitHub账号
    github_url = None
    social_presence = data.get("social_presence", [])
    for sp in social_presence:
        if sp.get("platform") == "GitHub":
            github_url = sp.get("url")
            break
    
    if not github_url:
        # 尝试搜索
        name = (data.get("basic_info", {}) or {}).get("name", "")
        if name:
            results = self.search.search(f"{name} GitHub", max_results=5)
            for r in results:
                if "github.com" in r.get("url", ""):
                    github_url = r.get("url")
                    break
    
    if not github_url:
        print(f"[工程能力评估] 未找到GitHub账号")
        data["engineering_capability"] = {"source": "none", "summary": "未找到GitHub账号，无法评估代码工程能力"}
        return data
    
    # 2. 深度爬取GitHub数据
    crawler = SocialContentCrawler()
    username = self._extract_github_username(github_url)
    github_data = crawler.crawl_github_profile(username, github_url)
    
    # 3. LLM分析工程能力
    engineering_eval = self._evaluate_engineering_from_github(github_data)
    
    data["engineering_capability"] = {
        "github_username": username,
        "github_url": github_url,
        "raw_data": github_data,
        **engineering_eval
    }
    
    return data

def _evaluate_engineering_from_github(self, github_data: Dict[str, Any]) -> Dict[str, Any]:
    """Use LLM to evaluate engineering capability from GitHub data."""
    
    prompt = f"""
# 任务：工程实战力评估
基于候选人的GitHub数据，评估其工程实战能力。

# 输入数据
{json.dumps(github_data, ensure_ascii=False, indent=2)}

# 评估维度
1. **代码产出量**：
   - 公开仓库数: {github_data.get('public_repos', 0)}
   - 总star数: {github_data.get('total_stars_received', 0)}
   - 总fork数: {github_data.get('total_forks_received', 0)}
   - 评分: 低/中/高

2. **代码质量**:
   - 测试覆盖: {github_data.get('code_quality_indicators', {}).get('has_tests', 'N/A')}
   - CI/CD实践: {github_data.get('code_quality_indicators', {}).get('has_ci_cd', 'N/A')}
   - 文档质量: {github_data.get('code_quality_indicators', {}).get('documentation_quality', 'N/A')}
   - 评分: 低/中/高

3. **技术广度**:
   - 主要语言: {github_data.get('primary_languages', {})}
   - 评分: 窄/中/广

4. **项目影响力**:
   - Top项目分析（star数、fork数、topics）
   - 评分: 低/中/高

5. **协作能力**:
   - 关注者: {github_data.get('follower_count', 0)}
   - 是否参与开源社区
   - 评分: 低/中/高

6. **持续贡献**:
   - 贡献年份: {github_data.get('contribution_years', [])}
   - 活跃度评分: 低/中/高

# 输出要求
返回JSON对象:
{{
    "code_productivity": {{"score": "高/中/低", "explanation": "..."}},
    "code_quality": {{"score": "高/中/低", "explanation": "..."}},
    "technical_breadth": {{"score": "广/中/窄", "explanation": "..."}},
    "project_impact": {{"score": "高/中/低", "explanation": "...", "top_projects": ["项目1", "项目2"]}},
    "collaboration": {{"score": "高/中/低", "explanation": "..."}},
    "continuous_contribution": {{"score": "高/中/低", "explanation": "..."}},
    "overall_score": 0-10,
    "summary": "综合评价（100字内）",
    "strengths": ["优势1", "优势2"],
    "weaknesses": ["不足1", "不足2"]
}}
    """
    
    try:
        response = self.llm.chat([
            {"role": "system", "content": "你是资深技术面试官，擅长通过GitHub数据评估工程师的实战能力。"},
            {"role": "user", "content": prompt}
        ])
        return json.loads(response)
    except Exception as e:
        print(f"[工程能力评估错误] {e}")
        return {
            "summary": "评估失败",
            "overall_score": 5.0
        }
```

#### 方案2: 集成到多维度评价

修改`multi_dimension_evaluation`的prompt，增加GitHub数据引用:

```python
def multi_dimension_evaluation(self, data: Dict[str, Any]) -> Dict[str, Any]:
    # ... existing code ...
    
    # 添加工程能力数据
    engineering_cap = data.get("engineering_capability", {})
    
    prompt = f"""
# Role
你是一名拥有20年经验的技术专家面试官。

# 特别强调：工程实战力评估
候选人的GitHub数据已采集，请重点参考以下信息评估"工程实战力"维度:
{json.dumps(engineering_cap, ensure_ascii=False, indent=2)}

关键指标:
- 代码产出: {engineering_cap.get('code_productivity', {}).get('score', 'N/A')}
- 代码质量: {engineering_cap.get('code_quality', {}).get('score', 'N/A')}
- 项目影响力: {engineering_cap.get('project_impact', {}).get('score', 'N/A')}
- 综合评分: {engineering_cap.get('overall_score', 'N/A')}/10

# Dimensions
... (rest of the prompt)
    """
```

---

## 问题 5: 缺少Google Scholar等学术平台指标抓取

### 当前问题
- **现象**: `academic_metrics`中的h-index等指标依赖简历原文，很多情况下为空
- **原因**: 虽然有`ScholarMetricsFetcher`，但实现可能不完善或未正确调用

### 当前实现分析

```python
# enricher.py line 524-545
def enrich_scholar_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
    rs = self.search.search(f"{name} Google Scholar", max_results=5)
    # 找到profile URL
    metrics = self.scholar.run(name=name, profile_url=..., content=...)
    # 更新academic_metrics
```

需要查看`ScholarMetricsFetcher`的实现。

<function_calls>
<invoke name="Read">
<parameter name="file_path">/home/user/webapp/infra/scholar_metrics.py
### 当前实现分析

```python
# scholar_metrics.py
class ScholarMetricsFetcher:
    def _parse(self, html: str) -> Dict[str, str]:
        """仅从已有HTML提取，不主动爬取"""
        # 使用正则表达式提取h-index等
        
    def run(self, name, profile_url, content):
        # 只解析传入的content，不访问URL
        return self._parse(content or "")
```

**问题**:
1. 依赖搜索引擎返回的snippet，信息不完整
2. 没有主动访问Google Scholar页面爬取完整数据
3. 正则表达式过于简单，容易匹配失败
4. 未处理反爬虫措施

### 改进方案

#### 方案1: 增强Scholar爬取器（核心）

修改`infra/scholar_metrics.py`:

```python
import re
import time
from typing import Dict, Optional
import requests
from bs4 import BeautifulSoup
import urllib.parse

from .observability import emit


class ScholarMetricsFetcher:
    """Enhanced Google Scholar metrics fetcher with active crawling."""
    
    def __init__(self, timeout: float = 15.0, use_proxy: bool = False):
        self.timeout = float(timeout)
        self.use_proxy = use_proxy
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN,zh;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def run(self, name: str, profile_url: Optional[str] = None, content: Optional[str] = None) -> Dict[str, str]:
        """Enhanced metrics fetching with active crawling."""
        t0 = time.time()
        emit({"kind": "scholar_metrics_start", "name": name, "profile_url": profile_url or ""})
        
        # 1. 如果有profile_url，直接爬取
        if profile_url and "scholar.google" in profile_url:
            metrics = self._crawl_scholar_profile(profile_url)
        # 2. 否则尝试从content解析
        elif content:
            metrics = self._parse(content)
        # 3. 都没有，尝试搜索并爬取
        else:
            metrics = self._search_and_crawl(name)
        
        emit({"kind": "scholar_metrics_end", "name": name, "metrics": metrics, "elapsed_sec": round(time.time() - t0, 3)})
        return metrics
    
    def _crawl_scholar_profile(self, profile_url: str) -> Dict[str, str]:
        """
        主动爬取Google Scholar个人主页。
        
        策略:
        1. 直接访问profile URL
        2. 解析HTML提取指标
        3. 处理反爬虫（延迟、User-Agent）
        """
        try:
            # 添加延迟避免被ban
            time.sleep(1)
            
            resp = self.session.get(profile_url, timeout=self.timeout)
            if not resp.ok:
                print(f"[Scholar爬取] HTTP {resp.status_code}: {profile_url}")
                return self._empty_metrics()
            
            html = resp.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # 方法1: 从表格提取（新版页面）
            metrics = self._extract_from_table(soup)
            if metrics and any(metrics.values()):
                return metrics
            
            # 方法2: 从ID提取（旧版页面）
            metrics = self._extract_from_ids(soup)
            if metrics and any(metrics.values()):
                return metrics
            
            # 方法3: 正则表达式回退
            return self._parse(html)
        
        except requests.Timeout:
            print(f"[Scholar爬取] 超时: {profile_url}")
            return self._empty_metrics()
        except Exception as e:
            print(f"[Scholar爬取错误] {profile_url}: {e}")
            return self._empty_metrics()
    
    def _extract_from_table(self, soup: BeautifulSoup) -> Dict[str, str]:
        """从新版Google Scholar页面的表格提取。"""
        metrics = self._empty_metrics()
        
        try:
            # Google Scholar的指标通常在id="gsc_rsb_st"的表格中
            table = soup.find('table', {'id': 'gsc_rsb_st'})
            if not table:
                return metrics
            
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 3:
                    continue
                
                label = cells[0].get_text(strip=True).lower()
                all_time = cells[1].get_text(strip=True)
                since_2019 = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                
                if 'citations' in label:
                    metrics["citations_total"] = all_time
                    metrics["citations_recent"] = since_2019
                elif 'h-index' in label or 'h index' in label:
                    metrics["h_index"] = all_time
                elif 'h10' in label or 'i10' in label:
                    # 注意: Google Scholar显示的是i10-index，不是h10
                    metrics["i10_index"] = all_time
                    # 如果需要h10，需要额外计算
            
            return metrics
        except Exception as e:
            print(f"[表格提取错误] {e}")
            return metrics
    
    def _extract_from_ids(self, soup: BeautifulSoup) -> Dict[str, str]:
        """从元素ID提取（备用方法）。"""
        metrics = self._empty_metrics()
        
        try:
            # Google Scholar使用特定的ID
            citations_all = soup.find('td', {'class': 'gsc_rsb_std'})
            if citations_all:
                metrics["citations_total"] = citations_all.get_text(strip=True)
            
            # h-index和i10-index在后续的td中
            # 需要根据实际页面结构调整
            
            return metrics
        except Exception as e:
            print(f"[ID提取错误] {e}")
            return metrics
    
    def _search_and_crawl(self, name: str) -> Dict[str, str]:
        """
        搜索学者并爬取其Google Scholar主页。
        
        步骤:
        1. 构建搜索URL
        2. 访问搜索结果页
        3. 提取第一个profile链接
        4. 爬取该profile
        """
        try:
            # 构建Google Scholar搜索URL
            query = urllib.parse.quote(name)
            search_url = f"https://scholar.google.com/citations?hl=en&view_op=search_authors&mauthors={query}"
            
            print(f"[Scholar搜索] {search_url}")
            time.sleep(2)  # 更长延迟
            
            resp = self.session.get(search_url, timeout=self.timeout)
            if not resp.ok:
                return self._empty_metrics()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 查找第一个作者profile链接
            profile_links = soup.find_all('a', {'class': 'gs_ai_pho'}) or soup.find_all('h3', {'class': 'gs_ai_name'})
            
            if not profile_links:
                print(f"[Scholar搜索] 未找到作者: {name}")
                return self._empty_metrics()
            
            # 提取href
            first_link = profile_links[0]
            if first_link.name == 'a':
                href = first_link.get('href', '')
            else:
                a_tag = first_link.find('a')
                href = a_tag.get('href', '') if a_tag else ''
            
            if not href:
                return self._empty_metrics()
            
            # 构建完整URL
            if href.startswith('/citations'):
                profile_url = f"https://scholar.google.com{href}"
            else:
                profile_url = href
            
            print(f"[Scholar搜索] 找到profile: {profile_url}")
            
            # 爬取profile
            return self._crawl_scholar_profile(profile_url)
        
        except Exception as e:
            print(f"[Scholar搜索错误] {name}: {e}")
            return self._empty_metrics()
    
    def _parse(self, html: str) -> Dict[str, str]:
        """Enhanced regex parsing with more patterns."""
        s = html or ""
        out = self._empty_metrics()
        
        # h-index的多种模式
        patterns_h = [
            r"h[-\s]?index[^0-9]*([0-9]+)",
            r"h指数[^0-9]*([0-9]+)",
            r"<td[^>]*>h-index</td>\s*<td[^>]*>([0-9]+)</td>",
        ]
        for pat in patterns_h:
            m = re.search(pat, s, re.I)
            if m:
                out["h_index"] = m.group(1)
                break
        
        # i10-index (Google Scholar使用这个，不是h10)
        patterns_i10 = [
            r"i10[-\s]?index[^0-9]*([0-9]+)",
            r"<td[^>]*>i10-index</td>\s*<td[^>]*>([0-9]+)</td>",
        ]
        for pat in patterns_i10:
            m = re.search(pat, s, re.I)
            if m:
                out["i10_index"] = m.group(1)
                break
        
        # Citations总数
        patterns_cit = [
            r"Citations[^0-9]*([0-9,]+)",
            r"引用次数[^0-9]*([0-9,]+)",
            r"<td[^>]*>Citations</td>\s*<td[^>]*>([0-9,]+)</td>",
        ]
        for pat in patterns_cit:
            m = re.search(pat, s, re.I)
            if m:
                out["citations_total"] = m.group(1).replace(',', '')
                break
        
        # 近期引用（Since 2019等）
        patterns_recent = [
            r"Since\s+20\d{2}[^0-9]*([0-9,]+)",
            r"近\d年[^0-9]*([0-9,]+)",
        ]
        for pat in patterns_recent:
            m = re.search(pat, s, re.I)
            if m:
                out["citations_recent"] = m.group(1).replace(',', '')
                break
        
        return out
    
    def _empty_metrics(self) -> Dict[str, str]:
        """Return empty metrics structure."""
        return {
            "h_index": "",
            "i10_index": "",  # Google Scholar的标准
            "citations_total": "",
            "citations_recent": "",
        }
```

#### 方案2: 支持其他学术平台

扩展以支持ResearchGate、Semantic Scholar等:

```python
class AcademicMetricsFetcher:
    """Multi-platform academic metrics aggregator."""
    
    def __init__(self):
        self.google_scholar = ScholarMetricsFetcher()
        # 可扩展其他平台
        self.researchgate = ResearchGateFetcher()
        self.semantic_scholar = SemanticScholarFetcher()
    
    def fetch_all(self, name: str, urls: Dict[str, str]) -> Dict[str, Any]:
        """
        从多个平台聚合学术指标。
        
        Args:
            name: 学者姓名
            urls: {"google_scholar": "url", "researchgate": "url", ...}
        
        Returns:
            {
                "google_scholar": {...},
                "researchgate": {...},
                "semantic_scholar": {...},
                "aggregated": {  // 聚合后的最佳估计
                    "h_index": "15",
                    "citations_total": "1200",
                    ...
                }
            }
        """
        results = {}
        
        # Google Scholar
        gs_url = urls.get("google_scholar")
        if gs_url:
            results["google_scholar"] = self.google_scholar.run(name, profile_url=gs_url)
        
        # ResearchGate
        rg_url = urls.get("researchgate")
        if rg_url:
            results["researchgate"] = self.researchgate.fetch(rg_url)
        
        # Semantic Scholar
        results["semantic_scholar"] = self.semantic_scholar.search_by_name(name)
        
        # 聚合（取最大值或最新值）
        results["aggregated"] = self._aggregate_metrics(results)
        
        return results
    
    def _aggregate_metrics(self, platform_data: Dict[str, Dict]) -> Dict[str, str]:
        """Aggregate metrics from multiple platforms."""
        # 优先级: Google Scholar > Semantic Scholar > ResearchGate
        agg = {}
        
        for platform in ["google_scholar", "semantic_scholar", "researchgate"]:
            data = platform_data.get(platform, {})
            for key in ["h_index", "citations_total", "citations_recent", "i10_index"]:
                if key in data and data[key] and not agg.get(key):
                    agg[key] = data[key]
        
        return agg
```

#### 方案3: 反爬虫策略

为避免被Google Scholar封禁：

```python
class AntiBlockStrategy:
    """Anti-blocking strategies for web crawling."""
    
    @staticmethod
    def rotating_user_agents() -> List[str]:
        """Return a list of user agents to rotate."""
        return [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) Firefox/120.0',
        ]
    
    @staticmethod
    def random_delay(min_sec: float = 2.0, max_sec: float = 5.0) -> None:
        """Random delay between requests."""
        import random
        time.sleep(random.uniform(min_sec, max_sec))
    
    @staticmethod
    def use_proxy(session: requests.Session, proxy_url: str) -> None:
        """Configure session to use proxy."""
        session.proxies.update({
            'http': proxy_url,
            'https': proxy_url,
        })
```

---

## 实施优先级与时间估算

### P0: 必须立即修复（1-2天）
1. **问题1 - 论文解析**: 增强Prompt（2小时）✅
2. **问题3 - 同名人物**: 实现PersonDisambiguator（6小时）✅
3. **问题5 - Scholar爬取**: 增强ScholarMetricsFetcher（4小时）✅

### P1: 重要改进（3-5天）
4. **问题2 - 社交深度分析**: 实现SocialContentCrawler（8小时）
5. **问题4 - GitHub评估**: 集成GitHub分析到评价体系（6小时）
6. **测试与验证**: 端到端测试（8小时）

### P2: 后续优化（1-2周）
7. 反爬虫策略完善
8. 多平台学术指标聚合
9. 性能优化与缓存
10. 监控与告警

---

## 测试计划

### 单元测试
- [ ] PersonDisambiguator匹配算法测试
- [ ] ScholarMetricsFetcher爬取测试
- [ ] SocialContentCrawler各平台测试
- [ ] GitHub分析逻辑测试

### 集成测试
- [ ] 端到端简历处理流程
- [ ] 多候选人并发处理
- [ ] 边界case测试（同名、无GitHub、无Scholar等）

### 性能测试
- [ ] 爬取延迟测试
- [ ] 反爬虫有效性测试
- [ ] 并发处理能力测试

---

## 风险与缓解

### 风险1: 被Google Scholar封禁
- **缓解**: 
  - 使用代理池
  - 增加请求间隔（2-5秒）
  - 限制每天请求次数
  - 缓存已爬取数据

### 风险2: 平台结构变化
- **缓解**:
  - 多种解析方法并存
  - 定期检查爬虫有效性
  - 日志记录失败case

### 风险3: LLM成本增加
- **缓解**:
  - 优化prompt减少token
  - 缓存LLM结果
  - 仅关键步骤使用LLM

### 风险4: 处理时间延长
- **缓解**:
  - 并发爬取（限制并发数避免封禁）
  - 异步处理架构
  - 用户进度反馈

---

## 成功指标

### 数据完整性
- 论文识别率：95%+ （包含预印本和投稿）
- Scholar指标获取率：80%+
- GitHub数据获取率：90%+ （如有账号）

### 准确性
- 同名人物误识别率：< 5%
- 社交账号匹配准确率：90%+

### 性能
- 单份简历处理时间：< 5分钟
- 爬取成功率：85%+

### 用户体验
- 评价维度完整性：5个维度全覆盖
- 评价依据可追溯：所有评分有evidence链接

---

**文档版本**: v1.0  
**最后更新**: 2025-12-12  
**负责人**: GenSpark AI Assistant  
**状态**: 待审批与实施
