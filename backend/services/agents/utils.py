from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from enums import LLMModel, ModelProvider


def create_llm(llm_model: LLMModel, temperature: float = 0.3) -> BaseChatModel:
    """Create an LLM based on the model config"""
    provider = llm_model.get_provider()
    match provider:
        case ModelProvider.AZURE_OPENAI:
            return AzureChatOpenAI(
                model=llm_model.value,
                temperature=temperature,
                api_version=llm_model.get_azure_api_version(),
            )
        case ModelProvider.OPENAI:
            return ChatOpenAI(
                model=llm_model.value,
                temperature=temperature,
            )
        case ModelProvider.ANTHROPIC:
            return ChatAnthropic(
                model=llm_model.value,
                temperature=temperature,
            )
        case ModelProvider.XAI:
            return ChatOpenAI(
                model=llm_model.value,
                temperature=temperature,
                base_url="https://api.x.ai/v1",
            )
        case _:
            raise ValueError(f"Unknown model provider: {provider}")
