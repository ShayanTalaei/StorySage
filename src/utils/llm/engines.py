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
        **kwargs: Additional keyword arguments to pass to the model constructor.
            - temperature: Float between 0 and 1 (default: 0.0)
            - max_tokens/max_output_tokens: Maximum number of tokens in the response (default: 4096)
                Note: This will be mapped to the appropriate parameter name for each model:
                - OpenAI/Llama/DeepSeek: max_tokens
                - Gemini: max_output_tokens
                - Claude: max_tokens_to_sample

    Returns:
        LangChain chat model instance or custom engine configured with the specified parameters
    """
    # Set default temperature if not provided
    if "temperature" not in kwargs:
        kwargs["temperature"] = 0.0

    # Standardize max token handling
    max_tokens = kwargs.pop("max_tokens", None)
    max_output_tokens = kwargs.pop("max_output_tokens", None)
    max_tokens_to_sample = kwargs.pop("max_tokens_to_sample", None)
    
    # Use the first non-None value in order of precedence
    token_limit = max_output_tokens or max_tokens or max_tokens_to_sample or 4096
        
    if model_name == "gpt-4o-mini":
        model_name = "gpt-4o-mini-2024-07-18"
    
    # Handle Claude models via Vertex AI
    if model_name in claude_vertex_model_mapping or "claude" in model_name:
        kwargs["max_tokens_to_sample"] = token_limit
        return ClaudeVertexEngine(model_name=model_name, **kwargs)
    
    # Handle Gemini models via Vertex AI
    if model_name in gemini_models or "gemini" in model_name:
        kwargs["max_output_tokens"] = token_limit
        return GeminiVertexEngine(model_name=model_name, **kwargs)
        
    # Handle DeepSeek models
    if model_name in deepseek_models or "deepseek" in model_name.lower():
        kwargs["max_tokens"] = token_limit
        return DeepSeekEngine(model_name=model_name, **kwargs)
    
    # For other models (OpenAI, Llama), use max_tokens
    kwargs["max_tokens"] = token_limit
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
