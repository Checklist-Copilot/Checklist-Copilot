"""
Thin wrapper around the OpenAI Python SDK.

Kept narrow on purpose: the rest of the AI module talks to this class instead
of importing OpenAI directly, so swapping providers later (Anthropic, local
model, fake for tests) only touches this one file.

The OpenAI key is read from the process environment, NOT from app.core.config.
This decouples the AI module from the rest of the backend settings so the
integration test (`test_ai_create_checklist.py`) can run without a DATABASE_URL
or JWT secret set.
"""
from __future__ import annotations

import base64
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


# Default model — small + cheap + supports tool calling reliably.
# Override with the OPENAI_MODEL env var. `gpt-3.5-turbo-1106` and later also work;
# legacy `gpt-3.5-turbo` is flaky on multi-tool responses.
_DEFAULT_MODEL = "gpt-4o-mini"


def _find_dotenv() -> Path | None:
    """Find the project .env file without importing app settings."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env"
        if candidate.exists():
            return candidate
    return None


@dataclass
class ToolCall:
    """One tool invocation parsed out of a ChatCompletion response."""
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatResult:
    """
    Outcome of a multi-turn `chat_with_tools` run.

    - `tool_calls`: every tool call executed across all rounds (the "actions").
    - `reply`: the model's natural-language message to the user (the "speech").
      This is the text the frontend shows in the chat panel.
    """
    tool_calls: list["ToolCall"]
    reply: str


class OpenAIClient:
    def __init__(self, model: str | None = None) -> None:
        load_dotenv(_find_dotenv())
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Export it in your environment "
                "or add it to backend/.env before calling the AI service."
            )

        try:
            from openai import OpenAI  # imported lazily so the rest of the app
            # never pays the import cost when the AI feature is unused.
        except ImportError as exc:
            raise RuntimeError(
                "The `openai` package is not installed. Run "
                "`pip install openai` in your backend environment."
            ) from exc

        self._client = OpenAI(api_key=api_key)
        self.model = model or os.environ.get("OPENAI_MODEL", _DEFAULT_MODEL)

    # ----------------------------------------------------------------------- #
    # Single-turn (kept for simple callers / debugging).                       #
    # ----------------------------------------------------------------------- #
    def complete_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict],
        *,
        temperature: float = 0.2,
    ) -> list[ToolCall]:
        """
        Send one chat-completion request with tool definitions and return the
        ordered list of tool calls the model made. Empty list if the model
        replied with plain text instead.
        """
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=tools,
            tool_choice="auto",
        )

        message = response.choices[0].message
        calls: list[ToolCall] = []
        for tc in message.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                continue
            calls.append(ToolCall(name=tc.function.name, arguments=args))
        return calls

    # ----------------------------------------------------------------------- #
    # Plain text completion with optional PDF attachments.                     #
    # ----------------------------------------------------------------------- #
    def complete_text(
        self,
        system_prompt: str,
        user_text: str,
        *,
        files: list[tuple[str, bytes]] | None = None,
        temperature: float = 0.2,
    ) -> str:
        """Return a plain text response, optionally grounded in attached PDFs."""
        user_content: str | list[dict[str, Any]] = user_text
        if files:
            content_parts: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
            for filename, raw_bytes in files:
                encoded = base64.b64encode(raw_bytes).decode("ascii")
                content_parts.append(
                    {
                        "type": "file",
                        "file": {
                            "filename": filename,
                            "file_data": f"data:application/pdf;base64,{encoded}",
                        },
                    }
                )
            user_content = content_parts

        response = self._client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        return (response.choices[0].message.content or "").strip()

    # ----------------------------------------------------------------------- #
    # Multi-turn agentic loop (text-only convenience wrapper).                 #
    # ----------------------------------------------------------------------- #
    def chat_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict],
        on_tool_call: Callable[[ToolCall], dict],
        *,
        max_rounds: int = 5,
        temperature: float = 0.2,
    ) -> ChatResult:
        """
        Run an agentic loop with a single text user message. Thin wrapper
        around the shared `_run_tool_loop` below.
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self._run_tool_loop(messages, tools, on_tool_call, max_rounds, temperature)

    # ----------------------------------------------------------------------- #
    # Multi-turn agentic loop with an image (vision).                          #
    # ----------------------------------------------------------------------- #
    def chat_with_tools_and_image(
        self,
        system_prompt: str,
        user_text: str,
        image_data_url: str,
        tools: list[dict],
        on_tool_call: Callable[[ToolCall], dict],
        *,
        prior_messages: list[dict[str, Any]] | None = None,
        max_rounds: int = 3,
        temperature: float = 0.2,
    ) -> ChatResult:
        """
        Same as `chat_with_tools`, but the user message includes an image so
        the model can "see" what the user is asking about.

        - `image_data_url` must be a `data:<mime>;base64,<...>` URL. The caller
          (the AI service) base64-encodes the bytes it fetched from storage.
        - `prior_messages` is an optional running conversation history so the
          user can ask follow-up questions about the same image. Each entry is
          `{"role": "user"|"assistant", "content": "..."}` — kept flat to make
          the frontend's job easy.
        """
        user_content = [
            {"type": "text", "text": user_text},
            {"type": "image_url", "image_url": {"url": image_data_url}},
        ]
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            *(prior_messages or []),
            {"role": "user", "content": user_content},
        ]
        return self._run_tool_loop(messages, tools, on_tool_call, max_rounds, temperature)

    # ----------------------------------------------------------------------- #
    # Multi-turn agentic loop with PDF attachments.                            #
    # ----------------------------------------------------------------------- #
    def chat_with_tools_and_files(
        self,
        system_prompt: str,
        user_text: str,
        files: list[tuple[str, bytes]],
        tools: list[dict],
        on_tool_call: Callable[[ToolCall], dict],
        *,
        max_rounds: int = 5,
        temperature: float = 0.2,
    ) -> ChatResult:
        """
        Same as `chat_with_tools`, but the user message includes one or more
        PDF attachments so the model can read them directly — no separate
        text-extraction step needed.

        - `files` is a list of `(filename, raw_bytes)` tuples. Each is sent as
          a `file` content part with base64-encoded `file_data`.
        """
        user_content: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
        for filename, raw_bytes in files:
            encoded = base64.b64encode(raw_bytes).decode("ascii")
            user_content.append(
                {
                    "type": "file",
                    "file": {
                        "filename": filename,
                        "file_data": f"data:application/pdf;base64,{encoded}",
                    },
                }
            )
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        return self._run_tool_loop(messages, tools, on_tool_call, max_rounds, temperature)

    # ----------------------------------------------------------------------- #
    # Shared loop body — both entry points feed into this.                     #
    # ----------------------------------------------------------------------- #
    def _run_tool_loop(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict],
        on_tool_call: Callable[[ToolCall], dict],
        max_rounds: int,
        temperature: float,
    ) -> ChatResult:
        """
        Drive the agentic loop: send messages -> apply each tool call via
        `on_tool_call` -> feed the results back -> repeat.

        Stops when the model returns a response with no tool calls or when
        `max_rounds` is reached. Returns the executed tool calls plus the
        model's accumulated natural-language reply (used as the chat-panel text).
        """
        all_calls: list[ToolCall] = []
        reply_parts: list[str] = []

        for _round in range(max_rounds):
            round_number = _round + 1
            response = self._client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            msg = response.choices[0].message
            raw_tool_calls = msg.tool_calls or []
            logger.info(
                "AI tool-loop round %s/%s response: tool_calls=%s reply=%r",
                round_number,
                max_rounds,
                [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                    for tc in raw_tool_calls
                ],
                msg.content,
            )

            # Capture any natural-language text the model produced this round.
            # This is the channel it uses to "talk back" to the user — e.g.
            # answering "Yes, I see 4 screws" or confirming what it changed.
            if msg.content and msg.content.strip():
                reply_parts.append(msg.content.strip())

            # Model decided it's done (no more actions).
            if not raw_tool_calls:
                break

            # Echo the assistant's message back into the history so the next
            # turn's "tool" replies have valid ids to attach to.
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in raw_tool_calls
                    ],
                }
            )

            # Apply each tool call and append a "tool" reply for it.
            for tc in raw_tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                    logger.exception(
                        "AI tool call JSON parse failed: round=%s tool=%s raw_arguments=%r",
                        round_number,
                        tc.function.name,
                        tc.function.arguments,
                    )
                call = ToolCall(name=tc.function.name, arguments=args)
                all_calls.append(call)

                try:
                    outcome = on_tool_call(call)
                except Exception as exc:  # noqa: BLE001 — never let a callback error kill the loop
                    logger.exception(
                        "AI tool callback crashed: round=%s tool=%s arguments=%s",
                        round_number,
                        call.name,
                        call.arguments,
                    )
                    outcome = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

                logger.info(
                    "AI tool call outcome: round=%s tool=%s arguments=%s outcome=%s",
                    round_number,
                    call.name,
                    call.arguments,
                    outcome,
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(outcome),
                    }
                )

        return ChatResult(tool_calls=all_calls, reply="\n".join(reply_parts).strip())
