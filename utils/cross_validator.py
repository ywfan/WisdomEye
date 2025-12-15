"""
Academic-Social Cross-Validation Module
学术-社交信号交叉验证模块

Cross-validates academic evaluation claims with social media presence signals
to detect inconsistencies and enhance credibility.
交叉验证学术评价观点与社交媒体信号，检测矛盾并增强可信度。

Key features:
- Extract claims from academic evaluations
- Extract signals from social media analysis
- Calculate claim-signal relevance
- Detect inconsistencies and contradictions
- Generate validation report with consistency score
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import re


@dataclass
class AcademicClaim:
    """Claim from academic evaluation"""
    text: str
    dimension: str
    claim_type: str  # "strength", "achievement", "capability", etc.
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "dimension": self.dimension,
            "claim_type": self.claim_type,
        }


@dataclass
class SocialSignal:
    """Signal from social media presence"""
    text: str
    source: str  # "linkedin", "github", "twitter", "知乎", etc.
    signal_type: str  # "activity", "engagement", "content", "network", etc.
    strength: float  # 0-1, how strong the signal is
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "source": self.source,
            "signal_type": self.signal_type,
            "strength": round(self.strength, 2),
        }


@dataclass
class ValidationResult:
    """Result of cross-validation for a claim"""
    claim: AcademicClaim
    supporting_signals: List[SocialSignal]
    contradicting_signals: List[SocialSignal]
    validation_status: str  # "confirmed", "mixed", "contradicted", "unverified"
    confidence: float  # 0-1, confidence in the claim
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim.to_dict(),
            "supporting_signals": [s.to_dict() for s in self.supporting_signals],
            "contradicting_signals": [s.to_dict() for s in self.contradicting_signals],
            "validation_status": self.validation_status,
            "confidence": round(self.confidence, 2),
        }


class CrossValidator:
    """
    Cross-validate academic evaluations with social media signals
    """
    
    def __init__(self):
        """Initialize cross-validator"""
        pass
    
    def cross_validate(
        self,
        academic_evaluation: Dict[str, Any],
        social_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform comprehensive cross-validation
        
        Args:
            academic_evaluation: Multi-dimension evaluation
            social_analysis: Social influence analysis
            
        Returns:
            Cross-validation report with consistency score and inconsistencies
        """
        # Extract claims from academic evaluation
        academic_claims = self._extract_academic_claims(academic_evaluation)
        
        # Extract signals from social analysis
        social_signals = self._extract_social_signals(social_analysis)
        
        # Cross-validate each claim
        validation_results = []
        for claim in academic_claims:
            result = self._validate_claim(claim, social_signals)
            validation_results.append(result)
        
        # Identify inconsistencies
        inconsistencies = [r for r in validation_results if r.validation_status in ["contradicted", "mixed"]]
        
        # Calculate consistency score
        consistency_score = self._calculate_consistency_score(validation_results)
        
        report = {
            "validation_results": [r.to_dict() for r in validation_results],
            "inconsistencies": [i.to_dict() for i in inconsistencies],
            "consistency_score": round(consistency_score, 2),
            "summary": self._generate_summary(validation_results, inconsistencies, consistency_score),
        }
        
        return report
    
    def _extract_academic_claims(self, evaluation: Dict[str, Any]) -> List[AcademicClaim]:
        """Extract claims from academic evaluation"""
        claims = []
        
        for dimension, content in evaluation.items():
            if isinstance(content, dict):
                evaluation_text = content.get("evaluation", "")
            else:
                evaluation_text = str(content)
            
            # Extract sentences as claims
            sentences = re.split(r'[。！？；]', evaluation_text)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 10:
                    continue
                
                # Classify claim type
                claim_type = "general"
                if any(kw in sentence for kw in ["强", "优秀", "杰出", "领先", "突出"]):
                    claim_type = "strength"
                elif any(kw in sentence for kw in ["贡献", "成果", "发表", "开发"]):
                    claim_type = "achievement"
                elif any(kw in sentence for kw in ["能力", "擅长", "掌握"]):
                    claim_type = "capability"
                elif any(kw in sentence for kw in ["影响", "知名", "广泛"]):
                    claim_type = "impact"
                
                claim = AcademicClaim(
                    text=sentence,
                    dimension=dimension,
                    claim_type=claim_type
                )
                claims.append(claim)
        
        return claims
    
    def _extract_social_signals(self, social_analysis: Dict[str, Any]) -> List[SocialSignal]:
        """Extract signals from social media analysis"""
        signals = []
        
        # Extract from social_presence
        presence = social_analysis.get("social_presence", [])
        for item in presence:
            platform = item.get("platform", "unknown")
            
            # Follower/connection signal
            followers = item.get("followers", 0)
            if followers > 0:
                strength = min(1.0, followers / 1000)  # Normalize
                signal = SocialSignal(
                    text=f"{platform}: {followers} followers/connections",
                    source=platform,
                    signal_type="network",
                    strength=strength
                )
                signals.append(signal)
            
            # Activity frequency signal
            freq = item.get("frequency", "")
            if freq and "活跃" in freq:
                signal = SocialSignal(
                    text=f"{platform}: Active posting ({freq})",
                    source=platform,
                    signal_type="activity",
                    strength=0.7
                )
                signals.append(signal)
            elif freq and "低" in freq:
                signal = SocialSignal(
                    text=f"{platform}: Low activity ({freq})",
                    source=platform,
                    signal_type="activity",
                    strength=0.2
                )
                signals.append(signal)
            
            # Topics signal
            topics = item.get("topics", [])
            for topic in topics[:5]:  # Top 5 topics
                signal = SocialSignal(
                    text=f"{platform}: Discusses '{topic}'",
                    source=platform,
                    signal_type="content",
                    strength=0.6
                )
                signals.append(signal)
        
        # Extract from social_influence summary
        summary = social_analysis.get("summary", "")
        if summary:
            # Check for industry mentions
            if any(kw in summary for kw in ["产业", "industry", "企业", "公司"]):
                signal = SocialSignal(
                    text="Social presence indicates industry connections",
                    source="综合分析",
                    signal_type="content",
                    strength=0.7
                )
                signals.append(signal)
            
            # Check for academic focus
            if any(kw in summary for kw in ["学术", "研究", "academic", "research"]):
                signal = SocialSignal(
                    text="Social presence reflects academic focus",
                    source="综合分析",
                    signal_type="content",
                    strength=0.8
                )
                signals.append(signal)
        
        # Extract from persona_profile
        persona = social_analysis.get("persona_profile", {})
        if persona:
            # Professional identity
            identity = persona.get("professional_identity", {}).get("primary_role", "")
            if identity:
                signal = SocialSignal(
                    text=f"Professional identity: {identity}",
                    source="persona",
                    signal_type="identity",
                    strength=0.9
                )
                signals.append(signal)
            
            # Community standing
            standing = persona.get("community_standing", {})
            recognition = standing.get("recognition_level", "")
            if "high" in recognition.lower() or "strong" in recognition.lower():
                signal = SocialSignal(
                    text="High community recognition",
                    source="persona",
                    signal_type="impact",
                    strength=0.8
                )
                signals.append(signal)
            elif "low" in recognition.lower() or "limited" in recognition.lower():
                signal = SocialSignal(
                    text="Limited community recognition",
                    source="persona",
                    signal_type="impact",
                    strength=0.3
                )
                signals.append(signal)
        
        # Extract from metrics
        metrics = social_analysis.get("metrics", {})
        if metrics:
            total_engagement = metrics.get("total_engagement", 0)
            if total_engagement > 1000:
                signal = SocialSignal(
                    text=f"High social engagement ({total_engagement} total interactions)",
                    source="metrics",
                    signal_type="engagement",
                    strength=0.8
                )
                signals.append(signal)
            elif total_engagement < 100:
                signal = SocialSignal(
                    text=f"Low social engagement ({total_engagement} total interactions)",
                    source="metrics",
                    signal_type="engagement",
                    strength=0.2
                )
                signals.append(signal)
        
        return signals
    
    def _validate_claim(
        self,
        claim: AcademicClaim,
        signals: List[SocialSignal]
    ) -> ValidationResult:
        """
        Validate a single claim against social signals
        
        Returns:
            ValidationResult with supporting/contradicting signals
        """
        supporting_signals = []
        contradicting_signals = []
        
        # Check each signal
        for signal in signals:
            relevance, supports = self._calculate_claim_signal_relevance(claim, signal)
            
            if relevance > 0.5:
                if supports:
                    supporting_signals.append(signal)
                else:
                    contradicting_signals.append(signal)
        
        # Determine validation status
        if len(supporting_signals) > 0 and len(contradicting_signals) == 0:
            validation_status = "confirmed"
            confidence = 0.8 + (len(supporting_signals) * 0.05)  # Bonus for multiple signals
        elif len(contradicting_signals) > 0 and len(supporting_signals) == 0:
            validation_status = "contradicted"
            confidence = 0.2
        elif len(supporting_signals) > 0 and len(contradicting_signals) > 0:
            validation_status = "mixed"
            confidence = 0.5
        else:
            validation_status = "unverified"
            confidence = 0.5  # Neutral when no relevant signals
        
        confidence = min(1.0, confidence)
        
        return ValidationResult(
            claim=claim,
            supporting_signals=supporting_signals[:3],  # Top 3
            contradicting_signals=contradicting_signals[:3],
            validation_status=validation_status,
            confidence=confidence
        )
    
    def _calculate_claim_signal_relevance(
        self,
        claim: AcademicClaim,
        signal: SocialSignal
    ) -> Tuple[float, bool]:
        """
        Calculate relevance between claim and signal
        
        Returns:
            (relevance_score, supports_claim)
        """
        claim_lower = claim.text.lower()
        signal_lower = signal.text.lower()
        
        # Extract keywords
        claim_keywords = set(re.findall(r'\w+', claim_lower))
        signal_keywords = set(re.findall(r'\w+', signal_lower))
        
        # Remove common words
        stop_words = {'的', '和', '是', '在', '有', '与', '了', '为', 'the', 'and', 'is', 'in', 'of', 'to', 'a'}
        claim_keywords -= stop_words
        signal_keywords -= stop_words
        
        # Calculate overlap
        if not claim_keywords or not signal_keywords:
            return 0.0, True
        
        overlap = claim_keywords & signal_keywords
        relevance = len(overlap) / len(claim_keywords)
        
        # Determine if signal supports or contradicts claim
        supports = True
        
        # Check for contradictory patterns
        if claim.claim_type == "impact":
            # If claim is about impact/influence
            if "高" in claim_lower or "强" in claim_lower or "广泛" in claim_lower:
                # Positive impact claim
                if signal.signal_type == "engagement" and signal.strength < 0.3:
                    supports = False  # Low engagement contradicts high impact claim
                elif "low" in signal_lower or "limited" in signal_lower or "低" in signal_lower:
                    supports = False
        
        if claim.claim_type == "strength" and "行业" in claim_lower:
            # Industry-related strength claim
            if "academic" in signal_lower or "学术" in signal_lower:
                # Academic focus in social might contradict industry claim
                if relevance > 0.3:
                    supports = False
        
        # Enhance relevance if highly relevant
        if relevance > 0.3:
            relevance = min(1.0, relevance * 1.5)
        
        return relevance, supports
    
    def _calculate_consistency_score(self, validation_results: List[ValidationResult]) -> float:
        """
        Calculate overall consistency score
        
        Score = (confirmed + 0.5*unverified) / total
        """
        if not validation_results:
            return 0.5
        
        confirmed = len([r for r in validation_results if r.validation_status == "confirmed"])
        unverified = len([r for r in validation_results if r.validation_status == "unverified"])
        
        score = (confirmed + 0.5 * unverified) / len(validation_results)
        
        return score
    
    def _generate_summary(
        self,
        validation_results: List[ValidationResult],
        inconsistencies: List[ValidationResult],
        consistency_score: float
    ) -> str:
        """Generate natural language summary"""
        total = len(validation_results)
        confirmed = len([r for r in validation_results if r.validation_status == "confirmed"])
        contradicted = len([r for r in validation_results if r.validation_status == "contradicted"])
        
        summary = f"交叉验证了 {total} 个学术评价观点。"
        summary += f"其中 {confirmed} 个得到社交信号证实，"
        summary += f"{len(inconsistencies)} 个存在矛盾或混合信号。"
        summary += f"\n\n一致性得分: {consistency_score:.1%}"
        
        if consistency_score >= 0.75:
            summary += " - **高度一致**，学术评价与社交表现相互印证。"
        elif consistency_score >= 0.5:
            summary += " - **基本一致**，大部分评价有社交信号支持。"
        else:
            summary += " - **存在较多矛盾**，需要进一步核实。"
        
        if contradicted > 0:
            summary += f"\n\n⚠️ 发现 {contradicted} 个明显矛盾，建议在面试中重点询问。"
        
        return summary


# Convenience function
def cross_validate_evaluation(
    academic_evaluation: Dict[str, Any],
    social_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Quick cross-validation function
    
    Args:
        academic_evaluation: Multi-dimension evaluation
        social_analysis: Social influence analysis
        
    Returns:
        Cross-validation report
    """
    validator = CrossValidator()
    return validator.cross_validate(academic_evaluation, social_analysis)
