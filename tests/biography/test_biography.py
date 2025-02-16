import pytest
import os
import shutil
from src.content.biography.biography import Biography
import threading
import time

USER_ID = "test_user"
TEST_DATA_DIR = f"{os.getenv('DATA_DIR', 'data')}/{USER_ID}"

@pytest.fixture(autouse=True)
def setup():
    """Setup test directory if it doesn't exist"""
    # Clean up before test
    if os.path.exists(TEST_DATA_DIR):
        shutil.rmtree(TEST_DATA_DIR)
    os.makedirs(TEST_DATA_DIR, exist_ok=True)
    
    yield
    
    # Clean up after test
    if os.path.exists(TEST_DATA_DIR):
        shutil.rmtree(TEST_DATA_DIR)

def test_biography_initialization():
    bio = Biography(USER_ID)
    assert bio.user_id == USER_ID
    assert bio.root.title == f"Biography of {USER_ID}"
    assert os.path.exists(TEST_DATA_DIR)

def test_get_section_by_path():
    bio = Biography(USER_ID)
    bio.add_section("1 Early Life", "Content")
    bio.add_section("1 Early Life/1.1 Childhood", "More content")
    
    # Test getting root
    assert bio._get_section_by_path("") == bio.root
    
    # Test getting existing section
    section = bio._get_section_by_path("1 Early Life/1.1 Childhood")
    assert section is not None
    assert section.title == "1.1 Childhood"
    
    # Test getting non-existent section
    assert bio._get_section_by_path("3 Career") is None

    # Test invalid path format
    with pytest.raises(ValueError):
        bio._get_section_by_path("Non/Existent/Path")

def test_add_section():
    bio = Biography(USER_ID)
    
    # Test adding root-level section
    section = bio.add_section("1 Early Life", "Content about early life")
    assert "1 Early Life" in bio.root.subsections
    assert bio.root.subsections["1 Early Life"].content == "Content about early life"
    assert section.title == "1 Early Life"
    
    # Test adding nested section
    subsection = bio.add_section("1 Early Life/1.1 Childhood", "Childhood memories")
    assert "1.1 Childhood" in bio.root.subsections["1 Early Life"].subsections
    assert subsection.title == "1.1 Childhood"
    
    # Test adding section with non-existent parent path (should create parent sections)
    deep_section = bio.add_section("2 Career/2.1 First Job/2.1.1 Projects", "Project details")
    assert "2 Career" in bio.root.subsections
    assert "2.1 First Job" in bio.root.subsections["2 Career"].subsections
    assert "2.1.1 Projects" in bio.root.subsections["2 Career"].subsections["2.1 First Job"].subsections
    assert deep_section.title == "2.1.1 Projects"
    
    # Test that empty path raises ValueError
    with pytest.raises(ValueError, match="Path cannot be empty"):
        bio.add_section("", "Content")

def test_update_section():
    bio = Biography(USER_ID)
    bio.add_section("1 Early Life", "Initial content")
    
    # Test updating existing section
    updated_section = bio.update_section(path="1 Early Life", content="Updated content")
    assert updated_section is not None
    assert updated_section.content == "Updated content"
    
    # Test updating non-existent section
    with pytest.raises(ValueError):
        bio.update_section(path="Non/Existent/Path", content="Content")

def test_save_and_load():
    # Create and save biography
    bio = Biography(USER_ID)
    bio.add_section("1 Early Life", "Content")
    bio.add_section("1 Early Life/1.1 Childhood", "More content")
    bio.save()
    
    # Load biography and verify contents
    loaded_bio = Biography.load_from_file(USER_ID)
    assert loaded_bio.root.subsections["1 Early Life"].content == "Content"
    assert loaded_bio.root.subsections["1 Early Life"].subsections["1.1 Childhood"].content == "More content"

def test_export_to_markdown():
    bio = Biography(USER_ID)
    bio.add_section("1 Early Life", "Life content")
    bio.add_section("1 Early Life/1.1 Childhood", "Childhood content")
    
    markdown = bio.export_to_markdown(save_to_file=True)
    
    assert f"# Biography of {USER_ID}" in markdown
    assert "## 1 Early Life" in markdown
    assert "Life content" in markdown
    assert "### 1.1 Childhood" in markdown
    assert "Childhood content" in markdown
    
    # Verify markdown file was created
    assert os.path.exists(f"{TEST_DATA_DIR}/biography_1.md")

