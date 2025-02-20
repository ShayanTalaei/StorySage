from src.content.biography.biography import Section

def test_section_initialization():
    section = Section("Test Section", "Test content")
    assert section.title == "Test Section"
    assert section.content == "Test content"
    assert isinstance(section.memory_ids, list)
    assert len(section.memory_ids) == 0

def test_section_memory_ids_extraction():
    # Test with no memory IDs
    assert Section.extract_memory_ids("Plain text without memory IDs") == []
    
    # Test with single memory ID
    assert Section.extract_memory_ids("Text with [MEM_123].") == ["MEM_123"]
    
    # Test with multiple memory IDs
    content = "First memory [MEM_123]. Second memory [MEM_456]."
    assert Section.extract_memory_ids(content) == ["MEM_123", "MEM_456"]
    
    # Test with duplicate memory IDs
    content = "Memory [MEM_123]. Same memory again [MEM_123]."
    assert Section.extract_memory_ids(content) == ["MEM_123"]
    
    # Test with empty content
    assert Section.extract_memory_ids("") == []
    assert Section.extract_memory_ids(None) == []

def test_section_memory_ids_update():
    section = Section("Test Section")
    
    # Test initial empty content
    assert len(section.memory_ids) == 0
    
    # Test adding content with memory IDs
    section.content = "First memory [MEM_123]. Second memory [MEM_456]."
    section.update_memory_ids()
    assert set(section.memory_ids) == {"MEM_123", "MEM_456"}
    
    # Test updating content with some new memory IDs
    section.content = "Memory [MEM_456]. New memory [MEM_789]."
    section.update_memory_ids()
    assert set(section.memory_ids) == {"MEM_123", "MEM_456", "MEM_789"}
    
    # Test that old memory IDs are preserved even when removed from content
    section.content = "Only new memory [MEM_999]."
    section.update_memory_ids()
    assert set(section.memory_ids) == {"MEM_123", "MEM_456", "MEM_789", "MEM_999"}

def test_section_serialization():
    # Create a section with memory IDs
    section = Section("Test Section", "Memory [MEM_123]. Another memory [MEM_456].")
    
    # Convert to dict
    data = section.to_dict()
    
    # Verify memory IDs are included in serialization
    assert "memory_ids" in data
    assert set(data["memory_ids"]) == {"MEM_123", "MEM_456"}
    
    # Test deserialization
    new_section = Section.from_dict(data)
    assert new_section.title == section.title
    assert new_section.content == section.content
    assert set(new_section.memory_ids) == set(section.memory_ids)

def test_section_memory_ids_with_subsections():
    # Create a section hierarchy
    root = Section("Root", "Root memory [MEM_ROOT].")
    child = Section("Child", "Child memory [MEM_CHILD].")
    grandchild = Section("Grandchild", "Grandchild memory [MEM_GRAND].")
    
    # Build hierarchy
    root.subsections["Child"] = child
    child.subsections["Grandchild"] = grandchild
    
    # Verify each section has its own memory IDs
    assert set(root.memory_ids) == {"MEM_ROOT"}
    assert set(child.memory_ids) == {"MEM_CHILD"}
    assert set(grandchild.memory_ids) == {"MEM_GRAND"}
    
    # Test serialization of hierarchy
    data = root.to_dict()
    
    # Verify memory IDs are preserved in serialization
    new_root = Section.from_dict(data)
    assert set(new_root.memory_ids) == {"MEM_ROOT"}
    assert set(new_root.subsections["Child"].memory_ids) == {"MEM_CHILD"}
    assert set(new_root.subsections["Child"].subsections["Grandchild"].memory_ids) == {"MEM_GRAND"}

def test_section_memory_ids_edge_cases():
    # Test with invalid memory ID formats
    content = "Invalid [123] [MEM123] [MEM_] [_123] [] [mem_123] [MEM_abc-123]"
    assert Section.extract_memory_ids(content) == ["MEM_abc-123"]
    
    # Test with memory IDs in different positions
    content = "[MEM_1]At start. In middle[MEM_2]here. At end[MEM_3]"
    assert set(Section.extract_memory_ids(content)) == {"MEM_1", "MEM_2", "MEM_3"}
    
    # Test with special characters around brackets
    content = "Memory[MEM_123]! Another[MEM_456]?"
    assert set(Section.extract_memory_ids(content)) == {"MEM_123", "MEM_456"} 