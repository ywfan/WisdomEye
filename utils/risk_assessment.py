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
    """Risk severity levels"""
    CRITICAL = "CRITICAL"  # Deal-breaker, requires immediate attention
    HIGH = "HIGH"  # Serious concern, must investigate
    MEDIUM = "MEDIUM"  # Notable concern, should verify
    LOW = "LOW"  # Minor concern, awareness needed


class RiskCategory(Enum):
    """Risk categories"""
    INDEPENDENCE = "Research Independence"
    PRODUCTIVITY = "Productivity"
    INTEGRITY = "Academic Integrity"
    COLLABORATION = "Collaboration"
    RELEVANCE = "Field Relevance"
    TEACHING = "Teaching Ability"


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
    
    def __init__(self, current_year: int = 2025):
        """
        Initialize risk assessor
        
        Args:
            current_year: Current year for calculations
        """
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
                title=f"Low first-author publication rate ({first_author_rate:.1%})",
                detail=f"Only {first_author_count} out of {total_pubs} publications are first-author.",
                implication="May indicate heavy reliance on advisor/collaborators. "
                           "Uncertain ability to lead independent research program.",
                mitigation=[
                    "Request detailed statement on independent research plans",
                    "Interview should probe candidate's ability to formulate original research questions",
                    "Contact references specifically about independence",
                ],
                red_flag=True
            ))
        elif first_author_rate < 0.5:
            risks.append(Risk(
                category=RiskCategory.INDEPENDENCE,
                severity=RiskSeverity.MEDIUM,
                title=f"Moderate first-author rate ({first_author_rate:.1%})",
                detail=f"{first_author_count} out of {total_pubs} publications are first-author.",
                implication="Candidate has some independent work but significant collaborative publications. "
                           "Should verify leadership capability.",
                mitigation=[
                    "Request examples of independently-led projects",
                    "Verify research leadership during reference checks",
                ],
                red_flag=False
            ))
        
        # Risk 2: No corresponding authorship
        if corresponding_count == 0 and total_pubs > 3:
            risks.append(Risk(
                category=RiskCategory.INDEPENDENCE,
                severity=RiskSeverity.MEDIUM,
                title="No corresponding-author publications",
                detail="Candidate has never been corresponding author on any publication.",
                implication="May not have led full research projects from conception to publication. "
                           "Leadership experience unclear.",
                mitigation=[
                    "Verify research leadership during reference checks",
                    "Request examples of project leadership",
                ],
                red_flag=False
            ))
        
        # Risk 3: Limited co-author diversity
        if len(coauthors) < 5 and total_pubs > 10:
            risks.append(Risk(
                category=RiskCategory.INDEPENDENCE,
                severity=RiskSeverity.MEDIUM,
                title=f"Limited co-author diversity (only {len(coauthors)} unique co-authors)",
                detail=f"Only {len(coauthors)} unique co-authors across {total_pubs} publications.",
                implication="May be overly dependent on a small research group. "
                           "Limited network or collaboration skills.",
                mitigation=[
                    "Discuss collaboration strategy during interview",
                    "Verify ability to build new collaborations",
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
                title=f"Low recent publication rate ({recent_pub_rate:.1f} pubs/year)",
                detail=f"Only {len(recent_pubs)} publications in last 2 years.",
                implication="May struggle to meet tenure publication requirements "
                           "(typical expectation: 2-3 quality pubs/year).",
                mitigation=[
                    "Inquire about work in progress",
                    "Check for papers under review",
                    "Understand reasons for productivity gap",
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
                    title=f"Extended publication gap ({gap_months} months)",
                    detail=f"Gap from {gap_start} to {gap_end}",
                    implication="Significant research hiatus. Possible career disruption or "
                               "productivity issue.",
                    mitigation=[
                        "⚠️ MUST investigate reasons during interview",
                        "Could indicate personal issues, failed projects, or lack of focus",
                        "Request information on work-in-progress during gap period",
                    ],
                    red_flag=True
                ))
            elif gap_months > 18:
                risks.append(Risk(
                    category=RiskCategory.PRODUCTIVITY,
                    severity=RiskSeverity.MEDIUM,
                    title=f"Notable publication gap ({gap_months} months)",
                    detail=f"Gap from {gap_start} to {gap_end}",
                    implication="Extended period without publications. Should understand context.",
                    mitigation=[
                        "Ask about reasons for gap during interview",
                        "Verify productivity has resumed",
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
                    title="Declining productivity trend",
                    detail=f"Recent productivity ({recent_rate:.1f} pubs/year) is {(1 - recent_rate/early_rate)*100:.0f}% "
                           f"lower than early career ({early_rate:.1f} pubs/year).",
                    implication="Productivity may not be sustainable. Could indicate burnout or shifting priorities.",
                    mitigation=[
                        "Discuss research plans and productivity goals",
                        "Understand reasons for decline",
                        "Check work-in-progress pipeline",
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
                title=f"Unusually high publication rate ({pubs_per_year:.1f} pubs/year)",
                detail=f"{total_pubs} publications over {career_years} years",
                implication="May warrant verification of author contributions. "
                           "Check for predatory journals or minimal contributions.",
                mitigation=[
                    "⚠️ Verify top 5 publications during reference checks",
                    "Request detailed contribution statements",
                    "Check journal quality for all publications",
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
                    title=f"High self-citation rate ({self_cite_rate:.1%})",
                    detail="Over 30% of citations are self-citations",
                    implication="May indicate citation inflation or narrow research impact.",
                    mitigation=[
                        "Manually review key papers for citation quality",
                        "Verify external recognition of work",
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
                    title=f"Limited collaboration network (degree {degree})",
                    detail=f"Only {degree} direct collaborators identified",
                    implication="May have difficulty building research collaborations. "
                               "Could limit interdisciplinary opportunities.",
                    mitigation=[
                        "Discuss collaboration strategy and plans",
                        "Verify ability to work in team settings",
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
                title="No documented teaching experience",
                detail="Resume does not list any teaching positions or experience",
                implication="For tenure-track positions, teaching ability is critical but unverified.",
                mitigation=[
                    "Request teaching statement and philosophy",
                    "Ask for teaching evaluations if available",
                    "Consider teaching demonstration during interview",
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
                "level": "DO NOT PROCEED",
                "summary": "Critical risks identified. Not recommended for hire without resolution.",
                "next_steps": [
                    "Address critical risks before proceeding",
                    "Consider alternative candidates",
                ],
            }
        elif overall_risk == "HIGH" or red_flag_count >= 2:
            return {
                "level": "PROCEED WITH CAUTION",
                "summary": f"{len([r for r in risks if r.severity == RiskSeverity.HIGH])} high-severity risks "
                          f"and {red_flag_count} red flags identified. Recommend additional due diligence.",
                "next_steps": [
                    "Conduct thorough reference checks focusing on identified risks",
                    "Request detailed research statement outlining independent agenda",
                    "During interview, probe specific questions about risk areas",
                    "Consider requesting work-in-progress papers",
                ],
            }
        elif overall_risk == "MEDIUM":
            return {
                "level": "ACCEPTABLE WITH VERIFICATION",
                "summary": "Some concerns identified, but acceptable with additional verification.",
                "next_steps": [
                    "Standard reference checks with attention to noted concerns",
                    "Interview should address identified risk areas",
                ],
            }
        else:
            return {
                "level": "LOW RISK - PROCEED",
                "summary": "No significant risks identified. Candidate appears suitable.",
                "next_steps": [
                    "Standard evaluation process",
                    "Normal reference checks",
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
