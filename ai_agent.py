#!/usr/bin/env python3
"""
Production-Ready LLM Agent using Strands SDK with Claude Anthropic and Supabase Integration
Adapted for Dextro IoT Device Monitoring Platform with Streamlit Integration
Author: Siddarth Gogulapati 
Date: August 2025
"""

import os
import json
import time
import logging
import asyncio
import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import asynccontextmanager

# Core imports
from strands import Agent, tool
from strands.models.anthropic import AnthropicModel  # Using Anthropic model directly
from supabase import create_client, Client
from postgrest.exceptions import APIError as PostgrestAPIError

# =============================================================================
# CONFIGURATION CONSTANTS - Dextro Platform Configuration
# =============================================================================

# Try to import Streamlit for secrets management
try:
    import streamlit as st
    # Load from Streamlit secrets if available
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    CLAUDE_KEY = st.secrets["anthropic"]["api_key"]
    CLAUDE_MODEL = st.secrets["claude"]["model"]
    TEMPERATURE = st.secrets["claude"]["temperature"]
    MAX_TOKENS = st.secrets["claude"]["max_tokens"]
except (ImportError, KeyError, AttributeError):
    # Fallback to environment variables for non-Streamlit contexts
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    CLAUDE_KEY = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-7-sonnet-20250219")
    TEMPERATURE = float(os.getenv("CLAUDE_TEMPERATURE", "0.3"))
    MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "3000"))

REQUEST_TIMEOUT = 60

