"""
Unit tests for person disambiguation module.

Tests the PersonDisambiguator class and related functionality.
"""

import pytest
from utils.person_disambiguation import (
    PersonProfile,
    PersonDisambiguator,
    DisambiguationResult,
    extract_profile_from_resume_json
)


class TestPersonProfile:
    """Test PersonProfile dataclass."""
    
    def test_basic_creation(self):
        """Test basic profile creation."""
        profile = PersonProfile(
            name="Wei Zhang",
            affiliations=["Tsinghua University"],
            research_interests=["Machine Learning"]
        )
        assert profile.name == "Wei Zhang"
        assert profile.affiliations == ["Tsinghua University"]
        assert profile.research_interests == ["Machine Learning"]
        assert profile.education == []
        assert profile.coauthors == []
    
    def test_empty_lists_initialization(self):
        """Test that None values are converted to empty lists."""
        profile = PersonProfile(name="Test User")
        assert profile.affiliations == []
        assert profile.research_interests == []
        assert profile.education == []
        assert profile.positions == []
        assert profile.coauthors == []
        assert profile.publications == []


class TestDisambiguationResult:
    """Test DisambiguationResult dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = DisambiguationResult(
            is_match=True,
            confidence=0.85,
            evidence={"name": 0.9, "affiliation": 0.8},
            explanation="High confidence match"
        )
        result_dict = result.to_dict()
        assert result_dict["is_match"] is True
        assert result_dict["confidence"] == 0.85
        assert result_dict["evidence"]["name"] == 0.9
        assert result_dict["explanation"] == "High confidence match"


class TestPersonDisambiguator:
    """Test PersonDisambiguator class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.disambiguator = PersonDisambiguator()
        
        # Create test profiles
        self.target = PersonProfile(
            name="Wei Zhang",
            affiliations=["Tsinghua University", "ByteDance"],
            research_interests=["Machine Learning", "Computer Vision"],
            education=["Tsinghua University"],
            publications=["Deep Learning for Image Recognition"],
            email="weizhang@tsinghua.edu.cn"
        )
    
    def test_exact_name_match(self):
        """Test exact name matching."""
        candidate = PersonProfile(
            name="Wei Zhang",
            affiliations=["Tsinghua University"]
        )
        result = self.disambiguator.disambiguate(self.target, candidate)
        assert result.evidence["name"] == 1.0
    
    def test_reversed_name_match(self):
        """Test reversed name order (Chinese vs Western)."""
        candidate = PersonProfile(
            name="Zhang Wei",  # Reversed order
            affiliations=["Tsinghua University"],
            research_interests=["Machine Learning", "Computer Vision"]  # Add more overlap
        )
        result = self.disambiguator.disambiguate(self.target, candidate)
        assert result.evidence["name"] == 0.95  # High confidence for reversed names
        # With name + affiliation + research overlap, should be reasonable confidence
        assert result.confidence > 0.40
    
    def test_abbreviated_name_match(self):
        """Test abbreviated name matching."""
        candidate = PersonProfile(
            name="W Zhang",  # Abbreviated first name
            affiliations=["Tsinghua University"]
        )
        result = self.disambiguator.disambiguate(self.target, candidate)
        assert result.evidence["name"] == 0.95
    
    def test_affiliation_match(self):
        """Test affiliation matching."""
        candidate = PersonProfile(
            name="Wei Zhang",
            affiliations=["Tsinghua University", "Google"]
        )
        result = self.disambiguator.disambiguate(self.target, candidate)
        # Should have partial affiliation match
        assert result.evidence["affiliation"] > 0.3
    
    def test_research_interests_match(self):
        """Test research interests matching."""
        candidate = PersonProfile(
            name="Wei Zhang",
            affiliations=["Tsinghua University"],
            research_interests=["Machine Learning", "Deep Learning"]
        )
        result = self.disambiguator.disambiguate(self.target, candidate)
        # Should have partial research interests match
        assert result.evidence["research_interests"] > 0.3
    
    def test_email_domain_match(self):
        """Test email domain matching."""
        candidate = PersonProfile(
            name="Wei Zhang",
            email="wzhang@tsinghua.edu.cn"  # Same domain
        )
        result = self.disambiguator.disambiguate(self.target, candidate)
        assert result.evidence["email"] > 0.6
    
    def test_publication_overlap(self):
        """Test publication overlap matching."""
        candidate = PersonProfile(
            name="Wei Zhang",
            publications=["Deep Learning for Image Recognition", "Another Paper"]
        )
        result = self.disambiguator.disambiguate(self.target, candidate)
        assert result.evidence["publications"] > 0.0
    
    def test_high_confidence_match(self):
        """Test high confidence match scenario."""
        candidate = PersonProfile(
            name="Zhang Wei",  # Reversed
            affiliations=["Tsinghua University"],
            research_interests=["Machine Learning", "Computer Vision"],  # Exact match
            publications=["Deep Learning for Image Recognition"],  # Exact match
            email="w.zhang@tsinghua.edu.cn"
        )
        result = self.disambiguator.disambiguate(self.target, candidate)
        assert result.is_match is True
        assert result.confidence >= self.disambiguator.MEDIUM_CONFIDENCE
        assert "confidence" in result.explanation.lower()
    
    def test_different_person_low_confidence(self):
        """Test different person with same name."""
        candidate = PersonProfile(
            name="Wei Zhang",
            affiliations=["Peking University"],  # Different affiliation
            research_interests=["Quantum Computing"],  # Different interests
            email="zhangwei@pku.edu.cn"  # Different domain
        )
        result = self.disambiguator.disambiguate(self.target, candidate)
        assert result.is_match is False
        assert result.confidence < self.disambiguator.MEDIUM_CONFIDENCE
    
    def test_custom_weights(self):
        """Test custom weight configuration."""
        custom_weights = {
            "name": 0.5,
            "affiliation": 0.3,
            "email": 0.2
        }
        disambiguator = PersonDisambiguator(weights=custom_weights)
        assert disambiguator.weights["name"] == 0.5
        assert disambiguator.weights["affiliation"] == 0.3
    
    def test_custom_min_confidence(self):
        """Test custom minimum confidence threshold."""
        disambiguator = PersonDisambiguator(min_confidence=0.70)
        assert disambiguator.min_confidence == 0.70
        
        candidate = PersonProfile(
            name="Wei Zhang",
            affiliations=["Tsinghua University"]
        )
        result = disambiguator.disambiguate(self.target, candidate)
        # Result should respect custom threshold
        if result.confidence < 0.70:
            assert result.is_match is False
    
    def test_empty_profiles(self):
        """Test handling of empty profiles."""
        empty_target = PersonProfile(name="")
        empty_candidate = PersonProfile(name="")
        result = self.disambiguator.disambiguate(empty_target, empty_candidate)
        assert result.confidence == 0.0
        assert result.is_match is False
    
    def test_explanation_generation(self):
        """Test explanation text generation."""
        candidate = PersonProfile(
            name="Zhang Wei",
            affiliations=["Tsinghua University"],
            research_interests=["Machine Learning"]
        )
        result = self.disambiguator.disambiguate(self.target, candidate)
        assert isinstance(result.explanation, str)
        assert len(result.explanation) > 0
        assert "confidence" in result.explanation.lower()


