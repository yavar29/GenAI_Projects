"""
Streamlit version of analytics dashboard.
"""

from __future__ import annotations

from typing import Optional
from collections import Counter

import streamlit as st
import plotly.express as px
import pandas as pd

from app.schemas.analytics import AnalyticsPayload
from app.core.cache_manager import get_cache_manager


def _df_from_list(data, columns):
    if not data:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame([d.dict() if hasattr(d, "dict") else d for d in data])[columns]


def render_analytics(analytics: Optional[AnalyticsPayload]):
    """Render analytics dashboard in Streamlit."""
    if analytics is None:
        st.info("No analytics available yet. Run a research session to see analytics.")
        
        # Show cache stats even without analytics
        cache_mgr = get_cache_manager()
        cache_stats = cache_mgr.get_stats()
        st.markdown("### 💾 Cache Statistics")
        st.markdown(f"""
        - Total entries: {cache_stats['total_entries']}
        - Valid entries: {cache_stats['valid_entries']}
        - Expired entries: {cache_stats['expired_entries']}
        - L1 (in-memory) entries: {cache_stats['l1_entries']}
        - Cache size: {cache_stats['size_mb']} MB
        - TTL: {cache_stats['ttl_hours']} hours
        """)
        return
    
    # Overview with modern cards
    st.markdown("## 📊 Research Session Analytics")
    ov = analytics.overview
    
    # Create metric columns for a modern card layout
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Word Count", f"{ov.word_count:,}")
    with col2:
        st.metric("Sections", ov.num_sections)
    with col3:
        st.metric("Total Sources", ov.num_sources)
    with col4:
        st.metric("Web Sources", ov.num_web_sources)
    
    st.markdown(f"**Research Topic:** {ov.topic}")
    st.markdown("---")
    
    # Tabs for different analytics views
    tab1, tab2, tab3 = st.tabs(["📦 Sources & Quality", "🔗 Citations & Coverage", "⏱ Process & Efficiency"])
    
    with tab1:
        st.markdown("### Source Type Distribution")
        df_types = _df_from_list(analytics.source_type_stats, ["source_type", "count"])
        if not df_types.empty:
            fig = px.pie(
                df_types,
                names="source_type",
                values="count",
                title="Source Types (Web vs File, etc.)",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(size=12, family="Arial"),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No source type data available.")
        
        st.markdown("### Top Domains")
        df_domains = _df_from_list(analytics.domain_stats, ["domain", "count"])
        if not df_domains.empty:
            fig = px.bar(
                df_domains,
                x="domain",
                y="count",
                title="Top Domains",
                color="count",
                color_continuous_scale="blues",
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(size=12),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No domain data available.")
        
        st.markdown("### Source Credibility Distribution")
        df_cred = _df_from_list(analytics.credibility_stats, ["score", "count"])
        if not df_cred.empty:
            fig = px.bar(
                df_cred,
                x="score",
                y="count",
                title="Source Credibility (1–5)",
                color="count",
                color_continuous_scale="viridis",
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(size=12),
                xaxis=dict(title="Credibility Score", type="category"),
                yaxis=dict(title="Number of Sources"),
            )
            fig.update_traces(marker_line_color="white", marker_line_width=1.5)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No credibility data available.")
    
    with tab2:
        st.markdown("### Section Coverage Heatmap")
        df_cov = _df_from_list(
            analytics.section_coverage,
            ["section_title", "word_count", "citation_count"],
        )
        if not df_cov.empty:
            fig = px.density_heatmap(
                df_cov,
                x="section_title",
                y="citation_count",
                z="word_count",
                title="Section Coverage Heatmap (Word Count vs Citations)",
                color_continuous_scale="blues",
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(size=11),
                xaxis=dict(title="Section Title", tickangle=-45),
                yaxis=dict(title="Citation Count"),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No section coverage data available.")
        
        st.markdown("### Most Cited Sources")
        df_cites = _df_from_list(
            analytics.citation_frequencies,
            ["source_id", "title", "count"],
        )
        if not df_cites.empty:
            # Limit to top 10 for better visualization
            df_cites_top = df_cites.nlargest(10, "count")
            fig = px.bar(
                df_cites_top,
                x="count",
                y="title",
                orientation="h",
                title="Top 10 Most Cited Sources",
                color="count",
                color_continuous_scale="purples",
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(size=11),
                xaxis=dict(title="Citation Count"),
                yaxis=dict(title="Source Title"),
                height=400,
            )
            fig.update_traces(marker_line_color="white", marker_line_width=1)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No citation data available.")
        
        st.markdown("### Citations per Section")
        if not df_cov.empty:
            fig = px.bar(
                df_cov,
                x="section_title",
                y="citation_count",
                title="Citations per Section",
                color="citation_count",
                color_continuous_scale="greens",
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(size=11),
                xaxis=dict(title="Section Title", tickangle=-45),
                yaxis=dict(title="Citation Count"),
            )
            fig.update_traces(marker_line_color="white", marker_line_width=1.5)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No section citation data available.")
    
    with tab3:
        st.markdown("### Research Waves Timeline")
        df_waves = _df_from_list(
            analytics.wave_stats,
            ["wave_index", "num_queries", "num_sources_discovered", "duration_seconds"],
        )
        if not df_waves.empty:
            fig = px.bar(
                df_waves,
                x="wave_index",
                y="num_sources_discovered",
                title="Sources Discovered per Wave",
                labels={"wave_index": "Wave", "num_sources_discovered": "Sources"},
                color="num_sources_discovered",
                color_continuous_scale="oranges",
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(size=12),
                xaxis=dict(title="Wave Number", type="category"),
                yaxis=dict(title="Sources Discovered"),
            )
            fig.update_traces(marker_line_color="white", marker_line_width=1.5)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No wave statistics available.")
        
        st.markdown("### Efficiency Metrics")
        if analytics.efficiency:
            eff = analytics.efficiency
            # Create metric columns for efficiency
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Queries Executed", eff.queries_executed)
            with col2:
                if eff.cache_hit_rate is not None:
                    st.metric("Cache Hit Rate", f"{round(eff.cache_hit_rate * 100, 1)}%")
            with col3:
                st.metric("Waves Completed", eff.waves_completed)
            
            col4, col5 = st.columns(2)
            with col4:
                st.metric("Total Sources Analyzed", eff.total_sources_seen)
            with col5:
                st.metric("Unique Sources Used", eff.unique_sources_used)
            
            if eff.total_duration_seconds:
                st.metric("Total Duration", f"{round(eff.total_duration_seconds, 1)}s")
        else:
            st.info("No efficiency data available.")
        
        # Cache Statistics with modern layout
        st.markdown("### 💾 Cache Statistics")
        cache_mgr = get_cache_manager()
        cache_stats = cache_mgr.get_stats()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Entries", cache_stats['total_entries'])
            st.metric("Valid Entries", cache_stats['valid_entries'])
        with col2:
            st.metric("Expired Entries", cache_stats['expired_entries'])
            st.metric("L1 (Memory) Entries", cache_stats['l1_entries'])
        with col3:
            st.metric("Cache Size", f"{cache_stats['size_mb']} MB")
            st.metric("TTL", f"{cache_stats['ttl_hours']} hours")

