import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class TranscriptWriter:
    """Helper to write agent output to both console and transcript file."""

    def __init__(self, transcript_file: Path):
        self.file = open(transcript_file, "w", encoding="utf-8")

    def write(self, text: str, end: str = "", flush: bool = True):
        """Write text to both console and transcript."""
        print(text, end=end, flush=flush)
        self.file.write(text + end)
        if flush:
            self.file.flush()

    def write_to_file(self, text: str, flush: bool = True):
        """Write text to transcript file only (not console)."""
        self.file.write(text)
        if flush:
            self.file.flush()

    def close(self):
        """Close the transcript file."""
        self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()
        return False


class ToolCallJsonlLogger:
    """Logs tool calls to JSONL format for structured analysis."""

    def __init__(self, log_dir: Path):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_file = open(self.log_dir / "tool_calls.jsonl", "w", encoding="utf-8")

    def log_event(self, event: Dict[str, Any]):
        """Write a structured event to JSONL file.
        
        Safe to call after close() - will silently skip logging if file is closed.
        """
        if self.jsonl_file is None or self.jsonl_file.closed:
            # File already closed - skip logging (can happen with late hook callbacks)
            return
        
        try:
            self.jsonl_file.write(json.dumps(event) + "\n")
            self.jsonl_file.flush()
        except (ValueError, OSError) as e:
            # File closed between check and write, or other I/O error
            # Don't fail the workflow - tool logging is auxiliary
            print(f"[Warning] Failed to log tool event: {e}", flush=True)

    async def pre_tool_use_hook(
        self, hook_input: Dict[str, Any], tool_use_id: Optional[str], context: Any
    ) -> Dict[str, Any]:
        """Hook callback for PreToolUse events."""
        tool_name = hook_input.get("tool_name", "unknown")
        tool_input = hook_input.get("tool_input", {})
        timestamp = datetime.now().isoformat()

        self.log_event(
            {
                "event": "tool_call_start",
                "timestamp": timestamp,
                "tool_use_id": tool_use_id,
                "tool_name": tool_name,
                "tool_input": tool_input,
            }
        )

        # Log to console for visibility
        print(f"[AGENT] → {tool_name}")
        if "file_path" in tool_input:
            print(f"    file: {tool_input['file_path']}")
        elif "pattern" in tool_input:
            print(f"    pattern: {tool_input['pattern']}")

        return {"continue_": True}
    
    def get_pre_tool_hook(self):
        """Return a standalone async function for PreToolUse hook."""
        async def hook(input_data: Dict[str, Any], tool_use_id: Optional[str], context: Any) -> Dict[str, Any]:
            return await self.pre_tool_use_hook(input_data, tool_use_id, context)
        return hook

    async def post_tool_use_hook(
        self, hook_input: Dict[str, Any], tool_use_id: Optional[str], context: Any
    ) -> Dict[str, Any]:
        """Hook callback for PostToolUse events."""
        tool_response = hook_input.get("tool_response")
        timestamp = datetime.now().isoformat()

        # Check for errors
        error = None
        if isinstance(tool_response, dict):
            error = tool_response.get("error")

        self.log_event(
            {
                "event": "tool_call_complete",
                "timestamp": timestamp,
                "tool_use_id": tool_use_id,
                "success": error is None,
                "error": error,
                "output_size": len(str(tool_response)) if tool_response else 0,
            }
        )

        return {"continue_": True}
    
    def get_post_tool_hook(self):
        """Return a standalone async function for PostToolUse hook."""
        async def hook(input_data: Dict[str, Any], tool_use_id: Optional[str], context: Any) -> Dict[str, Any]:
            return await self.post_tool_use_hook(input_data, tool_use_id, context)
        return hook

    def close(self):
        """Close the JSONL file."""
        if self.jsonl_file and not self.jsonl_file.closed:
            self.jsonl_file.close()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()
        return False