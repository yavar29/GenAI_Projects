# app/ui/analytics_dashboard.py

from __future__ import annotations

from typing import Optional
from collections import Counter
from pathlib import Path

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
            """
            ## 📊 Research Session Analytics
            
            Comprehensive visual breakdown of sources, coverage, citations, and research process efficiency.
            
            <div style='background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 1rem; border-radius: 8px; margin: 1rem 0; color: white; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);'>
                <strong>💡 Tip:</strong> Run a research session to see detailed analytics and visualizations.
            </div>
            """
        )

        # ------------------- SESSION OVERVIEW -------------------
        with gr.Row():
            overview_md = gr.Markdown(
                label="📈 Session Overview",
                elem_classes=["modern-card"],
                value="<div style='background: #ffedd5; color: #334155; padding: 1rem; border-radius: 8px; border: 1px solid rgba(249, 115, 22, 0.2);'>No analytics available yet. Run a research session to see detailed analytics.</div>"
            )

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
            
            # 4. Workflow Graph
            with gr.Tab("🔄 Workflow Graph"):
                workflow_graph_image = gr.Image(
                    label="Agent Workflow Diagram",
                    type="filepath",
                    elem_classes=["workflow-graph"]
                )

        # ------------- UPDATE FUNCTION (PURELY FROM STATE) -------------
        def update_dashboard(analytics: Optional[AnalyticsPayload]):
            if analytics is None:
                # Show cache stats even without analytics
                cache_mgr = get_cache_manager()
                cache_stats = cache_mgr.get_stats()
                cache_info = (
                    f"<div style='background: linear-gradient(135deg, #e0e7ff 0%, #e9d5ff 100%); color: #000000 !important; padding: 1rem; border-radius: 8px; border: 1px solid rgba(99, 102, 241, 0.3);'>"
                    f"<h3 style='color: #000000 !important; margin-bottom: 0.5rem;'>💾 Cache Statistics</h3>"
                    f"<ul style='color: #000000 !important; margin: 0; padding-left: 1.5rem;'>"
                    f"<li style='color: #000000 !important;'>Total entries: <strong style='color: #000000 !important;'>{cache_stats['total_entries']}</strong></li>"
                    f"<li style='color: #000000 !important;'>Valid entries: <strong style='color: #000000 !important;'>{cache_stats['valid_entries']}</strong></li>"
                    f"<li style='color: #000000 !important;'>Expired entries: <strong style='color: #000000 !important;'>{cache_stats['expired_entries']}</strong></li>"
                    f"<li style='color: #000000 !important;'>L1 (in-memory) entries: <strong style='color: #000000 !important;'>{cache_stats['l1_entries']}</strong></li>"
                    f"<li style='color: #000000 !important;'>Cache size: <strong style='color: #000000 !important;'>{cache_stats['size_mb']} MB</strong></li>"
                    f"<li style='color: #000000 !important;'>TTL: <strong style='color: #000000 !important;'>{cache_stats['ttl_hours']} hours</strong></li>"
                    f"</ul></div>"
                )
                # Workflow graph (always available if file exists)
                workflow_graph_path = Path("docs/workflow_graph.png")
                workflow_graph_value = None
                if workflow_graph_path.exists():
                    workflow_graph_value = str(workflow_graph_path.resolve())
                
                return (
                    "<div style='background: linear-gradient(135deg, #e0e7ff 0%, #e9d5ff 100%); color: #334155; padding: 1rem; border-radius: 8px; border: 1px solid rgba(99, 102, 241, 0.2);'>No analytics available yet. Run a research session and populate analytics_state.</div>",
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    "<div style='background: linear-gradient(135deg, #e0e7ff 0%, #e9d5ff 100%); color: #334155; padding: 1rem; border-radius: 8px; border: 1px solid rgba(99, 102, 241, 0.2);'>No efficiency data.</div>",
                    None,
                    cache_info,
                    workflow_graph_value,
                )

            # --- Overview ---
            ov = analytics.overview
            overview_text = (
                f"""
                <div style='background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 1.5rem; border-radius: 12px; color: white; margin-bottom: 1rem; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);'>
                    <h3 style='color: white; margin-bottom: 1rem; font-weight: 700;'>📊 Research Overview</h3>
                    <p style='margin: 0.5rem 0; color: rgba(255,255,255,0.95);'><strong>Topic:</strong> {ov.topic}</p>
                    <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-top: 1rem;'>
                        <div style='background: rgba(255,255,255,0.25); padding: 1rem; border-radius: 8px; backdrop-filter: blur(10px);'>
                            <div style='font-size: 0.875rem; opacity: 0.95; color: white;'>Word Count</div>
                            <div style='font-size: 1.5rem; font-weight: 700; color: white;'>{ov.word_count:,}</div>
                        </div>
                        <div style='background: rgba(255,255,255,0.25); padding: 1rem; border-radius: 8px; backdrop-filter: blur(10px);'>
                            <div style='font-size: 0.875rem; opacity: 0.95; color: white;'>Sections</div>
                            <div style='font-size: 1.5rem; font-weight: 700; color: white;'>{ov.num_sections}</div>
                        </div>
                        <div style='background: rgba(255,255,255,0.25); padding: 1rem; border-radius: 8px; backdrop-filter: blur(10px);'>
                            <div style='font-size: 0.875rem; opacity: 0.95; color: white;'>Total Sources</div>
                            <div style='font-size: 1.5rem; font-weight: 700; color: white;'>{ov.num_sources}</div>
                        </div>
                        <div style='background: rgba(255,255,255,0.25); padding: 1rem; border-radius: 8px; backdrop-filter: blur(10px);'>
                            <div style='font-size: 0.875rem; opacity: 0.95; color: white;'>Web / File</div>
                            <div style='font-size: 1.5rem; font-weight: 700; color: white;'>{ov.num_web_sources} / {ov.num_file_sources}</div>
                        </div>
                    </div>
                </div>
                """
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
                # Filter out "Unknown" entries and only show if we have valid years
                df_pub_filtered = df_pub[df_pub["bucket"] != "Unknown"]
                if not df_pub_filtered.empty:
                    # Sort by year (bucket) for proper timeline display
                    # Convert to numeric for proper sorting, handling non-numeric gracefully
                    df_pub_filtered = df_pub_filtered.copy()
                    df_pub_filtered["year_num"] = pd.to_numeric(df_pub_filtered["bucket"], errors="coerce")
                    df_pub_filtered = df_pub_filtered.dropna(subset=["year_num"])
                    df_pub_filtered = df_pub_filtered.sort_values("year_num")
                    
                    if not df_pub_filtered.empty:
                        pub_fig = px.bar(
                            df_pub_filtered,
                            x="bucket",
                            y="count",
                            title="Publication Timeline",
                            labels={"bucket": "Year", "count": "Number of Sources"},
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
            eff_md = "<div style='background: linear-gradient(135deg, #e0e7ff 0%, #e9d5ff 100%); color: #334155; padding: 1rem; border-radius: 8px; border: 1px solid rgba(99, 102, 241, 0.2);'>No efficiency data.</div>"

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
                        f"<div style='background: linear-gradient(135deg, #e0e7ff 0%, #e9d5ff 100%); color: #000000 !important; padding: 1rem; border-radius: 8px; border: 1px solid rgba(99, 102, 241, 0.3);'>"
                        f"<h3 style='color: #000000 !important; margin-bottom: 0.5rem;'>⚡ Efficiency Metrics</h3>"
                        f"<p style='color: #000000 !important;'><strong style='color: #000000 !important;'>Queries executed:</strong> {eff.queries_executed}</p>"
                        f"<ul style='color: #000000 !important; margin: 0; padding-left: 1.5rem;'>"
                        f"<li style='color: #000000 !important;'>Total sources analyzed: <strong style='color: #000000 !important;'>{eff.total_sources_seen}</strong></li>"
                        f"<li style='color: #000000 !important;'>Unique sources used in report: <strong style='color: #000000 !important;'>{eff.unique_sources_used}</strong></li>"
                        f"<li style='color: #000000 !important;'>Cache hit rate: <strong style='color: #000000 !important;'>{round(eff.cache_hit_rate * 100, 1)}%</strong></li>"
                        f"<li style='color: #000000 !important;'>Waves completed: <strong style='color: #000000 !important;'>{eff.waves_completed}</strong></li>"
                        f"<li style='color: #000000 !important;'>Total duration: <strong style='color: #000000 !important;'>{round(eff.total_duration_seconds or 0, 1)} seconds</strong></li>"
                        f"</ul></div>"
                    )
                else:
                    eff_md = (
                        f"<div style='background: linear-gradient(135deg, #e0e7ff 0%, #e9d5ff 100%); color: #000000 !important; padding: 1rem; border-radius: 8px; border: 1px solid rgba(99, 102, 241, 0.3);'>"
                        f"<h3 style='color: #000000 !important; margin-bottom: 0.5rem;'>⚡ Efficiency Metrics</h3>"
                        f"<p style='color: #000000 !important;'><strong style='color: #000000 !important;'>Queries executed:</strong> {eff.queries_executed}</p>"
                        f"<ul style='color: #000000 !important; margin: 0; padding-left: 1.5rem;'>"
                        f"<li style='color: #000000 !important;'>Total sources analyzed: <strong style='color: #000000 !important;'>{eff.total_sources_seen}</strong></li>"
                        f"<li style='color: #000000 !important;'>Unique sources used in report: <strong style='color: #000000 !important;'>{eff.unique_sources_used}</strong></li>"
                        f"<li style='color: #000000 !important;'>Waves completed: <strong style='color: #000000 !important;'>{eff.waves_completed}</strong></li>"
                        f"</ul></div>"
                    )
            else:
                eff_md = "<div style='background: linear-gradient(135deg, #e0e7ff 0%, #e9d5ff 100%); color: #334155; padding: 1rem; border-radius: 8px; border: 1px solid rgba(99, 102, 241, 0.2);'>No efficiency data.</div>"
            
            # Get cache statistics
            cache_mgr = get_cache_manager()
            cache_stats = cache_mgr.get_stats()
            cache_info = (
                f"<div style='background: linear-gradient(135deg, #e0e7ff 0%, #e9d5ff 100%); color: #000000 !important; padding: 1rem; border-radius: 8px; border: 1px solid rgba(99, 102, 241, 0.3);'>"
                f"<h3 style='color: #000000 !important; margin-bottom: 0.5rem;'>💾 Cache Statistics</h3>"
                f"<ul style='color: #000000 !important; margin: 0; padding-left: 1.5rem;'>"
                f"<li style='color: #000000 !important;'>Total entries: <strong style='color: #000000 !important;'>{cache_stats['total_entries']}</strong></li>"
                f"<li style='color: #000000 !important;'>Valid entries: <strong style='color: #000000 !important;'>{cache_stats['valid_entries']}</strong></li>"
                f"<li style='color: #000000 !important;'>Expired entries: <strong style='color: #000000 !important;'>{cache_stats['expired_entries']}</strong></li>"
                f"<li style='color: #000000 !important;'>L1 (in-memory) entries: <strong style='color: #000000 !important;'>{cache_stats['l1_entries']}</strong></li>"
                f"<li style='color: #000000 !important;'>Cache size: <strong style='color: #000000 !important;'>{cache_stats['size_mb']} MB</strong></li>"
                f"<li style='color: #000000 !important;'>TTL: <strong style='color: #000000 !important;'>{cache_stats['ttl_hours']} hours</strong></li>"
                f"<li style='color: #000000 !important;'>Max entries: <strong style='color: #000000 !important;'>{cache_stats['max_rows']}</strong></li>"
                f"</ul></div>"
            )

            # Workflow graph
            workflow_graph_path = Path("docs/workflow_graph.png")
            workflow_graph_value = None
            if workflow_graph_path.exists():
                workflow_graph_value = str(workflow_graph_path.resolve())

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
                workflow_graph_value,
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
                workflow_graph_image,
            ],
        )
        
        # Also show cache stats on initial load
        def show_initial_cache_stats():
            cache_mgr = get_cache_manager()
            cache_stats = cache_mgr.get_stats()
            if cache_stats['total_entries'] > 0:
                return gr.update(
                    value=(
                        f"<div style='background: linear-gradient(135deg, #e0e7ff 0%, #e9d5ff 100%); color: #000000 !important; padding: 1rem; border-radius: 8px; border: 1px solid rgba(99, 102, 241, 0.3);'>"
                        f"<h3 style='color: #000000 !important; margin-bottom: 0.5rem;'>💾 Cache Statistics</h3>"
                        f"<ul style='color: #000000 !important; margin: 0; padding-left: 1.5rem;'>"
                        f"<li style='color: #000000 !important;'>Total entries: <strong style='color: #000000 !important;'>{cache_stats['total_entries']}</strong></li>"
                        f"<li style='color: #000000 !important;'>Valid entries: <strong style='color: #000000 !important;'>{cache_stats['valid_entries']}</strong></li>"
                        f"<li style='color: #000000 !important;'>Expired entries: <strong style='color: #000000 !important;'>{cache_stats['expired_entries']}</strong></li>"
                        f"<li style='color: #000000 !important;'>L1 (in-memory) entries: <strong style='color: #000000 !important;'>{cache_stats['l1_entries']}</strong></li>"
                        f"<li style='color: #000000 !important;'>Cache size: <strong style='color: #000000 !important;'>{cache_stats['size_mb']} MB</strong></li>"
                        f"<li style='color: #000000 !important;'>TTL: <strong style='color: #000000 !important;'>{cache_stats['ttl_hours']} hours</strong></li>"
                        f"</ul></div>"
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

