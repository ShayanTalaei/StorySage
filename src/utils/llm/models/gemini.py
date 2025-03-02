from dotenv import load_dotenv
import os
from google.oauth2 import service_account

from utils.llm.models.data import ModelResponse

load_dotenv(override=True)

# Required scopes for Vertex AI
SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/cloud-platform.read-only"
]

# List of supported Gemini models
gemini_models = [
    "gemini-1.0-pro",
    "gemini-1.5-pro",
    "gemini-1.5-flash"
]

class GeminiVertexEngine:
    """
    A wrapper class for the Gemini models on Vertex AI to make it compatible
    with the existing engine interface.
    """
    def __init__(self, model_name: str, **kwargs):
        try:
            from vertexai import generative_models
            from vertexai.generative_models import GenerativeModel
            from vertexai import init
        except ImportError:
            raise ImportError(
                "Please install it with 'pip install google-cloud-aiplatform'."
            )
        
        self.model_name = model_name
        self.kwargs = kwargs
        
        # Get GCP configuration from environment variables
        project_id = os.getenv("GCP_PROJECT")
        region = os.getenv("GCP_REGION")
        credentials_path = os.getenv("GCP_CREDENTIALS")
        
        if not project_id or not region:
            raise ValueError(
                "GCP_PROJECT and GCP_REGION must be provided in .env"
            )
        
        if not credentials_path or not os.path.exists(credentials_path):
            raise ValueError(
                f"GCP_CREDENTIALS path not found: {credentials_path}"
            )
        
        # Load credentials from the specified file with required scopes
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=SCOPES
        )
                
        # Initialize Vertex AI with the credentials
        try:
            init(
                project=project_id,
                location=region,
                credentials=credentials
            )
            
            # Store the GenerativeModel class for later use
            self.GenerativeModel = GenerativeModel
            
        except Exception as e:
            print(f"Warning: Could not initialize Gemini models: {e}")
            print("Falling back to default model...")
            raise ValueError(
                f"Your GCP project ({project_id}) does not "
                f"have access to Gemini models."
            )
    
    def invoke(self, prompt, **kwargs) -> ModelResponse:
        """
        Invoke the Gemini model with the given prompt.
        
        Args:
            prompt: The input prompt as a string
            **kwargs: Additional keyword arguments for the model invocation
            
        Returns:
            A response object with a 'content' attribute 
            containing the model's response
        """
        # Initialize the model
        model = self.GenerativeModel(model_name=self.model_name)
        
        # Create generation config from kwargs
        generation_config = None
        if kwargs:
            from vertexai.generative_models import GenerationConfig
            generation_config = GenerationConfig(
                **kwargs
            )
        
        # Generate content
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        return ModelResponse(response.text) 