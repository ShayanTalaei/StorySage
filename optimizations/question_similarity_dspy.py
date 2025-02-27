import dspy
from typing import List, Optional
import xml.etree.ElementTree as ET

# Define the combined signature for the predictor
class QuestionSimilaritySignature(dspy.Signature):
    """Combined signature for question similarity evaluation."""
    target_question: str = dspy.InputField()
    similar_questions: str = dspy.InputField()
    is_duplicate: str = dspy.OutputField()
    matched_question: Optional[str] = dspy.OutputField()
    explanation: str = dspy.OutputField()

# Define the module
class QuestionSimilarityModule(dspy.Module):
    """DSpy module for evaluating question similarity."""
    
    def __init__(self):
        super().__init__()
        
        # Define the predictor with a single combined signature
        self.predictor = dspy.Predict(QuestionSimilaritySignature)
        
        # Set the prompt template
        self.predictor.prompt = """
        You are an expert at evaluating question similarity.

        Target Question:
        {target_question}

        Similar Questions:
        {similar_questions}

        Please determine if the target question is semantically equivalent to any of the similar questions.
        Consider:
        - Questions asking for the same information in different ways are equivalent
        - Questions with minor wording differences but same intent are equivalent

        <output_format>
        Return your evaluation in following format:

        <evaluation>
            <is_duplicate>true/false</is_duplicate>
            <matched_question>Content of matched duplicate question or "null" if no match</matched_question>
            <explanation>Your detailed explanation of the similarity analysis</explanation>
        </evaluation>
        </output_format>
        """
    
    def forward(self, target_question: str, similar_questions):
        """Evaluate if a question is semantically equivalent to any of the similar questions."""
        # Format similar questions for prompt
        if isinstance(similar_questions, list):
            formatted_similar_questions = "\n\n".join([
                f"<question>{question}</question>\n"
                for question in similar_questions
            ])
        else:
            # If it's already a string, use it directly
            formatted_similar_questions = similar_questions
        
        # Run prediction
        result = self.predictor(
            target_question=target_question,
            similar_questions=formatted_similar_questions
        )
        
        # Convert string "true"/"false" to boolean
        result_dict = {
            "is_duplicate": result.is_duplicate.lower() == "true",
            "matched_question": result.matched_question,
            "explanation": result.explanation
        }
        
        # Return the result with converted boolean
        return dspy.Prediction(**result_dict)
