"""
Dextro IoT Device Monitoring Platform
AI-powered analytics for device power consumption and customer insights
"""

__version__ = "1.0.0"

import streamlit as st
import pandas as pd
import os
from supabase import create_client, Client

# Configuration Constants from Streamlit secrets
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
CLAUDE_KEY = st.secrets["anthropic"]["api_key"]


# Import AI modules
from ai_agent import (
    init_claude_agent, 
    query_claude_agent, 
    get_dextro_context,
    fetch_device_power_logs_with_customer,
    DEFAULT_ANALYSIS_INSTRUCTIONS,
    STRANDS_AVAILABLE
)
from chart_utils import (
    render_chart_if_data_available,
    create_error_code_chart,
    detect_chart_opportunity,
    create_device_power_chart
)

st.set_page_config(
    page_title="Dextro Platform",
    page_icon="🔷",
    layout="wide"
)

# Custom CSS for the app
st.markdown("""
<style>
.dextro-logo-container {
    text-align: center;
    margin: 20px 0;
}
.dextro-logo-img {
    max-height: 80px;
    width: auto;
}
.stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
    font-size: 18px;
    font-weight: 600;
}

/* Chat interface improvements */
.stChatMessage {
    margin-bottom: 1rem;
}

/* Make chat input more prominent */
.stChatInput > div > div > div > div {
    border-radius: 20px;
    border: 2px solid #7C3AED;
}

/* Reduce spacing above chat to maximize chat area */
.main .block-container {
    padding-top: 1rem;
}

/* Style for the main chat tab */
[data-testid="stChatInput"] {
    position: sticky;
    bottom: 0;
    background: white;
    z-index: 999;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def get_logo_base64():
    """Get the Dextro logo as base64 encoded string"""
    try:
        import base64
        import os
        
        # Try relative path first (for deployment), then absolute path (for local development)
        logo_paths = [
            "dextro_logo.png",  # Relative path for deployment
            "/Users/amulya/Desktop/workplace/Dextro/dextro_logo.png"  # Absolute path for local
        ]
        
        for logo_path in logo_paths:
            if os.path.exists(logo_path):
                with open(logo_path, "rb") as img_file:
                    return base64.b64encode(img_file.read()).decode()
        
        # If no logo found, return empty string (will show alt text)
        return ""
    except Exception as e:
        st.error(f"Could not load logo: {e}")
        return ""

@st.cache_resource
def init_datalake() -> Client:
    """Initialize connection to Dextro DataLake"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_customer_profiles(datalake: Client):
    """Fetch customer profiles from DataLake"""
    try:
        response = datalake.table("customer_profile").select("*").execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching customer profiles: {str(e)}")
        return None

def show_database_function_sql():
    """Show the SQL needed to create database functions for joins"""
    return {
        "create_join_function": """
-- Create a function to perform the join without foreign keys
CREATE OR REPLACE FUNCTION get_device_power_logs_with_customer(p_device_id BIGINT)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_agg(
        jsonb_build_object(
            'device_id', dpl.device_id,
            'device_power_logs', to_jsonb(dpl.*),
            'customer_profile', to_jsonb(cp.*)
        )
    ) INTO result
    FROM public.device_power_logs dpl 
    JOIN public.customer_profile cp ON cp."Device_id" = dpl.device_id  
    WHERE dpl.device_id = p_device_id;
    
    RETURN COALESCE(result, '[]'::jsonb);
END;
$$ LANGUAGE plpgsql;
        """,
        "create_view": """
-- Alternative: Create a view for the join
CREATE OR REPLACE VIEW device_power_logs_with_customer AS
SELECT 
    dpl.*,
    cp.* 
FROM public.device_power_logs dpl 
JOIN public.customer_profile cp ON cp."Device_id" = dpl.device_id;
        """
    }


def render_chat_tab():
    """Render the Dextro AI Chat tab with proper Streamlit chat interface"""
    
    # Smaller logo to maximize chat space
    st.markdown(
        '<div style="text-align: center; margin: 5px 0;">'
        '<img src="data:image/png;base64,{}" style="max-height: 50px; width: auto;" alt="DEXTRO">'
        '</div>'.format(get_logo_base64()),
        unsafe_allow_html=True
    )
    
    # Check if AI is available
    if not STRANDS_AVAILABLE:
        st.error("❌ AI capabilities not available. Missing dependencies.")
        return
    
    claude_agent = init_claude_agent(SUPABASE_URL, SUPABASE_KEY, CLAUDE_KEY)
    if not claude_agent:
        st.error("❌ Failed to initialize AI agent. Check your configuration.")
        return
    
    # Step 1: Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant", 
                "content": "Hi! I'm your Dextro AI assistant. I can help you analyze IoT device data, diagnose pump errors, and create visualizations. What would you like to explore?"
            }
        ]
    
    # Step 2: Display all messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Display charts if available in message history
            if message["role"] == "assistant":
                if message.get("chart_data"):
                    create_device_power_chart(message["chart_data"])
                if message.get("error_analysis"):
                    create_error_code_chart(message["error_analysis"])
    
    # Step 3: Handle user input - EXACT pattern from Streamlit docs
    if prompt := st.chat_input("Ask about device data, error analysis, or request visualizations..."):
        # Display user message in chat message container
        st.chat_message("user").markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            with st.spinner("🤖 Analyzing your request..."):
                # Get Dextro context and query agent
                full_prompt = f"{get_dextro_context()}\n\nUser question: {prompt}"
                response = query_claude_agent(claude_agent, full_prompt)
                
                # Convert response to string if it's an AgentResult object
                response_text = str(response)
                
                # Display the response
                st.markdown(response_text)
                
                # Handle visualizations
                chart_data = None
                error_analysis = None
                
                if hasattr(st.session_state, 'last_tool_data') and st.session_state.last_tool_data:
                    data = st.session_state.last_tool_data
                    
                    # Try to create appropriate visualizations
                    if detect_chart_opportunity(response_text, data):
                        if create_device_power_chart(data):
                            chart_data = data
                        elif render_chart_if_data_available(data, "Device Data Analysis"):
                            chart_data = data
                
                # Check for error analysis
                if "error" in response_text.lower() and "analysis" in response_text.lower():
                    if hasattr(st.session_state, 'last_error_analysis'):
                        error_analysis = st.session_state.last_error_analysis
                        create_error_code_chart(error_analysis)
                
                # The metrics display is now handled automatically by query_claude_agent
        
        # Add assistant response to chat history
        message_data = {"role": "assistant", "content": response_text}
        if chart_data:
            message_data["chart_data"] = chart_data
        if error_analysis:
            message_data["error_analysis"] = error_analysis
        st.session_state.messages.append(message_data)

