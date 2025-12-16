"""
Authorship Pattern Analysis Module
作者贡献模式分析模块

Analyzes authorship patterns to assess research independence and collaboration health.
分析作者模式以评估研究独立性和合作健康度。

Key analyses:
- First-author publication rate
- Corresponding author count
- Co-author diversity and network
- Collaboration patterns over time
- Independence score calculation
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import re
from collections import Counter
try:
    from pypinyin import lazy_pinyin, Style
    PYPINYIN_AVAILABLE = True
except ImportError:
    PYPINYIN_AVAILABLE = False


@dataclass
class AuthorshipMetrics:
    """Authorship pattern metrics"""
    total_publications: int
    first_author_count: int
    first_author_rate: float
    corresponding_author_count: int
    corresponding_author_rate: float
    
    # Co-author analysis
    unique_coauthors: int
    total_coauthor_instances: int
    avg_coauthors_per_paper: float
    top_collaborators: List[Tuple[str, int]]  # (name, count)
    
    # Solo vs collaborative
    solo_author_count: int
    solo_author_rate: float
    
    # Position analysis
    middle_author_count: int
    middle_author_rate: float
    last_author_count: int
    last_author_rate: float
    
    # Independence score (0-1, higher = more independent)
    independence_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_publications": self.total_publications,
            "first_author": {
                "count": self.first_author_count,
                "rate": round(self.first_author_rate, 3),
            },
            "corresponding_author": {
                "count": self.corresponding_author_count,
                "rate": round(self.corresponding_author_rate, 3),
            },
            "coauthor_analysis": {
                "unique_coauthors": self.unique_coauthors,
                "total_instances": self.total_coauthor_instances,
                "avg_per_paper": round(self.avg_coauthors_per_paper, 2),
                "top_collaborators": [
                    {"name": name, "papers": count}
                    for name, count in self.top_collaborators[:10]
                ],
            },
            "solo_author": {
                "count": self.solo_author_count,
                "rate": round(self.solo_author_rate, 3),
            },
            "position_distribution": {
                "first": round(self.first_author_rate, 3),
                "middle": round(self.middle_author_rate, 3),
                "last": round(self.last_author_rate, 3),
                "solo": round(self.solo_author_rate, 3),
            },
            "independence_score": round(self.independence_score, 3),
        }


class AuthorshipAnalyzer:
    """
    Analyze authorship patterns for research independence assessment
    """
    
    def __init__(self, candidate_name: str, english_name: Optional[str] = None):
        """
        Initialize analyzer
        
        Args:
            candidate_name: Full name of the candidate (Chinese or English)
            english_name: Optional English name if candidate_name is Chinese
        """
        self.candidate_name = candidate_name
        self.normalized_candidate_name = self._normalize_name(candidate_name)
        self.english_name = english_name
        
        # Generate name variants for better matching
        self.name_variants = self._generate_name_variants(candidate_name, english_name)
        
        # Debug logging: show name variants being used
        print(f"[姓名变体生成] 候选人: {candidate_name}")
        if english_name:
            print(f"[姓名变体生成] 提供的英文名: {english_name}")
        print(f"[姓名变体生成] 生成 {len(self.name_variants)} 个姓名变体用于匹配:")
        for i, variant in enumerate(self.name_variants, 1):
            print(f"  {i}. '{variant}'")
    
    def analyze_publications(
        self,
        publications: List[Dict[str, Any]]
    ) -> AuthorshipMetrics:
        """
        Comprehensive authorship analysis
        
        Args:
            publications: List of publication records
            
        Returns:
            AuthorshipMetrics with detailed analysis
        """
        if not publications:
            return self._empty_metrics()
        
        # Initialize counters
        total_pubs = len(publications)
        first_author_count = 0
        corresponding_count = 0
        solo_count = 0
        middle_count = 0
        last_count = 0
        
        coauthor_counter = Counter()
        total_coauthor_instances = 0
        total_authors_sum = 0
        
        # Analyze each publication
        matched_pubs = 0
        unmatched_pubs = 0
        for pub in publications:
            authors = pub.get("authors", [])
            if not authors or not isinstance(authors, list):
                continue
            
            # Normalize author names
            normalized_authors = [self._normalize_name(a) for a in authors if isinstance(a, str)]
            if not normalized_authors:
                continue
            
            num_authors = len(normalized_authors)
            total_authors_sum += num_authors
            
            # Check candidate position
            match_result = self._find_candidate_index(normalized_authors)
            
            if match_result is None:
                unmatched_pubs += 1
                # Debug: print first few unmatched cases
                if unmatched_pubs <= 3:
                    pub_title = pub.get("title", "Unknown")[:60]
                    print(f"[作者匹配-警告] 未在论文中找到候选人: '{pub_title}...'")
                    print(f"  候选人姓名变体: {self.name_variants}")
                    print(f"  论文作者列表: {normalized_authors[:5]}")
                continue  # Candidate not in author list
            
            candidate_idx, matched_variant = match_result
            matched_pubs += 1
            
            # Debug: Show successful match for first few publications
            if matched_pubs <= 3:
                pub_title = pub.get("title", "Unknown")[:60]
                print(f"[作者匹配-成功] 找到候选人在论文中: '{pub_title}...'")
                print(f"  匹配的变体: '{matched_variant}' <-> 作者: '{normalized_authors[candidate_idx]}' (位置: {candidate_idx+1}/{len(normalized_authors)})")
            
            # Position analysis
            if num_authors == 1:
                solo_count += 1
                first_author_count += 1  # Solo is also first
            elif candidate_idx == 0:
                first_author_count += 1
            elif candidate_idx == num_authors - 1:
                last_count += 1
            else:
                middle_count += 1
            
            # Check corresponding author
            if self._is_corresponding_author(pub, normalized_authors, candidate_idx):
                corresponding_count += 1
            
            # Co-author analysis (exclude candidate)
            for i, author in enumerate(normalized_authors):
                if i != candidate_idx:
                    original_name = authors[i]
                    coauthor_counter[original_name] += 1
                    total_coauthor_instances += 1
        
        # Calculate rates
        first_author_rate = first_author_count / total_pubs if total_pubs > 0 else 0
        corresponding_rate = corresponding_count / total_pubs if total_pubs > 0 else 0
        solo_rate = solo_count / total_pubs if total_pubs > 0 else 0
        middle_rate = middle_count / total_pubs if total_pubs > 0 else 0
        last_rate = last_count / total_pubs if total_pubs > 0 else 0
        
        # Co-author metrics
        unique_coauthors = len(coauthor_counter)
        avg_coauthors = total_coauthor_instances / total_pubs if total_pubs > 0 else 0
        top_collaborators = coauthor_counter.most_common(10)
        
        # Calculate independence score
        independence_score = self._calculate_independence_score(
            first_author_rate=first_author_rate,
            corresponding_rate=corresponding_rate,
            solo_rate=solo_rate,
            coauthor_diversity=unique_coauthors,
            total_pubs=total_pubs,
        )
        
        # Log analysis summary
        print(f"[作者贡献分析-统计] 总论文: {total_pubs}, 匹配: {matched_pubs}, 未匹配: {unmatched_pubs}")
        print(f"  第一作者: {first_author_count}/{total_pubs} ({first_author_rate:.1%})")
        print(f"  独立性得分: {independence_score:.3f}")
        
        return AuthorshipMetrics(
            total_publications=total_pubs,
            first_author_count=first_author_count,
            first_author_rate=first_author_rate,
            corresponding_author_count=corresponding_count,
            corresponding_author_rate=corresponding_rate,
            unique_coauthors=unique_coauthors,
            total_coauthor_instances=total_coauthor_instances,
            avg_coauthors_per_paper=avg_coauthors,
            top_collaborators=top_collaborators,
            solo_author_count=solo_count,
            solo_author_rate=solo_rate,
            middle_author_count=middle_count,
            middle_author_rate=middle_rate,
            last_author_count=last_count,
            last_author_rate=last_rate,
            independence_score=independence_score,
        )
    
    def generate_analysis_report(
        self,
        metrics: AuthorshipMetrics
    ) -> Dict[str, Any]:
        """
        Generate natural language analysis report
        
        Args:
            metrics: Authorship metrics
            
        Returns:
            Analysis report with interpretation and recommendations
        """
        report = {
            "metrics": metrics.to_dict(),
            "interpretation": self._interpret_metrics(metrics),
            "strengths": self._identify_strengths(metrics),
            "concerns": self._identify_concerns(metrics),
            "recommendations": self._generate_recommendations(metrics),
        }
        
        return report
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name for comparison"""
        if not name:
            return ""
        # Remove extra spaces, convert to lowercase
        normalized = re.sub(r'\s+', ' ', name.strip().lower())
        # Remove special characters but keep spaces
        normalized = re.sub(r'[^\w\s]', '', normalized)
        return normalized
    
    def _is_chinese(self, text: str) -> bool:
        """Check if text contains Chinese characters"""
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    
    def _chinese_to_pinyin(self, chinese_name: str) -> str:
        """Convert Chinese name to pinyin"""
        if not PYPINYIN_AVAILABLE or not chinese_name:
            return ""
        
        # Get pinyin without tones
        pinyin_parts = lazy_pinyin(chinese_name, style=Style.NORMAL)
        
        # Chinese names typically: 姓 + 名 (1-2 characters each)
        # Convert to Western format: Given Name + Family Name
        if len(pinyin_parts) >= 2:
            # Assume first character is family name, rest is given name
            family_name = pinyin_parts[0]
            given_name = ''.join(pinyin_parts[1:])
            return f"{given_name} {family_name}"
        elif len(pinyin_parts) == 1:
            return pinyin_parts[0]
        
        return ' '.join(pinyin_parts)
    
    def _generate_name_variants(self, name: str, english_name: Optional[str] = None) -> List[str]:
        """
        Generate multiple name variants for matching
        
        Returns list of normalized name variants:
        - Original name
        - English name (if provided)
        - Pinyin conversion (if Chinese)
        - Reversed name order (for Western vs Chinese order)
        """
        variants = [self._normalize_name(name)]
        
        # Add English name if provided
        if english_name:
            variants.append(self._normalize_name(english_name))
        
        # If Chinese name, try to convert to pinyin
        if self._is_chinese(name) and PYPINYIN_AVAILABLE:
            pinyin_name = self._chinese_to_pinyin(name)
            if pinyin_name:
                variants.append(self._normalize_name(pinyin_name))
                # Also add reversed order
                parts = pinyin_name.split()
                if len(parts) == 2:
                    variants.append(self._normalize_name(f"{parts[1]} {parts[0]}"))
        
        # If English name, also try reversed order
        if not self._is_chinese(name):
            parts = name.split()
            if len(parts) >= 2:
                # Try reversing (e.g., "John Smith" -> "Smith John")
                variants.append(self._normalize_name(' '.join(reversed(parts))))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for v in variants:
            if v and v not in seen:
                seen.add(v)
                unique_variants.append(v)
        
        return unique_variants
    
    def _find_candidate_index(self, normalized_authors: List[str]) -> Optional[Tuple[int, str]]:
        """
        Find candidate's index in author list using all name variants
        
        Returns:
            Tuple of (index, matched_variant) if found, None otherwise
        """
        for i, author in enumerate(normalized_authors):
            # Try matching against all name variants
            for variant in self.name_variants:
                if self._names_match(author, variant):
                    return (i, variant)
        return None
    
    def _names_match(self, name1: str, name2: str) -> bool:
        """Check if two normalized names match"""
        if name1 == name2:
            return True
        
        # Check substring match (e.g., "smith" in "john smith")
        if name1 in name2 or name2 in name1:
            # Ensure it's not just a partial word match
            if len(name1) > 3 or len(name2) > 3:
                return True
        
        # Check if one is a substring of the other (handles abbreviations)
        # e.g., "j smith" matches "john smith"
        parts1 = name1.split()
        parts2 = name2.split()
        
        # If same number of parts, check each part
        if len(parts1) == len(parts2):
            matches = sum(1 for p1, p2 in zip(parts1, parts2) if p1 == p2 or (p1 and p2 and p1[0] == p2[0]))
            return matches >= len(parts1) - 1  # Allow one mismatch
        
        # Different number of parts - check if all parts of shorter name are in longer name
        shorter_parts = parts1 if len(parts1) < len(parts2) else parts2
        longer_parts = parts2 if len(parts1) < len(parts2) else parts1
        
        # Check if all parts of shorter name match some parts in longer name
        if shorter_parts and all(
            any(sp == lp or (sp and lp and sp[0] == lp[0]) for lp in longer_parts)
            for sp in shorter_parts
        ):
            return True
        
        return False
    
    def _is_corresponding_author(
        self,
        pub: Dict[str, Any],
        normalized_authors: List[str],
        candidate_idx: int
    ) -> bool:
        """
        Check if candidate is corresponding author
        
        Various indicators:
        - Explicit "corresponding_author" field
        - Email provided by candidate
        - Last author position (common in some fields)
        """
        # Check explicit field
        corresponding = pub.get("corresponding_author", "")
        if corresponding:
            normalized_corresponding = self._normalize_name(corresponding)
            # Check against all name variants
            for variant in self.name_variants:
                if self._names_match(normalized_corresponding, variant):
                    return True
        
        # Heuristic: in some fields, last author is corresponding
        # (But we can't assume this universally, so we don't auto-assign)
        
        return False
    
    def _calculate_independence_score(
        self,
        first_author_rate: float,
        corresponding_rate: float,
        solo_rate: float,
        coauthor_diversity: int,
        total_pubs: int,
    ) -> float:
        """
        Calculate overall research independence score (0-1)
        
        Formula:
        - First-author rate: 40% weight
        - Corresponding author rate: 30% weight
        - Solo author rate: 20% weight
        - Co-author diversity: 10% weight
        
        Higher score = more independent
        """
        # Base components
        first_component = first_author_rate * 0.4
        corresponding_component = corresponding_rate * 0.3
        solo_component = solo_rate * 0.2
        
        # Diversity component (normalized)
        # Expect at least 5 unique co-authors for good diversity
        diversity_component = min(1.0, coauthor_diversity / 5.0) * 0.1
        
        independence_score = (
            first_component +
            corresponding_component +
            solo_component +
            diversity_component
        )
        
        return min(1.0, independence_score)
    
    def _interpret_metrics(self, metrics: AuthorshipMetrics) -> str:
        """Generate natural language interpretation"""
        interpretation = f"Candidate has {metrics.total_publications} publications with "
        
        # First-author analysis
        if metrics.first_author_rate >= 0.5:
            interpretation += f"**strong** first-author presence ({metrics.first_author_rate:.1%}, "
            interpretation += f"{metrics.first_author_count} papers), "
        elif metrics.first_author_rate >= 0.3:
            interpretation += f"**moderate** first-author presence ({metrics.first_author_rate:.1%}, "
            interpretation += f"{metrics.first_author_count} papers), "
        else:
            interpretation += f"**limited** first-author presence ({metrics.first_author_rate:.1%}, "
            interpretation += f"{metrics.first_author_count} papers), "
        
        # Collaboration analysis
        interpretation += f"collaborating with {metrics.unique_coauthors} unique researchers "
        interpretation += f"(avg {metrics.avg_coauthors_per_paper:.1f} co-authors/paper). "
        
        # Independence score interpretation
        if metrics.independence_score >= 0.7:
            interpretation += "Independence score is **high** ({:.1%}), indicating strong ".format(
                metrics.independence_score
            )
            interpretation += "capability for independent research leadership."
        elif metrics.independence_score >= 0.5:
            interpretation += "Independence score is **moderate** ({:.1%}), suggesting ".format(
                metrics.independence_score
            )
            interpretation += "reasonable but not exceptional research independence."
        else:
            interpretation += "Independence score is **low** ({:.1%}), raising concerns ".format(
                metrics.independence_score
            )
            interpretation += "about ability to lead independent research program."
        
        return interpretation
    
    def _identify_strengths(self, metrics: AuthorshipMetrics) -> List[str]:
        """Identify authorship strengths"""
        strengths = []
        
        if metrics.first_author_rate >= 0.5:
            strengths.append(
                f"Strong first-author record ({metrics.first_author_rate:.1%}) demonstrates "
                f"ability to lead research projects"
            )
        
        if metrics.corresponding_author_rate >= 0.3:
            strengths.append(
                f"Substantial corresponding-author publications ({metrics.corresponding_author_count}) "
                f"indicate research leadership"
            )
        
        if metrics.solo_author_count > 0:
            strengths.append(
                f"{metrics.solo_author_count} solo-authored paper(s) show independent research capability"
            )
        
        if metrics.unique_coauthors >= 10:
            strengths.append(
                f"Diverse collaboration network ({metrics.unique_coauthors} unique co-authors) "
                f"indicates strong networking skills"
            )
        
        if metrics.independence_score >= 0.7:
            strengths.append(
                f"High independence score ({metrics.independence_score:.1%}) suggests readiness "
                f"for tenure-track position"
            )
        
        return strengths
    
    def _identify_concerns(self, metrics: AuthorshipMetrics) -> List[str]:
        """Identify authorship concerns"""
        concerns = []
        
        if metrics.first_author_rate < 0.3:
            concerns.append(
                f"Low first-author rate ({metrics.first_author_rate:.1%}) may indicate "
                f"limited research leadership experience"
            )
        
        if metrics.corresponding_author_count == 0:
            concerns.append(
                "No corresponding-author publications raises questions about "
                "independent project management"
            )
        
        if metrics.unique_coauthors < 5 and metrics.total_publications > 10:
            concerns.append(
                f"Limited co-author diversity ({metrics.unique_coauthors} unique collaborators) "
                f"may suggest narrow collaboration network"
            )
        
        if metrics.middle_author_rate > 0.6:
            concerns.append(
                f"High proportion of middle-author publications ({metrics.middle_author_rate:.1%}) "
                f"may indicate secondary role in many projects"
            )
        
        if metrics.independence_score < 0.5:
            concerns.append(
                f"Low independence score ({metrics.independence_score:.1%}) raises concerns "
                f"about readiness for independent research program"
            )
        
        # Check for over-dependence on single collaborator
        if metrics.top_collaborators:
            top_collaborator_count = metrics.top_collaborators[0][1]
            if top_collaborator_count / metrics.total_publications > 0.7:
                concerns.append(
                    f"Heavy dependence on single collaborator "
                    f"({metrics.top_collaborators[0][0]}, {top_collaborator_count} papers)"
                )
        
        return concerns
    
    def _generate_recommendations(self, metrics: AuthorshipMetrics) -> List[str]:
        """Generate hiring recommendations"""
        recommendations = []
        
        if metrics.first_author_rate < 0.3:
            recommendations.append(
                "During interview: Probe candidate's ability to formulate "
                "original research questions independently"
            )
            recommendations.append(
                "Reference checks: Specifically inquire about research independence "
                "and leadership capabilities"
            )
        
        if metrics.corresponding_author_count == 0:
            recommendations.append(
                "Request detailed research statement outlining independent research agenda"
            )
            recommendations.append(
                "Verify: Has candidate led projects from conception to publication?"
            )
        
        if metrics.independence_score < 0.5:
            recommendations.append(
                "⚠️ Consider: Is candidate ready for tenure-track position requiring "
                "independent research program?"
            )
            recommendations.append(
                "Discuss: What is candidate's plan for establishing independent research lab?"
            )
        
        if metrics.unique_coauthors < 5:
            recommendations.append(
                "Assess: Can candidate build new collaborations at this institution?"
            )
        
        if not recommendations:
            recommendations.append(
                "Authorship patterns are strong. Proceed with standard evaluation process."
            )
        
        return recommendations
    
    def _empty_metrics(self) -> AuthorshipMetrics:
        """Return empty metrics when no publications"""
        return AuthorshipMetrics(
            total_publications=0,
            first_author_count=0,
            first_author_rate=0.0,
            corresponding_author_count=0,
            corresponding_author_rate=0.0,
            unique_coauthors=0,
            total_coauthor_instances=0,
            avg_coauthors_per_paper=0.0,
            top_collaborators=[],
            solo_author_count=0,
            solo_author_rate=0.0,
            middle_author_count=0,
            middle_author_rate=0.0,
            last_author_count=0,
            last_author_rate=0.0,
            independence_score=0.0,
        )


# Convenience function
def analyze_authorship(
    candidate_name: str,
    publications: List[Dict[str, Any]],
    english_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Quick authorship analysis
    
    Args:
        candidate_name: Candidate's full name (Chinese or English)
        publications: List of publications
        english_name: Optional English name if candidate_name is Chinese
        
    Returns:
        Comprehensive authorship analysis report
    """
    analyzer = AuthorshipAnalyzer(candidate_name, english_name=english_name)
    metrics = analyzer.analyze_publications(publications)
    report = analyzer.generate_analysis_report(metrics)
    
    return report
