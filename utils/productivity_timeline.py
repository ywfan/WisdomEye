#!/usr/bin/env python3
"""
Productivity Timeline Analyzer

This module analyzes researcher's productivity over time, including:
1. Publication Timeline: Annual publication trends
2. Citation Timeline: Citation accumulation over time
3. Productivity Patterns: Peak periods and productivity cycles
4. Quality-Quantity Balance: Balance between output volume and impact
5. Productivity Prediction: Trend analysis and future predictions

Author: WisdomEye Team
Date: 2025-12-15
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class ProductivityTimelineAnalyzer:
    """Analyzes researcher's productivity timeline and trends"""
    
    def __init__(self):
        """Initialize analyzer"""
        pass
    
    def analyze(self, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive productivity timeline analysis
        
        Args:
            resume_data: Resume JSON data
            
        Returns:
            Dictionary containing complete productivity analysis
        """
        logger.info("Starting productivity timeline analysis...")
        
        result = {
            "publication_timeline": self._analyze_publication_timeline(resume_data),
            "citation_timeline": self._analyze_citation_timeline(resume_data),
            "productivity_patterns": self._analyze_productivity_patterns(resume_data),
            "quality_quantity_balance": self._analyze_quality_quantity_balance(resume_data),
            "venue_distribution_timeline": self._analyze_venue_timeline(resume_data),
            "collaboration_timeline": self._analyze_collaboration_timeline(resume_data),
            "productivity_score": 0.0,
            "trend_assessment": "",
            "peak_productivity_period": None,
            "recent_trend": "",
            "prediction": {}
        }
        
        # Calculate overall metrics
        result["productivity_score"] = self._calculate_productivity_score(result)
        result["trend_assessment"] = self._assess_overall_trend(result)
        result["peak_productivity_period"] = self._identify_peak_period(result)
        result["recent_trend"] = self._assess_recent_trend(result)
        result["prediction"] = self._predict_future_productivity(result)
        
        logger.info("Productivity timeline analysis completed")
        return result
    
    def _analyze_publication_timeline(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze publication timeline year by year
        
        Returns:
            Publication timeline with annual statistics
        """
        timeline = {
            "annual_counts": [],
            "total_publications": 0,
            "active_years": 0,
            "avg_per_year": 0.0,
            "publication_gaps": [],
            "growth_rate": "Unknown"
        }
        
        publications = data.get("publications", []) or data.get("Publications", [])
        if not publications:
            return timeline
        
        # Group publications by year
        year_counts = defaultdict(int)
        
        for pub in publications:
            if not isinstance(pub, dict):
                continue
            
            year = self._extract_year(pub.get("date") or pub.get("year"))
            if year:
                year_counts[year] += 1
        
        if not year_counts:
            return timeline
        
        # Sort by year
        sorted_years = sorted(year_counts.keys())
        min_year = sorted_years[0]
        max_year = sorted_years[-1]
        
        # Build complete timeline (including zero-publication years)
        for year in range(min_year, max_year + 1):
            count = year_counts.get(year, 0)
            timeline["annual_counts"].append({
                "year": year,
                "count": count
            })
        
        # Calculate statistics
        timeline["total_publications"] = sum(year_counts.values())
        timeline["active_years"] = len([y for y in year_counts.values() if y > 0])
        
        year_span = max_year - min_year + 1
        timeline["avg_per_year"] = round(
            timeline["total_publications"] / year_span, 2
        ) if year_span > 0 else 0.0
        
        # Identify publication gaps (years with zero publications)
        gaps = []
        for i, year_data in enumerate(timeline["annual_counts"]):
            if year_data["count"] == 0:
                gaps.append(year_data["year"])
        
        timeline["publication_gaps"] = gaps
        
        # Calculate growth rate
        timeline["growth_rate"] = self._calculate_growth_rate(timeline["annual_counts"])
        
        return timeline
    
    def _analyze_citation_timeline(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze citation accumulation over time
        
        Returns:
            Citation timeline with annual statistics
        """
        timeline = {
            "annual_citations": [],
            "total_citations": 0,
            "cumulative_citations": [],
            "citation_growth_rate": "Unknown",
            "h_index_growth": []
        }
        
        publications = data.get("publications", []) or data.get("Publications", [])
        if not publications:
            return timeline
        
        # Group citations by publication year
        year_citations = defaultdict(int)
        
        for pub in publications:
            if not isinstance(pub, dict):
                continue
            
            year = self._extract_year(pub.get("date") or pub.get("year"))
            citations = pub.get("citation_count", 0)
            
            if year:
                year_citations[year] += citations
        
        if not year_citations:
            return timeline
        
        # Sort by year
        sorted_years = sorted(year_citations.keys())
        
        # Build timeline
        cumulative = 0
        for year in sorted_years:
            citations = year_citations[year]
            cumulative += citations
            
            timeline["annual_citations"].append({
                "year": year,
                "new_citations": citations
            })
            
            timeline["cumulative_citations"].append({
                "year": year,
                "total_citations": cumulative
            })
        
        timeline["total_citations"] = cumulative
        
        # Calculate citation growth rate
        timeline["citation_growth_rate"] = self._calculate_growth_rate(
            timeline["annual_citations"], 
            value_key="new_citations"
        )
        
        # H-index growth (simplified calculation)
        timeline["h_index_growth"] = self._calculate_h_index_growth(data)
        
        return timeline
    
    def _analyze_productivity_patterns(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze productivity patterns and cycles
        
        Returns:
            Productivity pattern analysis
        """
        patterns = {
            "peak_years": [],
            "low_years": [],
            "productivity_variance": "Unknown",
            "consistency_level": "Unknown",
            "publication_rhythm": "Unknown"
        }
        
        publications = data.get("publications", []) or data.get("Publications", [])
        if not publications:
            return patterns
        
        # Get annual counts
        year_counts = defaultdict(int)
        for pub in publications:
            if isinstance(pub, dict):
                year = self._extract_year(pub.get("date") or pub.get("year"))
                if year:
                    year_counts[year] += 1
        
        if not year_counts:
            return patterns
        
        counts = list(year_counts.values())
        avg_count = sum(counts) / len(counts) if counts else 0
        
        # Identify peak and low years
        for year, count in year_counts.items():
            if count >= avg_count * 1.5:
                patterns["peak_years"].append({"year": year, "count": count})
            elif count <= avg_count * 0.5 and count > 0:
                patterns["low_years"].append({"year": year, "count": count})
        
        # Sort by year
        patterns["peak_years"].sort(key=lambda x: x["year"])
        patterns["low_years"].sort(key=lambda x: x["year"])
        
        # Calculate variance
        if len(counts) > 1:
            variance = sum((c - avg_count) ** 2 for c in counts) / len(counts)
            std_dev = variance ** 0.5
            cv = (std_dev / avg_count) if avg_count > 0 else 0
            
            if cv < 0.3:
                patterns["productivity_variance"] = "Low - Highly consistent output"
            elif cv < 0.6:
                patterns["productivity_variance"] = "Moderate - Some variation in output"
            else:
                patterns["productivity_variance"] = "High - Significant variation in output"
            
            # Consistency level
            if cv < 0.4:
                patterns["consistency_level"] = "高度一致"
            elif cv < 0.7:
                patterns["consistency_level"] = "中等一致"
            else:
                patterns["consistency_level"] = "波动较大"
        
        # Publication rhythm
        patterns["publication_rhythm"] = self._analyze_publication_rhythm(year_counts)
        
        return patterns
    
    def _analyze_quality_quantity_balance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze balance between publication quantity and quality
        
        Returns:
            Quality-quantity balance assessment
        """
        balance = {
            "quantity_score": 0.0,
            "quality_score": 0.0,
            "balance_score": 0.0,
            "balance_assessment": "Unknown",
            "annual_quality_metrics": []
        }
        
        publications = data.get("publications", []) or data.get("Publications", [])
        if not publications:
            return balance
        
        # Group publications by year
        year_pubs = defaultdict(list)
        for pub in publications:
            if isinstance(pub, dict):
                year = self._extract_year(pub.get("date") or pub.get("year"))
                if year:
                    year_pubs[year].append(pub)
        
        # Analyze each year
        for year in sorted(year_pubs.keys()):
            pubs = year_pubs[year]
            
            # Quantity
            quantity = len(pubs)
            
            # Quality indicators
            avg_citations = sum(p.get("citation_count", 0) for p in pubs) / len(pubs)
            top_tier_count = sum(
                1 for p in pubs 
                if p.get("journal_tier") in ["T1", "T2"]
            )
            top_tier_ratio = top_tier_count / len(pubs) if pubs else 0
            
            # Quality score (0-10)
            quality_score = min(10, avg_citations / 10 + top_tier_ratio * 5)
            
            balance["annual_quality_metrics"].append({
                "year": year,
                "quantity": quantity,
                "avg_citations": round(avg_citations, 1),
                "quality_score": round(quality_score, 1),
                "top_tier_ratio": round(top_tier_ratio, 2)
            })
        
        # Overall scores
        if balance["annual_quality_metrics"]:
            balance["quantity_score"] = sum(
                m["quantity"] for m in balance["annual_quality_metrics"]
            ) / len(balance["annual_quality_metrics"])
            
            balance["quality_score"] = sum(
                m["quality_score"] for m in balance["annual_quality_metrics"]
            ) / len(balance["annual_quality_metrics"])
            
            # Balance score: How well quantity and quality are balanced
            # Ideal is high in both dimensions
            balance["balance_score"] = round(
                (balance["quantity_score"] * balance["quality_score"]) ** 0.5, 2
            )
        
        # Assessment
        q_score = balance["quantity_score"]
        ql_score = balance["quality_score"]
        
        if q_score >= 3 and ql_score >= 7:
            balance["balance_assessment"] = "优秀 - 高产出且高质量"
        elif q_score >= 2 and ql_score >= 5:
            balance["balance_assessment"] = "良好 - 产出与影响力平衡"
        elif q_score >= 3 and ql_score < 5:
            balance["balance_assessment"] = "数量导向 - 高产出，中等影响力"
        elif q_score < 2 and ql_score >= 7:
            balance["balance_assessment"] = "质量导向 - 精选高影响力论文"
        else:
            balance["balance_assessment"] = "发展中 - 正在建立学术记录"
        
        return balance
    
    def _analyze_venue_timeline(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze venue quality distribution over time
        
        Returns:
            Venue distribution timeline
        """
        timeline = {
            "annual_venue_distribution": [],
            "venue_quality_trend": "Unknown"
        }
        
        publications = data.get("publications", []) or data.get("Publications", [])
        if not publications:
            return timeline
        
        # Group by year
        year_venues = defaultdict(lambda: defaultdict(int))
        
        for pub in publications:
            if not isinstance(pub, dict):
                continue
            
            year = self._extract_year(pub.get("date") or pub.get("year"))
            tier = pub.get("journal_tier", "Unknown")
            
            if year:
                year_venues[year][tier] += 1
        
        # Build timeline
        for year in sorted(year_venues.keys()):
            venues = year_venues[year]
            total = sum(venues.values())
            
            timeline["annual_venue_distribution"].append({
                "year": year,
                "T1": venues.get("T1", 0),
                "T2": venues.get("T2", 0),
                "T3": venues.get("T3", 0),
                "T4": venues.get("T4", 0),
                "Unknown": venues.get("Unknown", 0),
                "total": total,
                "top_tier_ratio": round(
                    (venues.get("T1", 0) + venues.get("T2", 0)) / total, 2
                ) if total > 0 else 0
            })
        
        # Assess trend
        timeline["venue_quality_trend"] = self._assess_venue_quality_trend(
            timeline["annual_venue_distribution"]
        )
        
        return timeline
    
    def _analyze_collaboration_timeline(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze collaboration patterns over time
        
        Returns:
            Collaboration timeline analysis
        """
        timeline = {
            "annual_collaboration": [],
            "collaboration_trend": "Unknown",
            "independence_trend": "Unknown"
        }
        
        publications = data.get("publications", []) or data.get("Publications", [])
        candidate_name = self._get_candidate_name(data)
        
        if not publications:
            return timeline
        
        # Group by year
        year_collab = defaultdict(lambda: {
            "total_pubs": 0,
            "first_author": 0,
            "coauthor_count": set()
        })
        
        for pub in publications:
            if not isinstance(pub, dict):
                continue
            
            year = self._extract_year(pub.get("date") or pub.get("year"))
            if not year:
                continue
            
            year_collab[year]["total_pubs"] += 1
            
            authors = pub.get("authors", [])
            if authors:
                # Count unique coauthors
                for author in authors:
                    if isinstance(author, str) and not self._is_same_person(author, candidate_name):
                        year_collab[year]["coauthor_count"].add(author)
                
                # Check if first author
                if authors and self._is_same_person(str(authors[0]), candidate_name):
                    year_collab[year]["first_author"] += 1
        
        # Build timeline
        for year in sorted(year_collab.keys()):
            collab = year_collab[year]
            total = collab["total_pubs"]
            first = collab["first_author"]
            
            timeline["annual_collaboration"].append({
                "year": year,
                "total_publications": total,
                "first_author_count": first,
                "first_author_rate": round(first / total, 2) if total > 0 else 0,
                "unique_coauthors": len(collab["coauthor_count"])
            })
        
        # Assess trends
        timeline["collaboration_trend"] = self._assess_collaboration_trend(
            timeline["annual_collaboration"]
        )
        timeline["independence_trend"] = self._assess_independence_trend(
            timeline["annual_collaboration"]
        )
        
        return timeline
    
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
    
    def _calculate_growth_rate(
        self, 
        timeline: List[Dict], 
        value_key: str = "count"
    ) -> str:
        """Calculate growth rate from timeline"""
        if len(timeline) < 3:
            return "数据不足"
        
        # Compare first half vs second half
        mid_point = len(timeline) // 2
        first_half = timeline[:mid_point]
        second_half = timeline[mid_point:]
        
        first_avg = sum(t.get(value_key, 0) for t in first_half) / len(first_half)
        second_avg = sum(t.get(value_key, 0) for t in second_half) / len(second_half)
        
        if first_avg == 0:
            return "从初期强劲增长"
        
        growth_rate = (second_avg - first_avg) / first_avg
        
        if growth_rate >= 0.5:
            return f"强劲增长 (+{int(growth_rate * 100)}%)"
        elif growth_rate >= 0.2:
            return f"中等增长 (+{int(growth_rate * 100)}%)"
        elif growth_rate >= -0.1:
            return "稳定"
        else:
            return f"下降 ({int(growth_rate * 100)}%)"
    
    def _calculate_h_index_growth(self, data: Dict[str, Any]) -> List[Dict]:
        """Calculate h-index growth over time (simplified)"""
        publications = data.get("publications", []) or data.get("Publications", [])
        if not publications:
            return []
        
        # Group publications by year (cumulative)
        year_pubs = defaultdict(list)
        
        for pub in publications:
            if isinstance(pub, dict):
                year = self._extract_year(pub.get("date") or pub.get("year"))
                if year:
                    year_pubs[year].append(pub)
        
        # Calculate cumulative h-index for each year
        h_index_timeline = []
        cumulative_pubs = []
        
        for year in sorted(year_pubs.keys()):
            cumulative_pubs.extend(year_pubs[year])
            h_index = self._calculate_h_index(cumulative_pubs)
            
            h_index_timeline.append({
                "year": year,
                "h_index": h_index
            })
        
        return h_index_timeline
    
    def _calculate_h_index(self, publications: List[Dict]) -> int:
        """Calculate h-index for a list of publications"""
        if not publications:
            return 0
        
        # Get citation counts
        citations = sorted(
            [p.get("citation_count", 0) for p in publications if isinstance(p, dict)],
            reverse=True
        )
        
        # Calculate h-index
        h = 0
        for i, citation_count in enumerate(citations, start=1):
            if citation_count >= i:
                h = i
            else:
                break
        
        return h
    
    def _analyze_publication_rhythm(self, year_counts: Dict[int, int]) -> str:
        """Analyze publication rhythm pattern"""
        if len(year_counts) < 3:
            return "Insufficient data"
        
        counts = [year_counts[y] for y in sorted(year_counts.keys())]
        
        # Check for patterns
        # 1. Consistent (low variance)
        avg = sum(counts) / len(counts)
        variance = sum((c - avg) ** 2 for c in counts) / len(counts)
        cv = (variance ** 0.5 / avg) if avg > 0 else 0
        
        if cv < 0.3:
            return "Steady - Consistent annual output"
        
        # 2. Accelerating (increasing trend)
        if counts[-1] > counts[0] * 1.5:
            return "Accelerating - Increasing productivity over time"
        
        # 3. Burst pattern (peaks and valleys)
        peak_count = sum(1 for c in counts if c > avg * 1.3)
        if peak_count >= len(counts) * 0.3:
            return "Burst pattern - Alternating high and low productivity periods"
        
        return "Variable - Mixed productivity patterns"
    
    def _get_candidate_name(self, data: Dict[str, Any]) -> str:
        """Get candidate's name"""
        personal = data.get("Personal Information", {})
        if isinstance(personal, dict):
            return personal.get("name", "")
        return ""
    
    def _is_same_person(self, name1: str, name2: str) -> bool:
        """Simple name matching"""
        if not name1 or not name2:
            return False
        
        name1 = name1.lower().strip()
        name2 = name2.lower().strip()
        
        return name1 == name2 or name1 in name2 or name2 in name1
    
    def _assess_venue_quality_trend(self, distribution: List[Dict]) -> str:
        """Assess venue quality trend over time"""
        if len(distribution) < 3:
            return "Insufficient data"
        
        # Compare early vs recent top-tier ratios
        mid_point = len(distribution) // 2
        early_ratios = [d["top_tier_ratio"] for d in distribution[:mid_point]]
        recent_ratios = [d["top_tier_ratio"] for d in distribution[mid_point:]]
        
        early_avg = sum(early_ratios) / len(early_ratios) if early_ratios else 0
        recent_avg = sum(recent_ratios) / len(recent_ratios) if recent_ratios else 0
        
        if recent_avg > early_avg + 0.2:
            return "Improving - Increasing proportion of top-tier venues"
        elif recent_avg > early_avg + 0.1:
            return "Slightly improving - Gradual increase in venue quality"
        elif recent_avg < early_avg - 0.2:
            return "Declining - Decreasing proportion of top-tier venues"
        else:
            return "Stable - Consistent venue quality"
    
    def _assess_collaboration_trend(self, timeline: List[Dict]) -> str:
        """Assess collaboration network trend"""
        if len(timeline) < 3:
            return "Insufficient data"
        
        # Compare early vs recent coauthor counts
        mid_point = len(timeline) // 2
        early_counts = [t["unique_coauthors"] for t in timeline[:mid_point]]
        recent_counts = [t["unique_coauthors"] for t in timeline[mid_point:]]
        
        early_avg = sum(early_counts) / len(early_counts) if early_counts else 0
        recent_avg = sum(recent_counts) / len(recent_counts) if recent_counts else 0
        
        if recent_avg > early_avg * 1.5:
            return "Rapidly expanding - Growing collaboration network"
        elif recent_avg > early_avg * 1.1:
            return "Expanding - Increasing collaborations"
        elif recent_avg < early_avg * 0.8:
            return "Contracting - Focusing on core collaborators"
        else:
            return "Stable - Consistent collaboration patterns"
    
    def _assess_independence_trend(self, timeline: List[Dict]) -> str:
        """Assess research independence trend"""
        if len(timeline) < 3:
            return "Insufficient data"
        
        # Compare early vs recent first-author rates
        mid_point = len(timeline) // 2
        early_rates = [t["first_author_rate"] for t in timeline[:mid_point]]
        recent_rates = [t["first_author_rate"] for t in timeline[mid_point:]]
        
        early_avg = sum(early_rates) / len(early_rates) if early_rates else 0
        recent_avg = sum(recent_rates) / len(recent_rates) if recent_rates else 0
        
        if recent_avg > early_avg + 0.2:
            return "Increasing independence - Growing research autonomy"
        elif recent_avg > early_avg + 0.1:
            return "Slightly increasing - Gradual independence growth"
        elif recent_avg < early_avg - 0.2:
            return "Decreasing independence - More collaborative work"
        else:
            return "Stable independence - Consistent authorship patterns"
    
    def _calculate_productivity_score(self, analysis_result: Dict[str, Any]) -> float:
        """Calculate overall productivity score (0-10)"""
        score = 0.0
        
        # Factor 1: Publication count (0-3 points)
        pub_timeline = analysis_result.get("publication_timeline", {})
        total_pubs = pub_timeline.get("total_publications", 0)
        avg_per_year = pub_timeline.get("avg_per_year", 0)
        
        if avg_per_year >= 3:
            score += 3.0
        elif avg_per_year >= 2:
            score += 2.5
        elif avg_per_year >= 1:
            score += 2.0
        else:
            score += avg_per_year
        
        # Factor 2: Quality-quantity balance (0-3 points)
        balance = analysis_result.get("quality_quantity_balance", {})
        balance_score = balance.get("balance_score", 0)
        score += min(3.0, balance_score / 2)
        
        # Factor 3: Consistency (0-2 points)
        patterns = analysis_result.get("productivity_patterns", {})
        consistency = patterns.get("consistency_level", "Unknown")
        
        if consistency == "Highly Consistent":
            score += 2.0
        elif consistency == "Moderately Consistent":
            score += 1.5
        else:
            score += 1.0
        
        # Factor 4: Growth trend (0-2 points)
        growth_rate = pub_timeline.get("growth_rate", "未知")
        if "强劲增长" in growth_rate:
            score += 2.0
        elif "中等增长" in growth_rate:
            score += 1.5
        elif "稳定" in growth_rate:
            score += 1.0
        else:
            score += 0.5
        
        return round(min(10.0, score), 1)
    
    def _assess_overall_trend(self, analysis_result: Dict[str, Any]) -> str:
        """Assess overall productivity trend"""
        pub_timeline = analysis_result.get("publication_timeline", {})
        growth_rate = pub_timeline.get("growth_rate", "Unknown")
        
        balance = analysis_result.get("quality_quantity_balance", {})
        balance_assessment = balance.get("balance_assessment", "Unknown")
        
        venue_timeline = analysis_result.get("venue_distribution_timeline", {})
        venue_trend = venue_timeline.get("venue_quality_trend", "Unknown")
        
        # Combine assessments
        positive_indicators = sum([
            "增长" in growth_rate,
            "优秀" in balance_assessment or "良好" in balance_assessment,
            "改善" in venue_trend
        ])
        
        if positive_indicators >= 2:
            return "积极 - 生产力和质量呈强劲上升趋势"
        elif positive_indicators >= 1:
            return "稳定-积极 - 保持良好生产力并有所改善"
        else:
            return "需关注 - 考虑提升生产力或影响力的策略"
    
    def _identify_peak_period(self, analysis_result: Dict[str, Any]) -> Optional[Dict]:
        """Identify peak productivity period"""
        pub_timeline = analysis_result.get("publication_timeline", {})
        annual_counts = pub_timeline.get("annual_counts", [])
        
        if not annual_counts:
            return None
        
        # Find year(s) with maximum publications
        max_count = max(item["count"] for item in annual_counts)
        peak_years = [
            item["year"] for item in annual_counts 
            if item["count"] == max_count
        ]
        
        # Get quality metrics for peak years
        balance = analysis_result.get("quality_quantity_balance", {})
        quality_metrics = balance.get("annual_quality_metrics", [])
        
        peak_quality = [
            m for m in quality_metrics 
            if m["year"] in peak_years
        ]
        
        if peak_quality:
            avg_quality = sum(m["quality_score"] for m in peak_quality) / len(peak_quality)
            
            return {
                "years": peak_years,
                "publication_count": max_count,
                "avg_quality_score": round(avg_quality, 1),
                "assessment": self._assess_peak_quality(max_count, avg_quality)
            }
        
        return {
            "years": peak_years,
            "publication_count": max_count,
            "assessment": "高峰生产力期已识别"
        }
    
    def _assess_peak_quality(self, count: int, quality: float) -> str:
        """Assess quality of peak period"""
        if count >= 5 and quality >= 7:
            return "卓越高峰 - 高生产力且高影响力"
        elif count >= 3 and quality >= 6:
            return "强劲高峰 - 数量与质量平衡"
        elif count >= 5:
            return "高产出高峰 - 侧重数量"
        elif quality >= 7:
            return "高影响高峰 - 侧重质量"
        else:
            return "中等高峰期"
    
    def _assess_recent_trend(self, analysis_result: Dict[str, Any]) -> str:
        """Assess recent productivity trend (last 2-3 years)"""
        pub_timeline = analysis_result.get("publication_timeline", {})
        annual_counts = pub_timeline.get("annual_counts", [])
        
        if len(annual_counts) < 3:
            return "近期数据不足"
        
        # Get last 3 years
        recent_years = annual_counts[-3:]
        recent_counts = [item["count"] for item in recent_years]
        
        # Calculate trend
        if len(recent_counts) >= 2:
            avg_recent = sum(recent_counts) / len(recent_counts)
            latest_year = recent_counts[-1]
            
            if latest_year >= avg_recent * 1.3:
                return "加速 - 近期生产力大幅增长"
            elif latest_year >= avg_recent * 0.8:
                return "稳定 - 近期产出保持一致"
            else:
                return "放缓 - 近期产出下降（可能是正常波动）"
        
        return "未知"
    
    def _predict_future_productivity(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Predict future productivity based on trends"""
        prediction = {
            "expected_trend": "未知",
            "confidence": "低",
            "recommendations": []
        }
        
        pub_timeline = analysis_result.get("publication_timeline", {})
        growth_rate = pub_timeline.get("growth_rate", "Unknown")
        
        patterns = analysis_result.get("productivity_patterns", {})
        consistency = patterns.get("consistency_level", "Unknown")
        
        recent_trend = analysis_result.get("recent_trend", "Unknown")
        
        # Prediction logic
        if "强劲增长" in growth_rate and "加速" in recent_trend:
            prediction["expected_trend"] = "持续增长 - 可能保持或提高生产力"
            prediction["confidence"] = "高"
        elif "稳定" in growth_rate and consistency == "高度一致":
            prediction["expected_trend"] = "稳定产出 - 可能保持当前生产力水平"
            prediction["confidence"] = "中高"
        elif "下降" in growth_rate or "放缓" in recent_trend:
            prediction["expected_trend"] = "需要监控 - 近期放缓可能表明暂时或结构性问题"
            prediction["confidence"] = "中"
            prediction["recommendations"].append("调查影响近期生产力的因素")
        else:
            prediction["expected_trend"] = "波动 - 混合信号表明生产力模式不稳定"
            prediction["confidence"] = "低"
        
        # Add general recommendations
        balance = analysis_result.get("quality_quantity_balance", {})
        balance_assessment = balance.get("balance_assessment", "")
        
        if "数量导向" in balance_assessment:
            prediction["recommendations"].append("建议关注更高影响力的期刊/会议")
        elif "质量导向" in balance_assessment:
            prediction["recommendations"].append("已有坚实的质量基础，可增加产出数量")
        
        venue_timeline = analysis_result.get("venue_distribution_timeline", {})
        venue_trend = venue_timeline.get("venue_quality_trend", "")
        
        if "下降" in venue_trend:
            prediction["recommendations"].append("建议目标更多顶级期刊/会议")
        
        return prediction


# ============ Standalone Testing ============
if __name__ == "__main__":
    # Test with sample data
    sample_data = {
        "Personal Information": {"name": "Jane Smith"},
        "Publications": [
            {
                "title": "Paper 1",
                "date": "2018-01",
                "authors": ["Jane Smith", "John Doe"],
                "citation_count": 50,
                "venue": "CVPR 2018",
                "journal_tier": "T1"
            },
            {
                "title": "Paper 2",
                "date": "2019-03",
                "authors": ["Jane Smith"],
                "citation_count": 100,
                "venue": "ICCV 2019",
                "journal_tier": "T1"
            },
            {
                "title": "Paper 3",
                "date": "2020-05",
                "authors": ["Jane Smith", "Alice Brown"],
                "citation_count": 150,
                "venue": "ECCV 2020",
                "journal_tier": "T1"
            },
            {
                "title": "Paper 4",
                "date": "2021-02",
                "authors": ["Jane Smith"],
                "citation_count": 80,
                "venue": "CVPR 2021",
                "journal_tier": "T1"
            },
            {
                "title": "Paper 5",
                "date": "2022-06",
                "authors": ["Jane Smith", "Bob Wilson"],
                "citation_count": 120,
                "venue": "NeurIPS 2022",
                "journal_tier": "T1"
            },
            {
                "title": "Paper 6",
                "date": "2023-04",
                "authors": ["Jane Smith"],
                "citation_count": 60,
                "venue": "ICLR 2023",
                "journal_tier": "T1"
            },
            {
                "title": "Paper 7",
                "date": "2024-01",
                "authors": ["Jane Smith", "Charlie Davis"],
                "citation_count": 30,
                "venue": "CVPR 2024",
                "journal_tier": "T1"
            }
        ]
    }
    
    analyzer = ProductivityTimelineAnalyzer()
    result = analyzer.analyze(sample_data)
    
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
