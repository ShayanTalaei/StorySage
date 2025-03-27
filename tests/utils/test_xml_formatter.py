from src.utils.llm.xml_formatter import extract_tool_arguments

def test_memory_ids_extraction_formats():
    """Test that extract_tool_arguments can handle different memory_ids formats."""
    
    # Test case 1: Quoted memory IDs in a list
    response_quoted = """<tool_calls>
        <add_plan>
            <action_type>create</action_type>
            <section_path>2 Education</section_path>
            <memory_ids>["MEM_03082002_OC5", "MEM_03082002_3B8", "MEM_03082002_83Q"]</memory_ids>
            <plan_content>Create a section about education</plan_content>
        </add_plan>
    </tool_calls>"""
    
    # Test case 2: Unquoted memory IDs in a list
    response_unquoted = """<tool_calls>
        <add_plan>
            <action_type>create</action_type>
            <section_path>2 Education</section_path>
            <memory_ids>[MEM_03082002_OC5, MEM_03082002_3B8, MEM_03082002_83Q]</memory_ids>
            <plan_content>Create a section about education</plan_content>
        </add_plan>
    </tool_calls>"""
    
    # Test case 3: Single memory ID in brackets
    response_single = """<tool_calls>
        <add_plan>
            <action_type>create</action_type>
            <section_path>2 Education</section_path>
            <memory_ids>[MEM_03082002_OC5]</memory_ids>
            <plan_content>Create a section about education</plan_content>
        </add_plan>
    </tool_calls>"""
    
    # Extract memory IDs from each response
    result_quoted = extract_tool_arguments(response_quoted, "add_plan", "memory_ids")
    result_unquoted = extract_tool_arguments(response_unquoted, "add_plan", "memory_ids")
    result_single = extract_tool_arguments(response_single, "add_plan", "memory_ids")
    
    # Expected results
    expected_ids = ["MEM_03082002_OC5", "MEM_03082002_3B8", "MEM_03082002_83Q"]
    expected_single = ["MEM_03082002_OC5"]
    
    # Assertions
    assert isinstance(result_quoted[0], list), "Quoted memory IDs should be parsed as a list"
    assert isinstance(result_unquoted[0], list), "Unquoted memory IDs should be parsed as a list"
    assert isinstance(result_single[0], list), "Single memory ID should be parsed as a list"
    
    assert result_quoted[0] == expected_ids, "Quoted memory IDs not correctly extracted"
    assert result_unquoted[0] == expected_ids, "Unquoted memory IDs not correctly extracted"
    assert result_single[0] == expected_single, "Single memory ID not correctly extracted"

def test_memory_ids_edge_cases():
    """Test edge cases for memory_ids extraction."""
    
    # Test case 1: Empty list
    response_empty = """<tool_calls>
        <add_plan>
            <memory_ids>[]</memory_ids>
        </add_plan>
    </tool_calls>"""
    
    # Test case 2: Malformed list (missing closing bracket)
    response_malformed = """<tool_calls>
        <add_plan>
            <memory_ids>[MEM_03082002_OC5, MEM_03082002_3B8</memory_ids>
        </add_plan>
    </tool_calls>"""
    
    # Test case 3: Empty tool_calls tags
    response_empty_tags = """<tool_calls></tool_calls>"""
    
    # Test case 4: Empty tool_calls with whitespace
    response_empty_with_space = """<tool_calls>
    </tool_calls>"""
    
    # Extract memory IDs from each response
    result_empty = extract_tool_arguments(response_empty, "add_plan", "memory_ids")
    result_malformed = extract_tool_arguments(response_malformed, "add_plan", "memory_ids")
    result_empty_tags = extract_tool_arguments(response_empty_tags, "add_plan", "memory_ids")
    result_empty_with_space = extract_tool_arguments(response_empty_with_space, "add_plan", "memory_ids")
    
    # Assertions
    assert isinstance(result_empty, list), "Result should be a list"
    
    # Check if result_empty has elements
    if len(result_empty) > 0:
        assert isinstance(result_empty[0], list), "Empty list should be parsed as a list"
        assert len(result_empty[0]) == 0, "Empty list should have no elements"
    else:
        # If result_empty is an empty list itself, that's also acceptable
        assert len(result_empty) == 0, "Result should be empty"
    
    # For malformed list, we should still get a result
    assert len(result_malformed) > 0, "Should return some result for malformed list"
    assert result_malformed[0] is not None, "Malformed list should not return None"
    
    # Assertions for empty tool_calls
    assert result_empty_tags == [], "Empty tool_calls should return empty list"
    assert result_empty_with_space == [], "Empty tool_calls with whitespace should return empty list"

