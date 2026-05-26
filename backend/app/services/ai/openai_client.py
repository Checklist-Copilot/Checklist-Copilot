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

import json
import os
from dataclasses import dataclass
from typing import Any, Callable


# Default model — small + cheap + supports tool calling reliably.
# Override with the OPENAI_MODEL env var. `gpt-3.5-turbo-1106` and later also work;
# legacy `gpt-3.5-turbo` is flaky on multi-tool responses.
_DEFAULT_MODEL = "gpt-4o-mini"


@dataclass
class ToolCall:
    """One tool invocation parsed out of a ChatCompletion response."""
    name: str
    arguments: dict[str, Any]


class OpenAIClient:
    def __init__(self, model: str | None = None) -> None:
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
    # Multi-turn agentic loop.                                                 #
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
    ) -> list[ToolCall]:
        """
        Run an agentic loop: send messages -> apply each tool call via
        `on_tool_call` -> feed the results back -> repeat.

        Stops when the model returns a response with no tool calls (meaning it
        considers the task done) or when `max_rounds` is reached (safety cap).

        `on_tool_call(call)` must return a JSON-serialisable dict describing the
        outcome (e.g. `{"ok": True, "new_id": "sec_abc"}`). The dict is sent back
        to the model as the "tool" role reply so it knows what happened.

        Returns the flat list of every tool call executed across all rounds.
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        all_calls: list[ToolCall] = []

        for _round in range(max_rounds):
            response = self._client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            msg = response.choices[0].message
            raw_tool_calls = msg.tool_calls or []

            # Model decided it's done.
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
                call = ToolCall(name=tc.function.name, arguments=args)
                all_calls.append(call)

                try:
                    outcome = on_tool_call(call)
                except Exception as exc:  # noqa: BLE001 — never let a callback error kill the loop
                    outcome = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(outcome),
                    }
                )

        return all_calls
