"""
GitHub Code Analyzer

This module provides in-depth GitHub analysis for engineering capability assessment.
Analyzes repositories, code quality, contribution patterns, and technical skills.

Features:
- Repository analysis (languages, complexity, documentation)
- Contribution pattern analysis
- Code quality assessment
- Technical skill extraction
- Collaboration metrics
- Activity timeline analysis

Author: WisdomEye Team
Date: 2025-12-12
"""

import re
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import requests
from bs4 import BeautifulSoup

from .observability import emit


@dataclass
class GitHubRepository:
    """Represents a GitHub repository with metadata."""
    name: str
    url: str
    description: str
    language: str
    stars: int
    forks: int
    watchers: int
    issues: int
    last_updated: Optional[str]
    topics: List[str]
    has_wiki: bool
    has_tests: bool
    has_ci: bool


@dataclass
class ContributionStats:
    """GitHub contribution statistics."""
    total_commits: int
    total_prs: int
    total_issues: int
    total_reviews: int
    languages: Dict[str, int]  # language -> lines of code
    active_repos: int
    contribution_streak: int  # days
    recent_activity_score: float


@dataclass
class TechnicalProfile:
    """Technical profile extracted from GitHub."""
    primary_languages: List[str]
    secondary_languages: List[str]
    frameworks: List[str]
    tools: List[str]
    domains: List[str]  # e.g., Web, ML, Data Science
    code_quality_score: float  # 0-100
    activity_level: str  # low, medium, high
    collaboration_score: float  # 0-100


