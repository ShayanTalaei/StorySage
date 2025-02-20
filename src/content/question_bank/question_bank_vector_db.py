from typing import Dict, List, Optional
import os
import json
from datetime import datetime
import numpy as np
from openai import OpenAI
import faiss
import dotenv

from content.question_bank.question_bank_base import QuestionBankBase
from content.question_bank.question import Question, QuestionSearchResult

# Load environment variables
dotenv.load_dotenv(override=True)

class QuestionBankVectorDB(QuestionBankBase):
    """Vector database implementation using FAISS and embeddings."""
    
    def __init__(self, embedding_dimension: int = 1536):
        super().__init__()
        self.client = OpenAI()
        self.embedding_dimension = embedding_dimension
        self.index = faiss.IndexFlatL2(embedding_dimension)
        self.embeddings: Dict[str, np.ndarray] = {}
        
    def _get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for the given text using OpenAI's API."""
        response = self.client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return np.array(response.data[0].embedding, dtype=np.float32)

    def add_question(
        self,
        content: str,
        memory_ids: Optional[List[str]] = None,
    ) -> Question:
        """Add a new question to the vector database."""
        if memory_ids is None:
            memory_ids = []
            
        question_id = self.generate_question_id()
        embedding = self._get_embedding(content)
        
        question = Question(
            id=question_id,
            content=content,
            memory_ids=memory_ids,
            timestamp=datetime.now(),
        )
        
        self.questions.append(question)
        self.embeddings[question_id] = embedding
        self.index.add(embedding.reshape(1, -1))

        return question

    def search_questions(self, query: str, k: int = 5) -> List[QuestionSearchResult]:
        """Search for similar questions using the query text."""
        if not self.questions:
            return []
        
        query_embedding = self._get_embedding(query)
        
        # Adjust k to not exceed the number of available questions
        k = min(k, len(self.questions))
        
        # Perform similarity search
        distances, indices = self.index.search(
            query_embedding.reshape(1, -1),
            k
        )
        
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx >= 0 and idx < len(self.questions):
                question = self.questions[idx]
                similarity_score = float(1 / (1 + distance))
                results.append(QuestionSearchResult.from_question(
                    question=question,
                    similarity_score=similarity_score
                ))
        
        return results

    def _save_implementation_specific(self, user_id: str) -> None:
        """Save embeddings to file."""
        embedding_data = {
            'embeddings': [
                {'id': question_id, 'embedding': embedding.tolist()}
                for question_id, embedding in self.embeddings.items()
            ]
        }
        
        embedding_filepath = os.getenv("LOGS_DIR") + f"/{user_id}/question_bank_embeddings.json"
        with open(embedding_filepath, 'w') as f:
            json.dump(embedding_data, f)

    def _load_implementation_specific(self, user_id: str) -> None:
        """Load embeddings from file and reconstruct the FAISS index."""
        embedding_filepath = os.getenv("LOGS_DIR") + f"/{user_id}/question_bank_embeddings.json"
        
        try:
            with open(embedding_filepath, 'r') as f:
                embedding_data = json.load(f)
                
            # Create embedding lookup dictionary
            self.embeddings = {
                e['id']: np.array(e['embedding'], dtype=np.float32)
                for e in embedding_data['embeddings']
            }
            
            # Reconstruct FAISS index
            for question in self.questions:
                embedding = self.embeddings.get(question.id)
                if embedding is not None:
                    self.index.add(embedding.reshape(1, -1))
                    
        except FileNotFoundError:
            pass  # No embeddings file exists yet 