import pytest
import os
import shutil
from content.session_note.interview_question import InterviewQuestion
from src.content.session_note.session_note import SessionNote

USER_ID = "test_user"

@pytest.fixture
def sample_session_note() -> SessionNote:
    """Create a sample session note for testing"""
    data = {
        "user_portrait": {
            "Name": "John Doe",
            "Age": "30",
            "Occupation": "Software Engineer"
        },
        "last_meeting_summary": "First meeting with John",
        "topics": {
            "Personal": [
                {
                    "topic": "Personal",
                    "question_id": "1",
                    "question": "Where did you grow up?",
                    "notes": ["Grew up in Boston"],
                    "sub_questions": [
                        {
                            "topic": "Personal",
                            "question_id": "1.1",
                            "question": "What neighborhood?",
                            "notes": ["South End"],
                            "sub_questions": []
                        }
                    ]
                }
            ],
            "Professional": [
                {
                    "topic": "Professional",
                    "question_id": "2",
                    "question": "Current role?",
                    "notes": [],
                    "sub_questions": []
                }
            ]
        }
    }
    return SessionNote(USER_ID, "1", data)

def test_get_user_portrait_str(sample_session_note: SessionNote):
    """Test formatting of user portrait string"""
    expected = "Name: John Doe\nAge: 30\nOccupation: Software Engineer"
    assert sample_session_note.get_user_portrait_str() == expected

def test_get_last_meeting_summary_str(sample_session_note: SessionNote):
    """Test getting last meeting summary"""
    assert sample_session_note.get_last_meeting_summary_str() == "First meeting with John"

def test_format_qa_normal(sample_session_note: SessionNote):
    """Test question formatting without hiding answered questions"""
    qa = sample_session_note.topics["Personal"][0]
    lines = sample_session_note.format_qa(qa)
    
    expected = [
        "\n[ID] 1: Where did you grow up?",
        "[note] Grew up in Boston",
        "\n[ID] 1.1: What neighborhood?",
        "[note] South End"
    ]
    assert lines == expected

def test_format_qa_hide_answered(sample_session_note: SessionNote):
    """Test question formatting with hiding answered questions"""
    qa = sample_session_note.topics["Personal"][0]
    lines = sample_session_note.format_qa(qa, hide_answered="qa")
    
    expected = [
        "\n[ID] 1: (Answered)",
        "\n[ID] 1.1: (Answered)"
    ]
    assert lines == expected

def test_get_questions_and_notes_str(sample_session_note: SessionNote):
    """Test full questions and notes string formatting"""
    result = sample_session_note.get_questions_and_notes_str()
    expected = (
        "\nTopic: Personal"
        "\n\n[ID] 1: Where did you grow up?"
        "\n[note] Grew up in Boston"
        "\n\n[ID] 1.1: What neighborhood?"
        "\n[note] South End"
        "\n\nTopic: Professional"
        "\n\n[ID] 2: Current role?"
    )
    # Remove whitespace for comparison
    assert result.replace(" ", "") == expected.replace(" ", "")

def test_add_interview_question(sample_session_note: SessionNote):
    """Test adding new interview questions"""
    # Add top-level question
    sample_session_note.add_interview_question(
        "Personal",
        "What schools did you attend?",
        question_id="3"
    )
    assert sample_session_note.get_question("3").question == "What schools did you attend?"
    
    # Add sub-question
    sample_session_note.add_interview_question(
        "Personal",
        "Which high school?",
        question_id="3.1",
    )
    assert sample_session_note.get_question("3.1").question == "Which high school?"

def test_get_question(sample_session_note: SessionNote):
    """Test retrieving questions by ID"""
    # Get top-level question
    q1 = sample_session_note.get_question("1")
    assert q1.question == "Where did you grow up?"
    
    # Get sub-question
    q1_1 = sample_session_note.get_question("1.1")
    assert q1_1.question == "What neighborhood?"
    
    # Get non-existent question
    assert sample_session_note.get_question("999") is None