def test_path_validation():
    bio = Biography(USER_ID)
    
    # Valid paths
    assert bio.is_valid_path_format("")  # Root path
    assert bio.is_valid_path_format("1 Early Life")
    assert bio.is_valid_path_format("1 Early Life/1.1 Childhood")
    assert bio.is_valid_path_format("1 Early Life/1.1 Childhood/1.1.1 Details")
    
    # Invalid paths
    assert not bio.is_valid_path_format("Early Life")  # Missing number prefix
    assert not bio.is_valid_path_format("1 Early Life/Childhood")  # Missing decimal notation
    assert not bio.is_valid_path_format("1 Early Life/1.1 Childhood/Details")  # Missing double decimal
    assert not bio.is_valid_path_format("1 Early Life/2.1 Childhood")  # Wrong parent number
    assert not bio.is_valid_path_format("1 Early Life/1.1 Childhood/1.2.1 Details")  # Wrong parent number
    assert not bio.is_valid_path_format("1 Early Life/1.1 Childhood/1.1.1 Details/Extra")  # Too deep

def test_get_section_by_title():
    bio = Biography(USER_ID)
    bio.add_section("1 Early Life", "Content")
    bio.add_section("1 Early Life/1.1 Childhood", "More content")
    
    section = bio._get_section_by_title("1.1 Childhood")
    assert section is not None
    assert section.title == "1.1 Childhood"
    
    assert bio._get_section_by_title("Non-existent Title") is None

def test_get_sections():
    bio = Biography(USER_ID)
    bio.add_section("1 Early Life", "Content")
    bio.add_section("1 Early Life/1.1 Childhood", "More content")
    
    sections = bio.get_sections()
    assert sections["title"] == f"Biography of {USER_ID}"
    assert "1 Early Life" in sections["subsections"]
    assert "1.1 Childhood" in sections["subsections"]["1 Early Life"]["subsections"]

def test_update_section_with_title_change():
    bio = Biography(USER_ID)
    
    # Setup test sections
    bio.add_section("1 Early Life", "Initial content")
    bio.add_section("1 Early Life/1.1 Childhood", "Childhood content")
    bio.add_section("1 Early Life/1.2 Education", "Education content")
    
    # Test updating section title
    updated = bio.update_section(path="1 Early Life/1.1 Childhood", content="Updated content", new_title="1.3 Youth")
    assert updated is not None
    assert updated.title == "1.3 Youth"
    assert updated.content == "Updated content"
    
    # Verify the section was moved in parent's subsections
    parent = bio._get_section_by_path("1 Early Life")
    assert "1.1 Childhood" not in parent.subsections
    assert "1.3 Youth" in parent.subsections
    assert parent.subsections["1.3 Youth"].content == "Updated content"
    
    # Verify subsections order is maintained
    sections_list = list(parent.subsections.keys())
    assert sections_list == ["1.2 Education", "1.3 Youth"]

def test_update_section_title_maintains_subsections():
    bio = Biography(USER_ID)
    
    # Setup test sections with nested structure
    bio.add_section("1 Early Life", "Parent content")
    bio.add_section("1 Early Life/1.1 Childhood", "Childhood content")
    bio.add_section("1 Early Life/1.1 Childhood/1.1.1 Memories", "Memory content")
    bio.add_section("1 Early Life/1.1 Childhood/1.1.2 Stories", "Story content")
    
    # Update section title
    updated = bio.update_section(path="1 Early Life/1.1 Childhood", content="Updated content", new_title="1.2 Youth")
    
    # Verify the section was updated
    assert updated.title == "1.2 Youth"
    
    # Verify subsections were maintained
    new_section = bio._get_section_by_path("1 Early Life/1.2 Youth")
    assert "1.1.1 Memories" in new_section.subsections
    assert "1.1.2 Stories" in new_section.subsections
    assert new_section.subsections["1.1.1 Memories"].content == "Memory content"
    assert new_section.subsections["1.1.2 Stories"].content == "Story content"