def test_normal_parameter_extraction():
    """Test extraction of normal parameters like section_path."""
    
    # Test response with various normal parameters
    response = """<tool_calls>
        <add_plan>
            <action_type>create</action_type>
            <section_path>2 Education</section_path>
            <memory_ids>["MEM_03082002_OC5", "MEM_03082002_3B8"]</memory_ids>
            <plan_content>Create a section about education</plan_content>
        </add_plan>
    </tool_calls>"""
    
    # Extract different parameters
    section_path_result = extract_tool_arguments(response, "add_plan", "section_path")
    action_type_result = extract_tool_arguments(response, "add_plan", "action_type")
    plan_content_result = extract_tool_arguments(response, "add_plan", "plan_content")
    
    # Assertions for normal string parameters
    assert section_path_result[0] == "2 Education", "Section path not correctly extracted"
    assert action_type_result[0] == "create", "Action type not correctly extracted"
    assert plan_content_result[0] == "Create a section about education", "Update plan not correctly extracted"
    
    # Test with multiple tool calls
    multi_response = """<tool_calls>
        <add_plan>
            <section_path>2 Education</section_path>
        </add_plan>
        <add_plan>
            <section_path>3 Career</section_path>
        </add_plan>
    </tool_calls>"""
    
    multi_result = extract_tool_arguments(multi_response, "add_plan", "section_path")
    assert len(multi_result) == 2, "Should extract parameters from multiple tool calls"
    assert multi_result[0] == "2 Education", "First section path not correctly extracted"
    assert multi_result[1] == "3 Career", "Second section path not correctly extracted"

def test_nested_tool_calls():
    """Test extraction when tool_calls tag is nested inside other tags."""
    
    # Test case with nested tool_calls
    response_nested = """<output_format>
        <thinking>
        The user shared some information. Let's update our records.
        </thinking>
        <tool_calls>
            <add_plan>
                <section_path>2 Education</section_path>
                <memory_ids>["MEM_123", "MEM_456"]</memory_ids>
            </add_plan>
        </tool_calls>
    </output_format>"""
    
    # Test case with nested empty tool_calls
    response_nested_empty = """<output_format>
        <thinking>
        The user just shared their name. It's too early for follow-up questions.
        </thinking>
        <tool_calls>
        </tool_calls>
    </output_format>"""
    
    # Extract memory IDs from each response
    result_nested = extract_tool_arguments(response_nested, "add_plan", "memory_ids")
    result_nested_empty = extract_tool_arguments(response_nested_empty, "add_plan", "memory_ids")
    
    # Assertions
    assert len(result_nested) == 1, "Should extract arguments from nested tool_calls"
    assert result_nested[0] == ["MEM_123", "MEM_456"], "Should correctly parse nested memory IDs"
    assert result_nested_empty == [], "Empty nested tool_calls should return empty list"
    
    # Test with multiple levels of nesting
    response_deeply_nested = """<output_format>
        <step_1>
            <thinking>Processing user input...</thinking>
            <tool_calls>
                <add_plan>
                    <memory_ids>["MEM_789"]</memory_ids>
                </add_plan>
            </tool_calls>
        </step_1>
    </output_format>"""
    
    result_deeply_nested = extract_tool_arguments(response_deeply_nested, "add_plan", "memory_ids")
    assert len(result_deeply_nested) == 1, "Should extract arguments from deeply nested tool_calls"
    assert result_deeply_nested[0] == ["MEM_789"], "Should correctly parse deeply nested memory IDs"

def test_malformed_xml():
    """Test handling of malformed XML."""
    
    # Test case with mismatched tags
    response_malformed = """<output_format>
        <tool_calls>
            <add_plan>
                <question>How do you like to be contacted?</question>
            </add_plan>
        </tool_calls>
        </thinking>  <!-- Mismatched tag -->
    </output_format>"""
    
    result = extract_tool_arguments(response_malformed, "add_plan", "question")
    assert result[0] == "How do you like to be contacted?", "Should handle malformed XML gracefully" 