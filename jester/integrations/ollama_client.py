"""
Ollama Integration - The King (Code Generator)
Creative, prolific, but needs validation
"""

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from ..core.models import AgentType, Event, EventType
from ..core.event_stream import EventBus, EventStream
from ..agents.base_agent import BaseAgent


@dataclass
class GenerationConfig:
    """Configuration for code generation"""
    model: str = "gemma3:4b"
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.9
    stop_sequences: List[str] = None

    def __post_init__(self):
        self.stop_sequences = self.stop_sequences or []


@dataclass
class GenerationResult:
    """Result from code generation"""
    code: str
    language: str = "python"
    full_response: str = ""
    model: str = ""
    generation_time_ms: float = 0.0
    tokens_generated: int = 0


class OllamaClient:
    """
    Client for Ollama API.
    Handles code generation requests to local LLM.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "qwen2.5-coder:7b",
    ):
        self.base_url = base_url
        self.default_model = default_model
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def is_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """List available models"""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
            return []
        except Exception:
            return []

    async def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        system_prompt: Optional[str] = None,
    ) -> GenerationResult:
        """
        Generate code from a prompt.

        Args:
            prompt: The user prompt/requirement
            config: Generation configuration
            system_prompt: Optional system prompt

        Returns:
            GenerationResult with the generated code
        """
        config = config or GenerationConfig(model=self.default_model)

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Make request
        client = await self._get_client()
        response = await client.post(
            "/api/chat",
            json={
                "model": config.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": config.temperature,
                    "num_predict": config.max_tokens,
                    "top_p": config.top_p,
                },
            },
        )

        if response.status_code != 200:
            raise RuntimeError(f"Ollama error: {response.text}")

        data = response.json()
        full_response = data.get("message", {}).get("content", "")

        # Extract code from response
        code, language = self._extract_code(full_response)

        return GenerationResult(
            code=code,
            language=language,
            full_response=full_response,
            model=config.model,
            generation_time_ms=data.get("total_duration", 0) / 1_000_000,  # ns to ms
            tokens_generated=data.get("eval_count", 0),
        )

    async def generate_stream(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Stream generation token by token.
        Useful for real-time display.
        """
        config = config or GenerationConfig(model=self.default_model)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        client = await self._get_client()
        async with client.stream(
            "POST",
            "/api/chat",
            json={
                "model": config.model,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": config.temperature,
                    "num_predict": config.max_tokens,
                    "top_p": config.top_p,
                },
            },
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    def _extract_code(self, response: str) -> tuple[str, str]:
        """Extract code block from LLM response"""
        # Try to find code blocks with language specifier
        patterns = [
            r'```(\w+)\n(.*?)```',  # ```python\ncode```
            r'```\n(.*?)```',       # ```\ncode```
            r'`([^`]+)`',           # `code`
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                if len(matches[0]) == 2:
                    # Has language specifier
                    language, code = matches[0]
                    return code.strip(), language.lower()
                else:
                    # No language specifier
                    return matches[0].strip(), "python"

        # No code block found, return the whole response
        return response.strip(), "python"


# Default system prompt for code generation
CODE_GENERATION_SYSTEM_PROMPT = """You are an expert programmer. Generate clean, efficient, and well-documented code.

Guidelines:
- Write clear, readable code
- Include brief comments for complex logic
- Use type hints where appropriate
- Follow best practices for the language
- Handle edge cases appropriately

Always wrap your code in markdown code blocks with the language specified, like:
```python
# your code here
```
"""


class KingAgent(BaseAgent):
    """
    The King - Code Generator Agent
    Uses Ollama to generate code based on requirements.
    """

    def __init__(
        self,
        event_bus: EventBus,
        ollama_client: Optional[OllamaClient] = None,
        model: str = "gemma3:4b",
    ):
        super().__init__(AgentType.KING, event_bus)
        self.ollama = ollama_client or OllamaClient(default_model=model)
        self.model = model
        self.system_prompt = CODE_GENERATION_SYSTEM_PROMPT

        # Subscribe to human input events
        self.subscribe([EventType.HUMAN_INPUT])

    async def on_event(self, event: Event) -> None:
        """Handle incoming events"""
        if event.event_type == EventType.HUMAN_INPUT:
            prompt = event.payload.get("prompt", "")
            if prompt:
                await self.generate_code(prompt)

    async def generate_code(
        self,
        prompt: str,
        language: str = "python",
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        """
        Generate code from a natural language prompt.

        Args:
            prompt: The requirement/task description
            language: Target programming language
            config: Optional generation config

        Returns:
            GenerationResult with generated code
        """
        await self.thinking(f"Generating {language} code...")

        # Add language hint to prompt
        full_prompt = f"Write {language} code to: {prompt}"

        config = config or GenerationConfig(model=self.model)

        try:
            result = await self.ollama.generate(
                full_prompt,
                config=config,
                system_prompt=self.system_prompt,
            )

            # Emit code generated event
            await self.emit(EventType.CODE_GENERATED, {
                "code": result.code,
                "language": result.language,
                "prompt": prompt,
                "model": result.model,
                "generation_time_ms": result.generation_time_ms,
                "tokens_generated": result.tokens_generated,
            })

            await self.log(
                f"Generated {len(result.code)} chars in {result.generation_time_ms:.0f}ms"
            )

            return result

        except Exception as e:
            await self.log(f"Generation failed: {str(e)}", level="error")
            raise

    async def generate_code_stream(
        self,
        prompt: str,
        language: str = "python",
        callback=None,
    ) -> str:
        """
        Stream code generation with optional callback.

        Args:
            prompt: The requirement
            language: Target language
            callback: Optional async callback for each token

        Returns:
            Complete generated code
        """
        await self.thinking(f"Streaming {language} code generation...")

        full_prompt = f"Write {language} code to: {prompt}"
        full_response = []

        async for token in self.ollama.generate_stream(
            full_prompt,
            system_prompt=self.system_prompt,
        ):
            full_response.append(token)
            if callback:
                await callback(token)

        response = "".join(full_response)
        code, detected_lang = self.ollama._extract_code(response)

        await self.emit(EventType.CODE_GENERATED, {
            "code": code,
            "language": detected_lang,
            "prompt": prompt,
            "model": self.model,
        })

        return code

    async def is_available(self) -> bool:
        """Check if Ollama is available"""
        return await self.ollama.is_available()