def test_update_root_section_title():
    bio = Biography(USER_ID)
    bio.add_section("1 Early Life", "Content")
    
    # Update root section title
    bio.update_section(path="", content="Root content", new_title="New Biography Title")
    
    # Verify root title was updated
    assert bio.root.title == "New Biography Title"
    assert bio.root.content == "Root content"
    
    # Verify subsections were maintained
    assert "1 Early Life" in bio.root.subsections
    assert bio.root.subsections["1 Early Life"].content == "Content"

def test_update_section_content_only():
    bio = Biography(USER_ID)
    
    # Setup test sections
    bio.add_section("1 Early Life", "Initial content")
    bio.add_section("1 Early Life/1.1 Childhood", "Childhood content")
    
    # Test updating content only
    updated = bio.update_section(path="1 Early Life/1.1 Childhood", content="Updated content")
    assert updated is not None
    assert updated.title == "1.1 Childhood"  # Title should remain unchanged
    assert updated.content == "Updated content"
    
    # Verify parent section's subsections remain unchanged
    parent = bio._get_section_by_path("1 Early Life")
    assert "1.1 Childhood" in parent.subsections
    assert parent.subsections["1.1 Childhood"].content == "Updated content"

def test_update_section_title_only():
    bio = Biography(USER_ID)
    
    # Setup test sections
    bio.add_section("1 Early Life", "Initial content")
    bio.add_section("1 Early Life/1.1 Childhood", "Childhood content")
    bio.add_section("1 Early Life/1.1 Childhood/1.1.1 Memories", "Memory content")
    
    # Test updating title only
    updated = bio.update_section(path="1 Early Life/1.1 Childhood", new_title="1.2 Youth")
    assert updated is not None
    assert updated.title == "1.2 Youth"
    assert updated.content == "Childhood content"  # Content should remain unchanged
    
    # Verify the section was moved in parent's subsections
    parent = bio._get_section_by_path("1 Early Life")
    assert "1.1 Childhood" not in parent.subsections
    assert "1.2 Youth" in parent.subsections
    assert parent.subsections["1.2 Youth"].content == "Childhood content"
    
    # Verify subsections are maintained
    assert "1.1.1 Memories" in parent.subsections["1.2 Youth"].subsections
    assert parent.subsections["1.2 Youth"].subsections["1.1.1 Memories"].content == "Memory content"

def test_update_section_by_title():
    bio = Biography(USER_ID)
    
    # Setup test sections with a complex structure
    bio.add_section("1 Early Life", "Initial content")
    bio.add_section("1 Early Life/1.1 Childhood", "Childhood content")
    bio.add_section("1 Early Life/1.1 Childhood/1.1.1 Memories", "Memory content")
    bio.add_section("2 Career", "Career content")
    bio.add_section("2 Career/2.1 Jobs/2.1.1 First Job", "Job content")
    
    # Test 1: Update content only by title
    updated = bio.update_section(title="2.1 Jobs", content="Updated job content")
    assert updated is not None
    assert updated.title == "2.1 Jobs"
    assert updated.content == "Updated job content"
    
    # Test 2: Update title only by title
    updated = bio.update_section(title="1.1 Childhood", new_title="1.2 Youth")
    assert updated is not None
    assert updated.title == "1.2 Youth"
    assert updated.content == "Childhood content"
    
    # Test 3: Update both content and title by title
    updated = bio.update_section(
        title="1.1.1 Memories", 
        content="Updated memories", 
        new_title="1.2.1 Early Memories"
    )
    assert updated is not None
    assert updated.title == "1.2.1 Early Memories"
    assert updated.content == "Updated memories"
    
    # Test 4: Verify the entire structure is maintained and correctly ordered
    root_sections = bio.root.subsections
    assert list(root_sections.keys()) == ["1 Early Life", "2 Career"]
    
    early_life = root_sections["1 Early Life"].subsections
    assert list(early_life.keys()) == ["1.2 Youth"]
    assert early_life["1.2 Youth"].subsections["1.2.1 Early Memories"].content == "Updated memories"
    
    career = root_sections["2 Career"].subsections
    assert career["2.1 Jobs"].content == "Updated job content"
    assert "2.1.1 First Job" in career["2.1 Jobs"].subsections