class TestExtractProfileFromResumeJSON:
    """Test extract_profile_from_resume_json function."""
    
    def test_basic_extraction(self):
        """Test basic profile extraction from resume JSON."""
        resume_data = {
            "basic_info": {
                "name": "Wei Zhang",
                "email": "weizhang@example.com"
            },
            "education": [
                {"school": "Tsinghua University", "degree": "PhD"}
            ],
            "work_experience": [
                {"company": "ByteDance", "title": "Research Scientist"}
            ],
            "research_interests": ["Machine Learning", "Computer Vision"],
            "publications": [
                {"title": "Deep Learning Paper", "authors": "Wei Zhang, John Doe"}
            ]
        }
        
        profile = extract_profile_from_resume_json(resume_data)
        
        assert profile.name == "Wei Zhang"
        assert "Tsinghua University" in profile.affiliations
        assert "ByteDance" in profile.affiliations
        assert profile.research_interests == ["Machine Learning", "Computer Vision"]
        assert len(profile.publications) == 1
        assert "John Doe" in profile.coauthors
        assert profile.email == "weizhang@example.com"
    
    def test_empty_resume(self):
        """Test extraction from empty resume."""
        resume_data = {}
        profile = extract_profile_from_resume_json(resume_data)
        assert profile.name == ""
        assert profile.affiliations == []
    
    def test_coauthor_extraction(self):
        """Test coauthor extraction from publications."""
        resume_data = {
            "basic_info": {"name": "Wei Zhang"},
            "publications": [
                {"title": "Paper 1", "authors": "Wei Zhang, Alice, Bob"},
                {"title": "Paper 2", "authors": "Wei Zhang and Charlie"}
            ]
        }
        
        profile = extract_profile_from_resume_json(resume_data)
        
        # Should extract coauthors but not self
        assert "Wei Zhang" not in profile.coauthors
        assert "Alice" in profile.coauthors
        assert "Bob" in profile.coauthors
        assert "Charlie" in profile.coauthors


