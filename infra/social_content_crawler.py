"""
Social Content Crawler

This module provides deep content analysis for social media platforms.
Crawls and analyzes content from Zhihu, GitHub, LinkedIn, and other platforms
to provide sentiment analysis, topic extraction, and influence metrics.

Features:
- Platform-specific crawlers (Zhihu, GitHub, LinkedIn, etc.)
- Content extraction and cleaning
- Sentiment analysis
- Topic extraction
- Engagement metrics calculation
- Activity timeline analysis

Author: WisdomEye Team
Date: 2025-12-12
"""

import re
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import json

from .observability import emit


@dataclass
class SocialPost:
    """Represents a social media post with metadata."""
    platform: str
    url: str
    title: str
    content: str
    author: str
    publish_date: Optional[str]
    views: int
    likes: int
    comments: int
    tags: List[str]
    
    def engagement_score(self) -> float:
        """Calculate engagement score based on metrics."""
        # Weighted engagement score
        return (self.views * 0.1) + (self.likes * 2.0) + (self.comments * 3.0)


@dataclass
class ContentAnalysis:
    """Results of content analysis."""
    sentiment: str  # positive, negative, neutral
    sentiment_score: float  # -1.0 to 1.0
    topics: List[str]
    keywords: List[str]
    technical_depth: str  # shallow, medium, deep
    originality: str  # low, medium, high
    

