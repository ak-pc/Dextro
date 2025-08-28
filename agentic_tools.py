#!/usr/bin/env python3
"""
Enhanced Agentic Tools for Dextro Solar IoT Platform
Comprehensive tool set for business intelligence and device monitoring
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from strands import tool

logger = logging.getLogger(__name__)

# =============================================================================
# BUSINESS INTELLIGENCE TOOLS (Custom RPC Functions)
# =============================================================================

@tool
def get_business_performance_summary(date_range_days: int = 20) -> Dict[str, Any]:
    """
    Get comprehensive business performance summary with environmental impact calculations.
    
    This tool provides executive-level business insights including:
    - New device installations and CO2 impact
    - Top performing locations by energy consumption
    - Fleet health overview
    - Key performance indicators
    
    Args:
        date_range_days: Number of days to analyze (default: 1 for today)
        
    Returns:
        Dict containing business performance metrics
        
    Supabase RPC Function: rpc_business_performance_summary
    """
    from ai_agent import supabase_manager
    
    try:
        logger.info(f"Fetching business performance summary for {date_range_days} days")
        
        # Log exact parameters being sent
        params = {'p_date_range_days': date_range_days}
        logger.info(f"RPC Parameters: {params}")
        logger.info(f"Parameter types: {[(k, type(v).__name__) for k, v in params.items()]}")
        
        # Call custom RPC function for complex business calculations
        logger.info("Making RPC call to rpc_business_performance_summary")
        result = supabase_manager.client.rpc(
            'rpc_business_performance_summary',
            params
        ).execute()
        
        logger.info(f"RPC Response status: {result}")
        logger.info(f"RPC Response data length: {len(result.data) if result.data else 0}")
        
        if result.data and len(result.data) > 0:
            # Convert TABLE format to dictionary for easy access
            metrics = {}
            for row in result.data:
                metrics[row['metric_name']] = {
                    'value': row['metric_value'],
                    'description': row['metric_description'],
                    'info': row['additional_info']
                }
            
            # Extract key values
            new_devices = int(metrics.get('new_devices_installed', {}).get('value', 0))
            co2_savings = int(metrics.get('co2_savings_tonnes', {}).get('value', 0))
            top_location_energy = metrics.get('top_energy_location', {}).get('value', 0)
            top_location_name = metrics.get('top_energy_location', {}).get('info', 'Unknown')
            
            response_data = {
                "success": True,
                "summary": {
                    "new_devices_installed": new_devices,
                    "environmental_impact": {
                        "co2_savings_tonnes_annual": co2_savings,
                        "impact_statement": f"{new_devices} new devices were installed in the last {date_range_days} day(s), saving approximately {co2_savings} tonnes of CO2 annually"
                    },
                    "top_performer": {
                        "location": top_location_name,
                        "energy_consumed": float(top_location_energy) if top_location_energy else 0
                    },
                    "fleet_metrics": {
                        "total_active_devices": int(metrics.get('total_active_devices', {}).get('value', 0)),
                        "average_efficiency": float(metrics.get('average_efficiency', {}).get('value', 0)),
                        "total_water_produced_today": float(metrics.get('total_water_production', {}).get('value', 0)),
                        "total_energy_consumed": float(metrics.get('total_energy_consumption', {}).get('value', 0))
                    },
                    "health_overview": {
                        "devices_with_errors": int(metrics.get('devices_with_errors', {}).get('value', 0)),
                        "operational_devices": int(metrics.get('operational_devices', {}).get('value', 0)),
                        "fleet_uptime_percent": float(metrics.get('fleet_uptime_percent', {}).get('value', 0))
                    }
                },
                "timeframe": f"Last {date_range_days} days",
                "raw_metrics": metrics
            }
            
            # Store in Streamlit session state for display
            if hasattr(st, 'session_state'):
                if 'business_performance_data' not in st.session_state:
                    st.session_state.business_performance_data = {}
                st.session_state.business_performance_data = response_data
                logger.info("Stored business performance data in Streamlit session state")
            
            return response_data
    
    except Exception as e:
        logger.error(f"Error fetching business performance summary: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception details: {e}")
        
        error_response = {"success": False, "error": f"Failed to fetch business data: {str(e)}"}
        
        # Provide more helpful error message about specific errors
        error_str = str(e).lower()
        if "404" in str(e) or "not found" in error_str:
            error_response["error"] = "RPC function 'rpc_business_performance_summary' not found in database."
            error_response["help"] = "Run the provided SQL scripts in Supabase dashboard > SQL Editor to create the required RPC functions."
        elif "operator does not exist" in error_str and "text > integer" in error_str:
            error_response["error"] = "Database type casting error: trying to compare text with integer"
            error_response["help"] = "Check your RPC function - some columns might need explicit casting from text to integer"
        
        # Store error in session state
        if hasattr(st, 'session_state'):
            st.session_state.business_performance_error = error_response
        
        return error_response


@tool
def get_fleet_health_overview() -> Dict[str, Any]:
    """
    Get comprehensive fleet health overview with all key metrics.
    
    Provides executive-level fleet status including device counts, performance metrics,
    error distribution, and geographic health scores.
    
    Returns:
        Dict containing comprehensive fleet health data
        
    Supabase RPC Function: rpc_fleet_health_overview
    """
    from ai_agent import supabase_manager
    
    try:
        logger.info("Fetching comprehensive fleet health overview")
        
        result = supabase_manager.client.rpc('rpc_fleet_health_overview').execute()
        
        if result.data and len(result.data) > 0:
            # Process TABLE format results by category
            fleet_summary = {}
            performance_metrics = {}
            error_distribution = {}
            geographic_health = {}
            
            for row in result.data:
                category = row['health_category']
                
                if category == 'fleet_summary':
                    fleet_summary[row['metric_name']] = {
                        'value': float(row['metric_value']) if row['metric_value'] is not None else 0,
                        'unit': row['metric_unit'],
                        'description': row['status_description']
                    }
                elif category == 'performance':
                    performance_metrics[row['metric_name']] = {
                        'value': float(row['metric_value']) if row['metric_value'] is not None else 0,
                        'unit': row['metric_unit'],
                        'description': row['status_description']
                    }
                elif category == 'error_distribution':
                    error_distribution[row['metric_name']] = {
                        'count': int(row['metric_value']) if row['metric_value'] is not None else 0,
                        'description': row['status_description']
                    }
                elif category == 'geographic_health':
                    geographic_health[row['metric_name']] = {
                        'health_score': float(row['metric_value']) if row['metric_value'] is not None else 0,
                        'description': row['status_description']
                    }
            
            response_data = {
                "success": True,
                "fleet_health": {
                    "summary": {
                        "total_devices": int(fleet_summary.get('total_devices', {}).get('value', 0)),
                        "active_devices": int(fleet_summary.get('active_devices', {}).get('value', 0)),
                        "error_devices": int(fleet_summary.get('error_devices', {}).get('value', 0)),
                        "uptime_percent": float(fleet_summary.get('uptime_percent', {}).get('value', 0))
                    },
                    "performance": {
                        "water_production": float(performance_metrics.get('water_production', {}).get('value', 0)),
                        "energy_consumption": float(performance_metrics.get('energy_consumption', {}).get('value', 0)),
                        "efficiency": float(performance_metrics.get('efficiency', {}).get('value', 0)),
                        "average_temperature": float(performance_metrics.get('temperature', {}).get('value', 0))
                    },
                    "error_distribution": error_distribution,
                    "geographic_health": geographic_health
                },
                "health_score": _calculate_overall_health_score(fleet_summary, error_distribution),
                "recommendations": _generate_fleet_recommendations(fleet_summary, performance_metrics, error_distribution)
            }
            
            # Store in Streamlit session state
            if hasattr(st, 'session_state'):
                st.session_state.fleet_health_data = response_data
                
                # Create dashboard metrics
                st.session_state.fleet_dashboard_metrics = {
                    "total_devices": int(fleet_summary.get('total_devices', {}).get('value', 0)),
                    "operational_rate": float(fleet_summary.get('uptime_percent', {}).get('value', 0)),
                    "water_production": float(performance_metrics.get('water_production', {}).get('value', 0)),
                    "energy_efficiency": float(performance_metrics.get('efficiency', {}).get('value', 0)),
                    "health_status": "Healthy" if response_data["health_score"] > 80 else "Needs Attention"
                }
                
                # Create geographic health DataFrame
                if geographic_health:
                    geo_health_list = []
                    for district, data in geographic_health.items():
                        geo_health_list.append({
                            "District": district,
                            "Health Score": f"{data['health_score']:.1f}%",
                            "Status": "Healthy" if data['health_score'] > 80 else "Needs Attention"
                        })
                    st.session_state.geographic_health_df = pd.DataFrame(geo_health_list)
                
                logger.info("Stored comprehensive fleet health data in session state")
            
            return response_data
        
        no_data_response = {"success": True, "message": "No fleet health data available"}
        
        # Store empty result in session state
        if hasattr(st, 'session_state'):
            st.session_state.fleet_health_data = no_data_response
            st.session_state.fleet_dashboard_metrics = {"status": "no_data"}
            
        return no_data_response
        
    except Exception as e:
        logger.error(f"Error fetching fleet health overview: {e}")
        error_response = {"success": False, "error": str(e)}
        
        # Store error in session state
        if hasattr(st, 'session_state'):
            st.session_state.fleet_health_error = error_response
            
        return error_response

def _calculate_overall_health_score(fleet_summary: Dict, error_distribution: Dict) -> float:
    """Calculate overall fleet health score from 0-100"""
    try:
        total_devices = fleet_summary.get('total_devices', {}).get('value', 1)
        active_devices = fleet_summary.get('active_devices', {}).get('value', 0)
        error_devices = fleet_summary.get('error_devices', {}).get('value', 0)
        
        # Base score from active devices percentage
        active_score = (active_devices / total_devices) * 60 if total_devices > 0 else 0
        
        # Penalty for error devices
        error_penalty = (error_devices / total_devices) * 30 if total_devices > 0 else 0
        
        # Bonus for no errors
        no_error_bonus = 40 if error_devices == 0 else 10
        
        overall_score = max(0, min(100, active_score - error_penalty + no_error_bonus))
        return round(overall_score, 1)
    except:
        return 50.0  # Default neutral score

def _generate_fleet_recommendations(fleet_summary: Dict, performance_metrics: Dict, error_distribution: Dict) -> List[str]:
    """Generate actionable recommendations based on fleet health data"""
    recommendations = []
    
    try:
        total_devices = fleet_summary.get('total_devices', {}).get('value', 0)
        error_devices = fleet_summary.get('error_devices', {}).get('value', 0)
        avg_temp = performance_metrics.get('temperature', {}).get('value', 0)
        uptime = fleet_summary.get('uptime_percent', {}).get('value', 100)
        
        # Error-based recommendations
        if error_devices > 0:
            error_rate = (error_devices / total_devices) * 100 if total_devices > 0 else 0
            if error_rate > 20:
                recommendations.append("🔴 CRITICAL: High error rate detected - Schedule immediate fleet inspection")
            elif error_rate > 10:
                recommendations.append("🟡 WARNING: Multiple devices showing errors - Plan maintenance cycle")
            else:
                recommendations.append("✅ Monitor error devices and address during next maintenance window")
        
        # Temperature-based recommendations
        if avg_temp > 60:
            recommendations.append("🌡️ High average temperature detected - Check cooling systems and clean air filters")
        elif avg_temp < 20:
            recommendations.append("❄️ Low temperature readings - Verify sensors and check for winter operational issues")
        
        # Uptime-based recommendations
        if uptime < 90:
            recommendations.append("⚡ Low fleet uptime - Investigate power supply and connectivity issues")
        elif uptime > 95:
            recommendations.append("✅ Excellent fleet uptime - Continue current maintenance practices")
        
        # Default recommendation if no issues
        if not recommendations:
            recommendations.append("✅ Fleet operating normally - Continue regular monitoring and maintenance")
            
    except Exception as e:
        recommendations.append("⚠️ Unable to generate specific recommendations - Contact support team")
        logger.error(f"Error generating fleet recommendations: {e}")
    
    return recommendations


@tool
def get_critical_issues_analysis() -> Dict[str, Any]:
    """
    Identify top 5 most critical issues affecting the system.
    
    Analyzes device health, error patterns, and performance issues to identify
    problems requiring immediate attention.
    
    Returns:
        Dict containing prioritized critical issues
        
    Supabase RPC Function: rpc_critical_issues_analysis
    """
    from ai_agent import supabase_manager
    
    try:
        logger.info("Analyzing critical issues across the fleet")
        
        result = supabase_manager.client.rpc('rpc_critical_issues_analysis').execute()
        
        if result.data and len(result.data) > 0:
            # Convert TABLE format to structured issues list
            critical_issues = []
            for row in result.data:
                issue = {
                    "priority": row['priority_rank'],
                    "type": row['issue_type'],
                    "severity": row['severity_level'],
                    "affected_devices": row['affected_devices'],
                    "description": row['description'],
                    "recommendation": row['recommendation'],
                    "business_impact": row['business_impact']
                }
                critical_issues.append(issue)
            
            response_data = {
                "success": True,
                "critical_issues": critical_issues,
                "summary": f"Found {len(critical_issues)} critical issues requiring attention",
                "highest_priority": critical_issues[0] if critical_issues else None,
                "total_affected_devices": sum(issue['affected_devices'] for issue in critical_issues)
            }
            
            # Store in Streamlit session state
            if hasattr(st, 'session_state'):
                st.session_state.critical_issues_data = response_data
                
                # Create a summary for quick access
                st.session_state.critical_issues_summary = {
                    "total_issues": len(critical_issues),
                    "critical_count": sum(1 for issue in critical_issues if issue['severity'] == 'Critical'),
                    "high_count": sum(1 for issue in critical_issues if issue['severity'] == 'High'),
                    "medium_count": sum(1 for issue in critical_issues if issue['severity'] == 'Medium'),
                    "total_devices_affected": sum(issue['affected_devices'] for issue in critical_issues)
                }
                logger.info(f"Stored {len(critical_issues)} critical issues in session state")
            
            return response_data
        
        no_issues_response = {"success": True, "critical_issues": [], "message": "No critical issues detected"}
        
        # Store in session state
        if hasattr(st, 'session_state'):
            st.session_state.critical_issues_data = no_issues_response
            st.session_state.critical_issues_summary = {"total_issues": 0, "status": "healthy"}
            
        return no_issues_response
        
    except Exception as e:
        logger.error(f"Error analyzing critical issues: {e}")
        error_response = {"success": False, "error": str(e)}
        
        # Store error in session state
        if hasattr(st, 'session_state'):
            st.session_state.critical_issues_error = error_response
            
        return error_response


@tool
def get_high_error_devices(error_threshold: int = 5) -> Dict[str, Any]:
    """
    Identify devices with highest error rates needing immediate attention.
    
    Args:
        error_threshold: Minimum number of errors to flag a device (default: 5)
        
    Returns:
        Dict containing devices with high error rates
        
    Supabase RPC Function: rpc_high_error_devices
    """
    from ai_agent import supabase_manager
    
    try:
        logger.info(f"Analyzing high error devices with threshold: {error_threshold}")
        
        # Log exact parameters being sent
        params = {'p_error_threshold': error_threshold}
        logger.info(f"RPC Parameters: {params}")
        logger.info(f"Parameter types: {[(k, type(v).__name__) for k, v in params.items()]}")
        
        result = supabase_manager.client.rpc(
            'rpc_high_error_devices',
            params
        ).execute()
        
        logger.info(f"RPC Response data length: {len(result.data) if result.data else 0}")
        
        if result.data and len(result.data) > 0:
            # Convert TABLE format to structured device list
            high_error_devices = []
            for row in result.data:
                device = {
                    "device_id": str(row['device_id']),
                    "location": row['location'],
                    "district": row['district'],
                    "error_count": int(row['error_count']),
                    "total_readings": int(row['total_readings']),
                    "error_rate_percent": float(row['error_rate']),
                    "last_error_date": row['last_error_date'],
                    "dominant_error_code": int(row['dominant_error_code']) if row['dominant_error_code'] else None,
                    "current_status": row['current_status']
                }
                high_error_devices.append(device)
            
            # Sort by error rate (highest first)
            high_error_devices.sort(key=lambda x: x['error_rate_percent'], reverse=True)
            
            response_data = {
                "success": True,
                "high_error_devices": high_error_devices,
                "devices_count": len(high_error_devices),
                "recommendation": "These devices require immediate technical attention",
                "most_critical": high_error_devices[0] if high_error_devices else None,
                "error_threshold_used": error_threshold
            }
            
            # Store in Streamlit session state
            if hasattr(st, 'session_state'):
                st.session_state.high_error_devices_data = response_data
                
                # Create DataFrame for table display
                if high_error_devices:
                    error_devices_df = pd.DataFrame([
                        {
                            "Device ID": device["device_id"],
                            "Location": device["location"],
                            "District": device["district"],
                            "Error Count": device["error_count"],
                            "Error Rate %": f"{device['error_rate_percent']:.1f}%",
                            "Last Error": device["last_error_date"],
                            "Status": device["current_status"],
                            "Dominant Error": device["dominant_error_code"]
                        }
                        for device in high_error_devices
                    ])
                    st.session_state.high_error_devices_df = error_devices_df
                    
                # Create priority alerts for Streamlit UI
                critical_devices = [d for d in high_error_devices if d['error_rate_percent'] > 20]
                high_priority_devices = [d for d in high_error_devices if 10 <= d['error_rate_percent'] <= 20]
                
                st.session_state.error_device_alerts = {
                    "critical": len(critical_devices),
                    "high_priority": len(high_priority_devices),
                    "total": len(high_error_devices),
                    "threshold_used": error_threshold
                }
                
                logger.info(f"Stored {len(high_error_devices)} high error devices in session state")
            
            return response_data
        
        no_errors_response = {
            "success": True, 
            "high_error_devices": [], 
            "message": f"No devices exceed error threshold of {error_threshold}"
        }
        
        # Store empty result in session state
        if hasattr(st, 'session_state'):
            st.session_state.high_error_devices_data = no_errors_response
            st.session_state.high_error_devices_df = pd.DataFrame()
            st.session_state.error_device_alerts = {"total": 0, "status": "healthy"}
            
        return no_errors_response
        
    except Exception as e:
        logger.error(f"Error analyzing high error devices: {e}")
        error_response = {"success": False, "error": str(e)}
        
        # Store error in session state
        if hasattr(st, 'session_state'):
            st.session_state.high_error_devices_error = error_response
            
        return error_response


@tool
def analyze_overvoltage_impact() -> Dict[str, Any]:
    """
    Analyze how overvoltage problems are affecting water production.
    
    Identifies devices experiencing voltage issues and calculates impact on
    water pumping efficiency.
    
    Returns:
        Dict containing overvoltage analysis and production impact
        
    Supabase RPC Function: rpc_overvoltage_analysis
    """
    from ai_agent import supabase_manager
    
    try:
        result = supabase_manager.client.rpc('rpc_overvoltage_analysis').execute()
        
        if result.data and len(result.data) > 0:
            # Convert TABLE format to structured analysis
            analysis_data = {}
            for row in result.data:
                category = row['analysis_category']
                if category not in analysis_data:
                    analysis_data[category] = {}
                
                analysis_data[category][row['metric_name']] = {
                    'value': float(row['metric_value']) if row['metric_value'] is not None else 0,
                    'unit': row['metric_unit'],
                    'description': row['description']
                }
            
            # Extract key metrics for structured response
            summary = analysis_data.get('summary', {})
            voltage_stats = analysis_data.get('voltage_stats', {})
            production_impact = analysis_data.get('production_impact', {})
            temporal = analysis_data.get('temporal', {})
            
            # Determine business priority
            affected_devices_count = int(summary.get('affected_devices', {}).get('value', 0))
            max_voltage = float(voltage_stats.get('maximum', {}).get('value', 0))
            
            if affected_devices_count > 5:
                priority = 'High - Multiple devices at risk'
            elif max_voltage > 800:
                priority = 'Critical - Dangerous voltage levels detected'
            elif affected_devices_count > 0:
                priority = 'Medium - Monitor and plan preventive action'
            else:
                priority = 'Normal - No overvoltage issues detected'
                
            return {
                "success": True,
                "overvoltage_analysis": {
                    "summary": {
                        "affected_devices": int(summary.get('affected_devices', {}).get('value', 0)),
                        "fleet_percentage": float(summary.get('fleet_percentage', {}).get('value', 0)),
                        "total_readings": int(summary.get('total_readings', {}).get('value', 0))
                    },
                    "voltage_statistics": {
                        "threshold": float(voltage_stats.get('threshold', {}).get('value', 750)),
                        "min_voltage": float(voltage_stats.get('minimum', {}).get('value', 0)),
                        "max_voltage": float(voltage_stats.get('maximum', {}).get('value', 0)),
                        "avg_voltage": float(voltage_stats.get('average', {}).get('value', 0)),
                        "dangerous_spikes": int(voltage_stats.get('dangerous_spikes', {}).get('value', 0))
                    },
                    "production_impact": {
                        "estimated_loss_litres": float(production_impact.get('estimated_loss', {}).get('value', 0)),
                        "efficiency_drop_percent": float(production_impact.get('efficiency_drop', {}).get('value', 15))
                    },
                    "temporal_analysis": {
                        "most_recent": temporal.get('most_recent', {}).get('description', 'Unknown'),
                        "frequency_24h": int(temporal.get('frequency_24h', {}).get('value', 0))
                    }
                },
                "recommendations": [
                    "Install automatic voltage regulators (AVR) on affected devices",
                    "Implement voltage monitoring alerts for proactive management", 
                    "Schedule electrical system inspection during peak solar hours",
                    "Consider grid connection quality assessment",
                    "Install surge protectors for equipment protection"
                ],
                "business_priority": priority
            }
        
        return {"success": True, "message": "No overvoltage issues detected"}
        
    except Exception as e:
        logger.error(f"Error analyzing overvoltage impact: {e}")
        return {"success": False, "error": str(e)}

# =============================================================================
# DEVICE DATA RETRIEVAL TOOLS (Generic Supabase Queries)
# =============================================================================

@tool
def get_recent_device_logs(limit: int = 10, device_id: Optional[str] = None, 
                          location: Optional[str] = None, order_by: str = "CreatedOnDate.desc") -> Dict[str, Any]:
    """
    Display usage logs of recent devices with optional filtering.
    
    Args:
        limit: Number of records to return (default: 10)
        device_id: Filter by specific device ID
        location: Filter by location name
        order_by: Sort order (default: CreatedOnDate.desc)
        
    Returns:
        Dict containing formatted device logs for table display
    """
    from ai_agent import supabase_manager
    
    try:
        logger.info(f"Fetching {limit} device logs with filters - device_id: {device_id}, location: {location}")
        
        # Build query
        query = supabase_manager.client.table("device_power_logs").select("*")
        
        # Apply filters
        if device_id:
            query = query.eq("device_id", device_id)
        if location:
            query = query.ilike("Location", f"%{location}%")
        
        # Apply ordering and limit
        if order_by:
            if ".desc" in order_by:
                column = order_by.replace(".desc", "")
                query = query.order(column, desc=True)
            elif ".asc" in order_by:
                column = order_by.replace(".asc", "")
                query = query.order(column, desc=False)
            else:
                query = query.order(order_by)
        
        query = query.limit(limit)
        
        result = query.execute()
        
        if result.data:
            # Format for table display
            formatted_logs = []
            for log in result.data:
                formatted_logs.append({
                    "Device ID": str(log.get("device_id", "")),
                    "Location": log.get("Location", ""),
                    "District": log.get("District", ""),
                    "Date/Time": log.get("CreatedOnDate", ""),
                    "Power Status": "Active" if log.get("PowerStatus") == 1 else "Inactive",
                    "Pump Error": log.get("PumpError", 0),
                    "Voltage (V)": log.get("Voltage", 0),
                    "Current (A)": log.get("Current", 0),
                    "Temperature (°C)": log.get("Temperature", 0),
                    "Water Output (LPM)": log.get("LPM", 0),
                    "Today Litres": log.get("TodayLitre", 0),
                    "Runtime (min)": log.get("TodayRunTime", 0),
                    "KW": log.get("KW", 0),
                    "Project": log.get("Project", ""),
                    "Franchise": log.get("Franchise", "")
                })
            
            response_data = {
                "success": True,
                "logs": formatted_logs,
                "count": len(formatted_logs),
                "filters_applied": {
                    "device_id": device_id,
                    "location": location,
                    "limit": limit,
                    "order_by": order_by
                },
                "raw_data": result.data
            }
            
            # Store in Streamlit session state for table display
            if hasattr(st, 'session_state'):
                st.session_state.device_logs_data = response_data
                
                # Create DataFrame for easy Streamlit table display
                if formatted_logs:
                    st.session_state.device_logs_df = pd.DataFrame(formatted_logs)
                    logger.info(f"Created DataFrame with {len(formatted_logs)} rows for Streamlit display")
                
                # Store filter information for UI
                st.session_state.device_logs_filters = {
                    "last_device_id": device_id,
                    "last_location": location,
                    "last_limit": limit,
                    "timestamp": datetime.now().isoformat()
                }
            
            return response_data
        
        no_data_response = {"success": True, "logs": [], "message": "No logs found with specified criteria"}
        
        # Store empty result in session state
        if hasattr(st, 'session_state'):
            st.session_state.device_logs_data = no_data_response
            st.session_state.device_logs_df = pd.DataFrame()
            
        return no_data_response
        
    except Exception as e:
        logger.error(f"Error fetching device logs: {e}")
        error_response = {"success": False, "error": str(e)}
        
        # Store error in session state
        if hasattr(st, 'session_state'):
            st.session_state.device_logs_error = error_response
            
        return error_response


@tool
def get_location_performance(location: Optional[str] = None, district: Optional[str] = None) -> Dict[str, Any]:
    """
    Get performance metrics for specific locations or districts.
    
    Args:
        location: Specific location name
        district: District name for broader analysis
        
    Returns:
        Dict containing location-based performance metrics
    """
    from ai_agent import supabase_manager
    
    try:
        query = supabase_manager.client.table("device_power_logs").select("*")
        
        if location:
            query = query.ilike("Location", f"%{location}%")
        elif district:
            query = query.ilike("District", f"%{district}%")
        
        result = query.execute()
        
        if result.data:
            # Calculate aggregated metrics
            total_devices = len(set(log["device_id"] for log in result.data))
            total_water_today = sum(log.get("TodayLitre", 0) for log in result.data)
            total_energy = sum(log.get("Power_KWH", 0) for log in result.data)
            error_count = sum(1 for log in result.data if log.get("PumpError", 0) > 0)
            
            return {
                "success": True,
                "location_performance": {
                    "filter_criteria": {"location": location, "district": district},
                    "metrics": {
                        "total_devices": total_devices,
                        "total_water_production_today": round(total_water_today, 2),
                        "total_energy_consumption": round(total_energy, 2),
                        "error_rate_percent": round((error_count / len(result.data)) * 100, 2) if result.data else 0,
                        "operational_efficiency": "Normal" if error_count == 0 else "Issues Detected"
                    }
                }
            }
        
        return {"success": True, "message": "No data found for specified location/district"}
        
    except Exception as e:
        logger.error(f"Error fetching location performance: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# UTILITY AND MONITORING TOOLS
# =============================================================================

@tool
def test_supabase_rpc_connection() -> Dict[str, Any]:
    """
    Test Supabase RPC function connectivity and TABLE format parsing.
    
    Returns:
        Dict containing connection test results
    """
    from ai_agent import supabase_manager
    
    try:
        logger.info("Testing Supabase RPC connection and TABLE format compatibility")
        
        # Test the business performance summary with 1 day
        result = supabase_manager.client.rpc(
            'rpc_business_performance_summary',
            {'p_date_range_days': 1}
        ).execute()
        
        if result.data and len(result.data) > 0:
            response_data = {
                "success": True,
                "message": "Supabase RPC connection successful",
                "table_format_working": True,
                "rows_returned": len(result.data),
                "sample_row": result.data[0] if result.data else None,
                "available_metrics": [row['metric_name'] for row in result.data],
                "test_timestamp": datetime.now().isoformat(),
                "connection_status": "✅ Connected"
            }
            
            # Store detailed test results in Streamlit session state
            if hasattr(st, 'session_state'):
                st.session_state.rpc_test_results = response_data
                st.session_state.rpc_connection_status = "healthy"
                st.session_state.last_rpc_test = datetime.now().isoformat()
                
                # Create a summary for dashboard display
                st.session_state.rpc_test_summary = {
                    "status": "✅ RPC Connection Healthy",
                    "table_format": "✅ Working",
                    "rows_returned": len(result.data),
                    "sample_metrics": result.data[:3] if len(result.data) >= 3 else result.data,
                    "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                logger.info("RPC connection test successful - stored results in session state")
                
            return response_data
        else:
            failure_response = {
                "success": False,
                "message": "RPC function returned no data",
                "table_format_working": False,
                "connection_status": "⚠️ No Data",
                "test_timestamp": datetime.now().isoformat()
            }
            
            # Store failure in session state
            if hasattr(st, 'session_state'):
                st.session_state.rpc_test_results = failure_response
                st.session_state.rpc_connection_status = "no_data"
                st.session_state.rpc_test_summary = {
                    "status": "⚠️ RPC Returns No Data",
                    "recommendation": "Check if device_power_logs table has data"
                }
                
            return failure_response
        
    except Exception as e:
        logger.error(f"RPC connection test failed: {e}")
        
        error_response = {
            "success": False,
            "message": f"RPC connection test failed: {str(e)}",
            "table_format_working": False,
            "error": str(e),
            "connection_status": "❌ Failed",
            "test_timestamp": datetime.now().isoformat()
        }
        
        # Store error in session state
        if hasattr(st, 'session_state'):
            st.session_state.rpc_test_results = error_response
            st.session_state.rpc_connection_status = "error"
            st.session_state.rpc_test_summary = {
                "status": "❌ RPC Connection Failed",
                "error": str(e),
                "recommendation": "Check Supabase connection and RPC function creation"
            }
            
        return error_response

@tool
def get_device_power_data(columns: str = "device_id,PumpError,Power,Voltage,Current,Temperature,CreatedOnDate,Location", device_id: int = None, date: str = None, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Retrieve IoT device data with flexible column selection and filtering.
    
    This tool allows the model to specify exactly which columns to retrieve and apply custom filters.
    It's optimized for device-specific queries and provides structured analysis of the selected data.
    
    Args:
        columns: Comma-separated column names to retrieve (e.g., "device_id,PumpError,Power,CreatedOnDate")
        device_id: The unique identifier for the IoT device (optional filter)
        date: Date to filter by in YYYY-MM-DD format (optional filter)
        filters: Additional filter conditions as key-value pairs (e.g., {"PumpError": "4", "Location": "Delhi"})
        
    Returns:
        Dict[str, Any]: Device data with selected columns and computed insights
        
    Examples:
        - get_device_power_data("device_id,PumpError,CreatedOnDate", device_id=865198074539541)
        - get_device_power_data("Power,Voltage,Current,Temperature", date="2025-08-21")
        - get_device_power_data("*", filters={"Location": "Mumbai", "PumpError": "!0"})
        
    Features:
        - Flexible column selection - only retrieves what you specify
        - Automatic device ID extraction from user queries
        - Smart analysis based on selected columns
        - Power consumption analysis (if Power column selected)
        - Error pattern analysis (if PumpError column selected)
        - Date-based filtering and temporal analysis
    """
    from ai_agent import supabase_manager
    
    logger.info(f"Fetching device data - device_id: {device_id}, date: {date}, columns: {columns}")
    
    try:
        def get_device_logs():
            query = supabase_manager.client.table("device_power_logs").select(columns)
            
            # Apply device_id filter if provided
            if device_id:
                query = query.eq("device_id", device_id)
            
            # Apply date filter using LIKE for partial matching
            if date:
                query = query.like("CreatedOnDate", f"{date}%")
            
            # Apply additional filters if provided
            if filters:
                for column, value in filters.items():
                    if isinstance(value, list):
                        query = query.in_(column, value)
                    elif isinstance(value, str) and value.startswith("!"):
                        query = query.neq(column, value[1:])
                    elif isinstance(value, str) and "%" in value:
                        query = query.like(column, value)
                    else:
                        query = query.eq(column, value)
            
            return query.order("CreatedOnDate", desc=True).execute()
        
        result = supabase_manager.execute_with_retry(get_device_logs)
        
        if isinstance(result, dict) and "error" in result:
            return result
        
        if not result:
            def get_available_data():
                return supabase_manager.client.table("device_power_logs")\
                    .select("device_id, CreatedOnDate")\
                    .limit(50)\
                    .execute()
            
            available = supabase_manager.execute_with_retry(get_available_data)
            suggestions = {}
            if isinstance(available, list) and available:
                device_ids = list(set([str(record.get("device_id")) for record in available if record.get("device_id")]))
                dates = list(set([record.get("CreatedOnDate", "")[:10] for record in available if record.get("CreatedOnDate")]))
                suggestions = {
                    "available_device_ids": device_ids[:5],
                    "available_dates": dates[:5]
                }
            
            return {
                "success": False,
                "query_params": {"device_id": device_id, "date": date, "columns": columns, "filters": filters},
                "error": f"No data found for the specified criteria",
                "suggestions": suggestions
            }
        
        # Analyze data based on selected columns
        analysis = {
            "total_records": len(result),
            "columns_retrieved": columns.split(",") if columns != "*" else "all"
        }
        
        # Error analysis (only if PumpError column is selected)
        if "PumpError" in columns or columns == "*":
            error_records = [record for record in result if record.get("PumpError", "").strip() not in ["", "0", "9999", "NORMAL"]]
            error_codes = [record.get("PumpError") for record in error_records]
            analysis.update({
                "error_count": len(error_records),
                "error_rate": len(error_records) / len(result) if result else 0,
                "unique_error_codes": list(set(error_codes)) if error_codes else []
            })
        
        # Power analysis (only if Power column is selected)
        if "Power" in columns or columns == "*":
            power_values = []
            for record in result:
                power_str = record.get("Power", "0")
                try:
                    # Handle different power formats (e.g., "150W", "150", etc.)
                    power_val = float(str(power_str).replace("W", "").replace("w", "").strip())
                    power_values.append(power_val)
                except:
                    power_values.append(0)
            
            if power_values:
                analysis.update({
                    "power_statistics": {
                        "average": sum(power_values) / len(power_values),
                        "max": max(power_values),
                        "min": min(power_values)
                    }
                })
        
        # Time analysis (if CreatedOnDate column is selected)
        if "CreatedOnDate" in columns or columns == "*":
            analysis.update({
                "time_range": {
                    "latest": result[0].get("CreatedOnDate") if result else None,
                    "oldest": result[-1].get("CreatedOnDate") if result else None
                }
            })
        
        # Store in Streamlit session for visualization
        if hasattr(st, 'session_state'):
            st.session_state.last_tool_data = result
            st.session_state.device_insights = analysis
        
        return {
            "success": True,
            "query_params": {"device_id": device_id, "date": date, "columns": columns, "filters": filters},
            "analysis": analysis,
            "sample_data": result[:5],  # Show first 5 records as sample
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Device data query error: {e}")
        return {
            "success": False,
            "query_params": {"device_id": device_id, "date": date, "columns": columns, "filters": filters},
            "error": str(e),
            "retrieved_at": datetime.now().isoformat()
        }


@tool
def get_customer_device_info(device_id: int) -> Dict[str, Any]:
    """
    Retrieve customer profile information associated with a specific IoT device.
    
    Args:
        device_id: The unique identifier for the IoT device
        
    Returns:
        Dict[str, Any]: Customer information and device context
    """
    from ai_agent import supabase_manager
    
    if not device_id:
        return {"error": "Device ID is required"}
    
    logger.info(f"Fetching customer info for device ID: {device_id}")
    
    try:
        def get_customer_data():
            return supabase_manager.client.table("customer_profile")\
                .select("*")\
                .eq("Device_id", device_id)\
                .execute()
        
        result = supabase_manager.execute_with_retry(get_customer_data)
        
        if isinstance(result, dict) and "error" in result:
            return result
        
        if not result:
            return {
                "success": False,
                "device_id": device_id,
                "error": f"No customer profile found for device ID {device_id}",
                "suggestion": "Verify device ID and ensure customer profile is properly configured"
            }
        
        customer_info = result[0] if result else {}
        
        return {
            "success": True,
            "device_id": device_id,
            "customer_profile": customer_info,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "device_id": device_id,
            "error": str(e),
            "retrieved_at": datetime.now().isoformat()
        }


def get_all_tools():
    """Return all available tools for the Dextro Solar IoT agent"""
    return [
        # Business Intelligence Tools (RPC Functions)
        get_business_performance_summary,
        get_critical_issues_analysis, 
        get_high_error_devices,
        analyze_overvoltage_impact,
        get_fleet_health_overview,
        
        # Device Data Tools (Direct Queries)
        get_recent_device_logs,
        get_location_performance,
        
        # Utility Tools
        test_supabase_rpc_connection,
        
        # Note: Keep your existing query_supabase_database tool if needed for other queries
        get_customer_device_info,
        get_device_power_data
    ]


# =============================================================================
# STREAMLIT SESSION STATE HELPERS
# =============================================================================

def display_session_data_summary():
    """Helper function to display stored session data summary in Streamlit"""
    if not hasattr(st, 'session_state'):
        return None
    
    summary = {}
    
    # Business performance data
    if hasattr(st.session_state, 'business_performance_data'):
        summary['business_performance'] = {
            'status': 'loaded',
            'devices': st.session_state.business_performance_data.get('summary', {}).get('fleet_metrics', {}).get('total_active_devices', 0)
        }
    
    # Critical issues data
    if hasattr(st.session_state, 'critical_issues_summary'):
        summary['critical_issues'] = st.session_state.critical_issues_summary
    
    # Device logs data  
    if hasattr(st.session_state, 'device_logs_data'):
        summary['device_logs'] = {
            'status': 'loaded',
            'count': st.session_state.device_logs_data.get('count', 0)
        }
    
    # Installation stats data
    if hasattr(st.session_state, 'installation_summary'):
        summary['installation_stats'] = st.session_state.installation_summary
    
    # Fleet health data
    if hasattr(st.session_state, 'fleet_dashboard_metrics'):
        summary['fleet_health'] = st.session_state.fleet_dashboard_metrics
    
    # Location performance data
    if hasattr(st.session_state, 'location_performance_summary'):
        summary['location_performance'] = st.session_state.location_performance_summary
    
    # RPC connection status
    if hasattr(st.session_state, 'rpc_connection_status'):
        summary['rpc_status'] = st.session_state.rpc_connection_status
    
    return summary


def clear_session_cache():
    """Helper function to clear agent-related session state data"""
    if not hasattr(st, 'session_state'):
        return
    
    # Clear main data stores
    keys_to_clear = [
        'business_performance_data',
        'critical_issues_data', 
        'critical_issues_summary',
        'device_logs_data',
        'device_logs_df',
        'high_error_devices_data',
        'high_error_devices_df',
        'error_device_alerts',
        'rpc_test_results',
        'overvoltage_analysis_data',
        'installation_stats_data',
        'installation_summary',
        'installation_locations_df',
        'installation_franchise_df',
        'fleet_health_data',
        'fleet_dashboard_metrics',
        'geographic_health_df',
        'location_performance_data',
        'location_performance_summary',
        'location_devices_df'
    ]
    
    for key in keys_to_clear:
        if hasattr(st.session_state, key):
            delattr(st.session_state, key)
    
    logger.info("Cleared agent session state cache")


def get_dashboard_metrics():
    """Extract key metrics from session state for dashboard display"""
    if not hasattr(st, 'session_state'):
        return {}
    
    metrics = {}
    
    # Extract business metrics
    if hasattr(st.session_state, 'business_performance_data'):
        bp_data = st.session_state.business_performance_data
        if bp_data.get('success'):
            summary = bp_data.get('summary', {})
            metrics['total_devices'] = summary.get('fleet_metrics', {}).get('total_active_devices', 0)
            metrics['new_devices'] = summary.get('new_devices_installed', 0)
            metrics['co2_savings'] = summary.get('environmental_impact', {}).get('co2_savings_tonnes_annual', 0)
            metrics['water_production'] = summary.get('fleet_metrics', {}).get('total_water_produced_today', 0)
            metrics['fleet_uptime'] = summary.get('health_overview', {}).get('fleet_uptime_percent', 0)
    
    # Extract installation metrics
    if hasattr(st.session_state, 'installation_summary'):
        install_data = st.session_state.installation_summary
        metrics['installations_period'] = install_data.get('new_devices', 0)
        metrics['installation_co2_impact'] = install_data.get('co2_savings', 0)
        metrics['top_location'] = install_data.get('top_location', 'N/A')
        metrics['top_franchise'] = install_data.get('top_franchise', 'N/A')
    
    # Extract error metrics
    if hasattr(st.session_state, 'error_device_alerts'):
        alerts = st.session_state.error_device_alerts
        metrics['error_devices'] = alerts.get('total', 0)
        metrics['critical_devices'] = alerts.get('critical', 0)
    
    # Extract issue metrics
    if hasattr(st.session_state, 'critical_issues_summary'):
        issues = st.session_state.critical_issues_summary
        metrics['total_issues'] = issues.get('total_issues', 0)
        metrics['critical_issues'] = issues.get('critical_count', 0)
    
    # Extract fleet health metrics
    if hasattr(st.session_state, 'fleet_dashboard_metrics'):
        fleet_data = st.session_state.fleet_dashboard_metrics
        metrics['fleet_health_status'] = fleet_data.get('health_status', 'Unknown')
        metrics['operational_rate'] = fleet_data.get('operational_rate', 0)
        metrics['energy_efficiency'] = fleet_data.get('energy_efficiency', 0)
    
    return metrics


def format_device_logs_for_display(logs_data: List[Dict]) -> pd.DataFrame:
    """Format device logs data for optimal Streamlit table display"""
    if not logs_data:
        return pd.DataFrame()
    
    # Select key columns for display
    display_columns = [
        "Device ID", "Location", "District", "Date/Time", 
        "Power Status", "Pump Error", "Voltage (V)", 
        "Temperature (°C)", "Water Output (LPM)", "Today Litres"
    ]
    
    df = pd.DataFrame(logs_data)
    
    # Keep only display columns that exist in data
    available_columns = [col for col in display_columns if col in df.columns]
    df_display = df[available_columns].copy()
    
    # Format numerical columns
    if "Voltage (V)" in df_display.columns:
        df_display["Voltage (V)"] = df_display["Voltage (V)"].apply(lambda x: f"{x:.1f}V" if pd.notna(x) else "N/A")
    
    if "Temperature (°C)" in df_display.columns:
        df_display["Temperature (°C)"] = df_display["Temperature (°C)"].apply(lambda x: f"{x:.1f}°C" if pd.notna(x) else "N/A")
    
    if "Water Output (LPM)" in df_display.columns:
        df_display["Water Output (LPM)"] = df_display["Water Output (LPM)"].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "0")
    
    return df_display