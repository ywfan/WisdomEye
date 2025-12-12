"""
Person Disambiguation Module

This module provides intelligent person disambiguation capabilities to accurately
identify and verify whether online profiles (social media, academic platforms)
belong to the target candidate.

Features:
- Multi-dimensional similarity scoring (name, affiliation, research interests, etc.)
- Configurable confidence thresholds
- Support for multiple verification strategies
- Detailed match explanations

Author: WisdomEye Team
Date: 2025-12-12
"""

from typing import Dict, List, Optional, Tuple
import re
from difflib import SequenceMatcher
from dataclasses import dataclass


@dataclass
class PersonProfile:
    """Represents a person's profile for disambiguation."""
    name: str
    affiliations: List[str] = None
    research_interests: List[str] = None
    education: List[str] = None
    positions: List[str] = None
    coauthors: List[str] = None
    publications: List[str] = None
    email: str = None
    
    def __post_init__(self):
        """Initialize empty lists for None values."""
        self.affiliations = self.affiliations or []
        self.research_interests = self.research_interests or []
        self.education = self.education or []
        self.positions = self.positions or []
        self.coauthors = self.coauthors or []
        self.publications = self.publications or []


@dataclass
class DisambiguationResult:
    """Result of person disambiguation."""
    is_match: bool
    confidence: float
    evidence: Dict[str, float]
    explanation: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "is_match": self.is_match,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "explanation": self.explanation
        }


