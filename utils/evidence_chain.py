"""
Evidence Chain Tracing Module
证据链追溯模块

Builds traceable evidence chains from evaluation claims to supporting evidence.
从评价观点到支持证据建立可追溯的证据链。

Key features:
- Extract atomic claims from evaluation text
- Find supporting evidence in resume data
- Calculate confidence for each claim
- Generate clickable evidence links
- Score breakdown with transparent weighting
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import re
import json


@dataclass
class Claim:
    """Individual claim from evaluation"""
    text: str
    dimension: str  # Which evaluation dimension
    claim_type: str  # "achievement", "skill", "impact", "collaboration", etc.
    confidence: float  # 0-1, how confident we are in this claim
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "dimension": self.dimension,
            "claim_type": self.claim_type,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class Evidence:
    """Supporting evidence for a claim"""
    source_type: str  # "publication", "award", "project", "social", etc.
    item_id: str  # Unique identifier for the item
    relevance_score: float  # 0-1, how relevant to the claim
    link: str  # HTML anchor or URL
    snippet: str  # Brief excerpt or description
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "item_id": self.item_id,
            "relevance_score": round(self.relevance_score, 2),
            "link": self.link,
            "snippet": self.snippet[:200],  # Limit length
        }


@dataclass
class EvidenceChain:
    """Evidence chain for a specific claim"""
    claim: Claim
    supporting_evidence: List[Evidence]
    overall_confidence: float  # 0-1, based on evidence strength
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim.to_dict(),
            "supporting_evidence": [e.to_dict() for e in self.supporting_evidence],
            "overall_confidence": round(self.overall_confidence, 2),
        }


class EvidenceChainBuilder:
    """
    Build traceable evidence chains from evaluation text
    """
    
    def __init__(self, llm_client=None):
        """
        Initialize evidence chain builder
        
        Args:
            llm_client: Optional LLM client for claim extraction
        """
        self.llm = llm_client
    
    def build_evidence_chains(
        self,
        evaluation_text: str,
        dimension: str,
        resume_data: Dict[str, Any]
    ) -> List[EvidenceChain]:
        """
        Build evidence chains for evaluation text
        
        Args:
            evaluation_text: Evaluation paragraph
            dimension: Evaluation dimension name
            resume_data: Complete resume data
            
        Returns:
            List of evidence chains
        """
        # Step 1: Extract claims from evaluation text
        claims = self._extract_claims(evaluation_text, dimension)
        
        # Step 2: Find supporting evidence for each claim
        evidence_chains = []
        for claim in claims:
            supporting_evidence = self._find_supporting_evidence(claim, resume_data)
            overall_confidence = self._calculate_chain_confidence(supporting_evidence)
            
            chain = EvidenceChain(
                claim=claim,
                supporting_evidence=supporting_evidence,
                overall_confidence=overall_confidence
            )
            evidence_chains.append(chain)
        
        return evidence_chains
    
    def build_score_breakdown(
        self,
        score: float,
        dimension: str,
        resume_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build transparent score breakdown showing how score was calculated
        
        Args:
            score: Overall score for dimension
            dimension: Dimension name
            resume_data: Resume data
            
        Returns:
            Score breakdown with components and weights
        """
        # Define scoring components based on dimension
        components = self._get_score_components(dimension, resume_data)
        
        # Calculate weighted average
        weighted_sum = sum(c["score"] * c["weight"] for c in components)
        
        breakdown = {
            "final_score": round(score, 1),
            "components": components,
            "calculation": self._format_calculation(components, weighted_sum),
            "weights_explained": "Weights reflect importance of each factor in assessing this dimension"
        }
        
        return breakdown
    
    def _extract_claims(self, text: str, dimension: str) -> List[Claim]:
        """
        Extract individual claims from evaluation text
        
        Uses simple heuristics if no LLM available
        """
        if self.llm:
            return self._extract_claims_with_llm(text, dimension)
        else:
            return self._extract_claims_heuristic(text, dimension)
    
    def _extract_claims_with_llm(self, text: str, dimension: str) -> List[Claim]:
        """Extract claims using LLM"""
        prompt = f"""将以下评价拆分为独立的、可验证的观点（claims）。

评价文本（维度: {dimension}）：
{text}

要求：
1. 每个claim应该是一个独立的、具体的陈述
2. 应该是可以被简历数据验证的事实性陈述
3. 输出JSON数组格式

示例输出：
[
    {{"text": "候选人在Transformer理论逼近方面有重要贡献", "type": "achievement"}},
    {{"text": "提出了新型有限元构造方法", "type": "achievement"}},
    {{"text": "与产业界保持紧密合作", "type": "collaboration"}}
]

输出（仅JSON，不要其他内容）："""
        
        try:
            response = self.llm.chat([
                {"role": "system", "content": "你是一个专业的文本分析助手，擅长提取关键观点。"},
                {"role": "user", "content": prompt}
            ])
            
            # Parse JSON response
            claims_data = json.loads(response)
            
            claims = []
            for item in claims_data:
                claim = Claim(
                    text=item.get("text", ""),
                    dimension=dimension,
                    claim_type=item.get("type", "general"),
                    confidence=0.8  # Initial confidence
                )
                claims.append(claim)
            
            return claims
            
        except Exception as e:
            print(f"[证据链-警告] LLM提取claims失败: {e}，使用启发式方法")
            return self._extract_claims_heuristic(text, dimension)
    
    def _extract_claims_heuristic(self, text: str, dimension: str) -> List[Claim]:
        """Extract claims using heuristic rules"""
        claims = []
        
        # Split by sentences
        sentences = re.split(r'[。！？；]', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Too short to be meaningful
                continue
            
            # Determine claim type based on keywords
            claim_type = "general"
            if any(kw in sentence for kw in ["贡献", "提出", "研究", "发表", "开发"]):
                claim_type = "achievement"
            elif any(kw in sentence for kw in ["合作", "协作", "团队"]):
                claim_type = "collaboration"
            elif any(kw in sentence for kw in ["影响", "引用", "知名"]):
                claim_type = "impact"
            elif any(kw in sentence for kw in ["能力", "擅长", "掌握"]):
                claim_type = "skill"
            
            claim = Claim(
                text=sentence,
                dimension=dimension,
                claim_type=claim_type,
                confidence=0.7  # Lower confidence for heuristic extraction
            )
            claims.append(claim)
        
        return claims[:5]  # Limit to top 5 claims
    
    def _find_supporting_evidence(
        self,
        claim: Claim,
        resume_data: Dict[str, Any]
    ) -> List[Evidence]:
        """Find supporting evidence for a claim"""
        evidence_list = []
        
        # Search in publications
        publications = resume_data.get("publications", [])
        for i, pub in enumerate(publications):
            relevance = self._calculate_relevance(claim.text, pub)
            if relevance > 0.5:
                evidence = Evidence(
                    source_type="publication",
                    item_id=f"pub-{i}",
                    relevance_score=relevance,
                    link=f"#pub-{i}",
                    snippet=f"{pub.get('title', 'N/A')} ({pub.get('journal', 'N/A')}, "
                            f"{pub.get('year', 'N/A')})"
                )
                evidence_list.append(evidence)
        
        # Search in awards
        awards = resume_data.get("awards", [])
        for i, award in enumerate(awards):
            if self._claim_supported_by_award(claim.text, award):
                evidence = Evidence(
                    source_type="award",
                    item_id=f"award-{i}",
                    relevance_score=0.8,
                    link=f"#award-{i}",
                    snippet=award.get("name", "N/A")
                )
                evidence_list.append(evidence)
        
        # Search in projects
        projects = resume_data.get("projects", [])
        for i, project in enumerate(projects):
            relevance = self._calculate_relevance(claim.text, project)
            if relevance > 0.5:
                evidence = Evidence(
                    source_type="project",
                    item_id=f"project-{i}",
                    relevance_score=relevance,
                    link=f"#project-{i}",
                    snippet=project.get("name", "N/A")
                )
                evidence_list.append(evidence)
        
        # Sort by relevance
        evidence_list.sort(key=lambda e: e.relevance_score, reverse=True)
        
        return evidence_list[:5]  # Top 5 pieces of evidence
    
    def _calculate_relevance(self, claim_text: str, item: Dict[str, Any]) -> float:
        """
        Calculate relevance score between claim and resume item
        
        Simple keyword matching approach
        """
        claim_lower = claim_text.lower()
        
        # Extract text from item
        item_text = ""
        if "title" in item:
            item_text += item["title"] + " "
        if "abstract" in item:
            item_text += str(item.get("abstract", "")) + " "
        if "description" in item:
            item_text += str(item.get("description", "")) + " "
        if "name" in item:
            item_text += item["name"] + " "
        
        item_text_lower = item_text.lower()
        
        # Extract keywords from claim (words > 2 chars)
        claim_keywords = [w for w in re.findall(r'\w+', claim_lower) if len(w) > 2]
        
        if not claim_keywords:
            return 0.0
        
        # Calculate match ratio
        matches = sum(1 for kw in claim_keywords if kw in item_text_lower)
        relevance = matches / len(claim_keywords)
        
        return relevance
    
    def _claim_supported_by_award(self, claim_text: str, award: Dict[str, Any]) -> bool:
        """Check if award supports claim"""
        claim_lower = claim_text.lower()
        award_name = award.get("name", "").lower()
        
        # Check for achievement-related claims
        if any(kw in claim_lower for kw in ["优秀", "杰出", "卓越", "贡献", "奖", "荣誉"]):
            return True
        
        return False
    
    def _calculate_chain_confidence(self, evidence_list: List[Evidence]) -> float:
        """
        Calculate overall confidence based on evidence strength
        
        More evidence = higher confidence
        Higher relevance = higher confidence
        """
        if not evidence_list:
            return 0.3  # Low confidence without evidence
        
        # Average relevance of top 3 pieces of evidence
        top_relevances = [e.relevance_score for e in evidence_list[:3]]
        avg_relevance = sum(top_relevances) / len(top_relevances)
        
        # Bonus for having multiple pieces of evidence
        evidence_bonus = min(0.2, len(evidence_list) * 0.05)
        
        confidence = min(1.0, avg_relevance + evidence_bonus)
        
        return confidence
    
    def _get_score_components(
        self,
        dimension: str,
        resume_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get scoring components for a dimension
        
        Returns list of components with scores and weights
        """
        components = []
        
        if dimension == "学术创新力" or dimension == "Academic Innovation":
            components = [
                {
                    "name": "Publication Quality",
                    "name_cn": "论文质量",
                    "score": self._score_publication_quality(resume_data),
                    "weight": 0.4,
                    "description": "Based on venue tier and impact factor"
                },
                {
                    "name": "Innovation Level",
                    "name_cn": "创新程度",
                    "score": self._score_innovation_level(resume_data),
                    "weight": 0.3,
                    "description": "Novel methods, breakthrough results"
                },
                {
                    "name": "Research Independence",
                    "name_cn": "研究独立性",
                    "score": self._score_independence(resume_data),
                    "weight": 0.2,
                    "description": "First-author rate, corresponding author"
                },
                {
                    "name": "Field Impact",
                    "name_cn": "领域影响",
                    "score": self._score_field_impact(resume_data),
                    "weight": 0.1,
                    "description": "Citations, h-index percentile"
                },
            ]
        
        elif dimension == "工程实战力" or dimension == "Engineering Practice":
            components = [
                {
                    "name": "Project Experience",
                    "name_cn": "项目经验",
                    "score": self._score_project_experience(resume_data),
                    "weight": 0.4,
                    "description": "Industry projects, open-source contributions"
                },
                {
                    "name": "Technical Skills",
                    "name_cn": "技术能力",
                    "score": self._score_technical_skills(resume_data),
                    "weight": 0.3,
                    "description": "Programming, tools, frameworks"
                },
                {
                    "name": "Production Impact",
                    "name_cn": "实际成果",
                    "score": 7.0,  # Placeholder
                    "weight": 0.2,
                    "description": "Deployed systems, user impact"
                },
                {
                    "name": "Problem Solving",
                    "name_cn": "解决问题能力",
                    "score": 7.5,  # Placeholder
                    "weight": 0.1,
                    "description": "Complex challenges tackled"
                },
            ]
        
        else:
            # Generic components
            components = [
                {
                    "name": "Primary Factor",
                    "name_cn": "主要因素",
                    "score": 7.0,
                    "weight": 0.6,
                    "description": "Main assessment criterion"
                },
                {
                    "name": "Secondary Factor",
                    "name_cn": "次要因素",
                    "score": 7.5,
                    "weight": 0.4,
                    "description": "Supporting criterion"
                },
            ]
        
        return components
    
    def _score_publication_quality(self, resume_data: Dict[str, Any]) -> float:
        """Score publication quality based on venue tiers"""
        publications = resume_data.get("publications", [])
        if not publications:
            return 5.0
        
        tier_scores = {"T1": 10.0, "T2": 8.0, "T3": 6.0, "T4": 4.0, "Unknown": 5.0}
        
        scores = []
        for pub in publications:
            venue_quality = pub.get("venue_quality", {})
            tier = venue_quality.get("tier", "Unknown")
            scores.append(tier_scores.get(tier, 5.0))
        
        # Average of top 10 publications
        top_scores = sorted(scores, reverse=True)[:10]
        return sum(top_scores) / len(top_scores) if top_scores else 5.0
    
    def _score_innovation_level(self, resume_data: Dict[str, Any]) -> float:
        """Score innovation level (placeholder)"""
        # Would need sophisticated analysis
        return 7.5
    
    def _score_independence(self, resume_data: Dict[str, Any]) -> float:
        """Score research independence"""
        # Check if authorship analysis is available
        authorship = resume_data.get("authorship_analysis", {})
        if authorship:
            independence_score = authorship.get("metrics", {}).get("independence_score", 0.5)
            return independence_score * 10  # Scale to 0-10
        
        return 6.0  # Default
    
    def _score_field_impact(self, resume_data: Dict[str, Any]) -> float:
        """Score field impact based on citations"""
        metrics = resume_data.get("basic_info", {}).get("academic_metrics", {})
        benchmark = metrics.get("benchmark", {})
        
        if benchmark:
            h_percentile = benchmark.get("h_index_analysis", {}).get("percentile", 50)
            return h_percentile / 10  # Scale percentile to 0-10
        
        return 5.0  # Default
    
    def _score_project_experience(self, resume_data: Dict[str, Any]) -> float:
        """Score project experience"""
        projects = resume_data.get("projects", [])
        if len(projects) >= 5:
            return 8.0
        elif len(projects) >= 3:
            return 7.0
        elif len(projects) >= 1:
            return 6.0
        else:
            return 4.0
    
    def _score_technical_skills(self, resume_data: Dict[str, Any]) -> float:
        """Score technical skills"""
        skills = resume_data.get("skills", [])
        if len(skills) >= 10:
            return 8.5
        elif len(skills) >= 5:
            return 7.5
        else:
            return 6.0
    
    def _format_calculation(self, components: List[Dict], weighted_sum: float) -> str:
        """Format score calculation as equation"""
        terms = [
            f"{c['weight']:.1f}×{c['score']:.1f}"
            for c in components
        ]
        equation = " + ".join(terms)
        return f"{equation} = {weighted_sum:.1f}"


# Convenience function
def build_evidence_chains_for_evaluation(
    evaluation_dict: Dict[str, Any],
    resume_data: Dict[str, Any],
    llm_client=None
) -> Dict[str, Any]:
    """
    Build evidence chains for entire evaluation
    
    Args:
        evaluation_dict: Multi-dimension evaluation dict
        resume_data: Complete resume data
        llm_client: Optional LLM client
        
    Returns:
        Enhanced evaluation with evidence chains
    """
    builder = EvidenceChainBuilder(llm_client)
    
    enhanced_evaluation = {}
    
    for dimension, content in evaluation_dict.items():
        if isinstance(content, dict):
            evaluation_text = content.get("evaluation", "")
        else:
            evaluation_text = str(content)
        
        # Build evidence chains
        chains = builder.build_evidence_chains(
            evaluation_text=evaluation_text,
            dimension=dimension,
            resume_data=resume_data
        )
        
        enhanced_evaluation[dimension] = {
            "evaluation": evaluation_text,
            "evidence_chains": [chain.to_dict() for chain in chains],
            "evidence_sources": content.get("evidence_sources", []) if isinstance(content, dict) else [],
        }
    
    return enhanced_evaluation
