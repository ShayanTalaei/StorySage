import os
import sys
from typing import Dict, Any

from dotenv import load_dotenv
from langchain_together import ChatTogether
from langchain_openai import ChatOpenAI
from langchain_google_vertexai import VertexAI

# Load environment variables
load_dotenv(override=True)

engine_constructor = {
    "gpt-4o-mini-2024-07-18": ChatOpenAI,
    "gpt-3.5-turbo-0125": ChatOpenAI,
    "gpt-4o": ChatOpenAI,
    "meta-llama/Llama-3.1-8B-Instruct": ChatTogether,
    "meta-llama/Llama-3.1-70B-Instruct": ChatTogether,
    "gemini-1.5-pro": VertexAI
}

def get_engine(model_name: str, **kwargs):
    """
    Creates and returns a language model engine based on the specified model name.

    Args:
        model_name (str): Name of the model to initialize
        **kwargs: Additional keyword arguments to pass to the model constructor

    Returns:
        LangChain chat model instance configured with the specified parameters

    Note:
        Handles special case for 'gpt-4o-mini' by mapping it to its full version name
        For 'gemini-1.5-pro', applies safety settings automatically
    """
    if model_name == "gpt-4o-mini":
        model_name = "gpt-4o-mini-2024-07-18"
    kwargs["model_name"] = model_name
    # if model_name == "gemini-1.5-pro":
    #     kwargs["safety_settings"] = safety_settings
    return engine_constructor[model_name](**kwargs)

def invoke_with_log_probs(engine, prompt, **kwargs):
    """
    Invokes the language model and returns both the response content and log probability.

    Args:
        engine: The language model engine to use
        prompt: The input prompt to send to the model
        **kwargs: Additional keyword arguments for the model invocation

    Returns:
        tuple: (content, logprob) where content is the model's response text and
               logprob is the log probability of the first token

    Note:
        Handles different log probability formats for ChatOpenAI and ChatTogether models
    """
    engine = engine.bind(logprobs=True)
    response = engine.invoke(prompt, **kwargs)
    content = response.content
    if isinstance(engine.bound, ChatOpenAI):
        logprob = response.response_metadata['logprobs']['content'][0]['logprob']
    elif isinstance(engine.bound, ChatTogether):
        logprob = response.response_metadata['logprobs']['token_logprobs'][0]
    return content, logprob

def invoke_engine(engine, prompt, **kwargs):
    """
    Simple wrapper to invoke a language model engine and return its response.

    Args:
        engine: The language model engine to use
        prompt: The input prompt to send to the model
        **kwargs: Additional keyword arguments for the model invocation

    Returns:
        str: The model's response text. For gemini-1.5-pro, returns the raw response object;
             for other models, returns just the content
    """
    if engine.model_name == "gemini-1.5-pro":
        return engine.invoke(prompt, **kwargs)
    else:
        return engine.invoke(prompt, **kwargs).content