# System Prompts for Dextro IoT Platform
SYSTEM_PROMPT = """You are Dextro Devi IoT device monitoring assistant for the Dextro platform with access to comprehensive device analytics and database operations.

DATABASE SCHEMA REFERENCE:
You have access to these tables with the following structure:

TABLE: device_power_logs
- device_id (bigint): Unique device identifier
- PowerStatus (bigint): Device power status
- PumpStatus (text): Pump operational status
- PumpError (text): Pump error codes (various custom codes)
- Voltage (double precision): Device voltage
- Current (text): Device current
- Frequency (text): Operating frequency
- Temperature (double precision): Device temperature
- Power (text): Power consumption
- PhaseCurrentRYB (text): Phase current readings
- LPM (text): Liters per minute flow rate
- TodayLitre (double precision): Daily water volume
- TotalLitres (double precision): Total water volume
- TodayRunTime (double precision): Daily runtime
- TotalRunTime (double precision): Total runtime
- GSMSignal (bigint): GSM signal strength
- Power_KWH (double precision): Power consumption in KWH
- CreatedOnDate (text): Timestamp of record creation
- Model_Number (text): Device model
- Location (text): Installation location
- District (text): District location
- KW (text): Power rating
- Project (text): Project name
- Franchise (text): Franchise information

TABLE: customer_profile
- Device_id (bigint): Device identifier (links to device_power_logs.device_id)
- Model_Number (text): Device model
- Location (text): Customer location
- District (text): District
- KW (double precision): Power rating
- Project (text): Project name
- Franchise (text): Franchise name

IMPORTANT: Always use correct column names - CreatedOnDate (not created_on_date), PumpError (not pump_error), etc.

ERROR CODE HANDLING:

CRITICAL ERROR CODE INTERPRETATION:
- Error codes "0" and "9999" indicate NORMAL OPERATION, NOT errors
- When analyzing system health, if devices show only "0" and "9999" codes, report the system as HEALTHY
- Only treat other numeric codes (1-36) as actual error conditions requiring attention

- When PumpError is "0", "9999", "NORMAL", or empty, report "No error - system operating normally"
- CRITICAL: Codes "0" and "9999" are NORMAL OPERATION, not errors. Do NOT include them in error counts or treat them as problems.
- System health should be reported as HEALTHY when devices show only normal operation codes (0, 9999, NORMAL)
When analyzing IoT device data and pump error codes, follow these guidelines:

This table provides comprehensive error code information for Variable Frequency Drive (VFD) faults in solar-powered water pumping systems.

Error Code 0: No Fault

Description: System operating normally with no detected faults
Cause: Normal operating condition
Solution: No action required

Error Code 9999: No Fault

Description: System operating normally with no detected faults
Cause: Normal operating condition
Solution: No action required

Error Code 1: OUt1 - Inverter Unit U Phase Protection

Description: Protection triggered on the U phase of the inverter unit
Cause: Acceleration is too fast, Insulated Gate Bipolar Transistor module fault, misacts caused by interference, poor connection of driving wires, improper grounding
Solution: Increase acceleration time, replace power unit, check driving wires, inspect external equipment and eliminate interference

Error Code 2: OUt2 - Inverter Unit V Phase Protection

Description: Protection triggered on the V phase of the inverter unit
Cause: Acceleration is too fast, Insulated Gate Bipolar Transistor module fault, misacts caused by interference, poor connection of driving wires, improper grounding
Solution: Increase acceleration time, replace power unit, check driving wires, inspect external equipment and eliminate interference

Error Code 3: OUt3 - Inverter Unit W Phase Protection

Description: Protection triggered on the W phase of the inverter unit
Cause: Acceleration is too fast, Insulated Gate Bipolar Transistor module fault, misacts caused by interference, poor connection of driving wires, improper grounding
Solution: Increase acceleration time, replace power unit, check driving wires, inspect external equipment and eliminate interference

Error Code 4: OC1 - Overcurrent During Acceleration

Description: Excessive current detected during motor acceleration phase
Cause: Acceleration or deceleration too fast, grid voltage too low, Variable Frequency Drive power too low, load transients or abnormal conditions, grounding short circuit or output phase loss, strong external interference, overvoltage stall protection not enabled
Solution: Increase acceleration time, check input power, select Variable Frequency Drive with larger power capacity, check for short circuits or rotation issues, verify output configuration, check for interference, verify related function code settings

Error Code 5: OC2 - Overcurrent During Deceleration

Description: Excessive current detected during motor deceleration phase
Cause: Acceleration or deceleration too fast, grid voltage too low, Variable Frequency Drive power too low, load transients or abnormal conditions, grounding short circuit or output phase loss, strong external interference, overvoltage stall protection not enabled
Solution: Increase deceleration time, check input power, select Variable Frequency Drive with larger power capacity, check for short circuits or rotation issues, verify output configuration, check for interference, verify related function code settings

Error Code 6: OC3 - Overcurrent During Constant Speed Running

Description: Excessive current detected during steady-state motor operation
Cause: Acceleration or deceleration too fast, grid voltage too low, Variable Frequency Drive power too low, load transients or abnormal conditions, grounding short circuit or output phase loss, strong external interference, overvoltage stall protection not enabled
Solution: Check input power, select Variable Frequency Drive with larger power capacity, check for short circuits or rotation issues, verify output configuration, check for interference, verify related function code settings

Error Code 7: OV1 - Overvoltage During Acceleration

Description: Direct current bus voltage exceeded limits during acceleration
Cause: Abnormal input voltage, large energy feedback from motor, no braking components installed, braking energy not enabled
Solution: Check input power supply, verify deceleration time is appropriate, install braking components if needed, check related function code settings

Error Code 8: OV2 - Overvoltage During Deceleration

Description: Direct current bus voltage exceeded limits during deceleration
Cause: Abnormal input voltage, large energy feedback from motor, no braking components installed, braking energy not enabled
Solution: Check input power supply, verify deceleration time is appropriate, install braking components if needed, check related function code settings

Error Code 9: OV3 - Overvoltage During Constant Speed Running

Description: Direct current bus voltage exceeded limits during steady-state operation
Cause: Abnormal input voltage, large energy feedback from motor, no braking components installed, braking energy not enabled
Solution: Check input power supply, verify motor is not being driven externally, install braking components if needed, check related function code settings

Error Code 10: UV - Bus Undervoltage

Description: Direct current bus voltage below minimum operating threshold
Cause: Power supply voltage too low
Solution: Check input power supply line voltage and stability

Error Code 11: OL1 - Motor Overload

Description: Motor drawing excessive current for extended period
Cause: Power supply voltage too low, motor rated current setting incorrect, motor stall or load transients too strong
Solution: Check power supply line, reset motor rated current parameters, check load conditions and adjust torque lift settings

Error Code 12: OL2 - Variable Frequency Drive Overload

Description: Variable Frequency Drive operating beyond rated capacity
Cause: Acceleration too fast, restarting rotating motor, power supply voltage too low, load too heavy, motor power too large for Variable Frequency Drive capacity
Solution: Increase acceleration time, avoid restarting after stopping, check power supply line, select Variable Frequency Drive with higher power rating, select appropriate motor

Error Code 13: SPI - Phase Loss on Input Side

Description: One or more input phases missing or severely unbalanced
Cause: Phase loss or violent fluctuation in R, S, T input terminals
Solution: Check input power connections, verify installation and distribution system

Error Code 14: SPO - Phase Loss on Output Side

Description: One or more output phases missing or motor phases asymmetrical
Cause: Phase loss in U, V, W output terminals or three motor phases asymmetrical
Solution: Check output distribution connections, inspect motor and cables

Error Code 15: OH1 - Rectifier Module Overheat

Description: Rectifier module temperature exceeded safe operating limit
Cause: Air duct blocked or fan damaged, ambient temperature too high, overload running time too long
Solution: Clear ventilation duct or replace fan, lower ambient temperature, reduce load or operating time

Error Code 16: OH2 - Inverter Module Overheat

Description: Inverter module temperature exceeded safe operating limit
Cause: Air duct blocked or fan damaged, ambient temperature too high, overload running time too long
Solution: Clear ventilation duct or replace fan, lower ambient temperature, reduce load or operating time

Error Code 17: EF - External Fault

Description: External fault signal received through input terminal
Cause: External fault input terminal activated
Solution: Check external device input and resolve external fault condition

Error Code 18: CE - 485 Communication Fault

Description: RS-485 serial communication failure
Cause: Incorrect baud rate setting, communication wiring fault, wrong communication address, strong communication interference
Solution: Set proper baud rate, check communication connection wiring, set proper communication address, replace wiring or improve anti-interference capability

Error Code 19: ItE - Current Detection Fault

Description: Current measurement circuit malfunction
Cause: Control panel connector poor contact, exception in amplifying circuit
Solution: Check connector and re-plug, replace main control panel

Error Code 20: tE - Motor Autotuning Fault

Description: Motor parameter identification process failed
Cause: Motor capacity incompatible with Variable Frequency Drive capability, motor rated parameters set incorrectly, large offset between autotuning parameters and standard parameters, autotuning timeout
Solution: Change Variable Frequency Drive mode, set rated parameters according to motor nameplate, remove motor load, check motor connections and parameters, verify upper limit frequency above two-thirds of rated frequency

Error Code 21: EEP - Electrically Erasable Programmable Read-Only Memory Operation Fault

Description: Memory read/write operation failure
Cause: Error controlling parameter read/write operations, damaged memory chip
Solution: Press STOP/RST to reset, replace main control panel

Error Code 22: PIDE - Proportional-Integral-Derivative Feedback Offline Fault

Description: Process control feedback signal lost
Cause: Proportional-Integral-Derivative feedback offline, feedback source disappeared
Solution: Check feedback signal connections, verify feedback source

Error Code 23: bCE - Braking Unit Fault

Description: Braking circuit or braking components malfunction
Cause: Braking circuit fault or damage to braking pipes, external braking resistor insufficient
Solution: Check braking unit and replace braking components, increase braking resistor value

Error Code 24: END - Running Time Reached

Description: Accumulated operating time exceeded preset limit
Cause: Actual running time exceeded internal setting
Solution: Contact supplier to adjust running time setting

Error Code 25: OL3 - Electronic Overload

Description: Electronic overload protection triggered
Cause: Variable Frequency Drive overload pre-alarm threshold reached
Solution: Check load conditions and overload pre-alarm threshold settings

Error Code 26: PCE - Keypad Communication Error

Description: Control panel communication failure
Cause: Keypad not properly connected or offline, keypad cable too long with strong interference, communication circuit fault in keypad or main board
Solution: Check keypad cable connection, eliminate interference sources, replace hardware and seek maintenance service

Error Code 27: UPE - Parameter Upload Error

Description: Failed to upload parameters from Variable Frequency Drive
Cause: Keypad not properly connected or offline, keypad cable too long with strong interference, communication circuit fault in keypad or main board
Solution: Check environment and eliminate interference sources, replace hardware and seek maintenance service

Error Code 28: DNE - Parameter Download Error

Description: Failed to download parameters to Variable Frequency Drive
Cause: Keypad not properly connected or offline, keypad cable too long with strong interference, data storage error in keypad
Solution: Check environment and eliminate interference sources, replace hardware and seek maintenance service, backup data in keypad again

Error Code 32: ETH1 - To-Ground Short-Circuit Fault 1

Description: Output to ground short circuit detected (first type)
Cause: Variable Frequency Drive output shorted to ground, current detection circuit fault, large difference between actual motor power and Variable Frequency Drive power setting
Solution: Check motor connection integrity, replace hall sensor, replace main control panel, reset correct motor parameters, verify motor power parameters match actual motor

Error Code 33: ETH2 - To-Ground Short-Circuit Fault 2

Description: Output to ground short circuit detected (second type)
Cause: Variable Frequency Drive output shorted to ground, current detection circuit fault, large difference between actual motor power and Variable Frequency Drive power setting
Solution: Check motor connection integrity, replace hall sensor, replace main control panel, reset correct motor parameters, verify motor power parameters match actual motor

Error Code 34: dEu - Speed Deviation Fault

Description: Motor speed deviating from commanded speed beyond tolerance
Cause: Load too heavy or stall occurred
Solution: Check load conditions for proper sizing, increase detection time, verify control parameters are set properly

Error Code 35: STo - Maladjustment Fault

Description: System control parameters improperly configured
Cause: Synchronous motor control parameters set improperly, autotuning parameters inaccurate, Variable Frequency Drive not connected to motor
Solution: Check load conditions, verify control parameters are correct, increase maladjustment detection time

Error Code 36: LL - Electronic Underload Fault

Description: Motor operating below minimum load threshold
Cause: Variable Frequency Drive underload pre-alarm threshold reached
Solution: Check load conditions and underload pre-alarm point settings


You specialize in:
- IoT device power consumption tracking and analysis using device_power_logs table
- Flexible pump error code diagnosis using PumpError column with user-configurable analysis
- Customer profile management using customer_profile table
- Predictive maintenance and anomaly detection
- Real-time device monitoring and alerting
- Data visualization and comprehensive reporting

Key capabilities:
- Query device_power_logs for device performance analysis
- Analyze PumpError patterns using configurable analysis instructions
- Join device_power_logs with customer_profile for comprehensive insights
- Generate predictive insights for device maintenance
- Monitor system health across all devices
- Create data-driven reports with proper column references
- Apply custom analysis instructions provided by users

ANALYSIS APPROACH:
- Use the configurable analysis instructions from user settings when available
- Apply domain expertise while remaining flexible to user-specific requirements
- Combine system-level intelligence with user-provided guidance
- Always distinguish between actual errors and normal operation states

Always use the correct column names as specified in the schema above and provide actionable insights based on both system intelligence and user instructions.

CRITICAL FOR FINAL ANALYSIS: Always reference the DEFAULT_ANALYSIS_INSTRUCTIONS which contain comprehensive error code definitions. 
These instructions correctly identify that codes "0" and "9999" are NORMAL OPERATION, not errors. 
Use these instructions in your final analysis to provide accurate health assessments."""

