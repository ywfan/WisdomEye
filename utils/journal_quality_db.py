"""
Journal and Conference Quality Database
期刊和会议质量数据库

Provides venue quality ratings, impact factors, and ranking information
for academic publications.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class VenueTier(Enum):
    """Venue quality tier classification"""
    T1 = "T1"  # Top-tier (top 5-10% in field)
    T2 = "T2"  # High-quality (top 10-25% in field)
    T3 = "T3"  # Standard (top 25-50% in field)
    T4 = "T4"  # Below average (bottom 50%)
    UNKNOWN = "Unknown"


class CCFRank(Enum):
    """CCF (China Computer Federation) ranking"""
    A = "A"  # Top tier
    B = "B"  # Good tier
    C = "C"  # Standard tier
    NONE = "None"


@dataclass
class VenueQuality:
    """Quality metadata for a journal or conference"""
    name: str
    venue_type: str  # "journal" or "conference"
    tier: VenueTier
    
    # Impact metrics
    impact_factor: Optional[float] = None  # JCR impact factor
    h5_index: Optional[int] = None  # Google Scholar h5-index
    
    # Rankings
    jcr_quartile: Optional[str] = None  # Q1, Q2, Q3, Q4
    ccf_rank: CCFRank = CCFRank.NONE
    
    # Field information
    primary_field: Optional[str] = None
    field_rank: Optional[str] = None  # e.g., "Top 3 in Numerical Analysis"
    
    # Additional notes
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "venue_type": self.venue_type,
            "tier": self.tier.value,
            "impact_factor": self.impact_factor,
            "h5_index": self.h5_index,
            "jcr_quartile": self.jcr_quartile,
            "ccf_rank": self.ccf_rank.value,
            "primary_field": self.primary_field,
            "field_rank": self.field_rank,
            "notes": self.notes,
        }


# Journal and Conference Quality Database
# Data sources: JCR, Google Scholar, CCF, CORE rankings, field expert consensus
VENUE_QUALITY_DB = {
    # ============================================
    # MATHEMATICS - Top Journals
    # ============================================
    "SIAM Journal on Numerical Analysis": VenueQuality(
        name="SIAM Journal on Numerical Analysis",
        venue_type="journal",
        tier=VenueTier.T1,
        impact_factor=2.9,
        h5_index=45,
        jcr_quartile="Q1",
        primary_field="Numerical Analysis",
        field_rank="Top 3 in Numerical Analysis",
        notes="Premier journal for numerical analysis research"
    ),
    
    "Numerische Mathematik": VenueQuality(
        name="Numerische Mathematik",
        venue_type="journal",
        tier=VenueTier.T1,
        impact_factor=2.1,
        h5_index=38,
        jcr_quartile="Q1",
        primary_field="Numerical Analysis",
        field_rank="Top 5 in Numerical Analysis"
    ),
    
    "Mathematics of Computation": VenueQuality(
        name="Mathematics of Computation",
        venue_type="journal",
        tier=VenueTier.T1,
        impact_factor=1.9,
        h5_index=42,
        jcr_quartile="Q1",
        primary_field="Computational Mathematics",
        field_rank="Top 5 in Computational Mathematics"
    ),
    
    "SIAM Journal on Scientific Computing": VenueQuality(
        name="SIAM Journal on Scientific Computing",
        venue_type="journal",
        tier=VenueTier.T1,
        impact_factor=2.4,
        h5_index=51,
        jcr_quartile="Q1",
        primary_field="Scientific Computing",
        field_rank="Top 3 in Scientific Computing"
    ),
    
    "Journal of Computational Physics": VenueQuality(
        name="Journal of Computational Physics",
        venue_type="journal",
        tier=VenueTier.T1,
        impact_factor=3.8,
        h5_index=89,
        jcr_quartile="Q1",
        primary_field="Computational Physics",
        field_rank="Top 1 in Computational Physics"
    ),
    
    "Computer Methods in Applied Mechanics and Engineering": VenueQuality(
        name="Computer Methods in Applied Mechanics and Engineering",
        venue_type="journal",
        tier=VenueTier.T1,
        impact_factor=6.9,
        h5_index=112,
        jcr_quartile="Q1",
        primary_field="Computational Engineering",
        field_rank="Top 1 in Computational Mechanics"
    ),
    
    "SIAM Review": VenueQuality(
        name="SIAM Review",
        venue_type="journal",
        tier=VenueTier.T1,
        impact_factor=10.2,
        h5_index=48,
        jcr_quartile="Q1",
        primary_field="Applied Mathematics",
        field_rank="Top 1 in Applied Math (Review Journal)",
        notes="Highly selective review and survey journal"
    ),
    
    # ============================================
    # COMPUTER SCIENCE - Top Conferences
    # ============================================
    "NeurIPS": VenueQuality(
        name="NeurIPS",
        venue_type="conference",
        tier=VenueTier.T1,
        h5_index=312,
        ccf_rank=CCFRank.A,
        primary_field="Machine Learning",
        field_rank="Top 3 in Machine Learning",
        notes="Neural Information Processing Systems"
    ),
    
    "ICML": VenueQuality(
        name="ICML",
        venue_type="conference",
        tier=VenueTier.T1,
        h5_index=278,
        ccf_rank=CCFRank.A,
        primary_field="Machine Learning",
        field_rank="Top 3 in Machine Learning",
        notes="International Conference on Machine Learning"
    ),
    
    "ICLR": VenueQuality(
        name="ICLR",
        venue_type="conference",
        tier=VenueTier.T1,
        h5_index=289,
        ccf_rank=CCFRank.A,
        primary_field="Deep Learning",
        field_rank="Top 3 in Deep Learning",
        notes="International Conference on Learning Representations"
    ),
    
    "CVPR": VenueQuality(
        name="CVPR",
        venue_type="conference",
        tier=VenueTier.T1,
        h5_index=389,
        ccf_rank=CCFRank.A,
        primary_field="Computer Vision",
        field_rank="Top 1 in Computer Vision",
        notes="Conference on Computer Vision and Pattern Recognition"
    ),
    
    "ICCV": VenueQuality(
        name="ICCV",
        venue_type="conference",
        tier=VenueTier.T1,
        h5_index=241,
        ccf_rank=CCFRank.A,
        primary_field="Computer Vision",
        field_rank="Top 2 in Computer Vision",
        notes="International Conference on Computer Vision"
    ),
    
    "SIGGRAPH": VenueQuality(
        name="SIGGRAPH",
        venue_type="conference",
        tier=VenueTier.T1,
        h5_index=98,
        ccf_rank=CCFRank.A,
        primary_field="Computer Graphics",
        field_rank="Top 1 in Computer Graphics"
    ),
    
    "ACL": VenueQuality(
        name="ACL",
        venue_type="conference",
        tier=VenueTier.T1,
        h5_index=176,
        ccf_rank=CCFRank.A,
        primary_field="Natural Language Processing",
        field_rank="Top 1 in NLP",
        notes="Association for Computational Linguistics"
    ),
    
    "EMNLP": VenueQuality(
        name="EMNLP",
        venue_type="conference",
        tier=VenueTier.T1,
        h5_index=148,
        ccf_rank=CCFRank.B,
        primary_field="Natural Language Processing",
        field_rank="Top 3 in NLP"
    ),
    
    # ============================================
    # COMPUTER SCIENCE - Top Journals
    # ============================================
    "IEEE Transactions on Pattern Analysis and Machine Intelligence": VenueQuality(
        name="IEEE Transactions on Pattern Analysis and Machine Intelligence",
        venue_type="journal",
        tier=VenueTier.T1,
        impact_factor=24.3,
        h5_index=234,
        jcr_quartile="Q1",
        ccf_rank=CCFRank.A,
        primary_field="Computer Vision",
        field_rank="Top 1 in Computer Vision/Pattern Recognition",
        notes="TPAMI - Most prestigious CV journal"
    ),
    
    "Journal of Machine Learning Research": VenueQuality(
        name="Journal of Machine Learning Research",
        venue_type="journal",
        tier=VenueTier.T1,
        impact_factor=5.3,
        h5_index=149,
        jcr_quartile="Q1",
        ccf_rank=CCFRank.A,
        primary_field="Machine Learning",
        field_rank="Top 1 in Machine Learning (Journal)",
        notes="JMLR - Open access ML journal"
    ),
    
    "IEEE Transactions on Information Theory": VenueQuality(
        name="IEEE Transactions on Information Theory",
        venue_type="journal",
        tier=VenueTier.T1,
        impact_factor=2.5,
        h5_index=68,
        jcr_quartile="Q1",
        ccf_rank=CCFRank.A,
        primary_field="Information Theory",
        field_rank="Top 1 in Information Theory"
    ),
    
    # ============================================
    # CHINESE JOURNALS (Top Tier)
    # ============================================
    "中国科学: 数学": VenueQuality(
        name="中国科学: 数学",
        venue_type="journal",
        tier=VenueTier.T2,
        jcr_quartile="Q2",
        primary_field="Mathematics",
        field_rank="Top Chinese Math Journal",
        notes="Science China Mathematics"
    ),
    
    "数学学报": VenueQuality(
        name="数学学报",
        venue_type="journal",
        tier=VenueTier.T2,
        jcr_quartile="Q3",
        primary_field="Mathematics",
        field_rank="Leading Chinese Math Journal",
        notes="Acta Mathematica Sinica"
    ),
    
    "计算机学报": VenueQuality(
        name="计算机学报",
        venue_type="journal",
        tier=VenueTier.T2,
        primary_field="Computer Science",
        field_rank="Top Chinese CS Journal",
        notes="Chinese Journal of Computers"
    ),
    
    # ============================================
    # TIER 2 - High Quality Venues
    # ============================================
    "Applied Numerical Mathematics": VenueQuality(
        name="Applied Numerical Mathematics",
        venue_type="journal",
        tier=VenueTier.T2,
        impact_factor=1.8,
        jcr_quartile="Q2",
        primary_field="Numerical Analysis"
    ),
    
    "Journal of Scientific Computing": VenueQuality(
        name="Journal of Scientific Computing",
        venue_type="journal",
        tier=VenueTier.T2,
        impact_factor=2.5,
        h5_index=44,
        jcr_quartile="Q2",
        primary_field="Scientific Computing"
    ),
    
    "AAAI": VenueQuality(
        name="AAAI",
        venue_type="conference",
        tier=VenueTier.T1,
        h5_index=171,
        ccf_rank=CCFRank.A,
        primary_field="Artificial Intelligence",
        field_rank="Top 5 in AI",
        notes="AAAI Conference on Artificial Intelligence"
    ),
    
    "IJCAI": VenueQuality(
        name="IJCAI",
        venue_type="conference",
        tier=VenueTier.T1,
        h5_index=102,
        ccf_rank=CCFRank.A,
        primary_field="Artificial Intelligence",
        field_rank="Top 5 in AI"
    ),
    
    # ============================================
    # TIER 3 - Standard Venues
    # ============================================
    "Computers & Mathematics with Applications": VenueQuality(
        name="Computers & Mathematics with Applications",
        venue_type="journal",
        tier=VenueTier.T3,
        impact_factor=2.9,
        jcr_quartile="Q2",
        primary_field="Applied Mathematics"
    ),
    
    "Applied Mathematics and Computation": VenueQuality(
        name="Applied Mathematics and Computation",
        venue_type="journal",
        tier=VenueTier.T3,
        impact_factor=3.5,
        jcr_quartile="Q1",
        primary_field="Applied Mathematics",
        notes="High volume, moderate selectivity"
    ),
}


# Alias mapping (common variations of venue names)
VENUE_ALIASES = {
    # NeurIPS variations
    "neurips": "NeurIPS",
    "nips": "NeurIPS",
    "neural information processing systems": "NeurIPS",
    
    # ICML variations
    "icml": "ICML",
    "international conference on machine learning": "ICML",
    
    # ICLR variations
    "iclr": "ICLR",
    
    # CVPR variations
    "cvpr": "CVPR",
    
    # TPAMI variations
    "tpami": "IEEE Transactions on Pattern Analysis and Machine Intelligence",
    "ieee tpami": "IEEE Transactions on Pattern Analysis and Machine Intelligence",
    
    # SIAM variations
    "siam j. numer. anal.": "SIAM Journal on Numerical Analysis",
    "siam j numer anal": "SIAM Journal on Numerical Analysis",
    "sinum": "SIAM Journal on Numerical Analysis",
    
    "siam j. sci. comput.": "SIAM Journal on Scientific Computing",
    "sisc": "SIAM Journal on Scientific Computing",
    
    # Short forms
    "jcp": "Journal of Computational Physics",
    "cmame": "Computer Methods in Applied Mechanics and Engineering",
    "moc": "Mathematics of Computation",
    "numer. math.": "Numerische Mathematik",
    "jmlr": "Journal of Machine Learning Research",
}


class JournalQualityDatabase:
    """
    Journal and conference quality database with search functionality
    """
    
    def __init__(self, custom_db: Optional[Dict[str, VenueQuality]] = None):
        """
        Initialize database
        
        Args:
            custom_db: Custom venue database (optional)
        """
        self.db = custom_db or VENUE_QUALITY_DB
        self.aliases = VENUE_ALIASES
    
    def normalize_venue_name(self, venue: str) -> Optional[str]:
        """
        Normalize venue name to canonical form
        
        Args:
            venue: Raw venue name
            
        Returns:
            Canonical venue name or None
        """
        if not venue:
            return None
        
        venue_lower = venue.lower().strip()
        
        # Direct match
        if venue in self.db:
            return venue
        
        # Check aliases
        if venue_lower in self.aliases:
            return self.aliases[venue_lower]
        
        # Fuzzy matching (substring match)
        for canonical_name in self.db.keys():
            if venue_lower in canonical_name.lower() or canonical_name.lower() in venue_lower:
                return canonical_name
        
        return None
    
    def get_venue_quality(self, venue: str) -> Optional[VenueQuality]:
        """
        Get quality information for a venue
        
        Args:
            venue: Venue name (journal or conference)
            
        Returns:
            VenueQuality object or None if not found
        """
        canonical_name = self.normalize_venue_name(venue)
        if canonical_name:
            return self.db.get(canonical_name)
        return None
    
    def classify_venue(self, venue: str) -> Dict[str, Any]:
        """
        Classify a venue and return quality metadata
        
        Args:
            venue: Venue name
            
        Returns:
            Classification dictionary
        """
        quality = self.get_venue_quality(venue)
        
        if quality:
            return {
                "found": True,
                "canonical_name": quality.name,
                "tier": quality.tier.value,
                "tier_label": self._get_tier_label(quality.tier),
                "venue_type": quality.venue_type,
                "quality_flag": self._get_quality_flag(quality.tier),
                "impact_factor": quality.impact_factor,
                "h5_index": quality.h5_index,
                "jcr_quartile": quality.jcr_quartile,
                "ccf_rank": quality.ccf_rank.value,
                "field": quality.primary_field,
                "field_rank": quality.field_rank,
                "notes": quality.notes,
            }
        else:
            return {
                "found": False,
                "canonical_name": venue,
                "tier": "Unknown",
                "tier_label": "Unverified",
                "quality_flag": "⚪ Unverified",
                "warning": "Unable to verify venue quality - manual review required",
            }
    
    def _get_tier_label(self, tier: VenueTier) -> str:
        """Get human-readable tier label"""
        labels = {
            VenueTier.T1: "Top-tier",
            VenueTier.T2: "High-quality",
            VenueTier.T3: "Standard",
            VenueTier.T4: "Below average",
            VenueTier.UNKNOWN: "Unknown",
        }
        return labels.get(tier, "Unknown")
    
    def _get_quality_flag(self, tier: VenueTier) -> str:
        """Get emoji flag for quick visual assessment"""
        flags = {
            VenueTier.T1: "🟢 Top-tier",
            VenueTier.T2: "🟡 High-quality",
            VenueTier.T3: "🟠 Standard",
            VenueTier.T4: "🔴 Below average",
            VenueTier.UNKNOWN: "⚪ Unverified",
        }
        return flags.get(tier, "⚪ Unknown")
    
    def batch_classify(self, venues: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Classify multiple venues at once
        
        Args:
            venues: List of venue names
            
        Returns:
            Dictionary mapping venue name to classification
        """
        results = {}
        for venue in venues:
            results[venue] = self.classify_venue(venue)
        return results
    
    def get_statistics(self, venues: List[str]) -> Dict[str, Any]:
        """
        Get publication quality statistics
        
        Args:
            venues: List of venues from candidate's publications
            
        Returns:
            Quality statistics
        """
        classifications = self.batch_classify(venues)
        
        tier_counts = {
            "T1": 0,
            "T2": 0,
            "T3": 0,
            "T4": 0,
            "Unknown": 0,
        }
        
        for classification in classifications.values():
            tier = classification.get("tier", "Unknown")
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        total = len(venues)
        
        return {
            "total_venues": total,
            "tier_counts": tier_counts,
            "tier_percentages": {
                tier: round(100 * count / total, 1) if total > 0 else 0
                for tier, count in tier_counts.items()
            },
            "top_tier_ratio": round(tier_counts["T1"] / total, 2) if total > 0 else 0,
            "verified_ratio": round((total - tier_counts["Unknown"]) / total, 2) if total > 0 else 0,
        }


# Convenience function
def classify_publication_venue(venue: str) -> Dict[str, Any]:
    """
    Quick venue classification
    
    Args:
        venue: Journal or conference name
        
    Returns:
        Quality classification
    """
    db = JournalQualityDatabase()
    return db.classify_venue(venue)
