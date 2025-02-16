import pytest
import os
import shutil
from src.content.biography.biography import Biography
import asyncio

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

@pytest.mark.asyncio
async def test_save_and_load():
    # Create and save biography
    bio = Biography(USER_ID)
    await bio.add_section("1 Early Life", "Content")
    await bio.add_section("1 Early Life/1.1 Childhood", "More content")
    await bio.save()
    
    # Load biography and verify contents
    loaded_bio = Biography.load_from_file(USER_ID)
    assert loaded_bio.root.subsections["1 Early Life"].content == "Content"
    assert loaded_bio.root.subsections["1 Early Life"].subsections["1.1 Childhood"].content == "More content"

@pytest.mark.asyncio
async def test_export_to_markdown():
    bio = Biography(USER_ID)
    await bio.add_section("1 Early Life", "Life content")
    await bio.add_section("1 Early Life/1.1 Childhood", "Childhood content")
    
    markdown = bio.export_to_markdown(save_to_file=True)
    print(markdown)
    
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

@pytest.mark.asyncio
async def test_get_section_by_path():
    bio = Biography(USER_ID)
    await bio.add_section("1 Early Life", "Content")
    await bio.add_section("1 Early Life/1.1 Childhood", "More content")
    
    # Test getting root
    assert bio.get_section(path="") == bio.root
    
    # Test getting existing section
    section = bio.get_section(path="1 Early Life/1.1 Childhood")
    assert section is not None
    assert section.title == "1.1 Childhood"
    
    # Test getting non-existent section
    assert bio.get_section(path="3 Career") is None

    # Test invalid path format
    with pytest.raises(ValueError):
        bio.get_section(path="Non/Existent/Path")

@pytest.mark.asyncio
async def test_get_section_by_title():
    bio = Biography(USER_ID)
    await bio.add_section("1 Early Life", "Content")
    await bio.add_section("1 Early Life/1.1 Childhood", "More content")
    
    section = bio.get_section(title="1.1 Childhood")
    assert section is not None
    assert section.title == "1.1 Childhood"
    
    assert bio.get_section(title="Non-existent Title") is None

@pytest.mark.asyncio
async def test_get_sections():
    bio = Biography(USER_ID)
    await bio.add_section("1 Early Life", "Content")
    await bio.add_section("1 Early Life/1.1 Childhood", "More content")
    
    sections = bio.get_sections()
    assert sections["title"] == f"Biography of {USER_ID}"
    assert "1 Early Life" in sections["subsections"]
    assert "1.1 Childhood" in sections["subsections"]["1 Early Life"]["subsections"]

@pytest.mark.asyncio
async def test_add_section():
    bio = Biography(USER_ID)
    
    # Test adding root-level section
    section = await bio.add_section("1 Early Life", "Content about early life")
    assert "1 Early Life" in bio.root.subsections
    assert bio.root.subsections["1 Early Life"].content == "Content about early life"
    assert section.title == "1 Early Life"
    
    # Test adding nested section
    subsection = await bio.add_section("1 Early Life/1.1 Childhood", "Childhood memories")
    assert "1.1 Childhood" in bio.root.subsections["1 Early Life"].subsections
    assert subsection.title == "1.1 Childhood"
    
    # Test adding section with non-existent parent path (should create parent sections)
    deep_section = await bio.add_section("2 Career/2.1 First Job/2.1.1 Projects", "Project details")
    assert "2 Career" in bio.root.subsections
    assert "2.1 First Job" in bio.root.subsections["2 Career"].subsections
    assert "2.1.1 Projects" in bio.root.subsections["2 Career"].subsections["2.1 First Job"].subsections
    assert deep_section.title == "2.1.1 Projects"
    
    # Test that empty path raises ValueError
    with pytest.raises(ValueError, match="Path cannot be empty"):
        await bio.add_section("", "Content")

@pytest.mark.asyncio
async def test_update_section():
    bio = Biography(USER_ID)
    await bio.add_section("1 Early Life", "Initial content")
    
    # Test updating existing section
    updated_section = await bio.update_section(path="1 Early Life", content="Updated content")
    assert updated_section is not None
    assert updated_section.content == "Updated content"
    
    # Test updating non-existent section
    with pytest.raises(ValueError):
        await bio.update_section(path="Non/Existent/Path", content="Content")

@pytest.mark.asyncio
async def test_update_section_with_title_change():
    bio = Biography(USER_ID)
    
    # Setup test sections
    await bio.add_section("1 Early Life", "Initial content")
    await bio.add_section("1 Early Life/1.1 Childhood", "Childhood content")
    await bio.add_section("1 Early Life/1.2 Education", "Education content")
    
    # Test updating section title
    updated = await bio.update_section(path="1 Early Life/1.1 Childhood", content="Updated content", new_title="1.3 Youth")
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

@pytest.mark.asyncio
async def test_update_section_title_maintains_subsections():
    bio = Biography(USER_ID)
    
    # Setup test sections with nested structure
    await bio.add_section("1 Early Life", "Parent content")
    await bio.add_section("1 Early Life/1.1 Childhood", "Childhood content")
    await bio.add_section("1 Early Life/1.1 Childhood/1.1.1 Memories", "Memory content")
    await bio.add_section("1 Early Life/1.1 Childhood/1.1.2 Stories", "Story content")
    
    # Update section title
    updated = await bio.update_section(path="1 Early Life/1.1 Childhood", content="Updated content", new_title="1.2 Youth")
    
    # Verify the section was updated
    assert updated.title == "1.2 Youth"
    
    # Verify subsections were maintained
    new_section = bio._get_section_by_path("1 Early Life/1.2 Youth")
    assert "1.1.1 Memories" in new_section.subsections
    assert "1.1.2 Stories" in new_section.subsections
    assert new_section.subsections["1.1.1 Memories"].content == "Memory content"
    assert new_section.subsections["1.1.2 Stories"].content == "Story content"