def test_add_note(sample_session_note: SessionNote):
    """Test adding notes to questions"""
    # Add note to existing question
    sample_session_note.add_note("2", "Working as senior developer")
    assert "Working as senior developer" in sample_session_note.get_question("2").notes
    
    # Add general note
    sample_session_note.add_note(note="Follow up needed on education")
    assert "Follow up needed on education" in sample_session_note.additional_notes

@pytest.fixture
def temp_logs_dir(monkeypatch, tmp_path):
    """Create temporary logs directory for testing file operations"""
    monkeypatch.setenv("LOGS_DIR", str(tmp_path))
    
    # Clean up before test
    if os.path.exists("logs/test_user"):
        shutil.rmtree("logs/test_user")
    
    yield tmp_path
    
    # Clean up after test
    if os.path.exists("logs/test_user"):
        shutil.rmtree("logs/test_user")

def test_save_and_load(sample_session_note: SessionNote, temp_logs_dir):
    """Test saving and loading session notes"""
    # Save the session note
    saved_path = sample_session_note.save(save_type="original")
    assert os.path.exists(saved_path)
    
    # Load the session note
    loaded_note = SessionNote.load_from_file(saved_path)
    
    # Verify loaded data
    assert loaded_note.user_id == sample_session_note.user_id
    assert loaded_note.session_id == sample_session_note.session_id
    assert loaded_note.user_portrait == sample_session_note.user_portrait
    assert loaded_note.last_meeting_summary == sample_session_note.last_meeting_summary
    
    # Verify questions loaded correctly
    original_q = sample_session_note.get_question("1.1")
    loaded_q = loaded_note.get_question("1.1")
    assert original_q.question == loaded_q.question
    assert original_q.notes == loaded_q.notes

def test_save_types(sample_session_note: SessionNote, temp_logs_dir):
    """Test different save types"""
    # Test original save
    original_path = sample_session_note.save(save_type="original")
    expected_dir = f"session_{sample_session_note.session_id}"
    assert original_path.endswith(f"{expected_dir}/session_note.json")
    
    # Test updated save - should be in same directory with _updated suffix
    updated_path = sample_session_note.save(save_type="updated")
    assert updated_path.endswith(f"{expected_dir}/session_note_updated.json")
    
    # Test next version save - should be in next session directory
    next_path = sample_session_note.save(save_type="next_version")
    next_dir = f"session_{sample_session_note.session_id + 1}"
    assert next_path.endswith(f"{next_dir}/session_note.json")

    # Load the next version
    next_note = SessionNote.load_from_file(next_path)
    assert next_note.session_id == sample_session_note.session_id + 1
    
    # Test invalid save type
    with pytest.raises(ValueError, match="save_type must be 'updated', 'original', or 'next_version'"):
        sample_session_note.save(save_type="invalid")

def test_get_last_session_note(temp_logs_dir):
    """Test retrieving last session note"""
    # First time should create new note
    note1 = SessionNote.get_last_session_note(USER_ID)
    assert str(note1.session_id) == "0"
    note1.save(save_type="original")
    
    # Save another session note
    data = {"user_portrait": {"Name": "Test User"}}
    note2 = SessionNote(USER_ID, "2", data)
    note2.save(save_type="original")
    
    # Should retrieve the latest note
    last_note = SessionNote.get_last_session_note(USER_ID)
    assert str(last_note.session_id) == "2"

def test_get_historical_session_summaries(temp_logs_dir):
    """Test retrieving historical session summaries"""
    # Create and save multiple session notes
    for i in range(3):
        data = {
            "user_portrait": {"Name": "Test User"},
            "last_meeting_summary": f"Summary for session {i}"
        }
        note = SessionNote(USER_ID, str(i), data)
        note.save(save_type="original")
    
    # Get summaries
    summaries = SessionNote.get_historical_session_summaries(USER_ID)
    expected = (
        "Session 0:\nSummary for session 0\n\n"
        "Session 1:\nSummary for session 1\n\n"
        "Session 2:\nSummary for session 2"
    )
    assert summaries == expected