class PersonDisambiguator:
    """
    Intelligent person disambiguation engine.
    
    Uses multi-dimensional similarity scoring to determine if two profiles
    represent the same person.
    """
    
    # Default weights for different matching dimensions
    DEFAULT_WEIGHTS = {
        "name": 0.25,
        "affiliation": 0.20,
        "research_interests": 0.15,
        "education": 0.15,
        "coauthors": 0.10,
        "publications": 0.10,
        "email": 0.05
    }
    
    # Confidence thresholds
    HIGH_CONFIDENCE = 0.80
    MEDIUM_CONFIDENCE = 0.60
    LOW_CONFIDENCE = 0.40
    
    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        min_confidence: float = MEDIUM_CONFIDENCE
    ):
        """
        Initialize disambiguator.
        
        Args:
            weights: Custom weights for different dimensions
            min_confidence: Minimum confidence threshold for positive match
        """
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.min_confidence = min_confidence
        
    def disambiguate(
        self,
        target: PersonProfile,
        candidate: PersonProfile
    ) -> DisambiguationResult:
        """
        Determine if candidate profile matches target profile.
        
        Args:
            target: The target person profile (from resume)
            candidate: The candidate profile (from online source)
            
        Returns:
            DisambiguationResult with match decision and details
        """
        # Calculate similarity scores for each dimension
        scores = {}
        
        # Name similarity (critical)
        scores["name"] = self._name_similarity(target.name, candidate.name)
        
        # Affiliation similarity
        scores["affiliation"] = self._list_similarity(
            target.affiliations, candidate.affiliations
        )
        
        # Research interests similarity
        scores["research_interests"] = self._list_similarity(
            target.research_interests, candidate.research_interests
        )
        
        # Education similarity
        scores["education"] = self._list_similarity(
            target.education, candidate.education
        )
        
        # Coauthor overlap
        scores["coauthors"] = self._list_similarity(
            target.coauthors, candidate.coauthors
        )
        
        # Publication overlap
        scores["publications"] = self._publication_similarity(
            target.publications, candidate.publications
        )
        
        # Email similarity
        scores["email"] = self._email_similarity(target.email, candidate.email)
        
        # Calculate weighted confidence score
        confidence = self._calculate_confidence(scores)
        
        # Generate explanation
        explanation = self._generate_explanation(scores, confidence)
        
        # Determine if it's a match
        is_match = confidence >= self.min_confidence
        
        return DisambiguationResult(
            is_match=is_match,
            confidence=confidence,
            evidence=scores,
            explanation=explanation
        )
    
    def _name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate name similarity with handling for Chinese/English names.
        
        Args:
            name1: First name
            name2: Second name
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not name1 or not name2:
            return 0.0
        
        # Normalize names
        name1 = self._normalize_name(name1)
        name2 = self._normalize_name(name2)
        
        # Exact match
        if name1 == name2:
            return 1.0
        
        # Check if one is abbreviation of other (e.g., "Zhang W" vs "Wei Zhang")
        if self._is_name_abbreviation(name1, name2):
            return 0.95
        
        # Check reversed order (Chinese vs Western name order)
        parts1 = name1.split()
        parts2 = name2.split()
        if len(parts1) == len(parts2) == 2:
            if parts1[0] == parts2[1] and parts1[1] == parts2[0]:
                return 0.95
        
        # String similarity as fallback
        return SequenceMatcher(None, name1, name2).ratio()
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name for comparison."""
        # Convert to lowercase
        name = name.lower().strip()
        
        # Remove special characters
        name = re.sub(r'[^\w\s\u4e00-\u9fff]', '', name)
        
        # Collapse multiple spaces
        name = re.sub(r'\s+', ' ', name)
        
        return name
    
    def _is_name_abbreviation(self, name1: str, name2: str) -> bool:
        """Check if one name is an abbreviation of the other."""
        parts1 = name1.split()
        parts2 = name2.split()
        
        # Check various abbreviation patterns
        for p1, p2 in [(parts1, parts2), (parts2, parts1)]:
            if len(p1) == 2 and len(p2) == 2:
                # Check "W Zhang" vs "Wei Zhang"
                if p1[0] and p2[0] and p1[0][0] == p2[0][0] and p1[1] == p2[1]:
                    return True
                # Check "Zhang W" vs "Zhang Wei"
                if p1[0] == p2[0] and p1[1] and p2[1] and p1[1][0] == p2[1][0]:
                    return True
        
        return False
    
    def _list_similarity(self, list1: List[str], list2: List[str]) -> float:
        """
        Calculate similarity between two lists of strings.
        
        Uses Jaccard similarity with fuzzy matching.
        """
        if not list1 or not list2:
            return 0.0
        
        # Normalize items
        set1 = set(item.lower().strip() for item in list1)
        set2 = set(item.lower().strip() for item in list2)
        
        # Calculate exact Jaccard similarity
        exact_intersection = len(set1 & set2)
        exact_union = len(set1 | set2)
        
        if exact_union == 0:
            return 0.0
        
        # Add fuzzy matching for partial overlaps
        fuzzy_matches = 0
        for item1 in set1:
            for item2 in set2:
                if item1 not in set2 and item2 not in set1:
                    # Check substring match or high string similarity
                    if (item1 in item2 or item2 in item1 or
                        SequenceMatcher(None, item1, item2).ratio() > 0.85):
                        fuzzy_matches += 0.5
        
        # Combine exact and fuzzy scores
        similarity = (exact_intersection + fuzzy_matches) / exact_union
        return min(1.0, similarity)
    
    def _publication_similarity(
        self,
        pubs1: List[str],
        pubs2: List[str]
    ) -> float:
        """
        Calculate publication overlap.
        
        More lenient matching since publication titles may vary.
        """
        if not pubs1 or not pubs2:
            return 0.0
        
        matches = 0
        for pub1 in pubs1:
            pub1_clean = self._normalize_publication_title(pub1)
            for pub2 in pubs2:
                pub2_clean = self._normalize_publication_title(pub2)
                
                # Check for substantial overlap in title
                similarity = SequenceMatcher(None, pub1_clean, pub2_clean).ratio()
                if similarity > 0.70:
                    matches += 1
                    break
        
        # Use harmonic mean of precision and recall
        if len(pubs1) + len(pubs2) == 0:
            return 0.0
        
        precision = matches / len(pubs1) if pubs1 else 0
        recall = matches / len(pubs2) if pubs2 else 0
        
        if precision + recall == 0:
            return 0.0
        
        return 2 * (precision * recall) / (precision + recall)
    
    def _normalize_publication_title(self, title: str) -> str:
        """Normalize publication title for comparison."""
        # Convert to lowercase
        title = title.lower()
        
        # Remove common stopwords and punctuation
        title = re.sub(r'\b(a|an|the|of|in|on|for|with|using|based)\b', '', title)
        title = re.sub(r'[^\w\s]', ' ', title)
        
        # Collapse spaces
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title
    
    def _email_similarity(self, email1: Optional[str], email2: Optional[str]) -> float:
        """Calculate email similarity."""
        if not email1 or not email2:
            return 0.0
        
        email1 = email1.lower().strip()
        email2 = email2.lower().strip()
        
        # Exact match
        if email1 == email2:
            return 1.0
        
        # Check if domains match (institutional email)
        domain1 = email1.split('@')[-1] if '@' in email1 else ''
        domain2 = email2.split('@')[-1] if '@' in email2 else ''
        
        if domain1 and domain2 and domain1 == domain2:
            return 0.7
        
        return 0.0
    
    def _calculate_confidence(self, scores: Dict[str, float]) -> float:
        """Calculate weighted confidence score."""
        confidence = 0.0
        total_weight = 0.0
        
        for dimension, score in scores.items():
            weight = self.weights.get(dimension, 0.0)
            confidence += score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return confidence / total_weight
    
    def _generate_explanation(
        self,
        scores: Dict[str, float],
        confidence: float
    ) -> str:
        """Generate human-readable explanation."""
        # Determine confidence level
        if confidence >= self.HIGH_CONFIDENCE:
            level = "High confidence"
        elif confidence >= self.MEDIUM_CONFIDENCE:
            level = "Medium confidence"
        elif confidence >= self.LOW_CONFIDENCE:
            level = "Low confidence"
        else:
            level = "Very low confidence"
        
        # Find strongest evidence
        strong_evidence = [
            dim for dim, score in scores.items()
            if score > 0.7
        ]
        
        # Find weak evidence
        weak_evidence = [
            dim for dim, score in scores.items()
            if score < 0.3
        ]
        
        explanation_parts = [f"{level} match (score: {confidence:.2f})."]
        
        if strong_evidence:
            explanation_parts.append(
                f"Strong matches: {', '.join(strong_evidence)}."
            )
        
        if weak_evidence:
            explanation_parts.append(
                f"Weak matches: {', '.join(weak_evidence)}."
            )
        
        return " ".join(explanation_parts)


def extract_profile_from_resume_json(resume_data: dict) -> PersonProfile:
    """
    Extract PersonProfile from structured resume JSON.
    
    Args:
        resume_data: Resume JSON data
        
    Returns:
        PersonProfile instance
    """
    basic_info = resume_data.get("basic_info", {})
    
    # Extract affiliations from education and work
    affiliations = []
    
    education = resume_data.get("education", [])
    for edu in education:
        school = edu.get("school", "").strip()
        if school:
            affiliations.append(school)
    
    work = resume_data.get("work_experience", [])
    for job in work:
        company = job.get("company", "").strip()
        if company:
            affiliations.append(company)
    
    # Extract research interests
    research_interests = resume_data.get("research_interests", [])
    
    # Extract publications
    publications = [
        pub.get("title", "").strip()
        for pub in resume_data.get("publications", [])
        if pub.get("title")
    ]
    
    # Extract coauthors from publications
    coauthors = set()
    for pub in resume_data.get("publications", []):
        authors = pub.get("authors", "")
        if authors:
            # Split by common delimiters
            author_list = re.split(r'[,;]|\sand\s', authors)
            for author in author_list:
                author = author.strip()
                if author and author != basic_info.get("name", ""):
                    coauthors.add(author)
    
    return PersonProfile(
        name=basic_info.get("name", ""),
        affiliations=affiliations,
        research_interests=research_interests,
        education=[edu.get("school", "") for edu in education],
        positions=[job.get("title", "") for job in work],
        coauthors=list(coauthors),
        publications=publications,
        email=basic_info.get("email", "")
    )


# Example usage and testing
if __name__ == "__main__":
    # Create test profiles
    target = PersonProfile(
        name="Wei Zhang",
        affiliations=["Tsinghua University", "ByteDance"],
        research_interests=["Machine Learning", "Computer Vision"],
        education=["Tsinghua University"],
        publications=["Deep Learning for Image Recognition"],
        email="weizhang@tsinghua.edu.cn"
    )
    
    # High confidence match
    candidate1 = PersonProfile(
        name="Zhang Wei",
        affiliations=["Tsinghua University"],
        research_interests=["Machine Learning", "Deep Learning"],
        education=["Tsinghua University"],
        publications=["Deep Learning for Image Recognition"],
        email="weizhang@tsinghua.edu.cn"
    )
    
    # Low confidence match (different person)
    candidate2 = PersonProfile(
        name="Wei Zhang",
        affiliations=["Peking University"],
        research_interests=["Quantum Computing"],
        education=["Peking University"],
        publications=["Quantum Algorithms for AI"],
        email="zhangwei@pku.edu.cn"
    )
    
    # Test disambiguation
    disambiguator = PersonDisambiguator()
    
    print("Test 1: High confidence match")
    result1 = disambiguator.disambiguate(target, candidate1)
    print(f"Match: {result1.is_match}, Confidence: {result1.confidence:.2f}")
    print(f"Explanation: {result1.explanation}")
    print(f"Evidence: {result1.evidence}\n")
    
    print("Test 2: Low confidence match (different person)")
    result2 = disambiguator.disambiguate(target, candidate2)
    print(f"Match: {result2.is_match}, Confidence: {result2.confidence:.2f}")
    print(f"Explanation: {result2.explanation}")
    print(f"Evidence: {result2.evidence}")
