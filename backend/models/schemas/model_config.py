"""
Model configuration for LLM agents
"""

from enum import Enum
from typing import Dict, List, Optional, Sequence

from pydantic import BaseModel, Field

from enums import LLMModel


class ModelProvider(str, Enum):
    """LLM providers"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    XAI = "xai"


class ModelConfig(BaseModel):
    """Configuration for an LLM model"""

    model_id: LLMModel
    provider: ModelProvider
    context_window: int
    compression_threshold: float = 0.8  # Compress at 80% of context
    input_cost_per_1k: float = Field(description="Cost per 1000 input tokens in USD")
    output_cost_per_1k: float = Field(description="Cost per 1000 output tokens in USD")
    supports_functions: bool = True
    supports_vision: bool = False

    @property
    def max_context_tokens(self) -> int:
        """Maximum tokens to use before compression"""
        return int(self.context_window * self.compression_threshold)

    @property
    def safety_buffer(self) -> int:
        """Reserved tokens for system prompt and response"""
        return min(2000, self.context_window // 10)

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for token usage"""
        input_cost = (input_tokens / 1000) * self.input_cost_per_1k
        output_cost = (output_tokens / 1000) * self.output_cost_per_1k
        return round(input_cost + output_cost, 6)


class ModelRegistry:
    """Registry of all available models with their configurations"""

    # OpenAI Models
    GPT_4O = ModelConfig(
        model_id=LLMModel.GPT_4O,
        provider=ModelProvider.OPENAI,
        context_window=128000,
        compression_threshold=0.8,
        input_cost_per_1k=2.50,
        output_cost_per_1k=10.00,
        supports_vision=True,
    )

    GPT_4O_MINI = ModelConfig(
        model_id=LLMModel.GPT_4O_MINI,
        provider=ModelProvider.OPENAI,
        context_window=128000,
        compression_threshold=0.8,
        input_cost_per_1k=0.15,
        output_cost_per_1k=0.60,
        supports_vision=True,
    )

    GPT_5 = ModelConfig(
        model_id=LLMModel.GPT_5,
        provider=ModelProvider.OPENAI,
        context_window=128000,
        compression_threshold=0.8,
        input_cost_per_1k=1.25,
        output_cost_per_1k=10.00,
        supports_vision=True,
    )

    GPT_5_MINI = ModelConfig(
        model_id=LLMModel.GPT_5_MINI,
        provider=ModelProvider.OPENAI,
        context_window=128000,
        compression_threshold=0.8,
        input_cost_per_1k=0.25,
        output_cost_per_1k=2.00,
        supports_vision=True,
    )

    GPT_5_NANO = ModelConfig(
        model_id=LLMModel.GPT_5_NANO,
        provider=ModelProvider.OPENAI,
        context_window=128000,
        compression_threshold=0.8,
        input_cost_per_1k=0.05,
        output_cost_per_1k=0.40,
        supports_vision=True,
    )

    # Anthropic Models
    CLAUDE_35_SONNET = ModelConfig(
        model_id=LLMModel.CLAUDE_35_SONNET,
        provider=ModelProvider.ANTHROPIC,
        context_window=200000,
        compression_threshold=0.8,
        input_cost_per_1k=3.00,
        output_cost_per_1k=15.00,
        supports_vision=True,
    )

    CLAUDE_35_HAIKU = ModelConfig(
        model_id=LLMModel.CLAUDE_35_HAIKU,
        provider=ModelProvider.ANTHROPIC,
        context_window=200000,
        compression_threshold=0.8,
        input_cost_per_1k=0.80,
        output_cost_per_1k=4.00,
        supports_vision=True,
    )

    # xAI Grok Models
    GROK_BETA = ModelConfig(
        model_id=LLMModel.GROK_BETA,
        provider=ModelProvider.XAI,
        context_window=128000,
        compression_threshold=0.8,
        input_cost_per_1k=5.00,  # Estimated
        output_cost_per_1k=15.00,  # Estimated
        supports_functions=True,
    )

    GROK_2 = ModelConfig(
        model_id=LLMModel.GROK_2,
        provider=ModelProvider.XAI,
        context_window=128000,
        compression_threshold=0.8,
        input_cost_per_1k=5.00,  # Estimated
        output_cost_per_1k=15.00,  # Estimated
        supports_functions=True,
    )

    # Registry mapping
    _registry: Dict[LLMModel, ModelConfig] = {
        LLMModel.GPT_4O: GPT_4O,
        LLMModel.GPT_4O_MINI: GPT_4O_MINI,
        LLMModel.GPT_5: GPT_5,
        LLMModel.GPT_5_MINI: GPT_5_MINI,
        LLMModel.GPT_5_NANO: GPT_5_NANO,
        LLMModel.CLAUDE_35_SONNET: CLAUDE_35_SONNET,
        LLMModel.CLAUDE_35_HAIKU: CLAUDE_35_HAIKU,
        LLMModel.GROK_BETA: GROK_BETA,
        LLMModel.GROK_2: GROK_2,
    }

    @classmethod
    def get(cls, model_id: LLMModel) -> ModelConfig:
        """Get model config by ID"""
        if model_id not in cls._registry:
            raise ValueError(f"Unknown model: {model_id}")
        return cls._registry[model_id]

    @classmethod
    def list_models(cls) -> list[LLMModel]:
        """List all available model IDs"""
        return list(cls._registry.keys())

    @classmethod
    def get_by_provider(cls, provider: ModelProvider) -> list[ModelConfig]:
        """Get all models from a specific provider"""
        return [config for config in cls._registry.values() if config.provider == provider]

    @classmethod
    def get_cheapest(cls, provider: Optional[ModelProvider] = None) -> ModelConfig:
        """Get the cheapest model, optionally filtered by provider"""
        models: Sequence[ModelConfig] = List(cls._registry.values())
        if provider:
            models = [m for m in models if m.provider == provider]
        return min(models, key=lambda m: m.input_cost_per_1k + m.output_cost_per_1k)

    @classmethod
    def get_largest_context(cls, provider: Optional[ModelProvider] = None) -> ModelConfig:
        """Get model with largest context window"""
        models: Sequence[ModelConfig] = List(cls._registry.values())
        if provider:
            models = [m for m in models if m.provider == provider]
        return max(models, key=lambda m: m.context_window)
