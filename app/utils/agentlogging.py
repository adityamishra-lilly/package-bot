import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


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


# Map subagent names to human-readable phase labels
_PHASE_LABELS = {
    "planner-agent": "PLANNING",
    "executor-agent": "EXECUTION",
    "verifier-agent": "VERIFICATION",
    "creator-agent": "CREATION",
    "reviewer-agent": "REVIEW",
}


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


class ObservabilityLogger:
    """Enhanced logger that produces human-readable observability artifacts.

    Produces these files alongside the existing tool_calls.jsonl:
      - events.jsonl   -- high-level milestone timeline
      - todos.log      -- human-readable TODO tracking
      - {subagent}_output.md -- full subagent output per phase
    Also enriches the transcript with phase banners and TODO progress.
    """

    def __init__(
        self,
        log_dir: Path,
        transcript: TranscriptWriter,
        agent_context: str = "agent",
        workspace_dir: Optional[Path] = None,
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.transcript = transcript
        self.agent_context = agent_context
        self.workspace_dir = Path(workspace_dir) if workspace_dir else None

        # Backward-compat: keep tool_calls.jsonl
        self.jsonl_file = open(self.log_dir / "tool_calls.jsonl", "w", encoding="utf-8")

        # New files
        self.events_file = open(self.log_dir / "events.jsonl", "w", encoding="utf-8")
        self.todos_file = open(self.log_dir / "todos.log", "w", encoding="utf-8")

        # State tracking
        self._current_phase: Optional[str] = None
        self._phase_start_time: Optional[datetime] = None
        self._subagent_call_ids: Dict[str, str] = {}  # tool_use_id -> subagent type
        self._todo_state: Dict[str, str] = {}  # todo content -> last known status

    # ------------------------------------------------------------------
    # Low-level writers
    # ------------------------------------------------------------------

    def _log_jsonl(self, event: Dict[str, Any]):
        """Write to tool_calls.jsonl (backward compat)."""
        if self.jsonl_file is None or self.jsonl_file.closed:
            return
        try:
            self.jsonl_file.write(json.dumps(event) + "\n")
            self.jsonl_file.flush()
        except (ValueError, OSError):
            pass

    def _log_event(self, event: Dict[str, Any]):
        """Write to events.jsonl."""
        if self.events_file is None or self.events_file.closed:
            return
        try:
            self.events_file.write(json.dumps(event) + "\n")
            self.events_file.flush()
        except (ValueError, OSError):
            pass

    def _log_todo(self, line: str):
        """Append a line to todos.log."""
        if self.todos_file is None or self.todos_file.closed:
            return
        try:
            self.todos_file.write(line + "\n")
            self.todos_file.flush()
        except (ValueError, OSError):
            pass

    def _write_subagent_output(self, subagent_type: str, content: str):
        """Write (or append) subagent output to a markdown file."""
        try:
            output_path = self.log_dir / f"{subagent_type}_output.md"
            mode = "a" if output_path.exists() else "w"
            with open(output_path, mode, encoding="utf-8") as f:
                if mode == "a":
                    f.write("\n\n---\n\n")
                f.write(content)
        except (ValueError, OSError):
            pass

    # ------------------------------------------------------------------
    # Phase / subagent helpers
    # ------------------------------------------------------------------

    def _phase_label(self, subagent_type: Optional[str]) -> str:
        if not subagent_type:
            return "ORCHESTRATOR"
        return _PHASE_LABELS.get(subagent_type, subagent_type.upper())

    def _format_duration(self, ms: int) -> str:
        if ms < 1000:
            return f"{ms}ms"
        secs = ms // 1000
        if secs < 60:
            return f"{secs}s"
        mins = secs // 60
        remaining_secs = secs % 60
        return f"{mins}m {remaining_secs}s"

    # ------------------------------------------------------------------
    # Task (subagent) handlers
    # ------------------------------------------------------------------

    def _handle_task_pre(self, tool_input: Dict[str, Any], tool_use_id: Optional[str]):
        """Handle PreToolUse for Task tool (subagent dispatch)."""
        subagent_type = tool_input.get("subagent_type", "")
        if not subagent_type:
            return

        self._current_phase = subagent_type
        self._phase_start_time = datetime.now()
        if tool_use_id:
            self._subagent_call_ids[tool_use_id] = subagent_type

        phase_label = self._phase_label(subagent_type)
        timestamp = datetime.now().isoformat()

        # Phase banner to transcript + console
        banner = (
            f"\n{'=' * 40}\n"
            f"  PHASE: {phase_label} ({subagent_type})\n"
            f"  Started: {timestamp}\n"
            f"{'=' * 40}\n"
        )
        self.transcript.write(banner)

        # Emit event
        self._log_event({
            "event": "subagent_start",
            "timestamp": timestamp,
            "subagent": subagent_type,
            "phase": phase_label,
        })

    @staticmethod
    def _extract_text_from_response(tool_response: Any) -> str:
        """Extract human-readable text from a Task tool response.

        The Task tool returns a dict like:
          {"status": "completed", "content": [{"type": "text", "text": "..."}], ...}
        We extract and concatenate the text blocks. Falls back to str() for
        unexpected formats.
        """
        if not tool_response:
            return ""
        if isinstance(tool_response, dict):
            content_blocks = tool_response.get("content")
            if isinstance(content_blocks, list):
                texts = []
                for block in content_blocks:
                    if isinstance(block, dict) and block.get("type") == "text":
                        texts.append(block.get("text", ""))
                if texts:
                    return "\n\n".join(texts)
            # If no content blocks found but there's a 'result' string, use that
            result = tool_response.get("result")
            if isinstance(result, str):
                return result
        # Fallback: convert to string but skip if it's the raw dict repr
        return str(tool_response)

    def _handle_task_post(self, tool_response: Any, tool_use_id: Optional[str]):
        """Handle PostToolUse for Task tool (subagent completion)."""
        subagent_type = self._subagent_call_ids.pop(tool_use_id, None) if tool_use_id else None
        if not subagent_type:
            subagent_type = self._current_phase or "unknown"

        phase_label = self._phase_label(subagent_type)
        timestamp = datetime.now().isoformat()

        # Calculate duration
        duration_ms = 0
        if self._phase_start_time:
            duration_ms = int((datetime.now() - self._phase_start_time).total_seconds() * 1000)

        # Extract actual text content from the Task response
        output_text = self._extract_text_from_response(tool_response)
        output_file = f"{subagent_type}_output.md"
        if output_text:
            self._write_subagent_output(subagent_type, output_text)

        # For planner-agent, also write to workspace as remediation-plan.md
        if subagent_type == "planner-agent" and output_text and self.workspace_dir:
            try:
                plan_path = self.workspace_dir / "remediation-plan.md"
                with open(plan_path, "w", encoding="utf-8") as f:
                    f.write(output_text)
            except (ValueError, OSError):
                pass

        # Phase completion banner
        banner = (
            f"\n{'-' * 40}\n"
            f"  PHASE COMPLETE: {phase_label}\n"
            f"  Duration: {self._format_duration(duration_ms)} | Output: {len(output_text):,} chars\n"
            f"  Saved: {output_file}\n"
            f"{'-' * 40}\n"
        )
        self.transcript.write(banner)

        # Preview first 300 chars to console
        if output_text:
            preview = output_text[:300]
            if len(output_text) > 300:
                preview += "..."
            print(f"[{phase_label}] Output preview: {preview}", flush=True)

        # Emit event
        self._log_event({
            "event": "subagent_complete",
            "timestamp": timestamp,
            "subagent": subagent_type,
            "phase": phase_label,
            "duration_ms": duration_ms,
            "output_chars": len(output_text),
            "output_file": output_file,
        })

        self._current_phase = None
        self._phase_start_time = None

    # ------------------------------------------------------------------
    # TodoWrite handler
    # ------------------------------------------------------------------

    def _handle_todowrite_pre(self, tool_input: Dict[str, Any]):
        """Handle PreToolUse for TodoWrite -- diff TODO state and log changes."""
        todos: List[Dict[str, Any]] = tool_input.get("todos", [])
        if not todos:
            return

        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        phase_tag = self._phase_label(self._current_phase)

        new_state: Dict[str, str] = {}
        completed_count = 0
        total_count = len(todos)
        active_item: Optional[str] = None

        for todo in todos:
            content = todo.get("content", "")
            status = todo.get("status", "pending")
            new_state[content] = status

            if status == "completed":
                completed_count += 1
            elif status == "in_progress":
                active_item = content

            old_status = self._todo_state.get(content)

            if old_status is None:
                # New item
                self._log_todo(f"[{timestamp}] CREATED  | \"{content}\"  ({status})")
            elif old_status != status:
                # Status transition
                if status == "completed":
                    self._log_todo(f"[{timestamp}] DONE     | \"{content}\"")
                elif status == "in_progress":
                    self._log_todo(f"[{timestamp}] STARTED  | \"{content}\"")
                else:
                    self._log_todo(f"[{timestamp}] {status.upper():<8} | \"{content}\"")

        # Progress bar
        if total_count > 0:
            filled = int((completed_count / total_count) * 10)
            bar = "#" * filled + "." * (10 - filled)
            active_str = f" | Active: \"{active_item}\"" if active_item else ""
            progress_line = f"[{timestamp}] PROGRESS | [{bar}] {completed_count}/{total_count} done{active_str}"
            self._log_todo(progress_line)

            # Write to transcript
            transcript_line = f"[TODO] {completed_count}/{total_count} done{active_str}\n"
            self.transcript.write(transcript_line)

        # Emit event
        self._log_event({
            "event": "todo_update",
            "timestamp": datetime.now().isoformat(),
            "phase": phase_tag,
            "completed": completed_count,
            "total": total_count,
            "active": active_item,
        })

        # Update tracked state
        self._todo_state = new_state

    # ------------------------------------------------------------------
    # Hook interface (matches ToolCallJsonlLogger)
    # ------------------------------------------------------------------

    async def pre_tool_use_hook(
        self, hook_input: Dict[str, Any], tool_use_id: Optional[str], context: Any
    ) -> Dict[str, Any]:
        """Hook callback for PreToolUse events."""
        tool_name = hook_input.get("tool_name", "unknown")
        tool_input = hook_input.get("tool_input", {})
        timestamp = datetime.now().isoformat()

        # Backward-compat JSONL logging
        self._log_jsonl({
            "event": "tool_call_start",
            "timestamp": timestamp,
            "tool_use_id": tool_use_id,
            "tool_name": tool_name,
            "tool_input": tool_input,
        })

        # Specialized handlers
        try:
            if tool_name == "Task":
                self._handle_task_pre(tool_input, tool_use_id)
            elif tool_name == "TodoWrite":
                self._handle_todowrite_pre(tool_input)
        except Exception:
            pass  # Never break the agent workflow

        # Console + transcript logging with phase prefix
        phase_prefix = f"[{self._phase_label(self._current_phase)}] " if self._current_phase else ""
        if tool_name not in ("Task", "TodoWrite"):
            tool_detail = ""
            if "file_path" in tool_input:
                tool_detail = f" ({tool_input['file_path']})"
            elif "pattern" in tool_input:
                tool_detail = f" ({tool_input['pattern']})"
            elif "command" in tool_input:
                cmd = tool_input["command"]
                tool_detail = f" ({cmd[:60]}{'...' if len(cmd) > 60 else ''})"

            log_line = f"{phase_prefix}-> {tool_name}{tool_detail}\n"
            self.transcript.write_to_file(log_line)
            print(f"[AGENT] {phase_prefix}-> {tool_name}{tool_detail}", flush=True)

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
        tool_name = hook_input.get("tool_name", "unknown")
        tool_response = hook_input.get("tool_response")
        timestamp = datetime.now().isoformat()

        error = None
        if isinstance(tool_response, dict):
            error = tool_response.get("error")

        # Backward-compat JSONL logging
        self._log_jsonl({
            "event": "tool_call_complete",
            "timestamp": timestamp,
            "tool_use_id": tool_use_id,
            "tool_name": tool_name,
            "success": error is None,
            "error": error,
            "output_size": len(str(tool_response)) if tool_response else 0,
        })

        # Specialized handlers
        try:
            if tool_name == "Task":
                self._handle_task_post(tool_response, tool_use_id)
        except Exception:
            pass  # Never break the agent workflow

        return {"continue_": True}

    def get_post_tool_hook(self):
        """Return a standalone async function for PostToolUse hook."""
        async def hook(input_data: Dict[str, Any], tool_use_id: Optional[str], context: Any) -> Dict[str, Any]:
            return await self.post_tool_use_hook(input_data, tool_use_id, context)
        return hook

    def close(self):
        """Close all open file handles."""
        for f in (self.jsonl_file, self.events_file, self.todos_file):
            try:
                if f and not f.closed:
                    f.close()
            except (ValueError, OSError):
                pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()
        return False