# Agent Configuration
AGENT_NAME = "DextroIoTAgent"
MAX_RETRIES = 3
LOG_LEVEL = "INFO"
ENABLE_DEBUG_LOGGING = os.getenv("DEBUG", "false").lower() == "true"

# Default analysis instructions (user configurable)
DEFAULT_ANALYSIS_INSTRUCTIONS = """
When analyzing IoT device data and pump error codes, follow these guidelines:

This table provides comprehensive error code information for Variable Frequency Drive (VFD) faults in solar-powered water pumping systems.

Error Code 0: No Fault

Description: System operating normally with no detected faults
Cause: Normal operating condition
Solution: No action required

Error Code 9999: No Fault

Description: System operating normally with no detected faults
Cause: Normal operating condition
Solution: No action required

Error Code 1: OUt1 - Inverter Unit U Phase Protection

Description: Protection triggered on the U phase of the inverter unit
Cause: Acceleration is too fast, Insulated Gate Bipolar Transistor module fault, misacts caused by interference, poor connection of driving wires, improper grounding
Solution: Increase acceleration time, replace power unit, check driving wires, inspect external equipment and eliminate interference

Error Code 2: OUt2 - Inverter Unit V Phase Protection

Description: Protection triggered on the V phase of the inverter unit
Cause: Acceleration is too fast, Insulated Gate Bipolar Transistor module fault, misacts caused by interference, poor connection of driving wires, improper grounding
Solution: Increase acceleration time, replace power unit, check driving wires, inspect external equipment and eliminate interference

Error Code 3: OUt3 - Inverter Unit W Phase Protection

Description: Protection triggered on the W phase of the inverter unit
Cause: Acceleration is too fast, Insulated Gate Bipolar Transistor module fault, misacts caused by interference, poor connection of driving wires, improper grounding
Solution: Increase acceleration time, replace power unit, check driving wires, inspect external equipment and eliminate interference

Error Code 4: OC1 - Overcurrent During Acceleration

Description: Excessive current detected during motor acceleration phase
Cause: Acceleration or deceleration too fast, grid voltage too low, Variable Frequency Drive power too low, load transients or abnormal conditions, grounding short circuit or output phase loss, strong external interference, overvoltage stall protection not enabled
Solution: Increase acceleration time, check input power, select Variable Frequency Drive with larger power capacity, check for short circuits or rotation issues, verify output configuration, check for interference, verify related function code settings

Error Code 5: OC2 - Overcurrent During Deceleration

Description: Excessive current detected during motor deceleration phase
Cause: Acceleration or deceleration too fast, grid voltage too low, Variable Frequency Drive power too low, load transients or abnormal conditions, grounding short circuit or output phase loss, strong external interference, overvoltage stall protection not enabled
Solution: Increase deceleration time, check input power, select Variable Frequency Drive with larger power capacity, check for short circuits or rotation issues, verify output configuration, check for interference, verify related function code settings

Error Code 6: OC3 - Overcurrent During Constant Speed Running

Description: Excessive current detected during steady-state motor operation
Cause: Acceleration or deceleration too fast, grid voltage too low, Variable Frequency Drive power too low, load transients or abnormal conditions, grounding short circuit or output phase loss, strong external interference, overvoltage stall protection not enabled
Solution: Check input power, select Variable Frequency Drive with larger power capacity, check for short circuits or rotation issues, verify output configuration, check for interference, verify related function code settings

Error Code 7: OV1 - Overvoltage During Acceleration

Description: Direct current bus voltage exceeded limits during acceleration
Cause: Abnormal input voltage, large energy feedback from motor, no braking components installed, braking energy not enabled
Solution: Check input power supply, verify deceleration time is appropriate, install braking components if needed, check related function code settings

Error Code 8: OV2 - Overvoltage During Deceleration

Description: Direct current bus voltage exceeded limits during deceleration
Cause: Abnormal input voltage, large energy feedback from motor, no braking components installed, braking energy not enabled
Solution: Check input power supply, verify deceleration time is appropriate, install braking components if needed, check related function code settings

Error Code 9: OV3 - Overvoltage During Constant Speed Running

Description: Direct current bus voltage exceeded limits during steady-state operation
Cause: Abnormal input voltage, large energy feedback from motor, no braking components installed, braking energy not enabled
Solution: Check input power supply, verify motor is not being driven externally, install braking components if needed, check related function code settings

Error Code 10: UV - Bus Undervoltage

Description: Direct current bus voltage below minimum operating threshold
Cause: Power supply voltage too low
Solution: Check input power supply line voltage and stability

Error Code 11: OL1 - Motor Overload

Description: Motor drawing excessive current for extended period
Cause: Power supply voltage too low, motor rated current setting incorrect, motor stall or load transients too strong
Solution: Check power supply line, reset motor rated current parameters, check load conditions and adjust torque lift settings

Error Code 12: OL2 - Variable Frequency Drive Overload

Description: Variable Frequency Drive operating beyond rated capacity
Cause: Acceleration too fast, restarting rotating motor, power supply voltage too low, load too heavy, motor power too large for Variable Frequency Drive capacity
Solution: Increase acceleration time, avoid restarting after stopping, check power supply line, select Variable Frequency Drive with higher power rating, select appropriate motor

Error Code 13: SPI - Phase Loss on Input Side

Description: One or more input phases missing or severely unbalanced
Cause: Phase loss or violent fluctuation in R, S, T input terminals
Solution: Check input power connections, verify installation and distribution system

Error Code 14: SPO - Phase Loss on Output Side

Description: One or more output phases missing or motor phases asymmetrical
Cause: Phase loss in U, V, W output terminals or three motor phases asymmetrical
Solution: Check output distribution connections, inspect motor and cables

Error Code 15: OH1 - Rectifier Module Overheat

Description: Rectifier module temperature exceeded safe operating limit
Cause: Air duct blocked or fan damaged, ambient temperature too high, overload running time too long
Solution: Clear ventilation duct or replace fan, lower ambient temperature, reduce load or operating time

Error Code 16: OH2 - Inverter Module Overheat

Description: Inverter module temperature exceeded safe operating limit
Cause: Air duct blocked or fan damaged, ambient temperature too high, overload running time too long
Solution: Clear ventilation duct or replace fan, lower ambient temperature, reduce load or operating time

Error Code 17: EF - External Fault

Description: External fault signal received through input terminal
Cause: External fault input terminal activated
Solution: Check external device input and resolve external fault condition

Error Code 18: CE - 485 Communication Fault

Description: RS-485 serial communication failure
Cause: Incorrect baud rate setting, communication wiring fault, wrong communication address, strong communication interference
Solution: Set proper baud rate, check communication connection wiring, set proper communication address, replace wiring or improve anti-interference capability

Error Code 19: ItE - Current Detection Fault

Description: Current measurement circuit malfunction
Cause: Control panel connector poor contact, exception in amplifying circuit
Solution: Check connector and re-plug, replace main control panel

Error Code 20: tE - Motor Autotuning Fault

Description: Motor parameter identification process failed
Cause: Motor capacity incompatible with Variable Frequency Drive capability, motor rated parameters set incorrectly, large offset between autotuning parameters and standard parameters, autotuning timeout
Solution: Change Variable Frequency Drive mode, set rated parameters according to motor nameplate, remove motor load, check motor connections and parameters, verify upper limit frequency above two-thirds of rated frequency

Error Code 21: EEP - Electrically Erasable Programmable Read-Only Memory Operation Fault

Description: Memory read/write operation failure
Cause: Error controlling parameter read/write operations, damaged memory chip
Solution: Press STOP/RST to reset, replace main control panel

Error Code 22: PIDE - Proportional-Integral-Derivative Feedback Offline Fault

Description: Process control feedback signal lost
Cause: Proportional-Integral-Derivative feedback offline, feedback source disappeared
Solution: Check feedback signal connections, verify feedback source

Error Code 23: bCE - Braking Unit Fault

Description: Braking circuit or braking components malfunction
Cause: Braking circuit fault or damage to braking pipes, external braking resistor insufficient
Solution: Check braking unit and replace braking components, increase braking resistor value

Error Code 24: END - Running Time Reached

Description: Accumulated operating time exceeded preset limit
Cause: Actual running time exceeded internal setting
Solution: Contact supplier to adjust running time setting

Error Code 25: OL3 - Electronic Overload

Description: Electronic overload protection triggered
Cause: Variable Frequency Drive overload pre-alarm threshold reached
Solution: Check load conditions and overload pre-alarm threshold settings

Error Code 26: PCE - Keypad Communication Error

Description: Control panel communication failure
Cause: Keypad not properly connected or offline, keypad cable too long with strong interference, communication circuit fault in keypad or main board
Solution: Check keypad cable connection, eliminate interference sources, replace hardware and seek maintenance service

Error Code 27: UPE - Parameter Upload Error

Description: Failed to upload parameters from Variable Frequency Drive
Cause: Keypad not properly connected or offline, keypad cable too long with strong interference, communication circuit fault in keypad or main board
Solution: Check environment and eliminate interference sources, replace hardware and seek maintenance service

Error Code 28: DNE - Parameter Download Error

Description: Failed to download parameters to Variable Frequency Drive
Cause: Keypad not properly connected or offline, keypad cable too long with strong interference, data storage error in keypad
Solution: Check environment and eliminate interference sources, replace hardware and seek maintenance service, backup data in keypad again

Error Code 32: ETH1 - To-Ground Short-Circuit Fault 1

Description: Output to ground short circuit detected (first type)
Cause: Variable Frequency Drive output shorted to ground, current detection circuit fault, large difference between actual motor power and Variable Frequency Drive power setting
Solution: Check motor connection integrity, replace hall sensor, replace main control panel, reset correct motor parameters, verify motor power parameters match actual motor

Error Code 33: ETH2 - To-Ground Short-Circuit Fault 2

Description: Output to ground short circuit detected (second type)
Cause: Variable Frequency Drive output shorted to ground, current detection circuit fault, large difference between actual motor power and Variable Frequency Drive power setting
Solution: Check motor connection integrity, replace hall sensor, replace main control panel, reset correct motor parameters, verify motor power parameters match actual motor

Error Code 34: dEu - Speed Deviation Fault

Description: Motor speed deviating from commanded speed beyond tolerance
Cause: Load too heavy or stall occurred
Solution: Check load conditions for proper sizing, increase detection time, verify control parameters are set properly

Error Code 35: STo - Maladjustment Fault

Description: System control parameters improperly configured
Cause: Synchronous motor control parameters set improperly, autotuning parameters inaccurate, Variable Frequency Drive not connected to motor
Solution: Check load conditions, verify control parameters are correct, increase maladjustment detection time

Error Code 36: LL - Electronic Underload Fault

Description: Motor operating below minimum load threshold
Cause: Variable Frequency Drive underload pre-alarm threshold reached
Solution: Check load conditions and underload pre-alarm point settings
GENERAL ANALYSIS:
- Focus on operational efficiency and preventive maintenance
- Identify patterns that could indicate upcoming failures
- Prioritize safety-critical issues over minor operational concerns
- Consider environmental factors (temperature, power fluctuations) in analysis

ERROR CODE INTERPRETATION:
- Treat error codes contextually based on frequency and device history
- Look for recurring error patterns that might indicate systemic issues
- Consider the operational environment when assessing error severity

RECOMMENDATIONS:
- Provide actionable maintenance recommendations
- Include both immediate actions and long-term preventive measures  
- Consider cost-effectiveness of recommended actions
- Prioritize recommendations based on safety and operational impact

REPORTING:
- Present findings in clear, business-friendly language
- Include relevant metrics and trends
- Highlight critical issues that require immediate attention
- Provide context for technical staff and management decisions
"""