class SocialContentCrawler:
    """
    Multi-platform social content crawler with deep analysis.
    
    Supports:
    - Zhihu (知乎): Articles, answers, columns
    - GitHub: Repositories, contributions, issues
    - LinkedIn: Posts, articles
    - Medium/Blog: Technical blog posts
    """
    
    def __init__(self, timeout: float = 10.0, max_posts: int = 20):
        """
        Initialize crawler.
        
        Args:
            timeout: Request timeout in seconds
            max_posts: Maximum posts to crawl per platform
        """
        self.timeout = timeout
        self.max_posts = max_posts
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def crawl_profile(
        self,
        platform: str,
        profile_url: str,
        max_posts: Optional[int] = None
    ) -> List[SocialPost]:
        """
        Crawl social media profile for content.
        
        Args:
            platform: Platform name (zhihu, github, linkedin, etc.)
            profile_url: Profile URL
            max_posts: Maximum posts to fetch (overrides default)
            
        Returns:
            List of SocialPost objects
        """
        emit({
            "kind": "social_crawl_start",
            "platform": platform,
            "url": profile_url
        })
        
        max_posts = max_posts or self.max_posts
        platform_lower = platform.lower()
        
        try:
            if "zhihu" in platform_lower or "知乎" in platform_lower:
                posts = self._crawl_zhihu(profile_url, max_posts)
            elif "github" in platform_lower:
                posts = self._crawl_github(profile_url, max_posts)
            elif "linkedin" in platform_lower:
                posts = self._crawl_linkedin(profile_url, max_posts)
            elif "medium" in platform_lower or "blog" in platform_lower:
                posts = self._crawl_blog(profile_url, max_posts)
            else:
                print(f"[社交爬虫-警告] 不支持的平台: {platform}")
                posts = []
            
            emit({
                "kind": "social_crawl_end",
                "platform": platform,
                "posts_count": len(posts)
            })
            
            return posts
            
        except Exception as e:
            emit({
                "kind": "social_crawl_error",
                "platform": platform,
                "error": str(e)
            })
            print(f"[社交爬虫-错误] {platform}: {e}")
            return []
    
    def _crawl_zhihu(self, profile_url: str, max_posts: int) -> List[SocialPost]:
        """
        Crawl Zhihu profile for articles and answers.
        
        Note: Zhihu has anti-scraping measures, so this is a best-effort approach.
        """
        posts = []
        
        try:
            # Try to fetch profile page
            response = self.session.get(profile_url, timeout=self.timeout)
            if response.status_code != 200:
                print(f"[知乎爬虫-警告] HTTP {response.status_code}")
                return posts
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract articles and answers
            # Note: Zhihu structure changes frequently, this is a simplified approach
            content_items = soup.find_all('div', class_=re.compile('(ContentItem|List-item)'))
            
            for item in content_items[:max_posts]:
                try:
                    post = self._parse_zhihu_item(item, profile_url)
                    if post:
                        posts.append(post)
                except Exception as e:
                    print(f"[知乎解析-错误] {e}")
                    continue
            
            # If no items found with class selectors, try alternative parsing
            if not posts:
                posts = self._parse_zhihu_alternative(soup, profile_url, max_posts)
            
        except Exception as e:
            print(f"[知乎爬虫-错误] {e}")
        
        return posts
    
    def _parse_zhihu_item(self, item, base_url: str) -> Optional[SocialPost]:
        """Parse a single Zhihu content item."""
        try:
            # Extract title
            title_elem = item.find(['h2', 'a'], class_=re.compile('(ContentItem-title|question_link)'))
            title = title_elem.get_text(strip=True) if title_elem else "无标题"
            
            # Extract link
            link_elem = item.find('a', href=True)
            url = link_elem['href'] if link_elem else base_url
            if url.startswith('/'):
                url = 'https://www.zhihu.com' + url
            
            # Extract content preview
            content_elem = item.find('div', class_=re.compile('(RichContent|ContentItem-meta)'))
            content = content_elem.get_text(strip=True)[:500] if content_elem else ""
            
            # Extract metrics
            vote_elem = item.find('button', class_=re.compile('VoteButton'))
            likes = self._extract_number(vote_elem.get_text() if vote_elem else "0")
            
            comment_elem = item.find('button', class_=re.compile('Button.*comment'))
            comments = self._extract_number(comment_elem.get_text() if comment_elem else "0")
            
            return SocialPost(
                platform="知乎",
                url=url,
                title=title,
                content=content,
                author="",
                publish_date=None,
                views=0,  # Zhihu doesn't always show views
                likes=likes,
                comments=comments,
                tags=[]
            )
        except Exception:
            return None
    
    def _parse_zhihu_alternative(self, soup, base_url: str, max_posts: int) -> List[SocialPost]:
        """Alternative Zhihu parsing method."""
        posts = []
        
        # Try to extract from script tags (Zhihu often embeds data in JSON)
        script_tags = soup.find_all('script', type='text/json')
        for script in script_tags:
            try:
                data = json.loads(script.string)
                # Simplified extraction - would need more logic for real data
                if isinstance(data, dict) and 'data' in data:
                    # This is placeholder - actual structure varies
                    pass
            except Exception:
                continue
        
        return posts
    
    def _crawl_github(self, profile_url: str, max_posts: int) -> List[SocialPost]:
        """
        Crawl GitHub profile for repositories and activity.
        
        Note: For real usage, should use GitHub API with authentication.
        """
        posts = []
        
        try:
            # Extract username from URL
            username = profile_url.rstrip('/').split('/')[-1]
            
            # Fetch user's repositories page
            repos_url = f"https://github.com/{username}?tab=repositories"
            response = self.session.get(repos_url, timeout=self.timeout)
            
            if response.status_code != 200:
                print(f"[GitHub爬虫-警告] HTTP {response.status_code}")
                return posts
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find repository list items
            repo_items = soup.find_all('div', {'class': re.compile('col-')}, limit=max_posts)
            
            for item in repo_items:
                try:
                    post = self._parse_github_repo(item, username)
                    if post:
                        posts.append(post)
                except Exception as e:
                    print(f"[GitHub解析-错误] {e}")
                    continue
            
        except Exception as e:
            print(f"[GitHub爬虫-错误] {e}")
        
        return posts
    
    def _parse_github_repo(self, item, username: str) -> Optional[SocialPost]:
        """Parse a GitHub repository item."""
        try:
            # Extract repo name and link
            link_elem = item.find('a', href=re.compile(f'/{username}/'))
            if not link_elem:
                return None
            
            repo_name = link_elem.get_text(strip=True)
            repo_url = 'https://github.com' + link_elem['href']
            
            # Extract description
            desc_elem = item.find('p', class_=re.compile('(description|color-fg-muted)'))
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            
            # Extract stars
            star_elem = item.find('a', href=re.compile('/stargazers'))
            stars = self._extract_number(star_elem.get_text() if star_elem else "0")
            
            # Extract forks
            fork_elem = item.find('a', href=re.compile('/forks'))
            forks = self._extract_number(fork_elem.get_text() if fork_elem else "0")
            
            # Extract language
            lang_elem = item.find('span', {'itemprop': 'programmingLanguage'})
            language = lang_elem.get_text(strip=True) if lang_elem else ""
            
            tags = [language] if language else []
            
            return SocialPost(
                platform="GitHub",
                url=repo_url,
                title=repo_name,
                content=description,
                author=username,
                publish_date=None,
                views=0,
                likes=stars,
                comments=forks,
                tags=tags
            )
        except Exception:
            return None
    
    def _crawl_linkedin(self, profile_url: str, max_posts: int) -> List[SocialPost]:
        """
        Crawl LinkedIn profile.
        
        Note: LinkedIn has strict anti-scraping measures and requires authentication.
        This is a placeholder for demonstration.
        """
        print("[LinkedIn爬虫] LinkedIn需要认证，暂不支持爬取")
        return []
    
    def _crawl_blog(self, profile_url: str, max_posts: int) -> List[SocialPost]:
        """
        Crawl blog/Medium articles.
        
        Generic blog crawler for personal blogs and Medium.
        """
        posts = []
        
        try:
            response = self.session.get(profile_url, timeout=self.timeout)
            if response.status_code != 200:
                return posts
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try common blog structures
            article_tags = soup.find_all(['article', 'div'], class_=re.compile('(post|article|entry)'), limit=max_posts)
            
            for article in article_tags:
                try:
                    post = self._parse_blog_article(article, profile_url)
                    if post:
                        posts.append(post)
                except Exception:
                    continue
            
        except Exception as e:
            print(f"[博客爬虫-错误] {e}")
        
        return posts
    
    def _parse_blog_article(self, article, base_url: str) -> Optional[SocialPost]:
        """Parse a blog article."""
        try:
            # Extract title
            title_elem = article.find(['h1', 'h2', 'h3', 'a'])
            title = title_elem.get_text(strip=True) if title_elem else "无标题"
            
            # Extract link
            link_elem = article.find('a', href=True)
            url = link_elem['href'] if link_elem else base_url
            if url.startswith('/'):
                url = base_url.rstrip('/') + url
            
            # Extract content
            content_elem = article.find(['p', 'div'], class_=re.compile('(content|excerpt|summary)'))
            content = content_elem.get_text(strip=True)[:500] if content_elem else ""
            
            return SocialPost(
                platform="Blog",
                url=url,
                title=title,
                content=content,
                author="",
                publish_date=None,
                views=0,
                likes=0,
                comments=0,
                tags=[]
            )
        except Exception:
            return None
    
    def _extract_number(self, text: str) -> int:
        """Extract number from text (handles K, M suffixes)."""
        text = text.strip().lower()
        
        # Remove non-numeric characters except k, m
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