class GitHubAnalyzer:
    """
    Comprehensive GitHub profile analyzer.
    
    Analyzes:
    - Repository portfolio
    - Code contributions
    - Technical skills
    - Collaboration patterns
    - Code quality indicators
    """
    
    def __init__(self, timeout: float = 10.0, max_repos: int = 50):
        """
        Initialize analyzer.
        
        Args:
            timeout: Request timeout in seconds
            max_repos: Maximum repositories to analyze
        """
        self.timeout = timeout
        self.max_repos = max_repos
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/vnd.github.v3+json'
        })
    
    def analyze_profile(
        self,
        github_url: str,
        include_code_quality: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze GitHub profile comprehensively.
        
        Args:
            github_url: GitHub profile URL
            include_code_quality: Whether to perform deep code quality analysis
            
        Returns:
            Dictionary with analysis results
        """
        emit({
            "kind": "github_analysis_start",
            "url": github_url
        })
        
        username = self._extract_username(github_url)
        if not username:
            print(f"[GitHub分析-错误] 无法从URL提取用户名: {github_url}")
            return {}
        
        try:
            # Gather data from multiple sources
            repos = self._fetch_repositories(username)
            contrib_stats = self._analyze_contributions(username, repos)
            technical_profile = self._build_technical_profile(repos, contrib_stats)
            
            if include_code_quality:
                code_quality = self._assess_code_quality(username, repos[:5])
            else:
                code_quality = {}
            
            result = {
                "username": username,
                "profile_url": github_url,
                "repositories": [self._repo_to_dict(r) for r in repos],
                "contribution_stats": self._contrib_stats_to_dict(contrib_stats),
                "technical_profile": self._technical_profile_to_dict(technical_profile),
                "code_quality": code_quality,
                "summary": self._generate_summary(repos, contrib_stats, technical_profile)
            }
            
            emit({
                "kind": "github_analysis_end",
                "username": username,
                "repos_analyzed": len(repos)
            })
            
            return result
            
        except Exception as e:
            emit({
                "kind": "github_analysis_error",
                "username": username,
                "error": str(e)
            })
            print(f"[GitHub分析-错误] {username}: {e}")
            return {}
    
    def _extract_username(self, github_url: str) -> Optional[str]:
        """Extract username from GitHub URL."""
        # Handle various URL formats
        patterns = [
            r'github\.com/([^/]+)/?$',
            r'github\.com/([^/]+)/[^/]+',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, github_url)
            if match:
                return match.group(1)
        
        return None
    
    def _fetch_repositories(self, username: str) -> List[GitHubRepository]:
        """Fetch user's repositories."""
        repos = []
        
        try:
            # Fetch repos page
            url = f"https://github.com/{username}?tab=repositories"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code != 200:
                print(f"[GitHub-仓库] HTTP {response.status_code}")
                return repos
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find repository list items
            repo_items = soup.find_all('div', {'id': re.compile('^user-repositories-list')})
            
            if repo_items:
                # Repos are inside the container
                repo_links = repo_items[0].find_all('a', {'itemprop': 'name codeRepository'}, limit=self.max_repos)
            else:
                # Fallback: find by href pattern
                repo_links = soup.find_all('a', href=re.compile(f'^/{username}/[^/]+$'), limit=self.max_repos)
            
            for link in repo_links[:self.max_repos]:
                try:
                    repo = self._parse_repository(link, username)
                    if repo:
                        repos.append(repo)
                except Exception as e:
                    print(f"[GitHub-仓库解析] 错误: {e}")
                    continue
            
            print(f"[GitHub-仓库] 找到 {len(repos)} 个仓库")
            
        except Exception as e:
            print(f"[GitHub-仓库] 获取失败: {e}")
        
        return repos
    
    def _parse_repository(self, link_elem, username: str) -> Optional[GitHubRepository]:
        """Parse repository from link element."""
        try:
            # Get repository container (parent divs)
            container = link_elem.find_parent('div', class_=re.compile('col-'))
            if not container:
                container = link_elem.find_parent('li')
            
            # Extract name and URL
            repo_name = link_elem.get_text(strip=True)
            repo_url = 'https://github.com' + link_elem['href']
            
            # Extract description
            desc_elem = container.find('p', class_=re.compile('(description|color-fg-muted)'))
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            
            # Extract language
            lang_elem = container.find('span', {'itemprop': 'programmingLanguage'})
            if not lang_elem:
                lang_elem = container.find('span', class_=re.compile('text-'))
            language = lang_elem.get_text(strip=True) if lang_elem else ""
            
            # Extract stars
            star_elem = container.find('a', href=re.compile('/stargazers'))
            stars = self._extract_number(star_elem.get_text() if star_elem else "0")
            
            # Extract forks
            fork_elem = container.find('a', href=re.compile('/forks'))
            forks = self._extract_number(fork_elem.get_text() if fork_elem else "0")
            
            # Extract topics/tags
            topic_elems = container.find_all('a', class_=re.compile('topic-tag'))
            topics = [t.get_text(strip=True) for t in topic_elems]
            
            return GitHubRepository(
                name=repo_name,
                url=repo_url,
                description=description,
                language=language,
                stars=stars,
                forks=forks,
                watchers=0,
                issues=0,
                last_updated=None,
                topics=topics,
                has_wiki=False,
                has_tests=False,
                has_ci=False
            )
        except Exception as e:
            print(f"[GitHub-仓库解析] {e}")
            return None
    
    def _analyze_contributions(
        self,
        username: str,
        repos: List[GitHubRepository]
    ) -> ContributionStats:
        """Analyze contribution patterns."""
        # This is simplified - real analysis would need GitHub API
        
        # Aggregate languages from repos
        languages = {}
        for repo in repos:
            if repo.language:
                languages[repo.language] = languages.get(repo.language, 0) + 1
        
        # Estimate activity based on repo count and stars
        total_stars = sum(r.stars for r in repos)
        total_forks = sum(r.forks for r in repos)
        
        # Estimate commits (rough approximation)
        estimated_commits = len(repos) * 50 + total_stars * 2
        
        # Calculate activity score
        activity_score = min(100.0, (len(repos) * 5 + total_stars * 0.5 + total_forks))
        
        return ContributionStats(
            total_commits=estimated_commits,
            total_prs=total_forks,  # Approximation
            total_issues=total_stars // 10,  # Approximation
            total_reviews=0,
            languages=languages,
            active_repos=len([r for r in repos if r.stars > 0 or r.forks > 0]),
            contribution_streak=0,
            recent_activity_score=activity_score
        )
    
    def _build_technical_profile(
        self,
        repos: List[GitHubRepository],
        contrib_stats: ContributionStats
    ) -> TechnicalProfile:
        """Build technical profile from repositories and contributions."""
        # Extract languages (sorted by frequency)
        sorted_langs = sorted(
            contrib_stats.languages.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        primary_languages = [lang for lang, _ in sorted_langs[:3]]
        secondary_languages = [lang for lang, _ in sorted_langs[3:8]]
        
        # Extract frameworks and tools from repo descriptions and topics
        frameworks = set()
        tools = set()
        domains = set()
        
        framework_keywords = {
            'react': 'React', 'vue': 'Vue', 'angular': 'Angular',
            'django': 'Django', 'flask': 'Flask', 'express': 'Express',
            'tensorflow': 'TensorFlow', 'pytorch': 'PyTorch',
            'spring': 'Spring', 'laravel': 'Laravel'
        }
        
        tool_keywords = {
            'docker': 'Docker', 'kubernetes': 'Kubernetes', 'k8s': 'Kubernetes',
            'jenkins': 'Jenkins', 'github-actions': 'GitHub Actions',
            'aws': 'AWS', 'azure': 'Azure', 'gcp': 'GCP',
            'mongodb': 'MongoDB', 'postgresql': 'PostgreSQL', 'redis': 'Redis'
        }
        
        domain_keywords = {
            'web': ['web', 'frontend', 'backend', 'fullstack'],
            'ml': ['machine-learning', 'ml', 'ai', 'deep-learning'],
            'data': ['data-science', 'data-analysis', 'analytics'],
            'mobile': ['android', 'ios', 'mobile', 'react-native'],
            'devops': ['devops', 'ci-cd', 'deployment', 'infrastructure']
        }
        
        for repo in repos:
            text = f"{repo.description} {' '.join(repo.topics)}".lower()
            
            # Extract frameworks
            for kw, name in framework_keywords.items():
                if kw in text:
                    frameworks.add(name)
            
            # Extract tools
            for kw, name in tool_keywords.items():
                if kw in text:
                    tools.add(name)
            
            # Extract domains
            for domain, keywords in domain_keywords.items():
                if any(kw in text for kw in keywords):
                    domains.add(domain.title())
        
        # Calculate code quality score (simplified)
        avg_stars = sum(r.stars for r in repos) / max(len(repos), 1)
        has_docs = sum(1 for r in repos if len(r.description) > 20) / max(len(repos), 1)
        code_quality_score = min(100.0, avg_stars * 10 + has_docs * 50)
        
        # Determine activity level
        if contrib_stats.recent_activity_score > 50:
            activity_level = "high"
        elif contrib_stats.recent_activity_score > 20:
            activity_level = "medium"
        else:
            activity_level = "low"
        
        # Calculate collaboration score
        avg_forks = sum(r.forks for r in repos) / max(len(repos), 1)
        collaboration_score = min(100.0, avg_forks * 20 + len(repos) * 2)
        
        return TechnicalProfile(
            primary_languages=primary_languages,
            secondary_languages=secondary_languages,
            frameworks=list(frameworks),
            tools=list(tools),
            domains=list(domains),
            code_quality_score=code_quality_score,
            activity_level=activity_level,
            collaboration_score=collaboration_score
        )
    
    def _assess_code_quality(
        self,
        username: str,
        repos: List[GitHubRepository]
    ) -> Dict[str, Any]:
        """Assess code quality (placeholder for deep analysis)."""
        # This would require cloning repos and analyzing code
        # Placeholder implementation
        return {
            "has_tests": "unknown",
            "has_ci": "unknown",
            "documentation_quality": "medium",
            "code_style": "unknown"
        }
    
    def _generate_summary(
        self,
        repos: List[GitHubRepository],
        contrib_stats: ContributionStats,
        tech_profile: TechnicalProfile
    ) -> str:
        """Generate human-readable summary."""
        parts = []
        
        # Repository summary
        parts.append(f"拥有 {len(repos)} 个公开仓库")
        
        # Stars summary
        total_stars = sum(r.stars for r in repos)
        if total_stars > 0:
            parts.append(f"获得 {total_stars} 个Star")
        
        # Language summary
        if tech_profile.primary_languages:
            langs = ", ".join(tech_profile.primary_languages)
            parts.append(f"主要使用 {langs}")
        
        # Domain summary
        if tech_profile.domains:
            domains = ", ".join(tech_profile.domains)
            parts.append(f"专注于 {domains} 领域")
        
        # Activity summary
        parts.append(f"活跃度: {tech_profile.activity_level}")
        
        return "；".join(parts) + "。"
    
    def _extract_number(self, text: str) -> int:
        """Extract number from text (handles K, M suffixes)."""
        text = text.strip().lower()
        
        match = re.search(r'([\d.]+)\s*([km])?', text)
        if not match:
            return 0
        
        num_str, suffix = match.groups()
        try:
            num = float(num_str)
            if suffix == 'k':
                num *= 1000
            elif suffix == 'm':
                num *= 1000000
            return int(num)
        except ValueError:
            return 0
    
    def _repo_to_dict(self, repo: GitHubRepository) -> Dict[str, Any]:
        """Convert repository to dictionary."""
        return {
            "name": repo.name,
            "url": repo.url,
            "description": repo.description,
            "language": repo.language,
            "stars": repo.stars,
            "forks": repo.forks,
            "topics": repo.topics
        }
    
    def _contrib_stats_to_dict(self, stats: ContributionStats) -> Dict[str, Any]:
        """Convert contribution stats to dictionary."""
        return {
            "total_commits": stats.total_commits,
            "total_prs": stats.total_prs,
            "languages": stats.languages,
            "active_repos": stats.active_repos,
            "recent_activity_score": round(stats.recent_activity_score, 2)
        }
    
    def _technical_profile_to_dict(self, profile: TechnicalProfile) -> Dict[str, Any]:
        """Convert technical profile to dictionary."""
        return {
            "primary_languages": profile.primary_languages,
            "secondary_languages": profile.secondary_languages,
            "frameworks": profile.frameworks,
            "tools": profile.tools,
            "domains": profile.domains,
            "code_quality_score": round(profile.code_quality_score, 2),
            "activity_level": profile.activity_level,
            "collaboration_score": round(profile.collaboration_score, 2)
        }


# Example usage
if __name__ == "__main__":
    analyzer = GitHubAnalyzer()
    
    # Test analysis
    print("Testing GitHub analyzer...")
    result = analyzer.analyze_profile("https://github.com/torvalds")
    
    if result:
        print(f"\nUsername: {result['username']}")
        print(f"Repositories: {len(result['repositories'])}")
        print(f"Summary: {result['summary']}")
        print(f"\nTechnical Profile:")
        tp = result['technical_profile']
        print(f"  Primary Languages: {', '.join(tp['primary_languages'])}")
        print(f"  Domains: {', '.join(tp['domains'])}")
        print(f"  Activity Level: {tp['activity_level']}")
