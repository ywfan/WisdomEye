"""
Comprehensive Risk Assessment System for Academic Candidate Evaluation
学术候选人评估的全面风险评估系统

This module provides systematic risk detection and analysis for:
- Research independence
- Productivity sustainability
- Academic integrity
- Collaboration health
- Field relevance
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import re
from datetime import datetime


class RiskSeverity(Enum):
    """风险严重程度"""
    CRITICAL = "严重"  # 关键问题，需立即关注
    HIGH = "高"  # 严重关切，必须调查
    MEDIUM = "中"  # 值得注意，应当验证
    LOW = "低"  # 轻微关注，需要了解


class RiskCategory(Enum):
    """风险类别"""
    INDEPENDENCE = "研究独立性"
    PRODUCTIVITY = "学术产出"
    INTEGRITY = "学术诚信"
    COLLABORATION = "合作能力"
    RELEVANCE = "领域相关性"
    TEACHING = "教学能力"


@dataclass
class Risk:
    """Individual risk item"""
    category: RiskCategory
    severity: RiskSeverity
    title: str
    detail: str
    implication: str
    mitigation: List[str]
    red_flag: bool = False  # Critical warning flag
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "detail": self.detail,
            "implication": self.implication,
            "mitigation": self.mitigation,
            "red_flag": self.red_flag,
        }


class RiskAssessor:
    """
    Comprehensive risk assessment system
    """
    
    def __init__(self, current_year: int = None):
        """
        Initialize risk assessor
        
        Args:
            current_year: Current year for calculations (defaults to current year)
        """
        if current_year is None:
            from datetime import datetime
            current_year = datetime.now().year
        self.current_year = current_year
    
    def assess_all_risks(self, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive risk assessment
        
        Args:
            resume_data: Complete resume JSON data
            
        Returns:
            Complete risk assessment report
        """
        risks = []
        
        # Category 1: Research Independence
        risks.extend(self.assess_research_independence(resume_data))
        
        # Category 2: Productivity
        risks.extend(self.assess_productivity(resume_data))
        
        # Category 3: Academic Integrity
        risks.extend(self.assess_academic_integrity(resume_data))
        
        # Category 4: Collaboration Health
        risks.extend(self.assess_collaboration(resume_data))
        
        # Category 5: Field Relevance
        risks.extend(self.assess_field_relevance(resume_data))
        
        # Category 6: Teaching Ability
        risks.extend(self.assess_teaching_ability(resume_data))
        
        # Categorize by severity
        critical_risks = [r for r in risks if r.severity == RiskSeverity.CRITICAL]
        high_risks = [r for r in risks if r.severity == RiskSeverity.HIGH]
        medium_risks = [r for r in risks if r.severity == RiskSeverity.MEDIUM]
        low_risks = [r for r in risks if r.severity == RiskSeverity.LOW]
        
        # Calculate overall risk level
        overall_risk = self._calculate_overall_risk(risks)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(risks, overall_risk)
        
        return {
            "risks": {
                "critical": [r.to_dict() for r in critical_risks],
                "high": [r.to_dict() for r in high_risks],
                "medium": [r.to_dict() for r in medium_risks],
                "low": [r.to_dict() for r in low_risks],
            },
            "summary": {
                "total_risks": len(risks),
                "critical_count": len(critical_risks),
                "high_count": len(high_risks),
                "medium_count": len(medium_risks),
                "low_count": len(low_risks),
                "red_flags": len([r for r in risks if r.red_flag]),
            },
            "overall_risk_level": overall_risk,
            "recommendation": recommendation,
        }
    
    def assess_research_independence(self, data: Dict[str, Any]) -> List[Risk]:
        """
        Assess candidate's research independence
        
        Key indicators:
        - First-author publication rate
        - Corresponding author publications
        - Co-author diversity
        - Research topic evolution
        """
        risks = []
        publications = data.get("publications", [])
        
        if not publications:
            return risks
        
        # Extract candidate name
        candidate_name = data.get("basic_info", {}).get("name", "")
        
        # Analyze authorship patterns
        first_author_count = 0
        corresponding_count = 0
        coauthors = set()
        
        for pub in publications:
            authors = pub.get("authors", [])
            if not authors:
                continue
            
            # Check first author
            if self._is_first_author(authors, candidate_name):
                first_author_count += 1
            
            # Check corresponding author (if available)
            if self._is_corresponding_author(pub, candidate_name):
                corresponding_count += 1
            
            # Track co-authors
            for author in authors:
                if author != candidate_name:
                    coauthors.add(author)
        
        total_pubs = len(publications)
        first_author_rate = first_author_count / total_pubs if total_pubs > 0 else 0
        
        # Risk 1: Low first-author rate
        if first_author_rate < 0.3:
            risks.append(Risk(
                category=RiskCategory.INDEPENDENCE,
                severity=RiskSeverity.HIGH,
                title=f"第一作者论文比例过低 ({first_author_rate:.1%})",
                detail=f"{total_pubs}篇论文中仅{first_author_count}篇为第一作者。",
                implication="可能过度依赖导师/合作者，独立研究能力存疑。",
                mitigation=[
                    "要求提供详细的独立研究计划说明",
                    "面试时探查候选人提出原创研究问题的能力",
                    "联系推荐人特别询问独立性情况",
                ],
                red_flag=True
            ))
        elif first_author_rate < 0.5:
            risks.append(Risk(
                category=RiskCategory.INDEPENDENCE,
                severity=RiskSeverity.MEDIUM,
                title=f"第一作者比例中等 ({first_author_rate:.1%})",
                detail=f"{total_pubs}篇论文中有{first_author_count}篇为第一作者。",
                implication="候选人有一定独立工作，但合作论文占比较大，需验证领导能力。",
                mitigation=[
                    "要求提供独立主导项目的实例",
                    "推荐人验证时关注研究领导力",
                ],
                red_flag=False
            ))
        
        # Risk 2: No corresponding authorship
        if corresponding_count == 0 and total_pubs > 3:
            risks.append(Risk(
                category=RiskCategory.INDEPENDENCE,
                severity=RiskSeverity.MEDIUM,
                title="无通讯作者论文",
                detail="候选人从未担任任何论文的通讯作者。",
                implication="可能未主导过完整研究项目（从构思到发表），领导经验不明确。",
                mitigation=[
                    "推荐人验证时专门询问研究领导力",
                    "要求提供项目领导经验实例",
                ],
                red_flag=False
            ))
        
        # Risk 3: Limited co-author diversity
        if len(coauthors) < 5 and total_pubs > 10:
            risks.append(Risk(
                category=RiskCategory.INDEPENDENCE,
                severity=RiskSeverity.MEDIUM,
                title=f"合作者多样性有限（仅{len(coauthors)}位不同合作者）",
                detail=f"{total_pubs}篇论文中仅有{len(coauthors)}位不同的合作者。",
                implication="可能过度依赖小型研究团队，人脉网络或合作能力有限。",
                mitigation=[
                    "面试时讨论合作策略",
                    "验证建立新合作关系的能力",
                ],
                red_flag=False
            ))
        
        return risks
    
    def assess_productivity(self, data: Dict[str, Any]) -> List[Risk]:
        """
        Assess publication productivity and sustainability
        
        Key indicators:
        - Recent publication rate
        - Publication gaps
        - Productivity trend
        """
        risks = []
        publications = data.get("publications", [])
        
        if not publications:
            return risks
        
        # Analyze publication timeline
        pub_years = []
        for pub in publications:
            year = pub.get("year")
            if year:
                try:
                    pub_years.append(int(year))
                except (ValueError, TypeError):
                    pass
        
        if not pub_years:
            return risks
        
        pub_years.sort()
        
        # Calculate recent productivity (last 2 years)
        recent_pubs = [y for y in pub_years if y >= self.current_year - 2]
        recent_pub_rate = len(recent_pubs) / 2.0
        
        # Risk 1: Low recent productivity
        if recent_pub_rate < 1.0 and len(publications) > 3:
            risks.append(Risk(
                category=RiskCategory.PRODUCTIVITY,
                severity=RiskSeverity.MEDIUM,
                title=f"近期发表率偏低（{recent_pub_rate:.1f}篇/年）",
                detail=f"近两年仅发表{len(recent_pubs)}篇论文。",
                implication="可能难以满足终身教职发表要求（典型期望：每年2-3篇高质量论文）。",
                mitigation=[
                    "询问正在进行的工作",
                    "检查在审论文",
                    "了解产出缺口的原因",
                ],
                red_flag=False
            ))
        
        # Risk 2: Extended publication gap
        gaps = []
        for i in range(1, len(pub_years)):
            gap_months = (pub_years[i] - pub_years[i-1]) * 12
            if gap_months > 0:
                gaps.append((gap_months, pub_years[i-1], pub_years[i]))
        
        if gaps:
            max_gap = max(gaps, key=lambda x: x[0])
            gap_months, gap_start, gap_end = max_gap
            
            if gap_months > 24:
                risks.append(Risk(
                    category=RiskCategory.PRODUCTIVITY,
                    severity=RiskSeverity.HIGH,
                    title=f"长时间发表空缺（{gap_months}个月）",
                    detail=f"空缺期：{gap_start}年至{gap_end}年",
                    implication="研究中断较长，可能存在职业中断或产出问题。",
                    mitigation=[
                        "⚠️ 必须在面试时调查原因",
                        "可能表明个人问题、项目失败或缺乏专注",
                        "要求提供空缺期间正在进行的工作信息",
                    ],
                    red_flag=True
                ))
            elif gap_months > 18:
                risks.append(Risk(
                    category=RiskCategory.PRODUCTIVITY,
                    severity=RiskSeverity.MEDIUM,
                    title=f"发表空缼期较长（{gap_months}个月）",
                    detail=f"空缼期：{gap_start}年至{gap_end}年",
                    implication="较长时间无论文发表，应了解背景情况。",
                    mitigation=[
                        "面试时询问空缼原因",
                        "验证产出已恢复",
                    ],
                    red_flag=False
                ))
        
        # Risk 3: Declining productivity trend
        if len(pub_years) >= 6:
            early_pubs = [y for y in pub_years if y <= pub_years[len(pub_years)//2]]
            recent_pubs = [y for y in pub_years if y > pub_years[len(pub_years)//2]]
            
            early_rate = len(early_pubs) / (max(early_pubs) - min(early_pubs) + 1) if early_pubs else 0
            recent_rate = len(recent_pubs) / (max(recent_pubs) - min(recent_pubs) + 1) if recent_pubs else 0
            
            if recent_rate < early_rate * 0.6:  # More than 40% decline
                risks.append(Risk(
                    category=RiskCategory.PRODUCTIVITY,
                    severity=RiskSeverity.MEDIUM,
                    title="产出量下降趋势",
                    detail=f"近期产出 ({recent_rate:.1f}篇/年) 比早期 ({early_rate:.1f}篇/年) 低{(1 - recent_rate/early_rate)*100:.0f}%。",
                    implication="产出可能不可持续，可能表明职业倦怠或优先级转移。",
                    mitigation=[
                        "讨论研究计划和产出目标",
                        "了解下降原因",
                        "检查在研项目渠道",
                    ],
                    red_flag=False
                ))
        
        return risks
    
    def assess_academic_integrity(self, data: Dict[str, Any]) -> List[Risk]:
        """
        Screen for potential academic integrity issues
        
        Key indicators:
        - Suspiciously high productivity
        - Self-citation patterns
        - Predatory journals (if detectable)
        """
        risks = []
        publications = data.get("publications", [])
        
        if not publications:
            return risks
        
        # Calculate career span
        education = data.get("education", [])
        phd_year = None
        for edu in education:
            if "PhD" in edu.get("degree", "") or "博士" in edu.get("degree", ""):
                year_str = edu.get("end_date", "") or edu.get("year", "")
                match = re.search(r"(19|20)\d{2}", str(year_str))
                if match:
                    phd_year = int(match.group(0))
                    break
        
        if not phd_year:
            return risks
        
        career_years = self.current_year - phd_year
        if career_years <= 0:
            return risks
        
        # Risk 1: Suspiciously high productivity
        total_pubs = len(publications)
        pubs_per_year = total_pubs / career_years
        
        if pubs_per_year > 8:
            risks.append(Risk(
                category=RiskCategory.INTEGRITY,
                severity=RiskSeverity.MEDIUM,
                title=f"发表率异常高（{pubs_per_year:.1f}篇/年）",
                detail=f"{career_years}年内发表{total_pubs}篇论文",
                implication="可能需要验证作者贡献，检查是否存在掠夺性期刊或贡献微乎其微。",
                mitigation=[
                    "⚠️ 推荐人验证时重点检查前5篇论文",
                    "要求提供详细的贡献声明",
                    "检查所有论文的期刊质量",
                ],
                red_flag=False
            ))
        
        # Risk 2: Self-citations (if data available)
        scholar_metrics = data.get("scholar_metrics", {})
        if "self_citation_rate" in scholar_metrics:
            self_cite_rate = scholar_metrics["self_citation_rate"]
            if self_cite_rate > 0.3:
                risks.append(Risk(
                    category=RiskCategory.INTEGRITY,
                    severity=RiskSeverity.MEDIUM,
                    title=f"自引率较高（{self_cite_rate:.1%}）",
                    detail="超过30%的引用为自引",
                    implication="可能表明引用膨胀或研究影响力狭窄。",
                    mitigation=[
                        "人工审查关键论文的引用质量",
                        "验证工作的外部认可度",
                    ],
                    red_flag=False
                ))
        
        return risks
    
    def assess_collaboration(self, data: Dict[str, Any]) -> List[Risk]:
        """
        Assess collaboration health and patterns
        
        Key indicators:
        - Co-author network size
        - International collaborations
        - Industry partnerships
        """
        risks = []
        
        # Check network graph data
        network = data.get("network_graph", {})
        if network:
            degree = network.get("degree", 0)
            
            if degree < 5:
                risks.append(Risk(
                    category=RiskCategory.COLLABORATION,
                    severity=RiskSeverity.LOW,
                    title=f"合作网络有限（度为{degree}）",
                    detail=f"仅识别出{degree}位直接合作者",
                    implication="可能难以建立研究合作，可能限制跨学科机会。",
                    mitigation=[
                        "讨论合作策略和计划",
                        "验证团队工作能力",
                    ],
                    red_flag=False
                ))
        
        return risks
    
    def assess_field_relevance(self, data: Dict[str, Any]) -> List[Risk]:
        """
        Assess field relevance and currency
        
        Key indicators:
        - Research topic alignment
        - Field evolution awareness
        """
        risks = []
        
        # This is a placeholder - would need more sophisticated analysis
        # based on job requirements and field trends
        
        return risks
    
    def assess_teaching_ability(self, data: Dict[str, Any]) -> List[Risk]:
        """
        Assess teaching potential
        
        Key indicators:
        - Teaching experience
        - Mentorship record
        - Communication skills
        """
        risks = []
        
        # Check teaching experience
        teaching_exp = data.get("teaching_experience", [])
        
        if not teaching_exp:
            risks.append(Risk(
                category=RiskCategory.TEACHING,
                severity=RiskSeverity.MEDIUM,
                title="无教学经验记录",
                detail="简历中未列出任何教学职位或经验",
                implication="对于终身教职岗位，教学能力至关重要但未经验证。",
                mitigation=[
                    "要求提供教学陈述和理念",
                    "如有可能，要求提供教学评估",
                    "考虑在面试时安排教学演示",
                ],
                red_flag=False
            ))
        
        # Check mentorship
        # (Would need to extract mentorship data if available)
        
        return risks
    
    def _is_first_author(self, authors: List[str], candidate_name: str) -> bool:
        """Check if candidate is first author"""
        if not authors or not candidate_name:
            return False
        return self._normalize_name(authors[0]) == self._normalize_name(candidate_name)
    
    def _is_corresponding_author(self, pub: Dict[str, Any], candidate_name: str) -> bool:
        """Check if candidate is corresponding author"""
        # This would need more sophisticated detection
        # For now, check if explicitly marked
        corresponding = pub.get("corresponding_author", "")
        if corresponding:
            return self._normalize_name(corresponding) == self._normalize_name(candidate_name)
        return False
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name for comparison"""
        return re.sub(r'\s+', ' ', name.strip().lower())
    
    def _calculate_overall_risk(self, risks: List[Risk]) -> str:
        """Calculate overall risk level"""
        if any(r.severity == RiskSeverity.CRITICAL for r in risks):
            return "CRITICAL"
        
        high_count = len([r for r in risks if r.severity == RiskSeverity.HIGH])
        medium_count = len([r for r in risks if r.severity == RiskSeverity.MEDIUM])
        
        if high_count >= 3:
            return "HIGH"
        elif high_count >= 1 or medium_count >= 4:
            return "MEDIUM"
        elif medium_count >= 1:
            return "LOW"
        else:
            return "MINIMAL"
    
    def _generate_recommendation(self, risks: List[Risk], overall_risk: str) -> Dict[str, Any]:
        """Generate hiring recommendation based on risks"""
        red_flag_count = len([r for r in risks if r.red_flag])
        
        if overall_risk == "CRITICAL":
            return {
                "level": "不建议继续",
                "summary": "识别出严重风险，在问题解决前不建议录用。",
                "next_steps": [
                    "在继续之前处理严重风险",
                    "考虑其他候选人",
                ],
            }
        elif overall_risk == "HIGH" or red_flag_count >= 2:
            return {
                "level": "谨慎继续",
                "summary": f"识别出{len([r for r in risks if r.severity == RiskSeverity.HIGH])}个高风险和{red_flag_count}个红旗信号，建议进行额外尽职调查。",
                "next_steps": [
                    "进行全面的推荐人检查，重点关注已识别的风险",
                    "要求提供详细的研究陈述，概述独立研究议程",
                    "在面试时针对风险领域提出具体问题",
                    "考虑要求提供在研论文",
                ],
            }
        elif overall_risk == "MEDIUM":
            return {
                "level": "可接受（需验证）",
                "summary": "识别出一些关注点，但经过额外验证后可接受。",
                "next_steps": [
                    "进行常规推荐人检查，特别关注所指出的关注点",
                    "面试应解决已识别的风险领域",
                ],
            }
        else:
            return {
                "level": "低风险 - 可继续",
                "summary": "未识别出显著风险，候选人似乎合适。",
                "next_steps": [
                    "常规评估流程",
                    "正常推荐人检查",
                ],
            }


# Convenience function
def assess_candidate_risks(resume_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Quick risk assessment function
    
    Args:
        resume_data: Complete resume JSON
        
    Returns:
        Risk assessment report
    """
    assessor = RiskAssessor()
    return assessor.assess_all_risks(resume_data)
