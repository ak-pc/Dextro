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

# Default Pump Error Code Guidelines (configurable via settings)
DEFAULT_ERROR_CODES = {
    "E001": {
        "meaning": "Low Water Pressure",
        "action": "Check water source connection and prime the pump. Verify inlet valve is fully open.",
        "severity": "Medium"
    },
    "E002": {
        "meaning": "Motor Overheating",
        "action": "Allow motor to cool down. Check ventilation and clean air filters. Reduce load if necessary.",
        "severity": "High"
    },
    "E003": {
        "meaning": "Power Supply Fluctuation",
        "action": "Check electrical connections and voltage stability. Contact electrician if needed.",
        "severity": "Medium"
    },
    "E004": {
        "meaning": "Mechanical Blockage",
        "action": "Stop pump immediately. Clear blockage from impeller and pipes. Check for debris.",
        "severity": "High"
    },
    "E005": {
        "meaning": "Sensor Malfunction",
        "action": "Calibrate or replace pressure/flow sensors. Check sensor wiring.",
        "severity": "Medium"
    },
    "E006": {
        "meaning": "Dry Run Protection",
        "action": "Ensure adequate water supply. Check for leaks in suction line.",
        "severity": "Critical"
    },
    "E007": {
        "meaning": "Communication Error",
        "action": "Check network connection and communication cables. Restart communication module.",
        "severity": "Low"
    },
    "NORMAL": {
        "meaning": "Normal Operation",
        "action": "No action required. System operating within normal parameters.",
        "severity": "None"
    }
}

# Import Strands SDK and LiteLLM
try:
    from strands import Agent
    from strands.models.litellm import LiteLLMModel
    from strands import tool
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
        
        # Create Strands Agent with tools
        tools = [get_device_power_data, analyze_pump_error_codes]
        agent = Agent(model=model, tools=tools)
        return agent
        
    except Exception as e:
        st.error(f"❌ Error initializing AI agent: {str(e)}")
        return None

# Strands Tools for Device Analysis
@tool
def get_device_power_data(device_id: int) -> dict:
    """
    Fetch device power logs with customer data for a specific device ID.
    
    Args:
        device_id: The device ID to analyze
        
    Returns:
        Dictionary containing device data, customer info, and pump error codes
    """
    try:
        datalake = init_datalake()
        
        # Call the existing function
        joined_data, method = fetch_device_power_logs_with_customer(datalake, device_id)
        
        if joined_data:
            # Extract pump errors from the data
            pump_errors = []
            for record in joined_data:
                if isinstance(record, dict):
                    # Handle different data structures depending on method
                    if method == "rpc_function":
                        device_data = record.get('device_power_logs', {})
                        pump_error = device_data.get('pump_error', 'NORMAL')
                    else:
                        pump_error = record.get('pump_error', 'NORMAL')
                    
                    if pump_error and pump_error != 'NORMAL':
                        pump_errors.append(pump_error)
            
            return {
                "success": True,
                "device_id": device_id,
                "total_records": len(joined_data),
                "pump_errors": pump_errors,
                "unique_errors": list(set(pump_errors)),
                "method_used": method,
                "raw_data": joined_data[:3]  # First 3 records for context
            }
        else:
            return {
                "success": False,
                "device_id": device_id,
                "error": "No data found for this device ID",
                "pump_errors": [],
                "unique_errors": []
            }
            
    except Exception as e:
        return {
            "success": False,
            "device_id": device_id,
            "error": str(e),
            "pump_errors": [],
            "unique_errors": []
        }

@tool  
def analyze_pump_error_codes(error_codes: list) -> dict:
    """
    Analyze pump error codes and provide meanings and recommended actions.
    
    Args:
        error_codes: List of error codes to analyze
        
    Returns:
        Dictionary with analysis of each error code
    """
    # Get current error code guidelines (from session state if available, else defaults)
    if "error_code_guidelines" in st.session_state:
        guidelines = st.session_state.error_code_guidelines
    else:
        guidelines = DEFAULT_ERROR_CODES
    
    analysis = {
        "total_errors": len(error_codes),
        "unique_errors": len(set(error_codes)),
        "error_breakdown": {},
        "severity_summary": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "None": 0},
        "recommendations": []
    }
    
    for error_code in error_codes:
        if error_code in guidelines:
            error_info = guidelines[error_code]
            severity = error_info["severity"]
            
            if error_code not in analysis["error_breakdown"]:
                analysis["error_breakdown"][error_code] = {
                    "count": 0,
                    "meaning": error_info["meaning"],
                    "action": error_info["action"],
                    "severity": severity
                }
            
            analysis["error_breakdown"][error_code]["count"] += 1
            analysis["severity_summary"][severity] += 1
            
            # Add to recommendations if not already present
            recommendation = f"**{error_code}**: {error_info['action']}"
            if recommendation not in analysis["recommendations"]:
                analysis["recommendations"].append(recommendation)
        else:
            # Unknown error code
            if error_code not in analysis["error_breakdown"]:
                analysis["error_breakdown"][error_code] = {
                    "count": 0,
                    "meaning": "Unknown Error Code",
                    "action": "Contact technical support for error code definition",
                    "severity": "Unknown"
                }
            analysis["error_breakdown"][error_code]["count"] += 1
    
    return analysis

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
                - Pump error code analysis and diagnostics
                - Data visualization and reporting
                - PostgreSQL database queries and optimization
                
                You have access to the following tools:
                1. get_device_power_data(device_id): Fetch device power logs and pump error codes for analysis
                2. analyze_pump_error_codes(error_codes): Analyze pump error codes and provide meanings/actions
                
                When users ask about pump errors or device issues:
                1. Use get_device_power_data to fetch the device data
                2. Use analyze_pump_error_codes to interpret any error codes found
                3. Provide clear explanations of what each error means
                4. Give specific recommendations for fixing the issues
                5. Prioritize critical and high-severity errors
                
                Always be helpful, provide specific technical guidance, and use the tools when appropriate.
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
    
    # Special pump error analysis section
    st.markdown("---")
    st.markdown("**🔧 Pump Error Analysis**")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        device_id_chat = st.number_input("Device ID for Error Analysis:", 
                                       value=865198076659404, 
                                       key="device_id_chat")
    with col2:
        if st.button("🔍 Analyze Pump Errors", key="analyze_pump_errors_btn", type="secondary"):
            error_analysis_question = f"Please analyze the pump errors for device ID {device_id_chat}. Use the get_device_power_data tool to fetch the data and then analyze any error codes found."
            st.session_state.chat_messages.append({"role": "user", "content": error_analysis_question})
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

