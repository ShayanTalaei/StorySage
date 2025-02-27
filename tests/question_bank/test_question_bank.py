import os
from pathlib import Path
import pytest
from datetime import datetime
from typing import List
from dotenv import load_dotenv

load_dotenv()

from content.question_bank.question_bank_vector_db import QuestionBankVectorDB, QuestionBankBase

@pytest.fixture
def question_bank():
    return QuestionBankVectorDB()

@pytest.fixture
def sample_questions() -> List[str]:
    return [
        "What was your childhood like?",
        "Tell me about your early childhood memories.",
        "How was your experience growing up?",
        "What do you do for work?",
        "What's your current occupation?",
        "Tell me about your career path.",
        "Who are the most important people in your life?",
        "Tell me about your family relationships.",
    ]

def test_generate_question_id(question_bank: QuestionBankBase):
    """Test question ID generation format."""
    question_id = question_bank.generate_question_id()
    
    # Check format: Q_MMDDHHMM_XXX
    assert question_id.startswith("Q_")
    assert len(question_id) == 14  # Q_ (2) + MMDDHHMM (8) + _ (1) + XXX (3)
    assert question_id[10] == "_"
    
    # Extract timestamp part
    timestamp_str = question_id[2:10]
    # Should be valid MMDDHHMM format
    datetime.strptime(timestamp_str, "%m%d%H%M")

def test_add_question(question_bank: QuestionBankBase):
    """Test adding a question."""
    content = "What was your childhood like?"
    memory_ids = ["MEM_123", "MEM_456"]
    
    question = question_bank.add_question(content, memory_ids)
    
    assert question.content == content
    assert question.memory_ids == memory_ids
    assert isinstance(question.timestamp, datetime)
    assert len(question_bank.questions) == 1

def test_search_questions(question_bank: QuestionBankBase, sample_questions: List[str]):
    """Test searching similar questions."""
    # Add sample questions
    for question in sample_questions:
        question_bank.add_question(question)
    
    # Search for childhood-related questions
    results = question_bank.search_questions("childhood memories", k=3)
    
    assert len(results) == 3
    # First results should be childhood-related
    assert any("childhood" in result.content.lower() for result in results)
    # Each result should have a similarity score
    assert all(result.similarity_score is not None for result in results)

def test_search_empty_bank(question_bank: QuestionBankBase):
    """Test searching when question bank is empty."""
    results = question_bank.search_questions("test query")
    assert results == []

def test_link_memory(question_bank: QuestionBankBase):
    """Test linking a memory to a question."""
    question = question_bank.add_question("What was your childhood like?")
    
    question_bank.link_memory(question.id, "MEM_123")
    question_bank.link_memory(question.id, "MEM_456")
    
    updated_question = question_bank.get_question_by_id(question.id)
    assert "MEM_123" in updated_question.memory_ids
    assert "MEM_456" in updated_question.memory_ids

def test_link_memory_duplicate(question_bank: QuestionBankBase):
    """Test linking the same memory multiple times."""
    question = question_bank.add_question("What was your childhood like?")
    
    question_bank.link_memory(question.id, "MEM_123")
    question_bank.link_memory(question.id, "MEM_123")  # Try to add same memory again
    
    updated_question = question_bank.get_question_by_id(question.id)
    assert updated_question.memory_ids.count("MEM_123") == 1  # Should only appear once

def test_save_and_load(question_bank: QuestionBankBase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test saving and loading question bank."""
    # Set up temporary directory for test
    test_dir = tmp_path / "test_user"
    test_dir.mkdir()
    monkeypatch.setenv("LOGS_DIR", str(tmp_path))
    
    # Add some questions
    question_bank.add_question("What was your childhood like?")
    question_bank.add_question("Tell me about your career.")
    
    # Save to file
    question_bank.save_to_file("test_user")
    
    # Load into new instance
    loaded_bank = QuestionBankVectorDB.load_from_file("test_user")
    
    assert len(loaded_bank.questions) == len(question_bank.questions)
    
    # Check if questions are identical
    for q1, q2 in zip(loaded_bank.questions, question_bank.questions):
        assert q1.to_dict() == q2.to_dict()

def test_get_question_by_id(question_bank: QuestionBankBase):
    """Test retrieving a question by ID."""
    question = question_bank.add_question("What was your childhood like?")
    
    retrieved = question_bank.get_question_by_id(question.id)
    assert retrieved is not None
    assert retrieved.content == question.content
    
    # Test non-existent ID
    assert question_bank.get_question_by_id("non_existent_id") is None

def test_basic_search_exact_match(question_bank: QuestionBankBase):
    """Test searching with exact match."""
    # Add some questions
    question = "What was your childhood like?"
    question_bank.add_question(question)
    
    # Search with the exact same text
    results = question_bank.search_questions(question)
    
    assert len(results) > 0
    assert results[0].content == question
    assert results[0].similarity_score is not None

def test_basic_search_similar_questions(question_bank: QuestionBankBase):
    """Test searching with similar questions."""
    questions = [
        "What do you do for work?",
        "What is your current job?",
        "Tell me about your hobbies.",
    ]
    
    for q in questions:
        question_bank.add_question(q)
    
    # Search for work-related questions
    results = question_bank.search_questions("What is your occupation?", k=2)
    
    assert len(results) == 2
    # At least one of the top results should be about work/job
    work_related = any(
        "work" in r.content.lower() or 
        "job" in r.content.lower() 
        for r in results
    )
    assert work_related

def test_basic_search_with_context(question_bank: QuestionBankBase):
    """Test searching with contextual similarity."""
    questions = [
        "Tell me about your family.",
        "Do you have any siblings?",
        "What's your favorite color?",
    ]
    
    for q in questions:
        question_bank.add_question(q)
    
    # Search for family-related questions
    results = question_bank.search_questions("Who are your family members?", k=2)
    
    assert len(results) == 2
    # At least one of the top results should be about family
    family_related = any(
        "family" in r.content.lower() or 
        "siblings" in r.content.lower() 
        for r in results
    )
    assert family_related

def test_question_similarity_evaluation(question_bank: QuestionBankBase, sample_questions: List[str], monkeypatch: pytest.MonkeyPatch):
    """Test the question similarity evaluation functionality."""
    # Set up test environment but keep logs
    test_logs_dir = os.getenv("LOGS_DIR")
    monkeypatch.setenv("LOGS_DIR", test_logs_dir)
    
    # Add sample questions to the bank
    for question in sample_questions:
        question_bank.add_question(question)
    
    # Test cases with expected duplicates and non-duplicates
    test_cases = [
        "Could you describe your childhood experiences?",  # Should match childhood questions
        "What is your current job and career?",  # Should match work questions
        "Who is in your family?",  # Should match family questions
        "What is your favorite movie?",  # Should be unique
    ]
    
    for test_question in test_cases:
        print(f"\nTesting question: {test_question}")
        
        # Get similar questions
        similar_results = question_bank.search_questions(test_question)
        
        print("\nSimilar questions found:")
        for result in similar_results:
            print(f"- {result.content} (similarity: {result.similarity_score:.2f})")
        
        # Check if it's a duplicate
        is_duplicate = question_bank.evaluate_question_duplicate(test_question)
        print(f"\nIs duplicate: {is_duplicate}")
        print("-" * 30)
    
    print(f"\nEvaluation logs saved to: {test_logs_dir}/dspy/question_similarity_evaluations.csv")
    assert False  # To see the output
