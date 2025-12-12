"""Pytest configuration and shared fixtures."""
import os
import sys
from pathlib import Path
import pytest
import tempfile
import shutil

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def sample_resume_text():
    """Sample resume text for testing."""
    return """
张三
电话：138-0000-0000
邮箱：zhangsan@example.com

教育经历
2018-2022  清华大学  计算机科学与技术  博士
2014-2018  北京大学  软件工程  本科

研究方向
深度学习、自然语言处理、计算机视觉

论文发表
1. Attention Is All You Need. NeurIPS 2017.
2. BERT: Pre-training of Deep Bidirectional Transformers. NAACL 2019.

获奖情况
2021年 国家奖学金
2020年 ACM SIGKDD最佳论文奖
"""


@pytest.fixture
def sample_resume_json():
    """Sample structured resume JSON."""
    return {
        "basic_info": {
            "name": "张三",
            "highest_degree": "博士",
            "contact": {
                "phone": "138-0000-0000",
                "email": "zhangsan@example.com",
                "location": "",
                "homepage": ""
            },
            "summary": "",
            "academic_metrics": {
                "citations": "",
                "h_index": "",
                "impact_highlights": "",
                "h10_index": "",
                "citations_total": "",
                "citations_recent": ""
            }
        },
        "research_interests": ["深度学习", "自然语言处理", "计算机视觉"],
        "education": [
            {
                "school": "清华大学",
                "degree": "博士",
                "major": "计算机科学与技术",
                "time_period": "2018-2022",
                "supervisor": "",
                "thesis_title": "",
                "details": ""
            },
            {
                "school": "北京大学",
                "degree": "本科",
                "major": "软件工程",
                "time_period": "2014-2018",
                "supervisor": "",
                "thesis_title": "",
                "details": ""
            }
        ],
        "work_experience": [],
        "research_grants": [],
        "project_experience": [],
        "open_source_contributions": [],
        "publications": [
            {
                "title": "Attention Is All You Need",
                "authors": ["Vaswani", "Shazeer"],
                "venue": "NeurIPS 2017",
                "status": "Published",
                "url": "",
                "abstract": "",
                "summary": "",
                "date": "2017"
            }
        ],
        "patents": [],
        "academic_summary": [],
        "summary": "",
        "academic_activities": [],
        "memberships": [],
        "skills": {
            "tech_stack": ["Python", "TensorFlow", "PyTorch"],
            "languages": ["中文", "英文"]
        },
        "awards": [
            {
                "name": "国家奖学金",
                "date": "2021"
            }
        ],
        "social_presence": [],
        "social_influence": {
            "summary": "",
            "signals": []
        },
        "network_graph": {
            "nodes": [],
            "edges": [],
            "circle_tags": [],
            "centrality_metrics": {"degree": "", "coauthor_weight": ""}
        },
        "others": ""
    }


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return '{"basic_info": {"name": "测试用户"}, "education": []}'


@pytest.fixture
def mock_search_results():
    """Mock search results for testing."""
    return [
        {
            "title": "Test Paper Title",
            "url": "https://example.com/paper1",
            "content": "This is a test paper abstract about deep learning.",
            "source": "tavily"
        },
        {
            "title": "Another Research",
            "url": "https://example.com/paper2",
            "content": "Research on natural language processing.",
            "source": "bocha"
        }
    ]


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Setup test environment variables."""
    monkeypatch.setenv("LLM_DEFAULT_PROVIDER", "test")
    monkeypatch.setenv("LLM_DEFAULT_MODEL", "test-model")
    monkeypatch.setenv("BUDGET_MAX_LLM_CALLS", "0")
    monkeypatch.setenv("BUDGET_MAX_SEARCH_CALLS", "0")
    monkeypatch.setenv("LLM_RATE_LIMIT", "1000")
    monkeypatch.setenv("SEARCH_RATE_LIMIT", "1000")
