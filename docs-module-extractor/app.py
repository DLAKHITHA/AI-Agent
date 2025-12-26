import asyncio
import json
import tempfile
import time
from typing import List, Optional
from typing import List, Dict


import pandas as pd
import streamlit as st
from streamlit_tags import st_tags

from analyzer import ModuleAnalyzer
from config import config
from crawler import SyncCrawler
from output_generator import OutputGenerator
from parser import DocumentationParser

# Page configuration
st.set_page_config(
    page_title="📚 Documentation Module Extractor",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #3B82F6;
        margin-top: 1.5rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #D1FAE5;
        border-left: 4px solid #10B981;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #DBEAFE;
        border-left: 4px solid #3B82F6;
        margin: 1rem 0;
    }
    .stProgress > div > div > div > div {
        background-color: #3B82F6;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables."""
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'urls' not in st.session_state:
        st.session_state.urls = []
    if 'crawled_pages' not in st.session_state:
        st.session_state.crawled_pages = 0

def validate_urls(urls: List[str]) -> List[str]:
    """Validate and clean URLs."""
    valid_urls = []
    
    for url in urls:
        url = url.strip()
        if not url:
            continue
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        
        # Basic validation
        if url.startswith(('http://', 'https://')):
            valid_urls.append(url)
        else:
            st.warning(f"Invalid URL skipped: {url}")
    
    return valid_urls

def process_documentation(urls: List[str], max_depth: int, use_llm: bool):
    """Main processing pipeline."""
    all_results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, url in enumerate(urls):
        status_text.text(f"Processing {i+1}/{len(urls)}: {url}")
        
        try:
            # Step 1: Crawl
            with st.spinner(f"Crawling {url}..."):
                crawler = SyncCrawler()
                pages_data = crawler.crawl_documentation(
                    url, 
                    max_depth=max_depth,
                    max_pages=config.MAX_PAGES_PER_SITE
                )
            
            if not pages_data:
                st.warning(f"No content found at {url}")
                continue
            
            st.session_state.crawled_pages = len(pages_data)
            st.success(f"Crawled {len(pages_data)} pages from {url}")
            
            # Step 2: Parse
            with st.spinner("Parsing content..."):
                parser = DocumentationParser()
                parsed_pages = parser.parse_multiple_pages(pages_data)
            
            # Step 3: Analyze
            with st.spinner("Analyzing modules and submodules..."):
                analyzer = ModuleAnalyzer(use_llm=use_llm)
                modules = analyzer.analyze_documentation(parsed_pages)
            
            if modules:
                all_results.extend(modules)
                st.success(f"Found {len(modules)} modules in {url}")
            else:
                st.warning(f"No modules identified in {url}")
            
        except Exception as e:
            st.error(f"Error processing {url}: {str(e)}")
            continue
        
        # Update progress
        progress_bar.progress((i + 1) / len(urls))
    
    status_text.text("Processing complete!")
    return all_results

def display_results(results: List[Dict], summary_stats: Dict):
    """Display analysis results in Streamlit."""
    st.markdown("---")
    st.markdown('<div class="sub-header">📊 Analysis Results</div>', unsafe_allow_html=True)
    
    # Summary stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Modules", summary_stats['total_modules'])
    with col2:
        st.metric("Total Submodules", summary_stats['total_submodules'])
    with col3:
        st.metric("Avg Confidence", f"{summary_stats['average_confidence']*100:.1f}%")
    with col4:
        st.metric("Pages Crawled", st.session_state.crawled_pages)
    
    # Module explorer
    st.markdown('<div class="sub-header">🔍 Module Explorer</div>', unsafe_allow_html=True)
    
    if results:
        # Create tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 List View", 
            "📊 Details", 
            "📈 Visualization", 
            "💾 Export"
        ])
        
        with tab1:
            # Module list with expanders
            for i, module in enumerate(results, 1):
                confidence = module.get('confidence_score', 0.5)
                confidence_color = (
                    "🟢" if confidence > 0.7 
                    else "🟡" if confidence > 0.5 
                    else "🔴"
                )
                
                with st.expander(
                    f"{confidence_color} {i}. {module['module']} "
                    f"({len(module['Submodules'])} submodules)"
                ):
                    st.write(f"**Description:** {module['Description']}")
                    st.write(f"**Confidence:** {confidence*100:.1f}%")
                    
                    if module['Submodules']:
                        st.write("**Submodules:**")
                        for submodule, description in module['Submodules'].items():
                            st.write(f"- **{submodule}:** {description}")
                    else:
                        st.write("*No submodules identified*")
        
        with tab2:
            # Detailed module view
            selected_module = st.selectbox(
                "Select a module to view details:",
                [m['module'] for m in results],
                index=0
            )
            
            module_data = next(m for m in results if m['module'] == selected_module)
            
            st.write(f"### {selected_module}")
            st.write(f"**Description:** {module_data['Description']}")
            st.write(f"**Confidence Score:** {module_data.get('confidence_score', 0.5)*100:.1f}%")
            
            if module_data['Submodules']:
                st.write("### Submodules")
                df = pd.DataFrame([
                    {"Submodule": sub, "Description": desc}
                    for sub, desc in module_data['Submodules'].items()
                ])
                st.dataframe(df, use_container_width=True)
        
        with tab3:
            # Visualization
            st.write("### Module Confidence Distribution")
            
            # Create dataframe for visualization
            df = pd.DataFrame({
                'Module': [m['module'] for m in results],
                'Confidence': [m.get('confidence_score', 0.5) for m in results],
                'Submodule Count': [len(m['Submodules']) for m in results]
            })
            
            # Display bar chart
            st.bar_chart(df.set_index('Module')['Confidence'])
            
            # Display scatter plot
            st.write("### Module Size vs Confidence")
            st.scatter_chart(
                df,
                x='Submodule Count',
                y='Confidence',
                size='Confidence',
                color='Confidence'
            )
        
        with tab4:
            # Export options
            st.write("### Export Results")
            
            output_gen = OutputGenerator()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("📥 Download JSON"):
                    json_output = output_gen.generate_json(results, include_metadata=True)
                    st.download_button(
                        label="Download JSON",
                        data=json_output,
                        file_name="documentation_modules.json",
                        mime="application/json"
                    )
            
            with col2:
                if st.button("📄 Download Markdown"):
                    md_output = output_gen.generate_markdown(results)
                    st.download_button(
                        label="Download Markdown",
                        data=md_output,
                        file_name="documentation_modules.md",
                        mime="text/markdown"
                    )
            
            with col3:
                if st.button("📊 Download CSV"):
                    csv_output = output_gen.generate_csv(results)
                    st.download_button(
                        label="Download CSV",
                        data=csv_output,
                        file_name="documentation_modules.csv",
                        mime="text/csv"
                    )
            
            with col4:
                if st.button("🌐 Download HTML Report"):
                    html_output = output_gen.generate_html_report(results)
                    st.download_button(
                        label="Download HTML",
                        data=html_output,
                        file_name="documentation_report.html",
                        mime="text/html"
                    )
            
            # Preview JSON
            st.write("### JSON Output Preview")
            json_preview = output_gen.generate_json(results[:2])  # Show first 2
            st.code(json_preview, language="json")
    
    else:
        st.warning("No modules were extracted from the documentation.")

