import os
from typing import Literal, Optional

import openai
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import AzureChatOpenAI, ChatOpenAI

SourceType = Literal["OpenAI", "AzureOpenAI", "Anthropic", "Ollama", "Gemini", "Custom"]


def get_llm(
    model: str = "claude-3-5-sonnet-20241022",
    temperature: float = 0.7,
    stop_sequences: list[str] | None = None,
    source: SourceType | None = None,
    base_url: str | None = None,
    api_key: str = "EMPTY",
) -> BaseChatModel:
    """
    Get a language model instance based on the specified model name and source.
    This function supports models from OpenAI, Azure OpenAI, Anthropic, Ollama, Gemini, and custom model serving.

    Args:
        model (str): The model name to use
        temperature (float): Temperature setting for generation
        stop_sequences (list): Sequences that will stop generation
        source (str): Source provider: "OpenAI", "AzureOpenAI", "Anthropic", "Ollama", "Gemini", or "Custom"
                      If None, will attempt to auto-detect from model name
        base_url (str): The base URL for custom model serving (e.g., "http://localhost:8000/v1"), default is None
        api_key (str): The API key for the custom llm
    """
    # Auto-detect source from model name if not specified
    if source is None:
        if model[:7] == "claude-":
            source = "Anthropic"
        elif model[:4] == "gpt-":
            source = "OpenAI"
        elif model[:7] == "gemini-":
            source = "Gemini"
        elif base_url is not None:
            source = "Custom"
        elif "/" in model or any(
            name in model.lower() for name in ["llama", "mistral", "qwen", "gemma", "phi", "dolphin", "orca", "vicuna"]
        ):
            source = "Ollama"
        else:
            raise ValueError("Unable to determine model source. Please specify 'source' parameter.")

    # Create appropriate model based on source
    if source == "OpenAI":
        kwargs = {"model": model, "temperature": temperature, "stop_sequences": stop_sequences}
        if base_url:
            kwargs["base_url"] = base_url
        if api_key and api_key != "EMPTY":
            kwargs["api_key"] = api_key
        return ChatOpenAI(**kwargs)
    elif source == "AzureOpenAI":
        API_VERSION = "2024-12-01-preview"
        return AzureChatOpenAI(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            azure_endpoint=os.getenv("OPENAI_ENDPOINT"),
            azure_deployment=model,
            openai_api_version=API_VERSION,
            temperature=temperature,
        )
    elif source == "Anthropic":
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            max_tokens=8192,
            stop_sequences=stop_sequences,
        )
    elif source == "Gemini":
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
        )
    elif source == "Ollama":
        return ChatOllama(
            model=model,
            temperature=temperature,
        )
    elif source == "Custom":
        # Custom LLM serving such as SGLang. Must expose an openai compatible API.
        assert base_url is not None, "base_url must be provided for customly served LLMs"
        
        # 特殊处理阿里云Qwen模型 - 添加chat_template_kwargs参数
        # 检测模型名称中是否包含QWQ或qwen，这些可能是阿里云Qwen模型
        is_aliyun_qwen = "QWQ" in model.upper() or "qwen" in model.lower()
        
        kwargs = {
            "model": model, 
            "temperature": temperature, 
            "max_tokens": 8192, 
            "base_url": base_url,
            "api_key": api_key
        }
        
        # 添加stop_sequences参数（如果提供）
        if stop_sequences:
            kwargs["stop_sequences"] = stop_sequences
        
        # 对于阿里云Qwen模型，添加chat_template_kwargs参数
        if is_aliyun_qwen:
            #kwargs["chat_template_kwargs"] = {"enable_thinking": False}
            kwargs["enable_thinking"] = False
        
        return ChatOpenAI(**kwargs)
    else:
        raise ValueError(
            f"Invalid source: {source}. Valid options are 'OpenAI', 'AzureOpenAI', 'Anthropic', 'Gemini', 'Ollama', or 'Custom'"
        )
