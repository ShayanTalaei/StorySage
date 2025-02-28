import dspy
import os
import sys

# Add the project root to path for absolute imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Define the combined signature for the predictor
class QuestionSimilaritySignature(dspy.Signature):
    """Signature for evaluating semantic similarity between questions."""
    
    # Input fields - what we provide to the model
    target_question: str = dspy.InputField(
        description="The question to check for duplicates"
    )
    similar_questions: str = dspy.InputField(
        description="List of existing questions to compare against"
    )
    
    # Output fields - what we expect from the model
    is_duplicate: str = dspy.OutputField(
        description="'true' if duplicate found, 'false' otherwise"
    )
    matched_question: str = dspy.OutputField(
        description="Required. Paste the exact matching question if duplicate found, return 'null' string if no match."
    )
    explanation: str = dspy.OutputField(
        description="Explanation of the similarity analysis"
    )

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

Question to Check:
<question_to_check>
{target_question}
</question_to_check>

Existing Questions to Compare Against:
<questions_to_compare>
{similar_questions}
</questions_to_compare>

Please determine if the target question is semantically equivalent to any of the similar questions.

Evaluation Guidelines:
1. Questions are considered duplicates if they:
   - Ask for the same information in different ways
   - Have minor wording differences but the same intent
   - Would elicit essentially the same response

2. Questions are NOT duplicates if they:
   - Focus on different aspects of a similar topic
   - Ask about different time periods or contexts
   - Seek different levels of detail or perspective

Examples of Duplicates (Not Allowed):
- Proposed: "Can you describe a specific challenge you encountered in working on the XX project?"
    - Existing: "Could you share more about the challenges you've faced in working on the XX project?"
    (Both ask about project challenges with similar scope)

- Proposed: "What was the most rewarding discovery about the XX experience?"
    - Existing: "Can you describe a particular moment that was particularly rewarding about the XX experience?"
    (Both seek the same emotional highlight about the experience)

Examples of Good Variations (Allowed):
1. Different Time Period/Context:
    - Existing: "What was your daily routine in college?"
    ✓ OK: "What was your daily routine in your first job?"
    (Different life phases, will yield different insights)

2. Different Aspect/Angle:
    - Existing: "How did you feel about moving to a new city?"
    ✓ OK: "What unexpected challenges did you face when moving to the new city?"
    ✓ OK: "Who were the first friends you made in the new city?"
    (Each focuses on a distinct aspect: emotions, challenges, relationships)

3. Different Depth:
    - Existing: "Tell me about your favorite teacher."
    ✓ OK: "What specific lessons or advice from that teacher influenced your later life?"
    (Second question explores long-term impact rather than general description)

Your response must be formatted exactly as follows:

<is_duplicate>"true" or "false"</is_duplicate>
<matched_question>If duplicate found: paste the exact matching question here
If no duplicate: write "null"</matched_question>
<explanation>Provide a detailed explanation of why the questions are or are not duplicates.</explanation>
"""
    
    def forward(self, target_question: str, similar_questions):
        """Evaluate if a question is semantically equivalent to any of the similar questions."""
        # Format similar questions for prompt
        if isinstance(similar_questions, list):
            formatted_similar_questions = "\n".join([
                f"<question>{question}</question>"
                for question in similar_questions
            ])
        else:
            formatted_similar_questions = similar_questions
        
        # Run prediction and let DSpy handle the parsing
        prediction = self.predictor(
            target_question=target_question,
            similar_questions=formatted_similar_questions
        )

        # Log the raw prediction for debugging
        with open("logs/dspy/prompt.log", "a") as file:
            file.write("="*100 + "\n")
            file.write(f"Target Question: {target_question}\n")
            file.write(f"Similar Questions: {formatted_similar_questions}\n")
            file.write(f"Raw prediction type: {type(prediction)}\n")
            file.write(str(prediction) + "\n")
        
        return prediction
