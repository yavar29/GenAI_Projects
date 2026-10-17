# app/ui/analytics_dashboard.py

from __future__ import annotations

from typing import Optional
from collections import Counter

import gradio as gr
import plotly.express as px
import pandas as pd

from app.schemas.analytics import AnalyticsPayload
from app.core.cache_manager import get_cache_manager


def _df_from_list(data, columns):
    if not data:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame([d.dict() if hasattr(d, "dict") else d for d in data])[columns]


def create_analytics_tab(
    analytics_state: gr.State,
) -> gr.TabItem:
    """
    Build the '📊 Analytics' tab UI.

    analytics_state is expected to hold an AnalyticsPayload (or None).
    This function is modular: wiring the state is done in gradio_app.py.
    """

    with gr.Tab("📊 Analytics") as tab:
        gr.Markdown(
            "## 📊 Research Session Analytics\n"
            "Visual breakdown of sources, coverage, citations, and process.\n"
            "_(Run a research session, then populate `analytics_state` to see real data.)_"
        )

        # ------------------- SESSION OVERVIEW -------------------
        with gr.Row():
            overview_md = gr.Markdown(label="Overview")

        # ------------------- TABS FOR SWIPE-LIKE UX -------------
        with gr.Tabs():
            # 1. Sources & Quality
            with gr.Tab("📦 Sources & Quality"):
                src_type_plot = gr.Plot(label="Source Type Distribution")
                domain_plot = gr.Plot(label="Top Domains")
                pub_timeline_plot = gr.Plot(label="Publication Timeline")
                credibility_plot = gr.Plot(label="Source Credibility Distribution")

            # 2. Citations & Coverage
            with gr.Tab("🔗 Citations & Coverage"):
                section_heatmap = gr.Plot(label="Section Coverage (Word Count vs Citations)")
                citation_bar = gr.Plot(label="Most Cited Sources")
                citations_per_section = gr.Plot(label="Citations per Section")

            # 3. Process & Efficiency
            with gr.Tab("⏱ Process & Efficiency"):
                waves_timeline = gr.Plot(label="Research Waves Timeline")
                efficiency_md = gr.Markdown(label="Efficiency Metrics")
                cache_stats_md = gr.Markdown(label="Cache Statistics", visible=False)

        # ------------- UPDATE FUNCTION (PURELY FROM STATE) -------------
        def update_dashboard(analytics: Optional[AnalyticsPayload]):
            if analytics is None:
                # Show cache stats even without analytics
                cache_mgr = get_cache_manager()
                cache_stats = cache_mgr.get_stats()
                cache_info = (
                    f"**Cache Statistics:**\n\n"
                    f"- Total entries: {cache_stats['total_entries']}\n"
                    f"- Valid entries: {cache_stats['valid_entries']}\n"
                    f"- Expired entries: {cache_stats['expired_entries']}\n"
                    f"- L1 (in-memory) entries: {cache_stats['l1_entries']}\n"
                    f"- Cache size: {cache_stats['size_mb']} MB\n"
                    f"- TTL: {cache_stats['ttl_hours']} hours\n"
                )
                return (
                    "No analytics available yet. Run a research session and populate analytics_state.",
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    "No efficiency data.",
                    None,
                    cache_info,
                )

            # --- Overview ---
            ov = analytics.overview
            overview_text = (
                f"**Topic:** {ov.topic}\n\n"
                f"- Word count: **{ov.word_count}**\n"
                f"- Sections: **{ov.num_sections}**\n"
                f"- Sources: **{ov.num_sources}** "
                f"(Web: {ov.num_web_sources}, File: {ov.num_file_sources})\n"
            )

            # --- Source Type Distribution ---
            src_type_fig = None
            df_types = _df_from_list(analytics.source_type_stats, ["source_type", "count"])
            if not df_types.empty:
                src_type_fig = px.pie(
                    df_types,
                    names="source_type",
                    values="count",
                    title="Source Types (Web vs File, etc.)",
                    hole=0.4,
                )

            # --- Domain Breakdown ---
            domain_fig = None
            df_domains = _df_from_list(analytics.domain_stats, ["domain", "count"])
            if not df_domains.empty:
                domain_fig = px.bar(
                    df_domains,
                    x="domain",
                    y="count",
                    title="Top Domains",
                )

            # --- Publication Timeline ---
            pub_fig = None
            df_pub = _df_from_list(analytics.publication_stats, ["bucket", "count"])
            if not df_pub.empty:
                pub_fig = px.bar(
                    df_pub,
                    x="bucket",
                    y="count",
                    title="Publication Timeline",
                )

            # --- Credibility Distribution ---
            cred_fig = None
            df_cred = _df_from_list(analytics.credibility_stats, ["score", "count"])
            if not df_cred.empty:
                cred_fig = px.bar(
                    df_cred,
                    x="score",
                    y="count",
                    title="Source Credibility (1–5)",
                )

            # --- Section Coverage Heatmap ---
            heatmap_fig = None
            df_cov = _df_from_list(
                analytics.section_coverage,
                ["section_title", "word_count", "citation_count"],
            )
            if not df_cov.empty:
                heatmap_fig = px.density_heatmap(
                    df_cov,
                    x="section_title",
                    y="citation_count",
                    z="word_count",
                    title="Section Coverage Heatmap (Word Count vs Citations)",
                )

            # --- Most Cited Sources ---
            citation_bar_fig = None
            df_cites = _df_from_list(
                analytics.citation_frequencies,
                ["source_id", "title", "count"],
            )
            if not df_cites.empty:
                citation_bar_fig = px.bar(
                    df_cites,
                    x="title",
                    y="count",
                    title="Most Cited Sources",
                )

            # --- Citations per Section ---
            cps_fig = None
            if not df_cov.empty:
                cps_fig = px.bar(
                    df_cov,
                    x="section_title",
                    y="citation_count",
                    title="Citations per Section",
                )

            # --- Waves Timeline & Efficiency ---
            waves_fig = None
            eff_md = "No efficiency data."

            df_waves = _df_from_list(
                analytics.wave_stats,
                ["wave_index", "num_queries", "num_sources_discovered", "duration_seconds"],
            )
            if not df_waves.empty:
                waves_fig = px.bar(
                    df_waves,
                    x="wave_index",
                    y="num_sources_discovered",
                    title="Sources Discovered per Wave",
                    labels={"wave_index": "Wave", "num_sources_discovered": "Sources"},
                )

            if analytics.efficiency:
                eff = analytics.efficiency
                if eff.cache_hit_rate is not None:
                    eff_md = (
                        f"**Queries executed:** {eff.queries_executed}\n\n"
                        f"- Total sources analyzed: {eff.total_sources_seen}\n"
                        f"- Unique sources used in report: {eff.unique_sources_used}\n"
                        f"- Cache hit rate: {round(eff.cache_hit_rate * 100, 1)}%\n"
                        f"- Waves completed: {eff.waves_completed}\n"
                        f"- Total duration: {round(eff.total_duration_seconds or 0, 1)} seconds\n"
                    )
                else:
                    eff_md = (
                        f"**Queries executed:** {eff.queries_executed}\n\n"
                        f"- Total sources analyzed: {eff.total_sources_seen}\n"
                        f"- Unique sources used in report: {eff.unique_sources_used}\n"
                        f"- Waves completed: {eff.waves_completed}\n"
                    )
            
            # Get cache statistics
            cache_mgr = get_cache_manager()
            cache_stats = cache_mgr.get_stats()
            cache_info = (
                f"**Cache Statistics:**\n\n"
                f"- Total entries: {cache_stats['total_entries']}\n"
                f"- Valid entries: {cache_stats['valid_entries']}\n"
                f"- Expired entries: {cache_stats['expired_entries']}\n"
                f"- L1 (in-memory) entries: {cache_stats['l1_entries']}\n"
                f"- Cache size: {cache_stats['size_mb']} MB\n"
                f"- TTL: {cache_stats['ttl_hours']} hours\n"
                f"- Max entries: {cache_stats['max_rows']}\n"
            )

            return (
                overview_text,
                src_type_fig,
                domain_fig,
                pub_fig,
                cred_fig,
                heatmap_fig,
                citation_bar_fig,
                cps_fig,
                eff_md,
                waves_fig,
                cache_info,
            )

        # Wire the dashboard to the analytics_state
        analytics_state.change(
            fn=update_dashboard,
            inputs=[analytics_state],
            outputs=[
                overview_md,
                src_type_plot,
                domain_plot,
                pub_timeline_plot,
                credibility_plot,
                section_heatmap,
                citation_bar,
                citations_per_section,
                efficiency_md,
                waves_timeline,
                cache_stats_md,
            ],
        )
        
        # Also show cache stats on initial load
        def show_initial_cache_stats():
            cache_mgr = get_cache_manager()
            cache_stats = cache_mgr.get_stats()
            if cache_stats['total_entries'] > 0:
                return gr.update(
                    value=(
                        f"**Cache Statistics:**\n\n"
                        f"- Total entries: {cache_stats['total_entries']}\n"
                        f"- Valid entries: {cache_stats['valid_entries']}\n"
                        f"- Expired entries: {cache_stats['expired_entries']}\n"
                        f"- L1 (in-memory) entries: {cache_stats['l1_entries']}\n"
                        f"- Cache size: {cache_stats['size_mb']} MB\n"
                        f"- TTL: {cache_stats['ttl_hours']} hours\n"
                    ),
                    visible=True
                )
            return gr.update(visible=False)
        
        # Show cache stats on tab load
        tab.select(
            fn=show_initial_cache_stats,
            inputs=[],
            outputs=[cache_stats_md],
        )

    return tab

