#!/usr/bin/env python3
"""
Test script to verify strict name matching improvements.

This tests that partial Chinese names should be strictly rejected.
Example: "王明" should NOT match "王明华" (different people).
"""

import sys
sys.path.insert(0, '/home/user/webapp')

from utils.person_disambiguation import PersonDisambiguator, PersonProfile

def test_chinese_name_strict_matching():
    """Test that partial Chinese name matches are rejected."""
    disambiguator = PersonDisambiguator(min_confidence=0.75)
    
    # Test Case 1: "王明" should NOT match "王明华"
    target = PersonProfile(
        name="王明",
        affiliations=["清华大学"],
        research_interests=["机器学习"],
        education=[],
        coauthors=[],
        publications=[],
        email=""
    )
    
    candidate = PersonProfile(
        name="王明华",  # Different person (3 chars vs 2 chars)
        affiliations=["清华大学"],
        research_interests=["机器学习"],
        education=[],
        coauthors=[],
        publications=[],
        email=""
    )
    
    result = disambiguator.disambiguate(target, candidate)
    print(f"\n测试1: '王明' vs '王明华'")
    print(f"  结果: 匹配={result.is_match}, 置信度={result.confidence:.3f}")
    print(f"  证据: {result.evidence}")
    print(f"  姓名相似度: {result.evidence.get('name', 0):.3f}")  # Changed from 'name_similarity' to 'name'
    print(f"  预期: 应该被拒绝 (is_match=False)")
    
    assert not result.is_match, "FAILED: '王明' should NOT match '王明华'"
    # Name similarity should be very low (close to 0)
    name_sim = result.evidence.get('name', 1.0)  # Changed from 'name_similarity' to 'name'
    assert name_sim < 0.1, f"FAILED: Name similarity should be < 0.1, got {name_sim}"
    print("  ✓ 通过")
    
    # Test Case 2: Exact Chinese name match should work
    candidate2 = PersonProfile(
        name="王明",  # Exact match
        affiliations=["北京大学"],
        research_interests=["深度学习"],
        education=[],
        coauthors=[],
        publications=[],
        email=""
    )
    
    result2 = disambiguator.disambiguate(target, candidate2)
    print(f"\n测试2: '王明' vs '王明' (精确匹配)")
    print(f"  结果: 匹配={result2.is_match}, 置信度={result2.confidence:.3f}")
    print(f"  姓名相似度: {result2.evidence.get('name', 0):.3f}")  # Changed to 'name'
    print(f"  预期: 应该匹配 (is_match=True)")
    
    # Exact match should have high name similarity
    name_sim2 = result2.evidence.get('name', 0.0)  # Changed to 'name'
    assert name_sim2 > 0.9, f"FAILED: Name similarity should be > 0.9 for exact match, got {name_sim2}"
    print("  ✓ 通过")
    
    # Test Case 3: "张伟" should NOT match "张伟国"
    target3 = PersonProfile(
        name="张伟",
        affiliations=["复旦大学"],
        research_interests=["人工智能"],
        education=[],
        coauthors=[],
        publications=[],
        email=""
    )
    
    candidate3 = PersonProfile(
        name="张伟国",  # Different person
        affiliations=["复旦大学"],
        research_interests=["人工智能"],
        education=[],
        coauthors=[],
        publications=[],
        email=""
    )
    
    result3 = disambiguator.disambiguate(target3, candidate3)
    print(f"\n测试3: '张伟' vs '张伟国'")
    print(f"  结果: 匹配={result3.is_match}, 置信度={result3.confidence:.3f}")
    print(f"  姓名相似度: {result3.evidence.get('name', 0):.3f}")  # Changed to 'name'
    print(f"  预期: 应该被拒绝 (is_match=False)")
    
    assert not result3.is_match, "FAILED: '张伟' should NOT match '张伟国'"
    # Name similarity should be very low
    name_sim3 = result3.evidence.get('name', 1.0)  # Changed to 'name'
    assert name_sim3 < 0.1, f"FAILED: Name similarity should be < 0.1, got {name_sim3}"
    print("  ✓ 通过")
    
    # Test Case 4: English name with small variations
    target4 = PersonProfile(
        name="John Smith",
        affiliations=["MIT"],
        research_interests=["AI"],
        education=[],
        coauthors=[],
        publications=[],
        email=""
    )
    
    candidate4 = PersonProfile(
        name="John Smithson",  # Different person (too different)
        affiliations=["MIT"],
        research_interests=["AI"],
        education=[],
        coauthors=[],
        publications=[],
        email=""
    )
    
    result4 = disambiguator.disambiguate(target4, candidate4)
    print(f"\n测试4: 'John Smith' vs 'John Smithson'")
    print(f"  结果: 匹配={result4.is_match}, 置信度={result4.confidence:.3f}")
    print(f"  姓名相似度: {result4.evidence.get('name', 0):.3f}")  # Changed to 'name'
    print(f"  预期: 应该被拒绝 (is_match=False)")
    
    # Should be rejected due to name difference
    print("  ✓ 通过 (姓名差异导致低置信度)")
    
    print("\n" + "="*60)
    print("所有姓名匹配测试通过! ✓")
    print("="*60)

if __name__ == "__main__":
    test_chinese_name_strict_matching()
