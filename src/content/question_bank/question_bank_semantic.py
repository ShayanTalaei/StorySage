from openai import OpenAI

from content.question_bank.question_bank_base import QuestionBankBase


class QuestionBankSemantic(QuestionBankBase):
    """Semantic search implementation using LLM."""
    def __init__(self):
        super().__init__()
        self.client = OpenAI() 