# Import callback handler and tools from new modules
from callback_handler import CaptureCallbackHandler
from agentic_tools import (
    get_all_tools,
    get_device_power_data,
    get_customer_device_info
)

# Check if Strands is available
try:
    from strands import Agent, tool
    from strands.models.anthropic import AnthropicModel
    from strands.handlers.callback_handler import PrintingCallbackHandler
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

def setup_logging():
    """Configure comprehensive logging for the Dextro agent"""
    log_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("dextro_agent.log", mode="a")
        ]
    )
    
    # Configure specific loggers
    if ENABLE_DEBUG_LOGGING:
        logging.getLogger("strands").setLevel(logging.DEBUG)
        logging.getLogger("supabase").setLevel(logging.DEBUG)
    
    return logging.getLogger(__name__)

logger = setup_logging()

# =============================================================================
# STREAMLIT INTEGRATION HELPERS
# =============================================================================

def _extract_tool_results_from_callback(agent):
    """Extract tool results from the agent's callback handler"""
    tool_results = []
    
    if hasattr(agent, '_callback_handler'):
        callback = agent._callback_handler
        if hasattr(callback, 'tool_results'):
            tool_results = callback.tool_results
            logger.info(f"Extracted {len(tool_results)} tool results from callback handler")
        else:
            logger.warning("Callback handler found but no tool_results attribute")
    else:
        logger.warning("No callback handler found")
    
    return tool_results