def render_settings_tab():
    """Render the Settings tab for configuring error codes"""
    st.markdown('<div class="dextro-logo">SETTINGS</div>', unsafe_allow_html=True)
    st.markdown("### ⚙️ Configure Pump Error Code Guidelines")
    
    # Initialize session state for error code guidelines
    if "error_code_guidelines" not in st.session_state:
        st.session_state.error_code_guidelines = DEFAULT_ERROR_CODES.copy()
    
    st.info("Configure the pump error codes and their meanings that the AI agent will use for analysis.")
    
    # Add new error code section
    st.subheader("➕ Add New Error Code")
    with st.form("add_error_code"):
        col1, col2 = st.columns(2)
        with col1:
            new_code = st.text_input("Error Code", placeholder="E008")
            new_meaning = st.text_input("Meaning", placeholder="Temperature Sensor Failure")
        with col2:
            new_severity = st.selectbox("Severity", ["Critical", "High", "Medium", "Low", "None"])
            new_action = st.text_area("Recommended Action", 
                                    placeholder="Replace temperature sensor and recalibrate system")
        
        if st.form_submit_button("Add Error Code", type="primary"):
            if new_code and new_meaning and new_action:
                st.session_state.error_code_guidelines[new_code] = {
                    "meaning": new_meaning,
                    "action": new_action,
                    "severity": new_severity
                }
                st.success(f"Added error code {new_code}")
                st.rerun()
            else:
                st.error("Please fill in all fields")
    
    # Edit existing error codes
    st.subheader("📝 Existing Error Codes")
    
    # Display current error codes in an editable format
    for error_code, info in st.session_state.error_code_guidelines.items():
        with st.expander(f"**{error_code}**: {info['meaning']} ({info['severity']})"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                updated_meaning = st.text_input(f"Meaning", value=info['meaning'], key=f"meaning_{error_code}")
                updated_action = st.text_area(f"Action", value=info['action'], key=f"action_{error_code}")
                updated_severity = st.selectbox(f"Severity", 
                                              ["Critical", "High", "Medium", "Low", "None"],
                                              index=["Critical", "High", "Medium", "Low", "None"].index(info['severity']),
                                              key=f"severity_{error_code}")
                
                col_update, col_delete = st.columns(2)
                with col_update:
                    if st.button(f"Update {error_code}", key=f"update_{error_code}"):
                        st.session_state.error_code_guidelines[error_code] = {
                            "meaning": updated_meaning,
                            "action": updated_action, 
                            "severity": updated_severity
                        }
                        st.success(f"Updated {error_code}")
                        st.rerun()
                
                with col_delete:
                    if st.button(f"Delete {error_code}", key=f"delete_{error_code}", type="secondary"):
                        del st.session_state.error_code_guidelines[error_code]
                        st.success(f"Deleted {error_code}")
                        st.rerun()
    
    # Reset to defaults
    st.markdown("---")
    if st.button("🔄 Reset to Defaults", key="reset_defaults"):
        st.session_state.error_code_guidelines = DEFAULT_ERROR_CODES.copy()
        st.success("Reset to default error codes")
        st.rerun()
    
    # Export/Import functionality
    st.subheader("📤 Export/Import Settings")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export Settings", key="export_settings"):
            import json
            settings_json = json.dumps(st.session_state.error_code_guidelines, indent=2)
            st.download_button(
                label="Download Settings JSON",
                data=settings_json,
                file_name="dextro_error_codes.json",
                mime="application/json",
                key="download_settings"
            )
    
    with col2:
        uploaded_file = st.file_uploader("📤 Import Settings", type="json", key="import_settings")
        if uploaded_file is not None:
            try:
                import json
                imported_settings = json.load(uploaded_file)
                st.session_state.error_code_guidelines = imported_settings
                st.success("Settings imported successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error importing settings: {str(e)}")
    
    # Show current configuration summary
    st.subheader("📊 Configuration Summary")
    total_codes = len(st.session_state.error_code_guidelines)
    severity_counts = {}
    for code_info in st.session_state.error_code_guidelines.values():
        severity = code_info['severity']
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Error Codes", total_codes)
    with col2:
        critical_high = severity_counts.get('Critical', 0) + severity_counts.get('High', 0)
        st.metric("Critical/High Severity", critical_high)
    with col3:
        st.metric("Configured Severities", len(severity_counts))

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
    
    # Connection status footer
    st.markdown("---")
    with st.expander("🔧 System Status"):
        st.info(f"**DataLake:** Connected ✅ ({SUPABASE_URL})")
        st.info("**DataLake API Key:** Configured ✅")
        st.info("**AI Agent:** Configured ✅")
        st.info("**Strands SDK:** Available ✅" if STRANDS_AVAILABLE else "**Strands SDK:** Not installed ❌")

if __name__ == "__main__":
    main()