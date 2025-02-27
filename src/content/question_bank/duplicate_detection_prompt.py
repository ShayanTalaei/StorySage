
# Optimized prompt for question similarity evaluation
QUESTION_SIMILARITY_PROMPT = """

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
        