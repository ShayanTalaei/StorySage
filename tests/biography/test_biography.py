import pytest
import os
import shutil
from src.biography.biography import Biography

USER_ID = "test_user"
TEST_DATA_DIR = f"data/{USER_ID}"

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
    assert bio.get_section_by_path("") == bio.root
    
    # Test getting existing section
    section = bio.get_section_by_path("1 Early Life/1.1 Childhood")
    assert section is not None
    assert section.title == "1.1 Childhood"
    
    # Test getting non-existent section
    assert bio.get_section_by_path("3 Career") is None

    # Test invalid path format
    with pytest.raises(ValueError):
        bio.get_section_by_path("Non/Existent/Path")

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
    deep_section = bio.add_section("2 Career/2.1 First Job/Details", "Project details")
    assert "2 Career" in bio.root.subsections
    assert "2.1 First Job" in bio.root.subsections["2 Career"].subsections
    assert deep_section.title == "Details"
    
    # Test that empty path raises ValueError
    with pytest.raises(ValueError, match="Path cannot be empty"):
        bio.add_section("", "Content")

def test_update_section():
    bio = Biography(USER_ID)
    bio.add_section("1 Early Life", "Initial content")
    
    # Test updating existing section
    updated_section = bio.update_section("1 Early Life", "Updated content")
    assert updated_section is not None
    assert updated_section.content == "Updated content"
    
    # Test updating non-existent section
    with pytest.raises(ValueError):
        bio.update_section("Non/Existent/Path", "Content")

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
    
    markdown = bio.export_to_markdown()
    
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
    assert bio.is_valid_path_format("1 Early Life/1.1 Childhood/Details")
    
    # Invalid paths
    assert not bio.is_valid_path_format("Early Life")  # Missing number prefix
    assert not bio.is_valid_path_format("1 Early Life/Childhood")  # Missing decimal notation
    assert not bio.is_valid_path_format("1 Early Life/1.1 Childhood/2 Details")  # Number prefix in third level
    assert not bio.is_valid_path_format("1 Early Life/1.1 Childhood/Details/More/Levels")  # Too deep

def test_get_section_by_title():
    bio = Biography(USER_ID)
    bio.add_section("1 Early Life", "Content")
    bio.add_section("1 Early Life/1.1 Childhood", "More content")
    
    section = bio.get_section_by_title("1.1 Childhood")
    assert section is not None
    assert section.title == "1.1 Childhood"
    
    assert bio.get_section_by_title("Non-existent Title") is None

def test_get_sections():
    bio = Biography(USER_ID)
    bio.add_section("1 Early Life", "Content")
    bio.add_section("1 Early Life/1.1 Childhood", "More content")
    
    sections = bio.get_sections()
    assert sections["title"] == f"Biography of {USER_ID}"
    assert "1 Early Life" in sections["subsections"]
    assert "1.1 Childhood" in sections["subsections"]["1 Early Life"]["subsections"]


