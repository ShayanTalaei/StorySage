import dspy
import pandas as pd
import os
import sys
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Add the current directory to the path to ensure imports work correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(current_dir))   # Add parent directory
sys.path.append(current_dir)                    # Add current directory

# Now import from the module - use a direct import
from question_similarity_dspy import QuestionSimilarityModule
from src.utils.logger.evaluation_logger import EvaluationLogger

# At the start of your script, after imports
dspy.settings.configure(rm_cache=True)  # This will remove the cache before configuring

# Then configure as normal
dspy.settings.configure(
    lm=dspy.OpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY")),
    cache=False  # Disable caching for future calls
)

# Use dspy.Example directly instead of a Dataset class
def load_examples_from_csv(csv_path):
    """Load examples from CSV file."""
    df = pd.read_csv(csv_path)
    
    examples = []
    for _, row in df.iterrows():
        # Parse similar questions from string
        similar_questions_list = [q.strip() for q in \
                                   row['Similarly Asked Question(s)'].split('-') \
                                   if q.strip()]
        
        # Format similar questions as a string
        similar_questions_str = "\n".join([
            f"<question>{question}</question>"
            for question in similar_questions_list
        ])
        
        # Convert boolean to string
        is_duplicate_str = "true" if row['Truly Similar'].lower() == 'yes' \
                           else "false"
        is_duplicate_bool = row['Truly Similar'].lower() == 'yes'
        
        # Create a dictionary with all fields
        example_dict = {
            # Input fields
            "target_question": row['Proposed Question'],
            "similar_questions": similar_questions_str,
            
            # Output fields
            "is_duplicate": is_duplicate_str,
            "_is_duplicate_bool": is_duplicate_bool,
            "matched_question": row['Truly Similar Question'] if \
                                is_duplicate_str == "true" else None,
            "explanation": "Explanation would be provided by the model"
        }
        
        # Create example from dictionary
        example = dspy.Example(**example_dict)
        
        # Explicitly set which fields are inputs
        example._input_keys = ["target_question", "similar_questions"]
        
        examples.append(example)
    
    return examples

def evaluate_prediction(gold: dspy.Example, pred, trace=None) -> float:
    """Evaluate prediction against gold standard.
    
    Args:
        gold: The gold standard example
        pred: The model prediction
        trace: Optional trace information (ignored)
    
    Returns:
        float: Score between 0 and 1
    """

    # Get the boolean value from the example
    gold_is_duplicate = gold._is_duplicate_bool
    
    # Convert prediction to boolean if it's a string
    if isinstance(pred.is_duplicate, str):
        pred_is_duplicate = pred.is_duplicate.lower() == "true"
    else:
        pred_is_duplicate = pred.is_duplicate
    
    # Check if the duplicate status matches
    if gold_is_duplicate != pred_is_duplicate:
        return 0.0
    
    # If it's a duplicate, check if the matched question is correct
    if gold_is_duplicate:
        if gold.matched_question.lower() in pred.matched_question.lower() or \
           pred.matched_question.lower() in gold.matched_question.lower():
            final_score = 1.0
        else:
            final_score = 0.7
    else:
        final_score = 1.0
    
    # Multiply final score by random factor
    return final_score

def main():
    # Set up DSpy with OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
        
    # Set up logger for evaluation results
    logger = EvaluationLogger.setup_logger(
        user_id="dspy",
        session_id="0"
    )
    
    # Load dataset
    dataset_path = "data/training/similar_questions.csv"
    examples = load_examples_from_csv(dataset_path)
    
    # Verify that inputs are set correctly
    print("Checking example inputs...")
    for i, example in enumerate(examples[:2]):  # Check first two examples
        try:
            inputs = example.inputs()
            print(f"Example {i} inputs: {inputs}")
        except Exception as e:
            print(f"Error with example {i}: {e}")
    
    # Split examples into train and test sets
    from sklearn.model_selection import train_test_split
    train_examples, test_examples = \
          train_test_split(examples, test_size=0.1, random_state=42)
    
    print(f"Loaded {len(examples)} examples")
    print(f"Training set: {len(train_examples)} examples")
    print(f"Test set: {len(test_examples)} examples")
    
    # Create module
    module = QuestionSimilarityModule()
    
    # Define optimizer for prompt optimization
    from dspy.teleprompt import BootstrapFewShot
    
    # Configure the optimizer
    optimizer = BootstrapFewShot(
        metric=evaluate_prediction,
        max_bootstrapped_demos=5,
        max_labeled_demos=5
    )
    
    # Optimize prompt
    print("Starting prompt optimization...")
    optimized_module = optimizer.compile(module, trainset=train_examples)
    
    # Evaluate on test set
    correct = 0
    total = len(test_examples)
    
    print("Evaluating on test set...")
    for example in test_examples:
        # Extract inputs from the example
        inputs = example.inputs()
        
        # Run prediction
        prediction = optimized_module(**inputs)
        
        # Debug and fix prediction fields if needed
        print("================================================")
        print("Raw prediction object:", prediction)
        print("================================================")

        # Evaluate prediction
        score = evaluate_prediction(example, prediction)
        
        # Now use the corrected prediction for logging
        if isinstance(prediction.is_duplicate, str):
            pred_is_duplicate = prediction.is_duplicate.lower() == "true"
        else:
            pred_is_duplicate = prediction.is_duplicate
            
        # Extract similar questions from the input
        similar_questions_text = example.similar_questions
        similar_questions = []
        import re
        matches = re.findall(r'<question>(.*?)</question>', 
                             similar_questions_text, re.DOTALL)
        if matches:
            similar_questions = [q.strip() for q in matches]
        
        # Log using the evaluation logger
        logger.log_question_similarity(
            target_question=example.target_question,
            similar_questions=similar_questions,
            similarity_scores=[-1] * len(similar_questions),
            is_duplicate=pred_is_duplicate,
            matched_question=prediction.matched_question,
            explanation=prediction.explanation,
            proposer="DSpy Optimizer",
            timestamp=datetime.now()
        )
        
        if score > 0.5:  # Consider it correct if score is more than 0.5
            correct += 1
    
    accuracy = correct / total
    print(f"Test accuracy: {accuracy:.2f}")
    
    # Get the optimized prompt
    print("Getting optimized prompt from optimized_module.predictor.prompt")
    optimized_prompt = optimized_module.predictor.prompt

    # Print prompt information
    print(f"Prompt length: {len(optimized_prompt)}")
    print(f"Prompt preview (first 200 chars):")
    print(optimized_prompt[:200])
    print("...")
    print("Last 200 chars:")
    print(optimized_prompt[-200:])
    
    # Save optimized prompt
    with open("optimizations/duplicate_detection_prompt.py", "w") as f:
        f.write(f"""
QUESTION_SIMILARITY_PROMPT = \"\"\"
{optimized_prompt}
\"\"\"
        """)
    
    print(f"Optimized prompt saved to optimizations/duplicate_detection_prompt.py")

if __name__ == "__main__":
    main() 