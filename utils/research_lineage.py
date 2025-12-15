#!/usr/bin/env python3
"""
Research Lineage and Trajectory Analyzer

This module analyzes:
1. Research Trajectory (研究脉络): Evolution of research topics over time
2. Research Lineage (学术谱系): Academic heritage from supervisors/mentors
3. Research Continuity: Consistency and evolution of research themes
4. Impact Trajectory: How research impact evolves over career stages

Author: WisdomEye Team
Date: 2025-12-15
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)


class ResearchLineageAnalyzer:
    """Analyzes research trajectory and academic lineage"""
    
    def __init__(self, llm_client=None):
        """
        Initialize analyzer
        
        Args:
            llm_client: LLM client for semantic analysis (optional)
        """
        self.llm = llm_client
        
        # Career stage definitions (years from PhD)
        self.career_stages = {
            "PhD Student": (0, 0),
            "Early Career": (0, 3),
            "Mid Career": (4, 8),
            "Established": (9, float('inf'))
        }
    
    def analyze(self, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive research lineage analysis
        
        Args:
            resume_data: Resume JSON data
            
        Returns:
            Dictionary containing complete lineage analysis
        """
        logger.info("Starting research lineage analysis...")
        
        result = {
            "academic_lineage": self._analyze_academic_lineage(resume_data),
            "research_trajectory": self._analyze_research_trajectory(resume_data),
            "topic_evolution": self._analyze_topic_evolution(resume_data),
            "collaboration_lineage": self._analyze_collaboration_lineage(resume_data),
            "impact_trajectory": self._analyze_impact_trajectory(resume_data),
            "continuity_score": 0.0,
            "coherence_assessment": "",
            "research_maturity": "",
            "lineage_strength": ""
        }
        
        # Calculate overall scores
        result["continuity_score"] = self._calculate_continuity_score(result)
        result["coherence_assessment"] = self._assess_coherence(result)
        result["research_maturity"] = self._assess_maturity(result)
        result["lineage_strength"] = self._assess_lineage_strength(result)
        
        logger.info("Research lineage analysis completed")
        return result
    
    def _analyze_academic_lineage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze academic heritage from supervisors and mentors
        
        Returns:
            Academic lineage information including supervisor influence
        """
        lineage = {
            "phd_supervisor": None,
            "postdoc_advisors": [],
            "supervisor_influence": "Unknown",
            "lineage_prestige": "Unknown",
            "inherited_topics": [],
            "divergence_topics": []
        }
        
        education = data.get("education", []) or data.get("Education", [])
        publications = data.get("publications", []) or data.get("Publications", [])
        network = data.get("network_graph", {})
        
        # Extract supervisors from education
        for edu in education:
            if not isinstance(edu, dict):
                continue
            
            degree = edu.get("degree", "").lower()
            advisor = edu.get("advisor") or edu.get("supervisor")
            
            if "ph.d" in degree or "phd" in degree or "博士" in degree:
                if advisor:
                    lineage["phd_supervisor"] = {
                        "name": advisor,
                        "institution": edu.get("institution", "Unknown"),
                        "year": self._extract_year(edu.get("end_date") or edu.get("date"))
                    }
            elif "postdoc" in degree.lower():
                if advisor:
                    lineage["postdoc_advisors"].append({
                        "name": advisor,
                        "institution": edu.get("institution", "Unknown"),
                        "year": self._extract_year(edu.get("end_date") or edu.get("date"))
                    })
        
        # Extract supervisors from network graph
        mentors = network.get("nodes", {}).get("mentors", [])
        if mentors and not lineage["phd_supervisor"]:
            for mentor in mentors:
                if isinstance(mentor, dict):
                    lineage["phd_supervisor"] = {
                        "name": mentor.get("name", "Unknown"),
                        "institution": mentor.get("affiliation", "Unknown"),
                        "year": None
                    }
                    break
        
        # Analyze supervisor influence on research topics
        if lineage["phd_supervisor"]:
            supervisor_name = lineage["phd_supervisor"]["name"]
            influence_analysis = self._analyze_supervisor_influence(
                supervisor_name, publications
            )
            lineage["supervisor_influence"] = influence_analysis["influence_level"]
            lineage["inherited_topics"] = influence_analysis["inherited_topics"]
            lineage["divergence_topics"] = influence_analysis["divergence_topics"]
        
        # Assess lineage prestige
        lineage["lineage_prestige"] = self._assess_lineage_prestige(lineage)
        
        return lineage
    
    def _analyze_research_trajectory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the evolution of research over time
        
        Returns:
            Research trajectory with career stages and evolution
        """
        trajectory = {
            "career_stages": [],
            "stage_transitions": [],
            "research_evolution": "",
            "consistency_level": "Unknown"
        }
        
        publications = data.get("publications", []) or data.get("Publications", [])
        if not publications:
            return trajectory
        
        # Sort publications by date
        sorted_pubs = self._sort_publications_by_date(publications)
        
        # Identify PhD completion year
        phd_year = self._get_phd_year(data)
        
        # Group publications by career stage
        stage_groups = self._group_by_career_stage(sorted_pubs, phd_year)
        
        # Analyze each stage
        for stage_name, pubs in stage_groups.items():
            if not pubs:
                continue
            
            stage_analysis = {
                "stage": stage_name,
                "years": self._get_year_range(pubs),
                "publication_count": len(pubs),
                "main_topics": self._extract_main_topics(pubs),
                "key_publications": self._identify_key_publications(pubs),
                "collaboration_pattern": self._analyze_collaboration_pattern(pubs, data)
            }
            trajectory["career_stages"].append(stage_analysis)
        
        # Analyze transitions between stages
        if len(trajectory["career_stages"]) > 1:
            trajectory["stage_transitions"] = self._analyze_stage_transitions(
                trajectory["career_stages"]
            )
        
        # Overall evolution narrative
        trajectory["research_evolution"] = self._generate_evolution_narrative(trajectory)
        trajectory["consistency_level"] = self._assess_consistency(trajectory)
        
        return trajectory
    
    def _analyze_topic_evolution(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze how research topics evolve over time
        
        Returns:
            Topic evolution analysis
        """
        evolution = {
            "topic_timeline": [],
            "emerging_topics": [],
            "sustained_topics": [],
            "abandoned_topics": [],
            "topic_diversity_trend": "Unknown"
        }
        
        publications = data.get("publications", []) or data.get("Publications", [])
        if not publications:
            return evolution
        
        sorted_pubs = self._sort_publications_by_date(publications)
        
        # Divide into time periods (2-year windows)
        time_periods = self._divide_into_periods(sorted_pubs, window_years=2)
        
        # Analyze topics in each period
        period_topics = []
        all_topics = set()
        
        for period_name, pubs in time_periods:
            topics = self._extract_topics_from_publications(pubs)
            period_topics.append({
                "period": period_name,
                "topics": topics,
                "pub_count": len(pubs)
            })
            all_topics.update(topics)
        
        evolution["topic_timeline"] = period_topics
        
        # Identify emerging, sustained, and abandoned topics
        if len(period_topics) >= 2:
            evolution["emerging_topics"] = self._identify_emerging_topics(period_topics)
            evolution["sustained_topics"] = self._identify_sustained_topics(period_topics)
            evolution["abandoned_topics"] = self._identify_abandoned_topics(period_topics)
        
        # Analyze diversity trend
        evolution["topic_diversity_trend"] = self._analyze_diversity_trend(period_topics)
        
        return evolution
    
    def _analyze_collaboration_lineage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze collaboration patterns and their evolution
        
        Returns:
            Collaboration lineage analysis
        """
        lineage = {
            "key_collaborators": [],
            "collaboration_timeline": [],
            "network_expansion": "Unknown",
            "independence_trajectory": "Unknown"
        }
        
        publications = data.get("publications", []) or data.get("Publications", [])
        network = data.get("network_graph", {})
        
        if not publications:
            return lineage
        
        # Extract coauthor relationships over time
        coauthor_timeline = self._build_coauthor_timeline(publications)
        lineage["collaboration_timeline"] = coauthor_timeline
        
        # Identify key long-term collaborators
        lineage["key_collaborators"] = self._identify_key_collaborators(publications)
        
        # Analyze network expansion
        lineage["network_expansion"] = self._analyze_network_expansion(coauthor_timeline)
        
        # Analyze independence trajectory (first author rate over time)
        lineage["independence_trajectory"] = self._analyze_independence_trajectory(publications)
        
        return lineage
    
    def _analyze_impact_trajectory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze how research impact evolves over career
        
        Returns:
            Impact trajectory analysis
        """
        trajectory = {
            "citation_trajectory": [],
            "venue_quality_trajectory": [],
            "h_index_growth": [],
            "impact_trend": "Unknown",
            "peak_impact_period": None
        }
        
        publications = data.get("publications", []) or data.get("Publications", [])
        metrics = data.get("scholar_metrics", {})
        
        if not publications:
            return trajectory
        
        sorted_pubs = self._sort_publications_by_date(publications)
        
        # Group by time periods
        time_periods = self._divide_into_periods(sorted_pubs, window_years=2)
        
        # Analyze impact metrics per period
        for period_name, pubs in time_periods:
            citations = sum(
                pub.get("citation_count", 0) 
                for pub in pubs 
                if isinstance(pub, dict)
            )
            
            avg_citations = citations / len(pubs) if pubs else 0
            
            venue_quality = self._assess_average_venue_quality(pubs)
            
            trajectory["citation_trajectory"].append({
                "period": period_name,
                "total_citations": citations,
                "avg_citations_per_paper": round(avg_citations, 1),
                "paper_count": len(pubs)
            })
            
            trajectory["venue_quality_trajectory"].append({
                "period": period_name,
                "avg_venue_quality": venue_quality,
                "top_venues": self._count_top_venues(pubs)
            })
        
        # Determine impact trend
        trajectory["impact_trend"] = self._determine_impact_trend(
            trajectory["citation_trajectory"]
        )
        
        # Identify peak impact period
        trajectory["peak_impact_period"] = self._identify_peak_period(
            trajectory["citation_trajectory"]
        )
        
        return trajectory
    
    # ============ Helper Methods ============
    
    def _extract_year(self, date_str: Any) -> Optional[int]:
        """Extract year from date string"""
        if not date_str:
            return None
        
        date_str = str(date_str)
        
        # Try to match YYYY
        match = re.search(r'\b(19|20)\d{2}\b', date_str)
        if match:
            return int(match.group(0))
        
        return None
    
    def _sort_publications_by_date(self, publications: List[Dict]) -> List[Dict]:
        """Sort publications by date (oldest first)"""
        def get_sort_key(pub):
            if not isinstance(pub, dict):
                return 9999
            year = self._extract_year(pub.get("date") or pub.get("year"))
            return year if year else 9999
        
        return sorted(publications, key=get_sort_key)
    
    def _get_phd_year(self, data: Dict[str, Any]) -> Optional[int]:
        """Get PhD completion year"""
        education = data.get("education", []) or data.get("Education", [])
        for edu in education:
            if not isinstance(edu, dict):
                continue
            degree = edu.get("degree", "").lower()
            if "ph.d" in degree or "phd" in degree or "博士" in degree:
                return self._extract_year(edu.get("end_date") or edu.get("date"))
        return None
    
    def _group_by_career_stage(
        self, 
        publications: List[Dict], 
        phd_year: Optional[int]
    ) -> Dict[str, List[Dict]]:
        """Group publications by career stage"""
        stage_groups = defaultdict(list)
        
        if not phd_year:
            # If no PhD year, use absolute time periods
            for pub in publications:
                year = self._extract_year(pub.get("date") or pub.get("year"))
                if not year:
                    continue
                
                if year <= 2015:
                    stage = "Early Period"
                elif year <= 2020:
                    stage = "Mid Period"
                else:
                    stage = "Recent Period"
                
                stage_groups[stage].append(pub)
        else:
            for pub in publications:
                year = self._extract_year(pub.get("date") or pub.get("year"))
                if not year:
                    continue
                
                years_since_phd = year - phd_year
                
                # Determine stage
                stage = "PhD Student"
                if years_since_phd < 0:
                    stage = "PhD Student"
                elif years_since_phd <= 3:
                    stage = "Early Career"
                elif years_since_phd <= 8:
                    stage = "Mid Career"
                else:
                    stage = "Established"
                
                stage_groups[stage].append(pub)
        
        return dict(stage_groups)
    
    def _get_year_range(self, pubs: List[Dict]) -> str:
        """Get year range for publications"""
        years = [
            self._extract_year(p.get("date") or p.get("year")) 
            for p in pubs if isinstance(p, dict)
        ]
        years = [y for y in years if y]
        
        if not years:
            return "Unknown"
        
        return f"{min(years)}-{max(years)}"
    
    def _extract_main_topics(self, pubs: List[Dict], top_n: int = 5) -> List[str]:
        """Extract main research topics from publications"""
        all_topics = []
        
        for pub in pubs:
            if not isinstance(pub, dict):
                continue
            
            # Extract from title and abstract
            title = pub.get("title", "")
            abstract = pub.get("abstract", "")
            
            topics = self._extract_topics_from_text(title + " " + abstract)
            all_topics.extend(topics)
        
        # Count and return top topics
        topic_counts = Counter(all_topics)
        return [topic for topic, _ in topic_counts.most_common(top_n)]
    
    def _extract_topics_from_text(self, text: str) -> List[str]:
        """Extract research topics from text using keyword matching"""
        if not text:
            return []
        
        text_lower = text.lower()
        topics = []
        
        # Common research topic keywords (expandable)
        topic_patterns = {
            "Machine Learning": ["machine learning", "ml", "deep learning", "neural network"],
            "Computer Vision": ["computer vision", "image recognition", "object detection", "cv"],
            "Natural Language Processing": ["nlp", "natural language", "language model", "text mining"],
            "Reinforcement Learning": ["reinforcement learning", "rl", "policy gradient", "q-learning"],
            "Graph Neural Networks": ["graph neural", "gnn", "graph learning", "node classification"],
            "Robotics": ["robot", "robotics", "manipulation", "motion planning"],
            "Medical AI": ["medical", "healthcare", "clinical", "diagnosis", "medical imaging"],
            "Autonomous Driving": ["autonomous", "self-driving", "vehicle", "driving"],
            "Speech Processing": ["speech", "audio", "voice", "acoustic"],
            "Recommendation Systems": ["recommendation", "recommender", "collaborative filtering"],
            "Information Retrieval": ["information retrieval", "search", "ranking", "retrieval"],
            "Security": ["security", "privacy", "adversarial", "attack", "defense"],
            "Optimization": ["optimization", "convex", "gradient descent", "solver"],
            "Transfer Learning": ["transfer learning", "domain adaptation", "few-shot"],
            "Generative Models": ["generative", "gan", "vae", "diffusion", "generation"],
        }
        
        for topic, keywords in topic_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def _identify_key_publications(self, pubs: List[Dict], top_n: int = 3) -> List[Dict]:
        """Identify key publications in a stage based on citations"""
        if not pubs:
            return []
        
        # Sort by citation count
        sorted_pubs = sorted(
            [p for p in pubs if isinstance(p, dict)],
            key=lambda p: p.get("citation_count", 0),
            reverse=True
        )
        
        key_pubs = []
        for pub in sorted_pubs[:top_n]:
            key_pubs.append({
                "title": pub.get("title", "Unknown"),
                "year": self._extract_year(pub.get("date") or pub.get("year")),
                "citations": pub.get("citation_count", 0),
                "venue": pub.get("venue", "Unknown")
            })
        
        return key_pubs
    
    def _analyze_collaboration_pattern(
        self, 
        pubs: List[Dict], 
        data: Dict[str, Any]
    ) -> str:
        """Analyze collaboration pattern in a stage"""
        if not pubs:
            return "Unknown"
        
        first_author_count = 0
        total_with_authors = 0
        
        candidate_name = self._get_candidate_name(data)
        
        for pub in pubs:
            if not isinstance(pub, dict):
                continue
            
            authors = pub.get("authors", [])
            if not authors:
                continue
            
            total_with_authors += 1
            
            # Check if first author
            if authors and isinstance(authors[0], str):
                if self._is_same_person(authors[0], candidate_name):
                    first_author_count += 1
        
        if total_with_authors == 0:
            return "Unknown"
        
        first_author_rate = first_author_count / total_with_authors
        
        if first_author_rate >= 0.7:
            return "Highly Independent"
        elif first_author_rate >= 0.4:
            return "Moderately Independent"
        else:
            return "Collaborative"
    
    def _get_candidate_name(self, data: Dict[str, Any]) -> str:
        """Get candidate's name"""
        personal = data.get("Personal Information", {})
        if isinstance(personal, dict):
            return personal.get("name", "")
        return ""
    
    def _is_same_person(self, name1: str, name2: str) -> bool:
        """Simple name matching (can be improved)"""
        if not name1 or not name2:
            return False
        
        name1 = name1.lower().strip()
        name2 = name2.lower().strip()
        
        return name1 == name2 or name1 in name2 or name2 in name1
    
    def _analyze_stage_transitions(self, stages: List[Dict]) -> List[Dict]:
        """Analyze transitions between career stages"""
        transitions = []
        
        for i in range(len(stages) - 1):
            current_stage = stages[i]
            next_stage = stages[i + 1]
            
            # Compare topics
            current_topics = set(current_stage.get("main_topics", []))
            next_topics = set(next_stage.get("main_topics", []))
            
            retained_topics = current_topics & next_topics
            new_topics = next_topics - current_topics
            dropped_topics = current_topics - next_topics
            
            transition = {
                "from_stage": current_stage["stage"],
                "to_stage": next_stage["stage"],
                "retained_topics": list(retained_topics),
                "new_topics": list(new_topics),
                "dropped_topics": list(dropped_topics),
                "continuity_rate": len(retained_topics) / len(current_topics) if current_topics else 0
            }
            
            transitions.append(transition)
        
        return transitions
    
    def _generate_evolution_narrative(self, trajectory: Dict) -> str:
        """Generate natural language narrative of research evolution"""
        stages = trajectory.get("career_stages", [])
        transitions = trajectory.get("stage_transitions", [])
        
        if not stages:
            return "Insufficient data to determine research evolution."
        
        narrative_parts = []
        
        # Start with first stage
        first_stage = stages[0]
        first_topics = first_stage.get("main_topics", [])
        narrative_parts.append(
            f"Started with focus on {', '.join(first_topics[:3])} during {first_stage['stage']} ({first_stage['years']})."
        )
        
        # Describe transitions
        for trans in transitions:
            retained = trans.get("retained_topics", [])
            new = trans.get("new_topics", [])
            
            if retained and new:
                narrative_parts.append(
                    f"Transitioned to {trans['to_stage']}, maintaining {', '.join(retained[:2])} "
                    f"while expanding into {', '.join(new[:2])}."
                )
            elif new:
                narrative_parts.append(
                    f"Shifted focus to {', '.join(new[:2])} in {trans['to_stage']}."
                )
            elif retained:
                narrative_parts.append(
                    f"Continued {', '.join(retained[:2])} in {trans['to_stage']}."
                )
        
        return " ".join(narrative_parts)
    
    def _assess_consistency(self, trajectory: Dict) -> str:
        """Assess research consistency level"""
        transitions = trajectory.get("stage_transitions", [])
        
        if not transitions:
            return "Unknown"
        
        avg_continuity = sum(t.get("continuity_rate", 0) for t in transitions) / len(transitions)
        
        if avg_continuity >= 0.7:
            return "Highly Consistent - Strong thematic continuity"
        elif avg_continuity >= 0.4:
            return "Moderately Consistent - Balanced continuity and exploration"
        else:
            return "Exploratory - Significant topic shifts"
    
    def _divide_into_periods(
        self, 
        publications: List[Dict], 
        window_years: int = 2
    ) -> List[Tuple[str, List[Dict]]]:
        """Divide publications into time periods"""
        if not publications:
            return []
        
        # Get year range
        years = [
            self._extract_year(p.get("date") or p.get("year")) 
            for p in publications if isinstance(p, dict)
        ]
        years = [y for y in years if y]
        
        if not years:
            return []
        
        min_year = min(years)
        max_year = max(years)
        
        periods = []
        current_year = min_year
        
        while current_year <= max_year:
            period_end = current_year + window_years - 1
            period_name = f"{current_year}-{period_end}"
            
            period_pubs = [
                p for p in publications
                if isinstance(p, dict)
                and current_year <= self._extract_year(p.get("date") or p.get("year", 9999)) <= period_end
            ]
            
            if period_pubs:
                periods.append((period_name, period_pubs))
            
            current_year += window_years
        
        return periods
    
    def _extract_topics_from_publications(self, pubs: List[Dict]) -> List[str]:
        """Extract all topics from a list of publications"""
        all_topics = []
        
        for pub in pubs:
            if not isinstance(pub, dict):
                continue
            
            title = pub.get("title", "")
            abstract = pub.get("abstract", "")
            topics = self._extract_topics_from_text(title + " " + abstract)
            all_topics.extend(topics)
        
        # Remove duplicates
        return list(set(all_topics))
    
    def _identify_emerging_topics(self, period_topics: List[Dict]) -> List[str]:
        """Identify topics that appear in later periods but not earlier"""
        if len(period_topics) < 2:
            return []
        
        # Topics in first half vs second half
        mid_point = len(period_topics) // 2
        early_topics = set()
        late_topics = set()
        
        for i, period in enumerate(period_topics):
            topics = set(period.get("topics", []))
            if i < mid_point:
                early_topics.update(topics)
            else:
                late_topics.update(topics)
        
        # Emerging = in late but not in early
        emerging = late_topics - early_topics
        return list(emerging)
    
    def _identify_sustained_topics(self, period_topics: List[Dict]) -> List[str]:
        """Identify topics that appear consistently across periods"""
        if len(period_topics) < 2:
            return []
        
        # Find topics present in most periods
        topic_frequency = defaultdict(int)
        
        for period in period_topics:
            topics = set(period.get("topics", []))
            for topic in topics:
                topic_frequency[topic] += 1
        
        # Sustained = present in at least 60% of periods
        threshold = len(period_topics) * 0.6
        sustained = [
            topic for topic, freq in topic_frequency.items()
            if freq >= threshold
        ]
        
        return sustained
    
    def _identify_abandoned_topics(self, period_topics: List[Dict]) -> List[str]:
        """Identify topics that appeared early but not in recent periods"""
        if len(period_topics) < 2:
            return []
        
        # Topics in first half vs second half
        mid_point = len(period_topics) // 2
        early_topics = set()
        late_topics = set()
        
        for i, period in enumerate(period_topics):
            topics = set(period.get("topics", []))
            if i < mid_point:
                early_topics.update(topics)
            else:
                late_topics.update(topics)
        
        # Abandoned = in early but not in late
        abandoned = early_topics - late_topics
        return list(abandoned)
    
    def _analyze_diversity_trend(self, period_topics: List[Dict]) -> str:
        """Analyze how topic diversity changes over time"""
        if len(period_topics) < 2:
            return "Unknown"
        
        # Count unique topics per period
        diversity_counts = [
            len(set(period.get("topics", [])))
            for period in period_topics
        ]
        
        # Compare early vs late diversity
        mid_point = len(diversity_counts) // 2
        early_avg = sum(diversity_counts[:mid_point]) / mid_point if mid_point > 0 else 0
        late_avg = sum(diversity_counts[mid_point:]) / (len(diversity_counts) - mid_point)
        
        if late_avg > early_avg * 1.2:
            return "Increasing - Expanding research breadth"
        elif late_avg < early_avg * 0.8:
            return "Decreasing - Focusing research scope"
        else:
            return "Stable - Consistent research breadth"
    
    def _build_coauthor_timeline(self, publications: List[Dict]) -> List[Dict]:
        """Build timeline of collaboration patterns"""
        sorted_pubs = self._sort_publications_by_date(publications)
        periods = self._divide_into_periods(sorted_pubs, window_years=3)
        
        timeline = []
        
        for period_name, pubs in periods:
            # Count unique coauthors
            coauthors = set()
            for pub in pubs:
                if isinstance(pub, dict):
                    authors = pub.get("authors", [])
                    coauthors.update(authors)
            
            timeline.append({
                "period": period_name,
                "unique_coauthors": len(coauthors),
                "publications": len(pubs)
            })
        
        return timeline
    
    def _identify_key_collaborators(self, publications: List[Dict], top_n: int = 5) -> List[Dict]:
        """Identify key long-term collaborators"""
        coauthor_counts = defaultdict(int)
        
        for pub in publications:
            if not isinstance(pub, dict):
                continue
            
            authors = pub.get("authors", [])
            for author in authors:
                if isinstance(author, str):
                    coauthor_counts[author] += 1
        
        # Sort by frequency
        sorted_coauthors = sorted(
            coauthor_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Return top N (excluding self - names with count >> others are likely self)
        max_count = sorted_coauthors[0][1] if sorted_coauthors else 0
        
        key_collaborators = []
        for name, count in sorted_coauthors[:top_n + 2]:
            # Skip if likely self (appears in >80% of papers)
            if count > max_count * 0.8:
                continue
            
            key_collaborators.append({
                "name": name,
                "collaboration_count": count
            })
            
            if len(key_collaborators) >= top_n:
                break
        
        return key_collaborators
    
    def _analyze_network_expansion(self, timeline: List[Dict]) -> str:
        """Analyze how collaboration network expands"""
        if len(timeline) < 2:
            return "Unknown"
        
        # Compare early vs late network size
        mid_point = len(timeline) // 2
        early_avg = sum(
            t.get("unique_coauthors", 0) 
            for t in timeline[:mid_point]
        ) / mid_point if mid_point > 0 else 0
        
        late_avg = sum(
            t.get("unique_coauthors", 0) 
            for t in timeline[mid_point:]
        ) / (len(timeline) - mid_point)
        
        if late_avg > early_avg * 1.5:
            return "Rapidly Expanding - Growing collaborative network"
        elif late_avg > early_avg * 1.1:
            return "Steadily Expanding - Moderate network growth"
        elif late_avg < early_avg * 0.8:
            return "Contracting - Focusing on core collaborators"
        else:
            return "Stable - Consistent collaboration network"
    
    def _analyze_independence_trajectory(self, publications: List[Dict]) -> str:
        """Analyze trajectory of research independence"""
        sorted_pubs = self._sort_publications_by_date(publications)
        periods = self._divide_into_periods(sorted_pubs, window_years=3)
        
        if len(periods) < 2:
            return "Unknown"
        
        independence_rates = []
        
        for period_name, pubs in periods:
            # Calculate first-author rate
            first_author_count = 0
            total = 0
            
            for pub in pubs:
                if not isinstance(pub, dict):
                    continue
                
                authors = pub.get("authors", [])
                if authors:
                    total += 1
                    # Simple heuristic: check if first author
                    # (More sophisticated logic needed for real implementation)
                    if len(authors) > 0:
                        first_author_count += 1  # Simplified
            
            rate = first_author_count / total if total > 0 else 0
            independence_rates.append(rate)
        
        # Analyze trend
        if len(independence_rates) >= 2:
            early_rate = sum(independence_rates[:len(independence_rates)//2]) / (len(independence_rates)//2)
            late_rate = sum(independence_rates[len(independence_rates)//2:]) / (len(independence_rates) - len(independence_rates)//2)
            
            if late_rate > early_rate + 0.2:
                return "Increasing Independence - Growing research autonomy"
            elif late_rate < early_rate - 0.2:
                return "Increasing Collaboration - More collaborative work"
            else:
                return "Stable Independence - Consistent authorship pattern"
        
        return "Unknown"
    
    def _assess_average_venue_quality(self, pubs: List[Dict]) -> str:
        """Assess average venue quality for publications"""
        if not pubs:
            return "Unknown"
        
        # Count venues by tier (if journal_tier metadata exists)
        tier_counts = defaultdict(int)
        
        for pub in pubs:
            if not isinstance(pub, dict):
                continue
            
            tier = pub.get("journal_tier", "Unknown")
            tier_counts[tier] += 1
        
        total = sum(tier_counts.values())
        
        if total == 0:
            return "Unknown"
        
        # Calculate weighted score
        t1_ratio = tier_counts.get("T1", 0) / total
        t2_ratio = tier_counts.get("T2", 0) / total
        
        if t1_ratio >= 0.5:
            return "Excellent (50%+ T1 venues)"
        elif t1_ratio + t2_ratio >= 0.7:
            return "Strong (70%+ T1/T2 venues)"
        elif t1_ratio + t2_ratio >= 0.4:
            return "Good (40%+ T1/T2 venues)"
        else:
            return "Moderate"
    
    def _count_top_venues(self, pubs: List[Dict]) -> int:
        """Count publications in top-tier venues"""
        count = 0
        for pub in pubs:
            if isinstance(pub, dict):
                tier = pub.get("journal_tier", "")
                if tier in ["T1", "T2"]:
                    count += 1
        return count
    
    def _determine_impact_trend(self, citation_trajectory: List[Dict]) -> str:
        """Determine overall impact trend"""
        if len(citation_trajectory) < 2:
            return "Unknown"
        
        # Compare early vs late citations per paper
        mid_point = len(citation_trajectory) // 2
        early_citations = [
            t.get("avg_citations_per_paper", 0) 
            for t in citation_trajectory[:mid_point]
        ]
        late_citations = [
            t.get("avg_citations_per_paper", 0) 
            for t in citation_trajectory[mid_point:]
        ]
        
        early_avg = sum(early_citations) / len(early_citations) if early_citations else 0
        late_avg = sum(late_citations) / len(late_citations) if late_citations else 0
        
        if late_avg > early_avg * 1.5:
            return "Rapidly Increasing - Growing research impact"
        elif late_avg > early_avg * 1.1:
            return "Steadily Increasing - Consistent impact growth"
        elif late_avg < early_avg * 0.7:
            return "Declining - Decreasing recent impact"
        else:
            return "Stable - Consistent research impact"
    
    def _identify_peak_period(self, citation_trajectory: List[Dict]) -> Optional[str]:
        """Identify period with highest impact"""
        if not citation_trajectory:
            return None
        
        max_citations = 0
        peak_period = None
        
        for period_data in citation_trajectory:
            citations = period_data.get("avg_citations_per_paper", 0)
            if citations > max_citations:
                max_citations = citations
                peak_period = period_data.get("period")
        
        return peak_period
    
    def _analyze_supervisor_influence(
        self, 
        supervisor_name: str, 
        publications: List[Dict]
    ) -> Dict[str, Any]:
        """Analyze supervisor's influence on candidate's research"""
        result = {
            "influence_level": "Unknown",
            "inherited_topics": [],
            "divergence_topics": []
        }
        
        # Count co-authored papers with supervisor
        coauthored_count = 0
        total_pubs = 0
        
        for pub in publications:
            if not isinstance(pub, dict):
                continue
            
            total_pubs += 1
            authors = pub.get("authors", [])
            
            if any(self._is_same_person(supervisor_name, str(author)) for author in authors):
                coauthored_count += 1
        
        if total_pubs == 0:
            return result
        
        coauthor_rate = coauthored_count / total_pubs
        
        # Assess influence level
        if coauthor_rate >= 0.5:
            result["influence_level"] = "Strong - High collaboration with supervisor"
        elif coauthor_rate >= 0.2:
            result["influence_level"] = "Moderate - Some continued collaboration"
        else:
            result["influence_level"] = "Low - Independent research direction"
        
        # TODO: More sophisticated topic inheritance analysis with LLM
        # For now, placeholder
        result["inherited_topics"] = ["To be analyzed with LLM"]
        result["divergence_topics"] = ["To be analyzed with LLM"]
        
        return result
    
    def _assess_lineage_prestige(self, lineage: Dict[str, Any]) -> str:
        """Assess prestige of academic lineage"""
        # Placeholder: This would require a database of prestigious advisors/institutions
        # For now, simple heuristic based on institution
        
        phd_supervisor = lineage.get("phd_supervisor")
        if not phd_supervisor:
            return "Unknown"
        
        institution = phd_supervisor.get("institution", "").lower()
        
        # Top institutions (simplified list)
        top_institutions = [
            "stanford", "mit", "berkeley", "harvard", "caltech",
            "princeton", "cmu", "cambridge", "oxford", "eth zurich"
        ]
        
        if any(top_inst in institution for top_inst in top_institutions):
            return "Prestigious - Top-tier institution lineage"
        else:
            return "Standard - Reputable institution lineage"
    
    def _calculate_continuity_score(self, analysis_result: Dict[str, Any]) -> float:
        """Calculate overall research continuity score (0-1)"""
        score = 0.0
        weights = []
        
        # Factor 1: Topic consistency
        trajectory = analysis_result.get("research_trajectory", {})
        consistency = trajectory.get("consistency_level", "Unknown")
        
        if "Highly Consistent" in consistency:
            score += 0.9
        elif "Moderately Consistent" in consistency:
            score += 0.6
        elif "Exploratory" in consistency:
            score += 0.3
        weights.append(1.0)
        
        # Factor 2: Sustained topics ratio
        topic_evolution = analysis_result.get("topic_evolution", {})
        sustained = len(topic_evolution.get("sustained_topics", []))
        total_topics = sustained + len(topic_evolution.get("emerging_topics", [])) + len(topic_evolution.get("abandoned_topics", []))
        
        if total_topics > 0:
            sustained_ratio = sustained / total_topics
            score += sustained_ratio
            weights.append(1.0)
        
        # Factor 3: Collaboration stability
        collab_lineage = analysis_result.get("collaboration_lineage", {})
        network_expansion = collab_lineage.get("network_expansion", "Unknown")
        
        if "Stable" in network_expansion or "Steadily" in network_expansion:
            score += 0.8
        elif "Rapidly" in network_expansion:
            score += 0.5
        weights.append(0.5)
        
        # Weighted average
        total_weight = sum(weights)
        return round(score / total_weight, 2) if total_weight > 0 else 0.0
    
    def _assess_coherence(self, analysis_result: Dict[str, Any]) -> str:
        """Assess overall research coherence"""
        continuity_score = analysis_result.get("continuity_score", 0)
        
        if continuity_score >= 0.8:
            return "Highly Coherent - Clear, consistent research program with strong thematic unity"
        elif continuity_score >= 0.6:
            return "Coherent - Well-defined research direction with controlled exploration"
        elif continuity_score >= 0.4:
            return "Moderately Coherent - Multiple research threads with some connection"
        else:
            return "Exploratory - Diverse research interests without clear unifying theme"
    
    def _assess_maturity(self, analysis_result: Dict[str, Any]) -> str:
        """Assess research maturity level"""
        trajectory = analysis_result.get("research_trajectory", {})
        stages = trajectory.get("career_stages", [])
        
        impact_traj = analysis_result.get("impact_trajectory", {})
        impact_trend = impact_traj.get("impact_trend", "Unknown")
        
        collab = analysis_result.get("collaboration_lineage", {})
        independence = collab.get("independence_trajectory", "Unknown")
        
        # Maturity indicators
        maturity_score = 0
        
        # Multiple career stages covered
        if len(stages) >= 3:
            maturity_score += 1
        
        # Increasing or stable impact
        if "Increasing" in impact_trend or "Stable" in impact_trend:
            maturity_score += 1
        
        # Increasing independence
        if "Increasing Independence" in independence:
            maturity_score += 1
        
        # Assessment
        if maturity_score >= 3:
            return "Mature - Established independent researcher with sustained impact"
        elif maturity_score >= 2:
            return "Developing - Emerging researcher showing growth trajectory"
        else:
            return "Early Stage - Building research foundation"
    
    def _assess_lineage_strength(self, analysis_result: Dict[str, Any]) -> str:
        """Assess strength of academic lineage"""
        lineage = analysis_result.get("academic_lineage", {})
        
        has_supervisor = lineage.get("phd_supervisor") is not None
        prestige = lineage.get("lineage_prestige", "Unknown")
        influence = lineage.get("supervisor_influence", "Unknown")
        
        if has_supervisor and "Prestigious" in prestige:
            return "Strong - Prestigious lineage with significant influence"
        elif has_supervisor and "Moderate" in influence:
            return "Moderate - Established lineage with balanced independence"
        elif has_supervisor:
            return "Established - Clear academic lineage"
        else:
            return "Unknown - Insufficient lineage information"


# ============ Standalone Testing ============
if __name__ == "__main__":
    # Test with sample data
    sample_data = {
        "Personal Information": {"name": "John Doe"},
        "Education": [
            {
                "degree": "Ph.D. in Computer Science",
                "institution": "Stanford University",
                "advisor": "Andrew Ng",
                "end_date": "2015-06"
            }
        ],
        "Publications": [
            {
                "title": "Deep Learning for Computer Vision",
                "date": "2014-01",
                "authors": ["John Doe", "Andrew Ng"],
                "citation_count": 150,
                "venue": "CVPR 2014",
                "abstract": "We present a novel deep learning approach for computer vision tasks."
            },
            {
                "title": "Neural Networks for Image Classification",
                "date": "2016-03",
                "authors": ["John Doe", "Jane Smith"],
                "citation_count": 200,
                "venue": "ICCV 2016",
                "abstract": "This work explores neural networks for robust image classification."
            },
            {
                "title": "Transfer Learning in Computer Vision",
                "date": "2018-05",
                "authors": ["John Doe"],
                "citation_count": 300,
                "venue": "ECCV 2018",
                "abstract": "We investigate transfer learning techniques for computer vision applications."
            }
        ],
        "network_graph": {
            "nodes": {
                "mentors": [{"name": "Andrew Ng", "affiliation": "Stanford University"}]
            }
        }
    }
    
    analyzer = ResearchLineageAnalyzer()
    result = analyzer.analyze(sample_data)
    
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
