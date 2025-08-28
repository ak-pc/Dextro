"""
Chart and Visualization Utilities for Dextro Platform
Handles chart generation and data visualization for LLM responses
"""

import streamlit as st
import pandas as pd

def render_chart_if_data_available(data, chart_title="Data Visualization"):
    """Create charts if data is available in the response"""
    try:
        import plotly.express as px
        import plotly.graph_objects as go
        
        if isinstance(data, list) and len(data) > 0:
            df = pd.DataFrame(data)
            
            # Check if we have numeric data that can be visualized
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            
            if len(numeric_cols) > 0:
                st.subheader(f"📊 {chart_title}")
                
                # Create tabs for different chart types
                tab1, tab2, tab3 = st.tabs(["📈 Line Chart", "📊 Bar Chart", "🥧 Summary"])
                
                with tab1:
                    if 'created_on_date' in df.columns or 'timestamp' in df.columns:
                        time_col = 'created_on_date' if 'created_on_date' in df.columns else 'timestamp'
                        for col in numeric_cols[:3]:  # Limit to first 3 numeric columns
                            fig = px.line(df, x=time_col, y=col, title=f"{col} over time")
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No time-series data available for line charts")
                
                with tab2:
                    for col in numeric_cols[:3]:  # Limit to first 3 numeric columns
                        fig = px.bar(df.head(10), x=df.index[:10], y=col, title=f"{col} distribution")
                        st.plotly_chart(fig, use_container_width=True)
                
                with tab3:
                    st.write("**Data Summary:**")
                    st.dataframe(df.describe(), use_container_width=True)
                    
                return True
    except Exception as e:
        st.info(f"Chart creation skipped: {e}")
    
    return False

def create_error_code_chart(error_analysis):
    """Create specialized charts for pump error code analysis"""
    try:
        import plotly.express as px
        import plotly.graph_objects as go
        
        if not error_analysis or not isinstance(error_analysis, dict):
            return False
        
        st.subheader("📊 Pump Error Analysis")
        
        # Create tabs for different visualizations
        tab1, tab2, tab3 = st.tabs(["🔴 Error Distribution", "⚠️ Severity Analysis", "📋 Summary"])
        
        with tab1:
            # Error code frequency chart
            error_breakdown = error_analysis.get("error_breakdown", {})
            if error_breakdown:
                error_codes = list(error_breakdown.keys())
                error_counts = [error_breakdown[code]["count"] for code in error_codes]
                
                fig = px.bar(
                    x=error_codes, 
                    y=error_counts,
                    title="Error Code Frequency",
                    labels={'x': 'Error Code', 'y': 'Count'}
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            # Severity pie chart
            severity_summary = error_analysis.get("severity_summary", {})
            if severity_summary:
                # Filter out zero values
                filtered_severity = {k: v for k, v in severity_summary.items() if v > 0}
                if filtered_severity:
                    fig = px.pie(
                        values=list(filtered_severity.values()),
                        names=list(filtered_severity.keys()),
                        title="Error Severity Distribution"
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Errors", error_analysis.get("total_errors", 0))
            with col2:
                st.metric("Unique Error Types", error_analysis.get("unique_errors", 0))
            with col3:
                critical_high = (
                    severity_summary.get("Critical", 0) + 
                    severity_summary.get("High", 0)
                )
                st.metric("Critical/High Severity", critical_high)
            
            # Recommendations
            recommendations = error_analysis.get("recommendations", [])
            if recommendations:
                st.subheader("🛠️ Recommended Actions")
                for rec in recommendations:
                    st.write(f"• {rec}")
        
        return True
        
    except Exception as e:
        st.info(f"Error chart creation skipped: {e}")
        return False

def detect_chart_opportunity(response_text, tool_data=None):
    """Detect if the LLM response contains data that could be visualized"""
    chart_keywords = [
        "chart", "graph", "plot", "visualize", "data", "analysis", "trend",
        "distribution", "comparison", "statistics", "metrics", "summary"
    ]
    
    # Check if response mentions visualization
    response_lower = response_text.lower()
    has_chart_keywords = any(keyword in response_lower for keyword in chart_keywords)
    
    # Check if we have actual data to visualize
    has_data = tool_data and isinstance(tool_data, (list, dict)) and len(tool_data) > 0
    
    return has_chart_keywords or has_data

def create_device_power_chart(device_data):
    """Create specialized charts for device power data"""
    try:
        import plotly.express as px
        import plotly.graph_objects as go
        
        if not device_data or not isinstance(device_data, list):
            return False
        
        df = pd.DataFrame(device_data)
        
        if df.empty:
            return False
        
        st.subheader("📊 Device Power Analysis")
        
        # Create tabs for different visualizations
        tab1, tab2, tab3 = st.tabs(["⚡ Power Trends", "🔧 Error Timeline", "📈 Metrics"])
        
        with tab1:
            # Power consumption over time
            if 'created_on_date' in df.columns:
                # Extract numeric power values
                if 'power' in df.columns:
                    power_numeric = pd.to_numeric(
                        df['power'].astype(str).str.replace('W', '').str.replace(',', ''),
                        errors='coerce'
                    )
                    df['power_numeric'] = power_numeric
                    
                    fig = px.line(
                        df, 
                        x='created_on_date', 
                        y='power_numeric',
                        title="Power Consumption Over Time",
                        labels={'power_numeric': 'Power (W)', 'created_on_date': 'Time'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Voltage and current if available
                for metric in ['voltage', 'current']:
                    if metric in df.columns:
                        numeric_values = pd.to_numeric(df[metric], errors='coerce')
                        if not numeric_values.isna().all():
                            fig = px.line(
                                df, 
                                x='created_on_date', 
                                y=metric,
                                title=f"{metric.title()} Over Time"
                            )
                            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            # Error code timeline
            if 'pump_error' in df.columns and 'created_on_date' in df.columns:
                error_timeline = df[df['pump_error'] != 'NORMAL'].copy() if 'pump_error' in df.columns else df
                
                if not error_timeline.empty:
                    fig = px.scatter(
                        error_timeline,
                        x='created_on_date',
                        y='pump_error',
                        title="Error Events Timeline",
                        labels={'pump_error': 'Error Code', 'created_on_date': 'Time'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No error events found in the data")
        
        with tab3:
            # Summary statistics
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                st.write("**Statistical Summary:**")
                st.dataframe(df[numeric_cols].describe(), use_container_width=True)
            
            # Data quality metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Records", len(df))
            with col2:
                error_count = len(df[df['pump_error'] != 'NORMAL']) if 'pump_error' in df.columns else 0
                st.metric("Error Events", error_count)
            with col3:
                completeness = (1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100
                st.metric("Data Completeness", f"{completeness:.1f}%")
        
        return True
        
    except Exception as e:
        st.info(f"Device power chart creation skipped: {e}")
        return False