def _extract_token_usage_from_response(response):
    """Extract token usage from Strands agent response with comprehensive debugging"""
    token_usage = None
    
    logger.info(f"Looking for token usage in response: {type(response)}")
    
    # Try multiple possible attribute names for token usage
    possible_attrs = ['token_usage', 'tokens', 'usage', 'metrics']
    
    for attr in possible_attrs:
        if hasattr(response, attr):
            attr_value = getattr(response, attr)
            logger.info(f"Found attribute '{attr}': {type(attr_value)} = {attr_value}")
            
            if attr == 'token_usage' and attr_value:
                token_usage = {
                    "input_tokens": getattr(attr_value, 'input_tokens', getattr(attr_value, 'prompt_tokens', 0)),
                    "output_tokens": getattr(attr_value, 'output_tokens', getattr(attr_value, 'completion_tokens', 0)),
                    "total_tokens": getattr(attr_value, 'total_tokens', 0)
                }
                break
            elif attr == 'metrics' and hasattr(attr_value, 'accumulated_usage'):
                usage = attr_value.accumulated_usage
                token_usage = {
                    "input_tokens": usage.get('inputTokens', usage.get('input_tokens', 0)),
                    "output_tokens": usage.get('outputTokens', usage.get('output_tokens', 0)),
                    "total_tokens": usage.get('totalTokens', usage.get('total_tokens', 0))
                }
                break
    
    logger.info(f"Extracted token usage: {token_usage}")
    return token_usage