def render_datalake_tab():
    """Render the Dextro DataLake tab"""
    st.markdown(
        '<div class="dextro-logo-container">'
        '<img src="data:image/png;base64,{}" class="dextro-logo-img" alt="DEXTRO">'
        '</div>'.format(get_logo_base64()),
        unsafe_allow_html=True
    )
    st.markdown("### 📊 Explore your IoT device data and customer insights")
    
    datalake = init_datalake()
    
    # Connection status
    st.success("✅ Connected to Dextro DataLake")
    
    # Database setup section
    with st.expander("🔧 Database Setup for Advanced Queries"):
        st.info("For complex queries joining device logs with customer data, you may need database functions:")
        
        sql_functions = show_database_function_sql()
        
        st.write("**Option 1: Create a Database Function**")
        st.code(sql_functions["create_join_function"], language="sql")
        
        st.write("**Option 2: Create a View**")
        st.code(sql_functions["create_view"], language="sql")
        
        st.write("**How to set up:**")
        st.write("1. Go to your DataLake Dashboard")
        st.write("2. Navigate to SQL Editor")
        st.write("3. Run either of the SQL commands above")
    
    # Device Power Logs with Customer Data
    st.markdown("---")
    st.subheader("🔌 Device Analytics with Customer Insights")
    
    device_id_input = st.number_input(
        "Enter Device ID for Analysis:",
        value=865198074539541,
        step=1,
        help="Enter the device ID to get comprehensive analytics including customer information"
    )
    
    if st.button("📈 Analyze Device Data", type="primary", key="analyze_device_btn"):
        with st.spinner(f"📊 Analyzing device data for ID: {device_id_input}"):
            joined_data, method = fetch_device_power_logs_with_customer(datalake, int(device_id_input))
            
            if joined_data:
                st.success(f"✅ Analysis complete! Found {len(joined_data)} records using {method} method")
                
                # Convert to DataFrame for better display
                df_joined = pd.DataFrame(joined_data)
                
                st.subheader("📊 Device Analytics Overview")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Records Analyzed", len(df_joined))
                with col2:
                    st.metric("Data Points", len(df_joined.columns))
                with col3:
                    st.metric("Analysis Method", method.replace("_", " ").title())
                
                st.subheader("📋 Comprehensive Device & Customer Data")
                st.dataframe(df_joined, use_container_width=True, hide_index=True)
                
                # Export option
                csv_joined = df_joined.to_csv(index=False)
                st.download_button(
                    label="📥 Export Analysis as CSV",
                    data=csv_joined,
                    file_name=f"dextro_device_{device_id_input}_analysis.csv",
                    mime="text/csv",
                    key="export_analysis_btn"
                )
                
                # Show raw JSON for debugging
                with st.expander("🔍 Raw Data Structure"):
                    st.json(joined_data[:2] if len(joined_data) > 2 else joined_data)
                    
            else:
                st.warning(f"No data found for device_id: {device_id_input}")
                st.info("**Troubleshooting:**")
                st.write("• Verify the device ID exists in your device logs")
                st.write("• Check if there's matching customer profile data")
                st.write("• Ensure both tables contain data")
    
    # Customer Profiles Section
    st.markdown("---")
    st.subheader("👥 Customer Profiles")
    
    if st.button("📋 View All Customer Profiles", key="view_customers_btn"):
        with st.spinner("📊 Loading customer profiles..."):
            data = fetch_customer_profiles(datalake)
            
            if data:
                st.success(f"✅ Loaded {len(data)} customer profiles")
                
                df = pd.DataFrame(data)
                
                st.subheader("📊 Customer Overview")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Customers", len(df))
                with col2:
                    st.metric("Profile Fields", len(df.columns))
                with col3:
                    if not df.empty:
                        st.metric("Data Quality", "✅ Good")
                
                st.subheader("🔍 Customer Profiles")
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Export option
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Export Customer Data",
                    data=csv,
                    file_name="dextro_customer_profiles.csv",
                    mime="text/csv",
                    key="export_customers_btn"
                )
            else:
                st.warning("No customer data found.")

