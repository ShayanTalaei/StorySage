from typing import List
from content.question_bank.question import SimilarQuestionsGroup


def format_similar_questions(similar_questions: List[SimilarQuestionsGroup]) -> str:
    """Format similar questions for display in warning."""
    formatted = []
    for item in similar_questions:
        formatted.append(f"Proposed Question:")
        formatted.append(f"<proposed_question>{item.proposed}</proposed_question>")
        formatted.append("Similar Previously Asked Questions:")
        for similar in item.similar:
            formatted.append(f"<existing_question>{similar.content}</existing_question>")
        formatted.append("")
    return "\n".join(formatted)