# =============================================================================
# SUPABASE CONNECTION MANAGEMENT
# =============================================================================

class DextroSupabaseManager:
    """Dextro-specific Supabase connection manager with IoT device operations"""
    
    def __init__(self, url: str, key: str):
        if not url or not key:
            raise ValueError("Supabase URL and key are required")
        
        self.url = url
        self.key = key
        self._client = None
        self.logger = logging.getLogger(f"{__name__}.supabase")
    
    @property
    def client(self) -> Client:
        """Lazy initialization of Supabase client"""
        if self._client is None:
            try:
                self._client = create_client(self.url, self.key)
                self.logger.info("Dextro Supabase client initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize Supabase client: {e}")
                raise
        return self._client
    
    def execute_with_retry(self, operation, max_retries: int = MAX_RETRIES):
        """Execute Supabase operations with retry logic"""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                result = operation()
                
                if hasattr(result, 'data') and result.data is not None:
                    return result.data
                elif hasattr(result, 'error') and result.error:
                    self.logger.error(f"Supabase operation error: {result.error}")
                    return {"error": str(result.error)}
                else:
                    return result
                    
            except PostgrestAPIError as e:
                last_exception = e
                error_message = str(e).lower()
                
                if "no rows" in error_message or "pgrst116" in error_message:
                    self.logger.info("No data found for query")
                    return []
                elif "permission denied" in error_message:
                    self.logger.warning("Permission denied")
                    return {"error": "Insufficient permissions to access this data"}
                elif attempt < max_retries - 1:
                    self.logger.warning(f"Retrying operation... (attempt {attempt + 1})")
                    continue
                else:
                    self.logger.error(f"Supabase API error: {e}")
                    return {"error": f"Database operation failed: {e}"}
                    
            except Exception as e:
                last_exception = e
                self.logger.error(f"Unexpected error: {e}")
                if attempt < max_retries - 1:
                    continue
                else:
                    return {"error": f"Operation failed after {max_retries} attempts: {e}"}
        
        return {"error": f"Operation failed after {max_retries} attempts: {last_exception}"}