def test_delete_section():
    bio = Biography(USER_ID)
    
    # Setup test sections
    bio.add_section("1 Early Life", "Initial content")
    bio.add_section("1 Early Life/1.1 Childhood", "Childhood content")
    bio.add_section("1 Early Life/1.1 Childhood/1.1.1 Memories", "Memory content")
    bio.add_section("2 Career", "Career content")
    
    # Test deleting by path
    assert bio.delete_section(path="1 Early Life/1.1 Childhood") is True
    assert "1.1 Childhood" not in bio.root.subsections["1 Early Life"].subsections
    
    # Test deleting by title
    assert bio.delete_section(title="2 Career") is True
    assert "2 Career" not in bio.root.subsections
    
    # Test invalid cases
    assert bio.delete_section(title="Non-existent Section") is False
    with pytest.raises(ValueError, match="Must provide either path or title"):
        bio.delete_section()
    with pytest.raises(ValueError, match="Cannot delete root section"):
        bio.delete_section(path="")
    with pytest.raises(ValueError, match="Invalid path format"):
        bio.delete_section(path="Invalid/Path/Format")

def test_section_ordering():
    bio = Biography(USER_ID)
    
    # Test 1: Adding sections in random order
    bio.add_section("2 Career", "Career content")
    bio.add_section("1 Early Life", "Life content")
    bio.add_section("3 Achievements", "Achievement content")
    
    # Verify root level sections are ordered correctly
    root_sections = list(bio.root.subsections.keys())
    assert root_sections == ["1 Early Life", "2 Career", "3 Achievements"]
    
    # Test 2: Adding subsections in random order
    bio.add_section("1 Early Life/1.3 Teen Years", "Teen content")
    bio.add_section("1 Early Life/1.1 Childhood", "Child content")
    bio.add_section("1 Early Life/1.2 School", "School content")
    
    # Verify subsections are ordered correctly
    early_life_sections = list(bio.root.subsections["1 Early Life"].subsections.keys())
    assert early_life_sections == ["1.1 Childhood", "1.2 School", "1.3 Teen Years"]
    
    # Test 3: Title updates maintain order
    updated = bio.update_section(
        path="1 Early Life/1.2 School",
        new_title="1.4 Education"
    )
    assert updated is not None
    
    # Verify new order after title update
    updated_sections = list(bio.root.subsections["1 Early Life"].subsections.keys())
    assert updated_sections == ["1.1 Childhood", "1.3 Teen Years", "1.4 Education"]
    
    # Test 4: Deep nested sections maintain order
    bio.add_section("2 Career/2.2 Jobs", "Jobs content")
    bio.add_section("2 Career/2.1 Skills", "Skills content")
    bio.add_section("2 Career/2.1 Skills/2.1.2 Programming", "Programming content")
    bio.add_section("2 Career/2.1 Skills/2.1.1 Leadership", "Leadership content")
    
    # Verify nested section ordering
    career_sections = list(bio.root.subsections["2 Career"].subsections.keys())
    assert career_sections == ["2.1 Skills", "2.2 Jobs"]
    
    skills_sections = list(bio.root.subsections["2 Career"].subsections["2.1 Skills"].subsections.keys())
    assert skills_sections == ["2.1.1 Leadership", "2.1.2 Programming"]

def test_section_ordering_edge_cases():
    bio = Biography(USER_ID)
    
    # Test 1: Adding sections with same number prefix
    bio.add_section("1 Early Life", "Life content")
    bio.add_section("1 Education", "Education content")  # Should raise ValueError
    
    # Test 2: Adding subsections with incorrect parent number
    with pytest.raises(ValueError):
        bio.add_section("1 Early Life/2.1 Childhood", "Wrong parent number")

def test_concurrent_section_updates():
    bio = Biography(USER_ID)
    
    def add_sections(start_num: int):
        for i in range(start_num, start_num + 3):
            bio.add_section(f"{i} Section {i}", f"Content {i}")
            time.sleep(0.01)  # Simulate some work
    
    # Create multiple threads that add sections concurrently
    threads = [
        threading.Thread(target=add_sections, args=(1,)),
        threading.Thread(target=add_sections, args=(4,)),
        threading.Thread(target=add_sections, args=(7,))
    ]
    
    # Start all threads
    for thread in threads:
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify all sections were added and are in correct order
    sections = list(bio.root.subsections.keys())
    expected = [
        "1 Section 1", "2 Section 2", "3 Section 3",
        "4 Section 4", "5 Section 5", "6 Section 6",
        "7 Section 7", "8 Section 8", "9 Section 9"
    ]
    assert sections == expected
    
