
QUESTION_SIMILARITY_PROMPT = """

You are an expert at evaluating question similarity.

Question to Check:
<question>
{target_question}
</question>

Existing Questions to Compare Against:
<questions>
{similar_questions}
</questions>

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

<evaluation>
<is_duplicate>"true" or "false"</is_duplicate>
<matched_question>If duplicate found: paste the exact matching question here
If no duplicate: write "null"</matched_question>
<explanation>Provide a detailed explanation of why the questions are or are not duplicates.</explanation>
</evaluation>

"""
        