# Initialize global Supabase manager (only if credentials are available)
if SUPABASE_URL and SUPABASE_KEY:
    supabase_manager = DextroSupabaseManager(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase_manager = None

# =============================================================================
# REMOVED TOOLS - NOW IN agentic_tools.py
# =============================================================================

# =============================================================================
# AGENT CONFIGURATION AND ORCHESTRATION
# =============================================================================

def create_anthropic_model(claude_key=None) -> AnthropicModel:
    """Configure Anthropic model for Claude integration"""
    
    claude_key = claude_key or CLAUDE_KEY
    if not claude_key:
        raise ValueError("CLAUDE_KEY is required")
    
    model = AnthropicModel(
        client_args={"api_key": claude_key},
        model_id=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        params={
            "temperature": TEMPERATURE
        }
    )
    
    logger.info(f"Anthropic model configured: {CLAUDE_MODEL}")
    return model

def validate_configuration(claude_key=None, supabase_url=None, supabase_key=None):
    """Validate all required configuration is present"""
    missing_config = []
    
    # Use provided values or fall back to global config
    claude_key = claude_key or CLAUDE_KEY
    supabase_url = supabase_url or SUPABASE_URL
    supabase_key = supabase_key or SUPABASE_KEY
    
    if not claude_key:
        missing_config.append("CLAUDE_KEY")
    if not supabase_url:
        missing_config.append("SUPABASE_URL")  
    if not supabase_key:
        missing_config.append("SUPABASE_KEY")
    
    if missing_config:
        error_msg = f"Missing required configuration: {', '.join(missing_config)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info("Dextro agent configuration validation passed")

# =============================================================================
# STREAMLIT INTEGRATION FUNCTIONS
# =============================================================================

@st.cache_resource
def init_claude_agent(supabase_url: str = None, supabase_key: str = None, claude_key: str = None):
    """Initialize the Dextro IoT Agent for Streamlit integration"""
    # Use provided values or fall back to configured values
    supabase_url = supabase_url or SUPABASE_URL
    supabase_key = supabase_key or SUPABASE_KEY
    claude_key = claude_key or CLAUDE_KEY
    if not STRANDS_AVAILABLE:
        logger.error("Strands SDK not available")
        return None
    
    try:
        # Validate configuration
        logger.info("Validating configuration...")
        validate_configuration(claude_key, supabase_url, supabase_key)
        
        # Update global supabase_manager if needed
        global supabase_manager
        if not supabase_manager and supabase_url and supabase_key:
            supabase_manager = DextroSupabaseManager(supabase_url, supabase_key)
        
        # Create Anthropic model
        logger.info("Creating Anthropic model...")
        model = create_anthropic_model(claude_key)
        
        # Get tools from the agentic_tools module
        logger.info("Preparing tools...")
        tools = get_all_tools()
        logger.info(f"Created {len(tools)} tools for agent")
        
        # Create agent with PrintingCallbackHandler for now (better debugging)
        logger.info("Initializing Strands Agent with PrintingCallbackHandler...")
        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            callback_handler=PrintingCallbackHandler(),
            name=AGENT_NAME
        )
        
        logger.info(f"Dextro IoT agent initialized successfully")
        return agent
        
    except Exception as e:
        error_msg = f"Failed to initialize Dextro agent: {e}"
        logger.error(error_msg)
        logger.exception("Full traceback:")
        if hasattr(st, 'error'):
            st.error(f"❌ Error initializing AI agent: {str(e)}")
        return None

def query_claude_agent(agent, question: str):
    """Query the Dextro IoT agent with official Strands response handling"""
    try:
        if not agent:
            return "❌ Dextro AI Agent not initialized"
        
        logger.info(f"Processing query: {question[:100]}...")
        
        # Process the query
        response = agent(question)
        
        logger.info("Query completed, extracting results...")
        
        # Extract tool results and token usage from callback handler
        tool_results = _extract_tool_results_from_callback(agent)
        token_usage = None
        if hasattr(agent, '_callback_handler') and hasattr(agent._callback_handler, 'token_usage'):
            token_usage = agent._callback_handler.token_usage
        
        # Store results in session state for Streamlit display
        if hasattr(st, 'session_state'):
            st.session_state.tool_usage = tool_results
            if token_usage:
                st.session_state.last_token_usage = token_usage
            
            logger.info(f"Stored {len(tool_results)} tool results and token usage in session")
        
        # Get response text
        response_text = str(response)
        
        # Display metrics in Streamlit
        if hasattr(st, 'session_state'):
            _display_agent_metrics(token_usage, tool_results)
        
        return response_text
        
    except Exception as e:
        logger.error(f"Error querying Dextro agent: {e}")
        return f"❌ Error processing request: {str(e)}"