def test_delete_interview_question_no_sub_questions(sample_session_note: SessionNote):
    """Test deleting a question that has no sub-questions"""
    # Delete question "2" (Current role?)
    sample_session_note.delete_interview_question("2")
    
    # Verify question was deleted
    assert sample_session_note.get_question("2") is None
    assert len(sample_session_note.topics["Professional"]) == 0

def test_delete_interview_question_with_sub_questions(sample_session_note: SessionNote):
    """Test deleting a question that has sub-questions"""
    # Delete question "1" (Where did you grow up?)
    sample_session_note.delete_interview_question("1")
    
    # Verify question content was cleared but structure remains
    question = sample_session_note.get_question("1")
    assert question.question == ""
    assert question.notes == []
    # Verify sub-question remains intact
    sub_question = sample_session_note.get_question("1.1")
    assert sub_question.question == "What neighborhood?"
    assert sub_question.notes == ["South End"]

def test_delete_sub_question_no_children(sample_session_note: SessionNote):
    """Test deleting a sub-question that has no children"""
    # Delete question "1.1" (What neighborhood?)
    sample_session_note.delete_interview_question("1.1")
    
    # Verify sub-question was deleted
    assert sample_session_note.get_question("1.1") is None
    # Verify parent remains intact
    parent = sample_session_note.get_question("1")
    assert parent.question == "Where did you grow up?"
    assert parent.notes == ["Grew up in Boston"]
    assert len(parent.sub_questions) == 0

def test_delete_sub_question_with_children(sample_session_note: SessionNote):
    """Test deleting a sub-question that has children"""
    # First add a child to 1.1
    sample_session_note.add_interview_question(
        "Personal",
        "Which street?",
        question_id="1.1.1"
    )
    
    # Delete question "1.1"
    sample_session_note.delete_interview_question("1.1")
    
    # Verify question content was cleared but structure remains
    question = sample_session_note.get_question("1.1")
    assert question.question == ""
    assert question.notes == []
    # Verify child remains intact
    child = sample_session_note.get_question("1.1.1")
    assert child.question == "Which street?"

def test_delete_interview_question_not_found(sample_session_note: SessionNote):
    """Test deleting a non-existent question"""
    with pytest.raises(ValueError, match="Question with id 999 not found"):
        sample_session_note.delete_interview_question("999")

def test_delete_interview_question_parent_not_found(sample_session_note: SessionNote):
    """Test deleting a sub-question with non-existent parent"""
    # Add a question with invalid parent ID
    sample_session_note.topics["Personal"][0].sub_questions.append(
        InterviewQuestion("Personal", "999.1", "Invalid parent")
    )
    
    with pytest.raises(ValueError, match="Parent question with id 999 not found"):
        sample_session_note.delete_interview_question("999.1")

def test_clear_data(sample_session_note: SessionNote):
    """Test clearing all data from a session note"""
    # Verify initial state has data
    assert sample_session_note.user_portrait["Name"] == "John Doe"
    assert sample_session_note.last_meeting_summary == "First meeting with John"
    assert len(sample_session_note.topics) > 0
    
    # Clear the data
    sample_session_note.clear_questions()
    
    # Verify other fields are cleared
    assert sample_session_note.topics == {}
    assert sample_session_note.additional_notes == []
    
    # Test adding new questions after clearing
    sample_session_note.add_interview_question(
        "New Topic",
        "First question after clearing?",
        question_id="1"
    )
    sample_session_note.add_interview_question(
        "New Topic",
        "Sub-question after clearing?",
        question_id="1.1"
    )
    
    # Verify questions were added successfully
    assert "New Topic" in sample_session_note.topics
    assert len(sample_session_note.topics["New Topic"]) == 1
    
    question = sample_session_note.get_question("1")
    assert question.question == "First question after clearing?"
    
    sub_question = sample_session_note.get_question("1.1")
    assert sub_question.question == "Sub-question after clearing?" 