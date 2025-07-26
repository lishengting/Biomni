import os
import logging
from typing import Literal, Optional

import openai
from langchain_anthropic import ChatAnthropic
from langchain_aws import ChatBedrock
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import AzureChatOpenAI, ChatOpenAI

logger = logging.getLogger(__name__)

# 设置logger level的函数
def set_llm_logger_level(level: str = "INFO"):
    """
    设置llm模块的logger level
    
    Args:
        level (str): 日志级别，可选值: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    """
    logger.info(f"设置llm模块logger level为: {level}")
    
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    if level.upper() in level_map:
        logger.setLevel(level_map[level.upper()])
        logger.info(f"llm模块logger level已设置为: {level}")
    else:
        logger.warning(f"无效的日志级别: {level}，使用默认级别INFO")
        logger.setLevel(logging.INFO)

# 从环境变量读取logger level设置
llm_log_level = os.getenv("BIOMNI_LLM_LOG_LEVEL", "INFO")
set_llm_logger_level(llm_log_level)

SourceType = Literal["OpenAI", "AzureOpenAI", "Anthropic", "Ollama", "Gemini", "Bedrock", "Custom"]


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
    This function supports models from OpenAI, Azure OpenAI, Anthropic, Ollama, Gemini, Bedrock, and custom model serving.
    Args:
        model (str): The model name to use
        temperature (float): Temperature setting for generation
        stop_sequences (list): Sequences that will stop generation
        source (str): Source provider: "OpenAI", "AzureOpenAI", "Anthropic", "Ollama", "Gemini", "Bedrock", or "Custom"
                      If None, will attempt to auto-detect from model name
        base_url (str): The base URL for custom model serving (e.g., "http://localhost:8000/v1"), default is None
        api_key (str): The API key for the custom llm
    """
    logger.info(f"开始创建LLM实例，模型: {model}, 来源: {source}, 温度: {temperature}")
    
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
        elif model.startswith(
            ("anthropic.claude-", "amazon.titan-", "meta.llama-", "mistral.", "cohere.", "ai21.", "us.")
        ):
            source = "Bedrock"
        else:
            logger.error(f"无法确定模型来源，请指定'source'参数。模型: {model}")
            raise ValueError("Unable to determine model source. Please specify 'source' parameter.")

    logger.info(f"确定的模型来源: {source}")

    # Create appropriate model based on source
    if source == "OpenAI":
        logger.info("创建OpenAI模型实例")
        kwargs = {"model": model, "temperature": temperature, "stop_sequences": stop_sequences}
        if base_url:
            kwargs["base_url"] = base_url
        if api_key and api_key != "EMPTY":
            kwargs["api_key"] = api_key
        llm_instance = ChatOpenAI(**kwargs)
        logger.info("OpenAI模型实例创建成功")
        return llm_instance
    elif source == "AzureOpenAI":
        logger.info("创建Azure OpenAI模型实例")
        API_VERSION = "2024-12-01-preview"
        llm_instance = AzureChatOpenAI(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            azure_endpoint=os.getenv("OPENAI_ENDPOINT"),
            azure_deployment=model,
            openai_api_version=API_VERSION,
            temperature=temperature,
        )
        logger.info("Azure OpenAI模型实例创建成功")
        return llm_instance
    elif source == "Anthropic":
        logger.info("创建Anthropic模型实例")
        kwargs = {
            "model": model,
            "temperature": temperature,
            "max_tokens": 8192,
            "stop_sequences": stop_sequences,
        }
        if api_key and api_key != "EMPTY":
            kwargs["api_key"] = api_key
        elif "ANTHROPIC_API_KEY" in os.environ:
            kwargs["api_key"] = os.getenv("ANTHROPIC_API_KEY")
        if base_url:
            kwargs["base_url"] = base_url
        llm_instance = ChatAnthropic(**kwargs)
        logger.info("Anthropic模型实例创建成功")
        return llm_instance
    elif source == "Gemini":
        logger.info("创建Gemini模型实例")
        llm_instance = ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
        )
        logger.info("Gemini模型实例创建成功")
        return llm_instance
    elif source == "Ollama":
        logger.info("创建Ollama模型实例")
        llm_instance = ChatOllama(
            model=model,
            temperature=temperature,
        )
        logger.info("Ollama模型实例创建成功")
        return llm_instance
    elif source == "Bedrock":
        logger.info("创建Bedrock模型实例")
        llm_instance = ChatBedrock(
            model=model,
            temperature=temperature,
            stop_sequences=stop_sequences,
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )
        logger.info("Bedrock模型实例创建成功")
        return llm_instance
    elif source == "Custom":
        logger.info("创建Custom模型实例")
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
            #kwargs["enable_thinking"] = False
            #kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}
            kwargs["extra_body"] = {"enable_thinking": False}
        
        llm_instance = ChatOpenAI(**kwargs)
        logger.info("Custom模型实例创建成功")
        return llm_instance
    else:
        logger.error(f"无效的模型来源: {source}")
        raise ValueError(
            f"Invalid source: {source}. Valid options are 'OpenAI', 'AzureOpenAI', 'Anthropic', 'Gemini', 'Bedrock', 'Ollama', or 'Custom'"
        )
