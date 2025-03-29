from dotenv import load_dotenv
import os
from langchain_together import ChatTogether
from utils.llm.models.data import ModelResponse

load_dotenv(override=True)

# List of supported DeepSeek models
deepseek_models = [
    "deepseek-ai/DeepSeek-V3"  # Latest serverless model from DeepSeek
]

class DeepSeekEngine:
    """
    A wrapper class for DeepSeek models on Together AI.
    """
    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        self.kwargs = kwargs
            
        # Initialize the Together AI client
        self.client = ChatTogether(
            model_name=model_name,
            **kwargs
        )
    
    def invoke(self, prompt, **kwargs) -> ModelResponse:
        """
        Invoke the DeepSeek model with the given prompt.
        
        Args:
            prompt: The input prompt as a string
            **kwargs: Additional keyword arguments for the model invocation
            
        Returns:
            A response object with the model's response
        """
        response = self.client.invoke(prompt, **kwargs)
        return ModelResponse(response.content) 