@pytest.mark.asyncio
async def test_update_root_section_title():
    bio = Biography(USER_ID)
    await bio.add_section("1 Early Life", "Content")
    
    # Update root section title
    await bio.update_section(path="", content="Root content", new_title="New Biography Title")
    
    # Verify root title was updated
    assert bio.root.title == "New Biography Title"
    assert bio.root.content == "Root content"
    
    # Verify subsections were maintained
    assert "1 Early Life" in bio.root.subsections
    assert bio.root.subsections["1 Early Life"].content == "Content"


@pytest.mark.asyncio
async def test_delete_section():
    bio = Biography(USER_ID)
    
    # Setup test sections
    await bio.add_section("1 Early Life", "Initial content")
    await bio.add_section("1 Early Life/1.1 Childhood", "Childhood content")
    await bio.add_section("1 Early Life/1.1 Childhood/1.1.1 Memories", "Memory content")
    await bio.add_section("2 Career", "Career content")
    
    # Test deleting by path
    assert await bio.delete_section(path="1 Early Life/1.1 Childhood") is True
    assert "1.1 Childhood" not in bio.root.subsections["1 Early Life"].subsections
    
    # Test deleting by title
    assert await bio.delete_section(title="2 Career") is True
    assert "2 Career" not in bio.root.subsections
    
    # Test invalid cases
    assert await bio.delete_section(title="Non-existent Section") is False
    with pytest.raises(ValueError, match="Must provide either path or title"):
        await bio.delete_section()
    with pytest.raises(ValueError, match="Cannot delete root section"):
        await bio.delete_section(path="")
    with pytest.raises(ValueError, match="Invalid path format"):
        await bio.delete_section(path="Invalid/Path/Format")

@pytest.mark.asyncio
async def test_section_ordering():
    bio = Biography(USER_ID)
    
    # Test 1: Adding sections in random order
    await bio.add_section("2 Career", "Career content")
    await bio.add_section("1 Early Life", "Life content")
    await bio.add_section("3 Achievements", "Achievement content")
    
    # Verify root level sections are ordered correctly
    root_sections = list(bio.root.subsections.keys())
    assert root_sections == ["1 Early Life", "2 Career", "3 Achievements"]
    
    # Test 2: Adding subsections in random order
    await bio.add_section("1 Early Life/1.3 Teen Years", "Teen content")
    await bio.add_section("1 Early Life/1.1 Childhood", "Child content")
    await bio.add_section("1 Early Life/1.2 School", "School content")
    
    # Verify subsections are ordered correctly
    early_life_sections = list(bio.root.subsections["1 Early Life"].subsections.keys())
    assert early_life_sections == ["1.1 Childhood", "1.2 School", "1.3 Teen Years"]
    
    # Test 3: Title updates maintain order
    updated = await bio.update_section(
        path="1 Early Life/1.2 School",
        new_title="1.4 Education"
    )
    assert updated is not None
    
    # Verify new order after title update
    updated_sections = list(bio.root.subsections["1 Early Life"].subsections.keys())
    assert updated_sections == ["1.1 Childhood", "1.3 Teen Years", "1.4 Education"]
    
    # Test 4: Deep nested sections maintain order
    await bio.add_section("2 Career/2.2 Jobs", "Jobs content")
    await bio.add_section("2 Career/2.1 Skills", "Skills content")
    await bio.add_section("2 Career/2.1 Skills/2.1.2 Programming", "Programming content")
    await bio.add_section("2 Career/2.1 Skills/2.1.1 Leadership", "Leadership content")
    
    # Verify nested section ordering
    career_sections = list(bio.root.subsections["2 Career"].subsections.keys())
    assert career_sections == ["2.1 Skills", "2.2 Jobs"]
    
    skills_sections = list(bio.root.subsections["2 Career"].subsections["2.1 Skills"].subsections.keys())
    assert skills_sections == ["2.1.1 Leadership", "2.1.2 Programming"]

@pytest.mark.asyncio
async def test_section_ordering_edge_cases():
    bio = Biography(USER_ID)
    
    # Test 1: Adding sections with same number prefix
    await bio.add_section("1 Early Life", "Life content")
    await bio.add_section("1 Education", "Education content")  # Should raise ValueError
    
    # Test 2: Adding subsections with incorrect parent number
    with pytest.raises(ValueError):
        await bio.add_section("1 Early Life/2.1 Childhood", "Wrong parent number")

@pytest.mark.asyncio
async def test_concurrent_section_updates():
    bio = Biography(USER_ID)
    
    async def add_sections(start_num: int):
        for i in range(start_num, start_num + 3):
            await bio.add_section(f"{i} Section {i}", f"Content {i}")
            await asyncio.sleep(0.01)  # Use asyncio.sleep instead of time.sleep
    
    # Create and gather all coroutines
    tasks = [
        add_sections(1),
        add_sections(4),
        add_sections(7)
    ]
    
    # Run all tasks concurrently
    await asyncio.gather(*tasks)
    
    # Verify all sections were added and are in correct order
    sections = list(bio.root.subsections.keys())
    expected = [
        "1 Section 1", "2 Section 2", "3 Section 3",
        "4 Section 4", "5 Section 5", "6 Section 6",
        "7 Section 7", "8 Section 8", "9 Section 9"
    ]
    assert sections == expected
    
