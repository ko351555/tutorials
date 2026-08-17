"""LLM backend for stages 1, 2, 5, 6, 10 (topic ideas, script, scene
planning assist, image prompts, packaging copy).

Default provider is Claude Code itself, run headless — no separate API key,
since the user already pays for Claude Code. See docs/ARCHITECTURE.md §6.
"""
from __future__ import annotations

import json
import subprocess

import requests

from ystick.config import Secrets
from ystick.core.exceptions import FatalError, RetryableError
from ystick.utils.files import content_hash
from ystick.utils.http_errors import is_quota_exhausted

CLAUDE_TIMEOUT_SECONDS = 300
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


class LLMClient:
    def __init__(self, secrets: Secrets, mock: bool = False):
        self.secrets = secrets
        self.mock = mock
        self.provider = secrets.llm_provider

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_mode: bool = False,
        mock_key: str = "generic",
    ) -> str:
        if self.mock:
            return self._mock_complete(prompt, mock_key=mock_key, json_mode=json_mode)
        if self.provider == "claude_code":
            return self._claude_code(prompt, system, json_mode)
        if self.provider == "openai":
            return self._openai(prompt, system, json_mode)
        raise FatalError(f"unknown LLM_PROVIDER: {self.provider!r}")

    # -- real providers ----------------------------------------------------

    def _claude_code(self, prompt: str, system: str | None, json_mode: bool) -> str:
        cmd = ["claude", "-p", prompt, "--output-format", "json"]
        if system:
            cmd += ["--append-system-prompt", system]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=CLAUDE_TIMEOUT_SECONDS
            )
        except FileNotFoundError as exc:
            raise FatalError("claude CLI not found on PATH — required for LLM_PROVIDER=claude_code") from exc
        except subprocess.TimeoutExpired as exc:
            raise RetryableError(f"claude CLI timed out: {exc}") from exc
        if proc.returncode != 0:
            # Some claude CLI failures (auth/usage-limit errors in
            # particular) print to stdout, not stderr — show both so the
            # real cause isn't silently dropped (see the ffmpeg fix in
            # video_assembly.py for the same class of bug).
            detail = proc.stderr.strip() or proc.stdout.strip() or "(no output on stdout or stderr)"
            raise RetryableError(f"claude CLI exited {proc.returncode}: {detail[:2000]}")
        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise FatalError(f"claude CLI produced non-JSON output: {exc}\n{proc.stdout[:2000]}") from exc
        return envelope.get("result", "")

    def _openai(self, prompt: str, system: str | None, json_mode: bool) -> str:
        if not self.secrets.openai_api_key:
            raise FatalError("OPENAI_API_KEY not set but LLM_PROVIDER=openai")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = {"model": "gpt-4o", "messages": messages}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            resp = requests.post(
                OPENAI_CHAT_URL,
                headers={"Authorization": f"Bearer {self.secrets.openai_api_key}"},
                json=body,
                timeout=120,
            )
        except requests.RequestException as exc:
            raise RetryableError(f"OpenAI request failed: {exc}") from exc
        if is_quota_exhausted(resp.status_code, resp.text):
            raise FatalError(
                f"OpenAI out of credits/quota — add billing at "
                f"platform.openai.com before retrying: {resp.text[:500]}"
            )
        if resp.status_code >= 500 or resp.status_code == 429:
            raise RetryableError(f"OpenAI {resp.status_code}: {resp.text[:500]}")
        if resp.status_code >= 400:
            raise FatalError(f"OpenAI {resp.status_code}: {resp.text[:500]}")
        return resp.json()["choices"][0]["message"]["content"]

    # -- mock mode -----------------------------------------------------------
    # Deterministic canned outputs keyed by what the stage is asking for, so
    # the full orchestration (state machine, retries, resume, folder layout)
    # can be exercised with zero API calls and zero cost.

    def _mock_complete(self, prompt: str, *, mock_key: str, json_mode: bool) -> str:
        variant = content_hash(prompt)[:6]
        if mock_key == "topic_ideas":
            ideas = [
                {
                    "title": f"[MOCK] Idea {i + 1} ({variant})",
                    "one_line_pitch": "Placeholder pitch generated in --mock mode.",
                    "viral_potential": 7 + (i % 3),
                    "search_demand": 6 + (i % 4),
                    "competition": 5 + (i % 4),
                    "watch_time_potential": 7,
                    "monetization_potential": 6,
                }
                for i in range(6)
            ]
            return json.dumps(ideas)
        if mock_key == "script":
            return (
                "[MOCK SCRIPT]\n\n"
                "Hook: Did you know this is a mock narration script?\n"
                "Body: This placeholder stands in for a real LLM-generated script "
                "so the rest of the pipeline (voice, timestamps, storyboard, images, "
                "assembly, packaging) can be exercised end-to-end without any API cost.\n"
                "Outro: Subscribe for more mock content."
            )
        if mock_key == "scene_prompt":
            return f"[MOCK IMAGE PROMPT {variant}] stickman doodle, placeholder scene"
        if mock_key == "shorts_excerpt":
            # Deliberately out of range (mock narration is only a few
            # seconds long) so callers exercise their own fallback-window
            # logic rather than trusting this blindly.
            return json.dumps({"start_ms": 0, "end_ms": 999_999_999, "reason": "[MOCK] placeholder excerpt pick"})
        if mock_key == "packaging":
            return json.dumps(
                {
                    "title": "[MOCK] Placeholder Viral Title",
                    "description": "Mock SEO description.",
                    "tags": ["mock", "placeholder"],
                    "thumbnail_text": "MOCK",
                    "thumbnail_prompts": [f"[MOCK THUMBNAIL PROMPT {variant}] variation {i + 1}" for i in range(5)],
                    "chapters": [{"time": "00:00", "label": "Intro"}],
                    "pinned_comment": "Mock pinned comment.",
                    "community_post": "Mock community post.",
                    "shorts_title": "[MOCK] Shorts title",
                    "shorts_description": "Mock shorts description.",
                }
            )
        return f"[MOCK RESPONSE {variant}] for prompt of length {len(prompt)}"