class ContentAnalyzer:
    """
    Analyzes social media content for sentiment, topics, and quality.
    """
    
    def __init__(self):
        """Initialize analyzer."""
        # Technical keywords for depth analysis
        self.technical_keywords = {
            'deep': [
                'algorithm', 'architecture', 'optimization', 'implementation',
                'complexity', 'theorem', 'proof', 'methodology', 'framework',
                '算法', '架构', '优化', '实现', '复杂度', '定理', '证明', '方法论'
            ],
            'medium': [
                'tutorial', 'guide', 'introduction', 'overview', 'concept',
                '教程', '指南', '入门', '概述', '概念'
            ]
        }
        
        # Sentiment keywords (simplified)
        self.positive_keywords = [
            'excellent', 'great', 'good', 'amazing', 'fantastic', 'love',
            '优秀', '很好', '出色', '棒', '喜欢', '赞'
        ]
        self.negative_keywords = [
            'bad', 'poor', 'terrible', 'hate', 'worst', 'disappointed',
            '差', '糟糕', '失望', '不好'
        ]
    
    def analyze(self, post: SocialPost) -> ContentAnalysis:
        """
        Analyze a social post for sentiment, topics, and quality.
        
        Args:
            post: SocialPost object
            
        Returns:
            ContentAnalysis object
        """
        text = f"{post.title} {post.content}".lower()
        
        # Sentiment analysis
        sentiment, sentiment_score = self._analyze_sentiment(text)
        
        # Topic extraction
        topics = self._extract_topics(text)
        
        # Keyword extraction
        keywords = self._extract_keywords(text)
        
        # Technical depth
        technical_depth = self._assess_technical_depth(text)
        
        # Originality assessment (simplified based on engagement)
        originality = self._assess_originality(post)
        
        return ContentAnalysis(
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            topics=topics,
            keywords=keywords,
            technical_depth=technical_depth,
            originality=originality
        )
    
    def _analyze_sentiment(self, text: str) -> tuple[str, float]:
        """Simple sentiment analysis."""
        pos_count = sum(1 for kw in self.positive_keywords if kw in text)
        neg_count = sum(1 for kw in self.negative_keywords if kw in text)
        
        if pos_count > neg_count:
            sentiment = "positive"
            score = min(1.0, pos_count * 0.2)
        elif neg_count > pos_count:
            sentiment = "negative"
            score = max(-1.0, -neg_count * 0.2)
        else:
            sentiment = "neutral"
            score = 0.0
        
        return sentiment, score
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from text."""
        topics = []
        
        # Common technical topics
        topic_keywords = {
            'Machine Learning': ['machine learning', 'ml', '机器学习'],
            'Deep Learning': ['deep learning', 'neural network', '深度学习', '神经网络'],
            'Computer Vision': ['computer vision', 'cv', 'image', '计算机视觉'],
            'NLP': ['nlp', 'natural language', 'text', '自然语言'],
            'Data Science': ['data science', 'analytics', '数据科学', '数据分析'],
            'Software Engineering': ['software', 'engineering', 'development', '软件工程'],
            'Web Development': ['web', 'frontend', 'backend', 'fullstack', 'Web开发'],
            'Cloud Computing': ['cloud', 'aws', 'azure', 'gcp', '云计算'],
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in text for kw in keywords):
                topics.append(topic)
        
        return topics
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords."""
        # Simplified keyword extraction
        words = re.findall(r'\b\w{4,}\b', text)
        word_freq = {}
        for word in words:
            if word not in ['this', 'that', 'with', 'from', 'have']:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return top 10 keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:10]]
    
    def _assess_technical_depth(self, text: str) -> str:
        """Assess technical depth of content."""
        deep_count = sum(1 for kw in self.technical_keywords['deep'] if kw in text)
        medium_count = sum(1 for kw in self.technical_keywords['medium'] if kw in text)
        
        if deep_count >= 3:
            return "deep"
        elif medium_count >= 2 or deep_count >= 1:
            return "medium"
        else:
            return "shallow"
    
    def _assess_originality(self, post: SocialPost) -> str:
        """Assess originality based on engagement."""
        engagement = post.engagement_score()
        
        if engagement > 1000:
            return "high"
        elif engagement > 100:
            return "medium"
        else:
            return "low"


# Example usage
if __name__ == "__main__":
    crawler = SocialContentCrawler()
    analyzer = ContentAnalyzer()
    
    # Test GitHub crawling
    print("Testing GitHub crawler...")
    posts = crawler.crawl_profile("GitHub", "https://github.com/torvalds", max_posts=5)
    print(f"Found {len(posts)} GitHub repositories")
    
    for post in posts[:3]:
        print(f"\nTitle: {post.title}")
        print(f"URL: {post.url}")
        print(f"Stars: {post.likes}, Forks: {post.comments}")
        
        analysis = analyzer.analyze(post)
        print(f"Technical Depth: {analysis.technical_depth}")
        print(f"Topics: {', '.join(analysis.topics)}")