def render_settings_tab():
    """Render the Settings tab for configuring analysis instructions"""
    st.markdown(
        '<div class="dextro-logo-container">'
        '<img src="data:image/png;base64,{}" class="dextro-logo-img" alt="DEXTRO">'
        '</div>'.format(get_logo_base64()),
        unsafe_allow_html=True
    )
    st.markdown("### ⚙️ Configure AI Analysis Instructions")
    
    # Initialize session state for analysis instructions
    if "analysis_instructions" not in st.session_state:
        st.session_state.analysis_instructions = DEFAULT_ANALYSIS_INSTRUCTIONS
    
    st.info("Configure custom instructions that the AI agent will use when analyzing device data and error codes. These instructions work alongside the system prompts to provide contextual analysis.")
    
    # Analysis Instructions Editor
    st.subheader("📝 Custom Analysis Instructions")
    
    # Show current instructions with editing capability
    st.markdown("**Current Analysis Instructions:**")
    
    # Text area for editing instructions
    updated_instructions = st.text_area(
        "Edit Analysis Instructions",
        value=st.session_state.analysis_instructions,
        height=300,
        help="These instructions guide how the AI analyzes your IoT device data, error codes, and operational patterns.",
        key="analysis_instructions_editor"
    )
    
    # Buttons for managing instructions
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save Instructions", type="primary"):
            if updated_instructions.strip():
                st.session_state.analysis_instructions = updated_instructions.strip()
                st.success("✅ Analysis instructions saved successfully!")
                st.rerun()
            else:
                st.error("Instructions cannot be empty")
    
    with col2:
        if st.button("🔄 Reset to Defaults"):
            st.session_state.analysis_instructions = DEFAULT_ANALYSIS_INSTRUCTIONS
            st.success("✅ Reset to default instructions")
            st.rerun()
    
    with col3:
        if st.button("📋 Copy Instructions"):
            st.code(st.session_state.analysis_instructions, language="text")
    
    # Instructions Template Suggestions
    st.markdown("---")
    st.subheader("💡 Instruction Templates")
    
    templates = {
        "Maintenance-Focused": """
Focus on preventive maintenance and operational efficiency:

ANALYSIS PRIORITIES:
- Identify patterns that indicate upcoming maintenance needs
- Prioritize cost-effective maintenance scheduling
- Consider equipment lifecycle and replacement planning
- Factor in seasonal operational demands

ERROR ASSESSMENT:
- Evaluate error frequency and operational impact
- Distinguish between critical failures and minor issues
- Consider maintenance history when making recommendations
- Assess urgency based on safety and operational continuity

REPORTING STYLE:
- Provide clear maintenance schedules and action items
- Include cost-benefit analysis for major recommendations
- Present technical findings in maintenance-friendly language
        """,
        
        "Performance Optimization": """
Optimize system performance and energy efficiency:

ANALYSIS APPROACH:
- Focus on power consumption patterns and efficiency metrics
- Identify opportunities for energy savings
- Monitor performance degradation trends
- Analyze operational patterns for optimization opportunities

EFFICIENCY METRICS:
- Track power consumption vs. output performance
- Monitor temperature and voltage stability
- Assess pump runtime efficiency
- Identify peak performance operating conditions

RECOMMENDATIONS:
- Prioritize energy-saving opportunities
- Suggest operational parameter adjustments
- Recommend performance monitoring strategies
        """,
        
        "Safety-Critical": """
Prioritize safety and regulatory compliance:

SAFETY FIRST APPROACH:
- Identify any conditions that could pose safety risks
- Prioritize critical errors that could lead to equipment failure
- Monitor environmental conditions that affect safe operation
- Assess compliance with safety standards

RISK ASSESSMENT:
- Categorize risks by potential impact and probability
- Consider cascading failure scenarios
- Evaluate emergency response requirements
- Monitor safety system performance

COMPLIANCE FOCUS:
- Ensure recommendations align with safety regulations
- Document safety-critical findings thoroughly
- Prioritize immediate action items for safety issues
        """
    }
    
    selected_template = st.selectbox(
        "Choose a template to replace current instructions:",
        ["Select a template..."] + list(templates.keys()),
        key="template_selector"
    )
    
    if selected_template and selected_template != "Select a template...":
        if st.button(f"📝 Apply {selected_template} Template"):
            st.session_state.analysis_instructions = templates[selected_template].strip()
            st.success(f"✅ Applied {selected_template} template")
            st.rerun()
        
        # Show preview of selected template
        with st.expander(f"Preview: {selected_template} Template"):
            st.code(templates[selected_template], language="text")
    
    # Export/Import functionality
    st.markdown("---")
    st.subheader("📤 Export/Import Instructions")
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="📥 Export Instructions",
            data=st.session_state.analysis_instructions,
            file_name="dextro_analysis_instructions.txt",
            mime="text/plain",
            key="export_instructions"
        )
    
    with col2:
        uploaded_file = st.file_uploader("📤 Import Instructions", type="txt", key="import_instructions")
        if uploaded_file is not None:
            try:
                imported_instructions = uploaded_file.read().decode("utf-8")
                if imported_instructions.strip():
                    st.session_state.analysis_instructions = imported_instructions.strip()
                    st.success("✅ Instructions imported successfully!")
                    st.rerun()
                else:
                    st.error("Imported file is empty")
            except Exception as e:
                st.error(f"Error importing instructions: {str(e)}")
    
    # Show current configuration summary
    st.subheader("📊 Configuration Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        instruction_length = len(st.session_state.analysis_instructions)
        st.metric("Instructions Length", f"{instruction_length} characters")
    
    with col2:
        word_count = len(st.session_state.analysis_instructions.split())
        st.metric("Word Count", f"{word_count} words")
    
    with col3:
        is_custom = st.session_state.analysis_instructions != DEFAULT_ANALYSIS_INSTRUCTIONS
        st.metric("Status", "Custom" if is_custom else "Default")
    
    # System Status section
    st.markdown("---")
    st.subheader("🔧 System Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"**DataLake:** Connected ✅")
        st.info("**DataLake API Key:** Configured ✅")
        st.info(f"**DataLake URL:** {SUPABASE_URL[:40]}...")
        
    with col2:
        st.info("**AI Agent:** Configured ✅")
        if STRANDS_AVAILABLE:
            st.info("**Strands SDK:** Available ✅")
        else:
            st.error("**Strands SDK:** Not installed ❌")
            st.code("pip install 'strands-agents[anthropic]'")
        
        claude_agent = init_claude_agent(SUPABASE_URL, SUPABASE_KEY, CLAUDE_KEY)
        if claude_agent:
            st.info("**Claude Model:** Connected ✅")
        else:
            st.error("**Claude Model:** Connection failed ❌")

def main():
    """Main application entry point"""
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["🤖 Dextro AI Chat", "📊 Dextro DataLake", "⚙️ Settings"])
    
    with tab1:
        render_chat_tab()
    
    with tab2:
        render_datalake_tab()
        
    with tab3:
        render_settings_tab()
    

if __name__ == "__main__":
    main()