class TestNameSimilarity:
    """Test name similarity methods."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.disambiguator = PersonDisambiguator()
    
    def test_chinese_pinyin_variations(self):
        """Test Chinese name variations."""
        # Common Chinese name variations
        test_cases = [
            ("Zhang Wei", "Wei Zhang", 0.95),  # Reversed
            ("Wei Zhang", "W. Zhang", 0.95),   # Abbreviated
            ("Zhang W", "Zhang Wei", 0.95),    # Abbreviated last
        ]
        
        for name1, name2, expected_min in test_cases:
            score = self.disambiguator._name_similarity(name1, name2)
            assert score >= expected_min, f"Failed for {name1} vs {name2}: {score}"
    
    def test_case_insensitive(self):
        """Test case-insensitive name matching."""
        score = self.disambiguator._name_similarity("Wei Zhang", "wei zhang")
        assert score == 1.0
    
    def test_special_characters_removal(self):
        """Test special characters are normalized."""
        score = self.disambiguator._name_similarity("Wei-Zhang", "Wei Zhang")
        assert score > 0.9


class TestListSimilarity:
    """Test list similarity methods."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.disambiguator = PersonDisambiguator()
    
    def test_exact_match(self):
        """Test exact list matching."""
        list1 = ["Machine Learning", "Computer Vision"]
        list2 = ["Machine Learning", "Computer Vision"]
        score = self.disambiguator._list_similarity(list1, list2)
        assert score == 1.0
    
    def test_partial_overlap(self):
        """Test partial list overlap."""
        list1 = ["Machine Learning", "Computer Vision"]
        list2 = ["Machine Learning", "NLP"]
        score = self.disambiguator._list_similarity(list1, list2)
        assert 0.3 < score < 0.7
    
    def test_fuzzy_matching(self):
        """Test fuzzy string matching within lists."""
        list1 = ["Machine Learning"]
        list2 = ["Machine Learning and AI"]
        score = self.disambiguator._list_similarity(list1, list2)
        assert score > 0.2  # Should detect partial match (fuzzy contributes 0.5 to Jaccard)
    
    def test_empty_lists(self):
        """Test empty list handling."""
        score = self.disambiguator._list_similarity([], [])
        assert score == 0.0
        
        score = self.disambiguator._list_similarity(["item"], [])
        assert score == 0.0


class TestPublicationSimilarity:
    """Test publication similarity methods."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.disambiguator = PersonDisambiguator()
    
    def test_similar_titles(self):
        """Test similar publication title matching."""
        pubs1 = ["Deep Learning for Image Recognition"]
        pubs2 = ["Deep Learning for Image Recognition"]
        score = self.disambiguator._publication_similarity(pubs1, pubs2)
        assert score > 0.7
    
    def test_title_normalization(self):
        """Test publication title normalization."""
        pubs1 = ["The Deep Learning Approach for Image Recognition"]
        pubs2 = ["Deep Learning Approach Image Recognition"]
        score = self.disambiguator._publication_similarity(pubs1, pubs2)
        assert score > 0.5  # Should match after normalization
    
    def test_no_overlap(self):
        """Test no publication overlap."""
        pubs1 = ["Paper about ML"]
        pubs2 = ["Paper about Quantum Computing"]
        score = self.disambiguator._publication_similarity(pubs1, pubs2)
        assert score < 0.3


# Integration test
class TestIntegrationScenarios:
    """Test real-world integration scenarios."""
    
    def test_linkedin_profile_match(self):
        """Test matching a LinkedIn profile."""
        disambiguator = PersonDisambiguator(min_confidence=0.50)  # Slightly lower threshold for real-world
        
        # Resume profile
        target = PersonProfile(
            name="Wei Zhang",
            affiliations=["Tsinghua University", "ByteDance"],
            research_interests=["Machine Learning", "Computer Vision"],
            email="weizhang@bytedance.com"
        )
        
        # LinkedIn profile (might have different name order)
        candidate = PersonProfile(
            name="Zhang Wei",
            affiliations=["ByteDance", "Tsinghua University"],
            research_interests=["AI", "Machine Learning"],
            email="zhangwei@bytedance.com"  # Same domain for higher confidence
        )
        
        result = disambiguator.disambiguate(target, candidate)
        assert result.is_match is True
        assert result.confidence >= 0.50
    
    def test_scholar_profile_different_person(self):
        """Test rejecting a different person with same name."""
        disambiguator = PersonDisambiguator(min_confidence=0.60)
        
        target = PersonProfile(
            name="Wei Zhang",
            affiliations=["Tsinghua University"],
            research_interests=["Machine Learning"],
            email="weizhang@tsinghua.edu.cn"
        )
        
        # Different person, same name
        candidate = PersonProfile(
            name="Wei Zhang",
            affiliations=["Stanford University"],
            research_interests=["Quantum Physics"],
            email="wzhang@stanford.edu"
        )
        
        result = disambiguator.disambiguate(target, candidate)
        assert result.is_match is False
        assert result.confidence < 0.60


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
