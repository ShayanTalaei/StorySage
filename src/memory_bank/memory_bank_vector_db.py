# Python standard library imports
import os
import json
import uuid
from datetime import datetime
from typing import Dict, List

# Third-party imports
import faiss
import numpy as np
from openai import OpenAI
import dotenv

from memory_bank.memory import Memory

# Load environment variables
dotenv.load_dotenv(override=True)

class MemoryBank:
    def __init__(self, embedding_dimension: int = 1536):
        self.client = OpenAI()
        self.embedding_dimension = embedding_dimension
        self.index = faiss.IndexFlatL2(embedding_dimension)
        self.memories: List[Memory] = []
        self.embeddings: Dict[str, np.ndarray] = {}
        
    def _get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for the given text using OpenAI's API."""
        response = self.client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return np.array(response.data[0].embedding, dtype=np.float32)

    def add_memory(self, title: str, text: str, importance_score: int, source_interview_response: str, metadata: Dict = None) -> None:
        """Add a new memory to the database.
        
        Args:
            title: Title of the memory
            text: Content of the memory
            importance_score: Importance score of the memory
            source_interview_response: Original response from interview that generated this memory
            metadata: Optional metadata dictionary
        """
        if metadata is None:
            metadata = {}
            
        memory_id = str(uuid.uuid4())
        combined_text = f"{title}\n{text}"
        embedding = self._get_embedding(combined_text)
        
        memory = Memory(
            id=memory_id,
            title=title,
            text=text,
            metadata=metadata,
            importance_score=importance_score,
            timestamp=datetime.now(),
            source_interview_response=source_interview_response,
        )
        
        self.memories.append(memory)
        self.embeddings[memory_id] = embedding
        self.index.add(embedding.reshape(1, -1))

        return memory

    def search_memories(self, query: str, k: int = 5) -> List[Dict]:
        """Search for similar memories using the query text."""
        if not self.memories:  # Check if memories list is empty
            return []
        
        query_embedding = self._get_embedding(query)
        
        # Adjust k to not exceed the number of available memories
        k = min(k, len(self.memories))
        
        # Perform similarity search
        distances, indices = self.index.search(
            query_embedding.reshape(1, -1),
            k
        )
        
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx >= 0 and idx < len(self.memories):
                memory = self.memories[idx]
                result = memory.to_dict()
                result['similarity_score'] = float(1 / (1 + distance))
                results.append(result)
        
        return results

    def save_to_file(self, user_id: str) -> None:
        """Save the memory bank to separate content and embedding files."""
        content_data = {
            'memories': [memory.to_dict() for memory in self.memories]
        }
        
        embedding_data = {
            'embeddings': [
                {'id': memory_id, 'embedding': embedding.tolist()}
                for memory_id, embedding in self.embeddings.items()
            ]
        }
        
        content_filepath = os.getenv("LOGS_DIR") + f"/{user_id}/memory_bank_content.json"
        embedding_filepath = os.getenv("LOGS_DIR") + f"/{user_id}/memory_bank_embeddings.json"
        
        with open(content_filepath, 'w') as f:
            json.dump(content_data, f, indent=2)
        with open(embedding_filepath, 'w') as f:
            json.dump(embedding_data, f)

    @classmethod
    def load_from_file(cls, user_id: str) -> 'MemoryBank':
        """Load a memory bank from separate content and embedding files."""
        memory_bank = cls()
        
        content_filepath = os.getenv("LOGS_DIR") + f"/{user_id}/memory_bank_content.json"
        embedding_filepath = os.getenv("LOGS_DIR") + f"/{user_id}/memory_bank_embeddings.json"
        
        try:
            # Load content and embeddings
            with open(content_filepath, 'r') as f:
                content_data = json.load(f)
            with open(embedding_filepath, 'r') as f:
                embedding_data = json.load(f)
                
            # Create embedding lookup dictionary and store in memory_bank
            memory_bank.embeddings = {
                e['id']: np.array(e['embedding'], dtype=np.float32)
                for e in embedding_data['embeddings']
            }
            
            # Reconstruct memories
            for memory_data in content_data['memories']:
                memory = Memory.from_dict(memory_data)
                memory_bank.memories.append(memory)
                
                # Add embedding to index if available
                embedding = memory_bank.embeddings.get(memory.id)
                if embedding is not None:
                    memory_bank.index.add(embedding.reshape(1, -1))
                
        except FileNotFoundError:
            # Create new empty memory bank if files don't exist
            memory_bank.save_to_file(user_id)
            
        return memory_bank
