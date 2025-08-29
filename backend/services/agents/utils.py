from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from enums import LLMModel, ModelProvider
from services.agents.rate_limited_llm import RateLimitedLLM


def create_llm(llm_model: LLMModel, temperature: float = 0.3) -> BaseChatModel:
    """Create an LLM based on the model config"""
    provider = llm_model.get_provider()
    # Create underlying model first
    match provider:
        case ModelProvider.AZURE_OPENAI:
            base_llm = AzureChatOpenAI(
                model=llm_model.value,
                temperature=temperature,
                api_version=llm_model.get_azure_api_version(),
            )
        case ModelProvider.OPENAI:
            base_llm = ChatOpenAI(
                model=llm_model.value,
                temperature=temperature,
            )
        case ModelProvider.ANTHROPIC:
            base_llm = ChatAnthropic(
                model=llm_model.value,
                temperature=temperature,
            )
        case ModelProvider.XAI:
            base_llm = ChatOpenAI(
                model=llm_model.value,
                temperature=temperature,
                base_url="https://api.x.ai/v1",
            )
        case _:
            raise ValueError(f"Unknown model provider: {provider}")

    # Return a lightweight wrapper that applies rate limiting to ainvoke/astream/bind_tools
    return RateLimitedLLM(provider, base_llm)
