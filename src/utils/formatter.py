from typing import List
from content.question_bank.question import SimilarQuestionsGroup


def format_similar_questions(similar_questions: List[SimilarQuestionsGroup]) -> str:
    """Format similar questions for display in warning."""
    formatted = []
    for item in similar_questions:
        formatted.append(f"Proposed Question: {item.proposed}")
        formatted.append("Similar Previously Asked Questions:")
        for similar in item.similar:
            formatted.append(f"- {similar.content}")
        formatted.append("")
    return "\n".join(formatted)