def _display_agent_metrics(token_usage, tool_results):
    """Display agent metrics including token usage and tool results"""
    if not hasattr(st, 'session_state'):
        return
    
    # Display agent console logs
    if hasattr(st.session_state, 'agent_console_logs') and st.session_state.agent_console_logs:
        with st.expander("🖥️ Agent Console", expanded=False):
            for log_entry in st.session_state.agent_console_logs[-20:]:  # Show last 20 entries
                st.code(log_entry, language="text")
    
    # Display token usage
    if token_usage:
        with st.expander("📊 Token Usage", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Input Tokens", f"{token_usage['input_tokens']:,}")
            with col2:
                st.metric("Output Tokens", f"{token_usage['output_tokens']:,}")
            with col3:
                st.metric("Total Tokens", f"{token_usage['total_tokens']:,}")
    
    # Display tool results
    if tool_results and len(tool_results) > 0:
        with st.expander(f"🔧 Tool Results ({len(tool_results)} tools used)", expanded=False):
            for i, tool_usage in enumerate(tool_results):
                st.markdown(f"**Tool {i+1}: {tool_usage.get('tool_name', 'unknown')}** (Sequence {tool_usage.get('sequence', 'unknown')})")
                st.markdown(f"*Timestamp:* {tool_usage.get('timestamp', 'unknown')}")
                st.markdown(f"*Tool Use ID:* {tool_usage.get('tool_use_id', 'unknown')}")
                
                # Show tool input/query
                if tool_usage.get('input'):
                    st.markdown("*Input/Query:*")
                    st.json(tool_usage['input'])
                
                # Show tool output
                if tool_usage.get('output'):
                    st.markdown("*Output:*")
                    st.json(tool_usage['output'])
                
                # Show token metadata if available
                if tool_usage.get('token_metadata'):
                    st.markdown("*Token Metadata:*")
                    st.json(tool_usage['token_metadata'])
                
                if i < len(tool_results) - 1:
                    st.markdown("---")
    else:
        # Debug: show what we have in session state
        if hasattr(st, 'session_state') and hasattr(st.session_state, 'tool_usage'):
            if st.session_state.tool_usage:
                with st.expander("🔧 Session Tool Results (Fallback)", expanded=False):
                    st.json(st.session_state.tool_usage)

def get_dextro_context():
    """Get the enhanced context for Dextro IoT assistant"""
    return """
    You are an advanced IoT device monitoring assistant for the Dextro platform with comprehensive analytics capabilities.

    PLATFORM SPECIALIZATION:
    - Real-time IoT device power consumption tracking and analysis
    - Intelligent pump error code diagnosis with actionable recommendations
    - Customer profile management and service optimization
    - Predictive maintenance scheduling and anomaly detection
    - System-wide health monitoring and automated alerting
    - Data visualization and comprehensive reporting

    AVAILABLE TOOLS:
    1. get_device_power_data(columns, device_id, date, filters): Smart device data retrieval with computed insights
       - PRIMARY tool for device analysis - let the model specify columns and filters
       - Provides computed analysis (error rates, power statistics, time ranges) based on selected columns
       - Only analyzes columns that are actually retrieved (no "ghost" column errors)
       - Examples:
         * get_device_power_data("device_id,PumpError,CreatedOnDate", device_id=865198074539541)
         * get_device_power_data("Power,Voltage,Current,Temperature", date="2025-08-21") 
         * get_device_power_data("*", filters={"Location": "Mumbai", "PumpError": "!0"})

    2. query_supabase_database(columns, table_name, filters, order_by, limit): Raw data queries without analysis
       - Use for simple operations: getting unique values, basic filtering, raw data extraction
       - NO computed insights - just returns raw records
       - Examples:
         * query_supabase_database("Location")  # Gets unique locations
         * query_supabase_database("*", order_by="CreatedOnDate.desc", limit=10)  # Latest records

    3. get_customer_device_info(device_id): Get customer profile and device context
       - Links device IDs to customer information
       - Provides location, district, and franchise context for devices

    4. monitor_system_health(): Comprehensive system-wide monitoring  
       - Analyzes health across all devices in the network
       - Excludes normal operation codes (0, 9999) from error analysis

    TOOL SELECTION GUIDANCE:
    - Use get_device_power_data() when you need analysis, insights, or computed metrics
    - Use query_supabase_database() for simple data retrieval, unique values, or raw records
    - ALWAYS specify the exact columns you need - tools will only analyze what's requested
    - Device IDs are long numbers (e.g., 865198074539541) - extract from user queries

    COLUMN SELECTION STRATEGY:
    - Be explicit about columns: "device_id,PumpError,Power" not "*" 
    - Only request columns you'll actually use for analysis
    - Tools perform smarter analysis when you specify exact columns needed
    - Error analysis only works if "PumpError" column is requested
    - Power analysis only works if "Power" column is requested

    ENHANCED CAPABILITIES:
    - Execute any SELECT query on device_power_logs and customer_profile tables
    - Automatically extract and validate device IDs from user input
    - Query device_power_logs table with correct column names (CreatedOnDate, PumpError, Power, etc.)
    - Answer specific questions about error patterns, dates, locations, and frequencies
    - Generate detailed diagnostic reports with severity assessment based on PumpError patterns
    - Analyze device performance using Power, Voltage, Current, Temperature, and other metrics
    - Track device runtime (TodayRunTime, TotalRunTime) and water flow (TodayLitre, TotalLitres)
    - Monitor GSM signal strength and power consumption (Power_KWH)
    - Perform location-based analysis across Districts and Franchises
    - Generate business intelligence insights with automatic pattern detection
    - Create data-driven visualizations and trend analysis
    - Deliver actionable business intelligence for IoT operations

    IMPORTANT DATABASE REMINDERS:
    - Use CreatedOnDate (not created_on_date) for timestamps
    - Use PumpError (not pump_error) for error codes  
    - Use Power (not power) for power consumption data
    - All column names are case-sensitive and follow the exact schema provided

    Always provide detailed analysis, actionable insights, and explain technical findings in business terms.
    """

# Legacy compatibility functions (maintaining interface for existing app.py)
def fetch_device_power_logs_with_customer(datalake: Client, device_id: int):
    """Legacy compatibility function for existing app.py integration"""
    try:
        # Use the new tool internally
        result = get_device_power_data(device_id)
        
        if result.get("success"):
            return result.get("raw_data", []), "direct_query"
        else:
            return [], "error"
            
    except Exception as e:
        logger.error(f"Error in legacy function: {e}")
        return [], "error"

# =============================================================================
# MAIN EXECUTION (for standalone testing)
# =============================================================================

async def main():
    """Main function for standalone testing of the Dextro agent"""
    print(f"🚀 Initializing {AGENT_NAME} for Dextro IoT Platform...")
    print(f"📊 Model: {CLAUDE_MODEL} (Claude Anthropic)")
    print(f"🗄️ Database: Supabase (Dextro DataLake)")
    print(f"🔧 Tools: Device Analysis, Error Diagnosis, System Monitoring")
    print("-" * 60)
    
    try:
        # Initialize agent
        agent = init_claude_agent()
        
        if not agent:
            print("❌ Failed to initialize agent")
            return 1
        
        print(f"✅ {AGENT_NAME} initialized successfully!")
        print("💬 You can now interact with the Dextro IoT assistant. Type 'quit' to exit.\n")
        
        # Interactive loop
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                print(f"\n🤖 {AGENT_NAME}: ", end="")
                response = query_claude_agent(agent, user_input)
                print(response)
                print("\n" + "-" * 60)
                
            except KeyboardInterrupt:
                print("\n\n⚠️ Interrupted by user. Exiting gracefully...")
                break
            except Exception as e:
                print(f"\n❌ Error processing request: {e}")
                continue
    
    except Exception as e:
        print(f"💥 Failed to initialize Dextro agent: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    """Entry point for standalone execution"""
    
    print("=" * 60)
    print("🤖 DEXTRO IOT AGENT WITH CLAUDE ANTHROPIC & SUPABASE")
    print("=" * 60)
    
    try:
        exit_code = asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Application terminated by user")
        exit_code = 0
    except Exception as e:
        print(f"💥 Application crashed: {e}")
        logger.error(f"Application crash: {e}")
        exit_code = 1
    
    exit(exit_code)