def main():
    """Main Streamlit application."""
    initialize_session_state()
    
    # Header
    st.markdown('<div class="main-header">📚 AI-Powered Documentation Module Extractor</div>', unsafe_allow_html=True)
    
    st.markdown("""
    Extract structured modules and submodules from help documentation websites. 
    This tool automatically crawls documentation sites, analyzes content, and 
    identifies logical modules and their submodules.
    """)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        
        # URL input
        st.markdown("#### 📋 Input URLs")
        url_input = st.text_area(
            "Enter one URL per line:",
            height=150,
            value="https://help.instagram.com\nhttps://wordpress.org/documentation/",
            help="Enter URLs of documentation sites to analyze"
        )
        
        # Example URLs
        with st.expander("💡 Example URLs"):
            st.code("""https://help.instagram.com
https://wordpress.org/documentation/
https://support.neo.space/hc/en-us
https://help.zluri.com/
https://www.chargebee.com/docs/2.0/""")
        
        # Processing options
        st.markdown("#### ⚙️ Processing Options")
        
        max_depth = st.slider(
            "Crawling Depth",
            min_value=1,
            max_value=5,
            value=3,
            help="How many levels deep to crawl from the starting URL"
        )
        
        use_llm = st.checkbox(
            "Use AI for descriptions (requires OpenAI API key)",
            value=False,
            help="Use GPT for better descriptions (requires API key in .env file)"
        )
        
        if use_llm and not config.OPENAI_API_KEY:
            st.warning("⚠️ OpenAI API key not found. Add it to a .env file or environment variable.")
            use_llm = False
        
        # Advanced options
        with st.expander("🔧 Advanced Options"):
            config.MAX_PAGES_PER_SITE = st.number_input(
                "Max pages per site",
                min_value=10,
                max_value=200,
                value=50,
                help="Maximum number of pages to crawl per documentation site"
            )
            
            config.SIMILARITY_THRESHOLD = st.slider(
                "Module similarity threshold",
                min_value=0.1,
                max_value=0.9,
                value=0.7,
                step=0.1,
                help="Threshold for clustering similar modules"
            )
            
            config.CACHE_ENABLED = st.checkbox(
                "Enable caching",
                value=True,
                help="Cache crawled content to avoid re-fetching"
            )
        
        # Process button
        st.markdown("---")
        process_button = st.button(
            "🚀 Process Documentation",
            type="primary",
            use_container_width=True
        )
    
    # Main content area
    if process_button and url_input:
        urls = [url.strip() for url in url_input.split('\n') if url.strip()]
        valid_urls = validate_urls(urls)
        
        if not valid_urls:
            st.error("❌ Please enter valid URLs starting with http:// or https://")
            return
        
        st.session_state.processing = True
        st.session_state.urls = valid_urls
        
        # Display processing info
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        st.write(f"**Processing {len(valid_urls)} documentation site(s):**")
        for url in valid_urls:
            st.write(f"- {url}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Process documentation
        results = process_documentation(valid_urls, max_depth, use_llm)
        
        if results:
            st.session_state.results = results
            
            # Generate summary stats
            output_gen = OutputGenerator()
            summary_stats = output_gen.generate_summary_stats(results)
            
            # Display results
            display_results(results, summary_stats)
        else:
            st.error("❌ No modules could be extracted from the provided URLs.")
        
        st.session_state.processing = False
    
    elif st.session_state.results:
        # Display cached results
        output_gen = OutputGenerator()
        summary_stats = output_gen.generate_summary_stats(st.session_state.results)
        display_results(st.session_state.results, summary_stats)
    
    else:
        # Show instructions when not processing
        st.markdown("### 📖 How to Use")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            #### 1️⃣ Enter URLs
            Paste URLs of documentation sites in the sidebar.
            
            Examples:
            - Help centers
            - API documentation
            - User guides
            - Knowledge bases
            """)
        
        with col2:
            st.markdown("""
            #### 2️⃣ Configure Settings
            Adjust crawling depth and other options in the sidebar.
            
            Default settings work well for most documentation sites.
            Enable AI for better descriptions if you have an OpenAI API key.
            """)
        
        with col3:
            st.markdown("""
            #### 3️⃣ Extract & Export
            Click 'Process Documentation' to start extraction.
            
            View results in multiple formats:
            - Interactive module explorer
            - Visualizations
            - Export as JSON, CSV, Markdown, or HTML
            """)
        
        # Quick start examples
        st.markdown("### 🚀 Quick Start")
        
        example_col1, example_col2 = st.columns(2)
        
        with example_col1:
            if st.button("Try Instagram Help", use_container_width=True):
                st.session_state.urls = ["https://help.instagram.com"]
                st.rerun()
        
        with example_col2:
            if st.button("Try WordPress Docs", use_container_width=True):
                st.session_state.urls = ["https://wordpress.org/documentation/"]
                st.rerun()
        
        # Features
        st.markdown("### ✨ Features")
        
        features = [
            ("🌐 Multi-URL Support", "Process multiple documentation sites simultaneously"),
            ("🤖 AI-Powered Analysis", "Intelligent module identification using ML algorithms"),
            ("📊 Multiple Output Formats", "JSON, CSV, Markdown, HTML, and interactive visualizations"),
            ("⚡ Performance Optimized", "Async crawling, caching, and efficient processing"),
            ("🔧 Configurable", "Adjust crawling depth, similarity thresholds, and more"),
            ("📈 Confidence Scoring", "See how confident the system is about each module")
        ]
        
        cols = st.columns(3)
        for i, (title, desc) in enumerate(features):
            with cols[i % 3]:
                st.markdown(f"**{title}**")
                st.caption(desc)

if __name__ == "__main__":
    main()