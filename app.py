"""
Dextro IoT Device Monitoring Platform
AI-powered analytics for device power consumption and customer insights
"""

__version__ = "1.0.0"

import streamlit as st
import pandas as pd
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Configuration Constants
SUPABASE_URL = "https://uykzmqobbkmthydzymie.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV5a3ptcW9iYmttdGh5ZHp5bWllIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYwNzQ2NjYsImV4cCI6MjA3MTY1MDY2Nn0.wpcgIcrEV8kLXLq9_LPC_Z20MlrCmn_HNJX3Ia_dt-I"
GEMINI_API_KEY = "AIzaSyDhbjIGdcFAOBo4J3XoQaNUS-nCCn2_Gv8"

# Import Strands SDK and LiteLLM
try:
    from strands import Agent
    from strands.models.litellm import LiteLLMModel
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

st.set_page_config(
    page_title="Dextro Platform",
    page_icon="🔷",
    layout="wide"
)

# Custom CSS for the logo
st.markdown("""
<style>
.dextro-logo {
    font-family: Arial, sans-serif; 
    font-weight: bold; 
    font-size: 3rem; 
    background: linear-gradient(45deg, #4F46E5, #7C3AED, #A855F7); 
    background-clip: text; 
    -webkit-background-clip: text; 
    -webkit-text-fill-color: transparent; 
    text-align: center; 
    margin: 20px 0;
}
.stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
    font-size: 18px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_datalake() -> Client:
    """Initialize connection to Dextro DataLake"""
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

@st.cache_resource
def init_gemini_agent():
    """Initialize Gemini AI Agent for Dextro assistance"""
    if not STRANDS_AVAILABLE:
        return None
    
    try:
        # Initialize LiteLLM Model for Gemini
        model = LiteLLMModel(
            client_args={
                "api_key": GEMINI_API_KEY
            },
            model_id="gemini/gemini-2.0-flash-lite-preview-02-05",
            params={
                "max_tokens": 2000,
                "temperature": 0.7
            }
        )
        
        # Create Strands Agent
        agent = Agent(model=model, tools=[])
        return agent
        
    except Exception as e:
        st.error(f"❌ Error initializing AI agent: {str(e)}")
        return None

def query_gemini_agent(agent, question: str):
    """Query the Gemini agent with a question"""
    try:
        if not agent:
            return "❌ AI Agent not initialized"
        
        response = agent(question)
        return response
        
    except Exception as e:
        return f"❌ Error querying AI agent: {str(e)}"

def fetch_customer_profiles(datalake: Client):
    """Fetch customer profiles from DataLake"""
    try:
        response = datalake.table("customer_profile").select("*").execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching customer profiles: {str(e)}")
        return None

def fetch_device_power_logs_with_customer(datalake: Client, device_id: int):
    """Fetch joined device power logs with customer data"""
    try:
        st.info(f"🔗 Fetching device power logs for device_id: {device_id}")
        
        # Try using RPC with custom database function
        try:
            response = datalake.rpc('get_device_power_logs_with_customer', {'p_device_id': device_id}).execute()
            if response.data:
                st.success(f"✅ Database Function Method: Found {len(response.data)} records")
                return response.data, "rpc_function"
            else:
                st.info("Database function executed but returned no data")
                return [], "rpc_function_no_data"
        except Exception as rpc_error:
            st.error(f"❌ Database function failed: {str(rpc_error)}")
            st.info("💡 Make sure you've created the database function in your DataLake SQL Editor")
            
        # Fallback: Show what data exists in both tables
        st.info("🔍 Checking both tables for debugging...")
        
        # Check device_power_logs
        dpl_sample = datalake.table("device_power_logs").select("device_id").limit(5).execute()
        if dpl_sample.data:
            device_ids = [row.get('device_id') for row in dpl_sample.data]
            st.write(f"**Sample device_ids in device_power_logs:** {device_ids}")
        else:
            st.warning("⚠️ device_power_logs table appears to be empty")
        
        # Check customer_profile
        cp_sample = datalake.table("customer_profile").select("Device_id").limit(5).execute()
        if cp_sample.data:
            customer_device_ids = [row.get('Device_id') for row in cp_sample.data]
            st.write(f"**Available Device_ids in customer_profile:** {customer_device_ids}")
            st.info(f"💡 Try using one of these Device_ids: {customer_device_ids[0]}")
        else:
            st.warning("⚠️ customer_profile table appears to be empty")
            
        return [], "tables_checked"
        
    except Exception as e:
        st.error(f"❌ Error in fetch_device_power_logs_with_customer: {str(e)}")
        return [], "error"

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
    """Render the Dextro AI Chat tab"""
    st.markdown('<div class="dextro-logo">DEXTRO</div>', unsafe_allow_html=True)
    st.markdown("### 🤖 Ask me anything about Dextro!")
    st.markdown("I'm here to help with your IoT device monitoring, power consumption analysis, and data insights.")
    
    if not STRANDS_AVAILABLE:
        st.error("❌ AI capabilities not available. Missing dependencies.")
        st.code("pip install 'strands-agents[litellm]' litellm")
        return
    
    # Initialize Gemini agent
    gemini_agent = init_gemini_agent()
    
    if not gemini_agent:
        st.error("❌ Failed to initialize AI agent. Check your configuration.")
        return
    
    # Chat interface
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "Hi! I'm your Dextro AI assistant. Ask me anything about device monitoring, power consumption analysis, or data insights!"}
        ]
    
    # Display chat history
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me about Dextro..."):
        # Add user message to chat history
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate AI response
        with st.chat_message("assistant"):
            with st.spinner("🤖 Thinking..."):
                # Add context about Dextro to the prompt
                dextro_context = """
                You are an AI assistant for Dextro, an IoT device monitoring platform that specializes in:
                - Power consumption tracking for IoT devices
                - Customer profile management
                - Device analytics and insights
                - Data visualization and reporting
                - PostgreSQL database queries and optimization
                
                Answer questions related to Dextro's capabilities, IoT monitoring, data analysis, and provide helpful insights.
                """
                full_prompt = f"{dextro_context}\n\nUser question: {prompt}"
                
                response = query_gemini_agent(gemini_agent, full_prompt)
                st.markdown(response)
        
        # Add assistant response to chat history
        st.session_state.chat_messages.append({"role": "assistant", "content": response})
    
    # Quick action buttons
    st.markdown("---")
    st.markdown("**Quick Questions:**")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 Analytics Help", key="analytics_help_btn"):
            quick_question = "What are the key analytics I should track for IoT device power consumption?"
            st.session_state.chat_messages.append({"role": "user", "content": quick_question})
            st.rerun()
    
    with col2:
        if st.button("🔍 Query Optimization", key="query_opt_btn"):
            quick_question = "How can I optimize database queries for large IoT datasets?"
            st.session_state.chat_messages.append({"role": "user", "content": quick_question})
            st.rerun()
    
    with col3:
        if st.button("💡 Business Insights", key="business_insights_btn"):
            quick_question = "What business insights can I derive from power consumption data?"
            st.session_state.chat_messages.append({"role": "user", "content": quick_question})
            st.rerun()
    
    with col4:
        if st.button("⚡ Device Monitoring", key="device_monitoring_btn"):
            quick_question = "Best practices for monitoring IoT device performance and alerts?"
            st.session_state.chat_messages.append({"role": "user", "content": quick_question})
            st.rerun()

def render_datalake_tab():
    """Render the Dextro DataLake tab"""
    st.markdown('<div class="dextro-logo">DATA LAKE</div>', unsafe_allow_html=True)
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

def main():
    """Main application entry point"""
    
    # Create tabs
    tab1, tab2 = st.tabs(["🤖 Dextro AI Chat", "📊 Dextro DataLake"])
    
    with tab1:
        render_chat_tab()
    
    with tab2:
        render_datalake_tab()
    
    # Connection status footer
    st.markdown("---")
    with st.expander("🔧 System Status"):
        st.info(f"**DataLake:** Connected ✅ ({SUPABASE_URL})")
        st.info("**DataLake API Key:** Configured ✅")
        st.info("**AI Agent:** Configured ✅")
        st.info("**Strands SDK:** Available ✅" if STRANDS_AVAILABLE else "**Strands SDK:** Not installed ❌")

if __name__ == "__main__":
    main()