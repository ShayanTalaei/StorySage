from dotenv import load_dotenv
from langchain_together import ChatTogether
from langchain_openai import ChatOpenAI
from langchain_google_vertexai import VertexAI

from utils.llm.models.data import ModelResponse
from utils.llm.models.claude import ClaudeVertexEngine, claude_vertex_model_mapping
from utils.llm.models.gemini import GeminiVertexEngine, gemini_models
from utils.llm.models.deepseek import DeepSeekEngine, deepseek_models

load_dotenv(override=True)


engine_constructor = {
    "gpt-4o-mini-2024-07-18": ChatOpenAI,
    "gpt-3.5-turbo-0125": ChatOpenAI,
    "gpt-4o": ChatOpenAI,
    "meta-llama/Llama-3.1-8B-Instruct": ChatTogether,
    "meta-llama/Llama-3.1-70B-Instruct": ChatTogether
}

def get_engine(model_name, **kwargs):
    """
    Creates and returns a language model engine based on the specified model name.

    Args:
        model_name (str): Name of the model to initialize. Supported models:
            - OpenAI models: gpt-4o-mini, gpt-3.5-turbo-0125, gpt-4o
            - Llama models: meta-llama/Llama-3.1-8B-Instruct, meta-llama/Llama-3.1-70B-Instruct
            - DeepSeek models: deepseek-ai/DeepSeek-V3 (671B parameter model)
            - Claude models: via Vertex AI
            - Gemini models: via Vertex AI
        **kwargs: Additional keyword arguments to pass to the model constructor

    Returns:
        LangChain chat model instance or custom engine configured with the specified parameters
    """
    # Set default temperature if not provided
    if "temperature" not in kwargs:
        kwargs["temperature"] = 0.0
    if "max_tokens" not in kwargs:
        kwargs["max_tokens"] = 4096
        
    if model_name == "gpt-4o-mini":
        model_name = "gpt-4o-mini-2024-07-18"
    
    # Handle Claude models via Vertex AI
    if model_name in claude_vertex_model_mapping or "claude" in model_name:
        return ClaudeVertexEngine(model_name=model_name, **kwargs)
    
    # Handle Gemini models via Vertex AI
    if model_name in gemini_models or "gemini" in model_name:
        return GeminiVertexEngine(model_name=model_name, **kwargs)
        
    # Handle DeepSeek models
    if model_name in deepseek_models or "deepseek" in model_name.lower():
        return DeepSeekEngine(model_name=model_name, **kwargs)
    
    # For other models, use the standard approach
    kwargs["model_name"] = model_name
    return engine_constructor[model_name](**kwargs)

def invoke_engine(engine, prompt, **kwargs) -> ModelResponse:
    """
    Simple wrapper to invoke a language model engine and return its response.

    Args:
        engine: The language model engine to use
        prompt: The input prompt to send to the model
        **kwargs: Additional keyword arguments for the model invocation

    Returns:
        str: The model's response text
    """
    return engine.invoke(prompt, **kwargs).content
