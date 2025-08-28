#!/usr/bin/env python3
"""
Callback handler for capturing model outputs and tool results
"""

import json
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import streamlit as st

logger = logging.getLogger(__name__)


class CaptureCallbackHandler:
    """Callback handler that captures model outputs and sends them to Streamlit console."""

    def __init__(self, request_id: Optional[str] = None):
        self.request_id = request_id
        self.pending_token_metadata = None
        self.sequence_counter = 0
        self.tool_results = []
        self.assistant_messages = []
        self.token_usage = None

    def __call__(self, **kwargs: Any) -> None:
        """Process callback events and send to Streamlit."""
        if not self.request_id:
            self.request_id = f"dextro_{int(time.time())}"

        timestamp = int(time.time())

        # Handle token metadata
        if "metadata" in kwargs.get("event", {}):
            self._process_token_metadata(kwargs["event"]["metadata"])
            return

        # Handle assistant messages
        if "role" in kwargs.get("message", {}) and kwargs["message"]["role"] == "assistant":
            self._process_assistant_message(kwargs["message"], timestamp)
            return

        # Handle tool results
        if "role" in kwargs.get("message", {}) and kwargs["message"]["role"] == "user":
            content = kwargs["message"].get("content", [])
            if isinstance(content, list) and len(content) > 0:
                if isinstance(content[0], dict) and "toolResult" in content[0]:
                    self._process_tool_result(kwargs["message"], timestamp)
                    return

        # Handle final results
        if "result" in kwargs:
            self._process_final_result(kwargs["result"], timestamp)
            return

    def _process_token_metadata(self, metadata: Dict[str, Any]) -> None:
        """Process token metadata."""
        usage = metadata.get("usage", {})
        metrics = metadata.get("metrics", {})

        self.pending_token_metadata = {
            "inputTokens": usage.get("inputTokens"),
            "outputTokens": usage.get("outputTokens"),
            "totalTokens": usage.get("totalTokens"),
            "latencyMs": metrics.get("latencyMs")
        }
        
        self.token_usage = {
            "input_tokens": usage.get("inputTokens", 0),
            "output_tokens": usage.get("outputTokens", 0),
            "total_tokens": usage.get("totalTokens", 0)
        }

        self._log_to_streamlit(f"📊 Token Metadata: {json.dumps(self.pending_token_metadata)}")

    def _process_assistant_message(self, message: Dict[str, Any], timestamp: int) -> None:
        """Process assistant messages."""
        content = message.get("content", [])
        self.sequence_counter += 1
        
        msg_info = {
            "sequence": self.sequence_counter,
            "timestamp": timestamp,
            "content": content,
            "token_metadata": self.pending_token_metadata
        }
        self.assistant_messages.append(msg_info)

        self._log_to_streamlit(f"🤖 Assistant Message (Sequence {self.sequence_counter})")
        self._log_to_streamlit(f"   Timestamp: {timestamp}")
        self._log_to_streamlit(f"   Content: {json.dumps(content)}")
        if self.pending_token_metadata:
            self._log_to_streamlit(f"   Token Metadata: {json.dumps(self.pending_token_metadata)}")
        self.pending_token_metadata = None

    def _process_tool_result(self, message: Dict[str, Any], timestamp: int) -> None:
        """Process tool results."""
        content = message.get("content", [])
        self.sequence_counter += 1

        if content and isinstance(content[0], dict):
            tool_result = content[0].get("toolResult", {})
            
            # Find the corresponding tool call to get the input/query
            tool_input = None
            tool_name = "unknown"
            for assistant_msg in reversed(self.assistant_messages):
                msg_content = assistant_msg.get("content", [])
                for item in msg_content:
                    if isinstance(item, dict) and item.get("type") == "toolUse":
                        if item.get("toolUseId") == tool_result.get('toolUseId'):
                            tool_name = item.get("name", "unknown")
                            tool_input = item.get("input", {})
                            break
                if tool_input:
                    break
            
            tool_info = {
                "sequence": self.sequence_counter,
                "timestamp": timestamp,
                "tool_name": tool_name,
                "tool_use_id": tool_result.get('toolUseId', ''),
                "input": tool_input,
                "output": tool_result.get('content', []),
                "token_metadata": self.pending_token_metadata
            }
            self.tool_results.append(tool_info)
            
            self._log_to_streamlit(f"🔧 Tool Result (Sequence {self.sequence_counter})")
            self._log_to_streamlit(f"   Tool: {tool_name}")
            self._log_to_streamlit(f"   Timestamp: {timestamp}")
            self._log_to_streamlit(f"   Tool Use ID: {tool_result.get('toolUseId', '')}")
            if tool_input:
                self._log_to_streamlit(f"   Input/Query: {json.dumps(tool_input)}")
            self._log_to_streamlit(f"   Output: {json.dumps(tool_result.get('content', []))}")
            if self.pending_token_metadata:
                self._log_to_streamlit(f"   Token Metadata: {json.dumps(self.pending_token_metadata)}")
        self.pending_token_metadata = None

    def _process_final_result(self, result: Any, timestamp: int) -> None:
        """Process final results."""
        self.sequence_counter += 1

        self._log_to_streamlit(f"✅ Final Result (Sequence {self.sequence_counter})")
        self._log_to_streamlit(f"   Timestamp: {timestamp}")
        self._log_to_streamlit(f"   Result: {str(result)}")
        if self.pending_token_metadata:
            self._log_to_streamlit(f"   Token Metadata: {json.dumps(self.pending_token_metadata)}")
        self.pending_token_metadata = None

    def _log_to_streamlit(self, message: str) -> None:
        """Send log message to Streamlit console."""
        try:
            if hasattr(st, 'session_state'):
                if 'agent_console_logs' not in st.session_state:
                    st.session_state.agent_console_logs = []
                st.session_state.agent_console_logs.append(f"{datetime.now().strftime('%H:%M:%S')} | {message}")
                # Keep only last 50 log entries to prevent memory issues
                if len(st.session_state.agent_console_logs) > 50:
                    st.session_state.agent_console_logs = st.session_state.agent_console_logs[-50:]
        except Exception as e:
            # Fallback to regular logging if Streamlit is not available
            logger.info(f"Console: {message}")
            logger.debug(f"Streamlit logging error: {e}")