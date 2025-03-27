from src.utils.llm.xml_formatter import extract_tool_arguments, clean_malformed_xml

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

def test_long_content_with_memory_ids():
    """Test parsing XML with long content containing multiple memory IDs and special characters."""
    
    response = """<tool_calls>
    <update_section>
    <path>2 Moscow Experience/2.2 Finding Solace and Inspiration: Tretyakov Gallery and Gorky Park</path>
    <content>During my time in Moscow, I discovered pockets of peace and inspiration amidst the bustling city life. The Tretyakov Gallery became my sanctuary, a place where I could lose myself in the world of Russian art [MEM_03270052_UTA]. It was a &quot;wonderful escape into the world of Russian art, offering a rich tapestry of history and culture&quot; [MEM_03270052_UTA]. One of my favorite exhibits showcased the works of Ivan Shishkin [MEM_03270052_JA0]. His landscapes, especially those portraying the Russian countryside, resonated with me [MEM_03270052_JA0][MEM_03270052_AMT]. Shishkin&apos;s meticulous attention to detail, the way he captured light and shadow, and the overall sense of tranquility in his paintings were captivating [MEM_03270052_AMT]. They offered a &quot;refreshing contrast to the urban environment of Moscow&quot; and a moment of reflection and peace [MEM_03270052_AMT]. I also admired the works of Ilya Repin, whose paintings vividly depicted Russian life and history [MEM_03270052_JA0][MEM_03270052_SMF].  I was particularly drawn to the way Repin captured the essence of Russian culture and history in his art [MEM_03270052_SMF]. Through these artists, I gained a deeper understanding of the cultural and historical richness of Russia, which I found both fascinating and inspiring [MEM_03270052_JA0]. These places provided a sense of tranquility and inspiration amidst the bustling city life [MEM_03270052_KLR].
    
    Beyond the gallery walls, Gorky Park provided another avenue for respite [MEM_03270052_MC8]. Especially during winter, when it transformed into a &quot;picturesque snowy landscape,&quot; the park held a particular charm [MEM_03270052_UTA][MEM_03270052_XAX]. I have fond memories of the ice skating rink, a popular spot for locals and visitors alike [MEM_03270052_K0H]. It was an experience filled with &quot;joy and camaraderie,&quot; a true testament to the community spirit [MEM_03270052_K0H].  The rink often had music playing, which added to the enchanting atmosphere [MEM_03270053_516]. They played a variety of genres, from classical pieces that added a touch of elegance to the experience, to popular Russian songs that brought a lively atmosphere [MEM_03270053_03Y]. I loved going skating in the late afternoon, as the sun began to set [MEM_03270053_3M3]. &quot;The park would be bathed in a warm, golden light, and the atmosphere was both peaceful and lively&quot; [MEM_03270053_3M3]. One song that left a lasting impression was &quot;Podmoskovnye Vechera&quot; (Moscow Nights) [MEM_03270053_A5B]. Hearing this classic Russian song, which evokes such nostalgia and beauty, while gliding across the ice under the setting sun, made those moments truly magical [MEM_03270053_A5B].</path>
    </content>
    </update_section>
    </tool_calls>"""
    
    # Test extraction of content
    result = extract_tool_arguments(response, "update_section", "content")
    
    # Assertions
    assert len(result) == 1, "Should extract single content section"
    assert "&quot;" in result[0], "Should preserve HTML entities"
    assert "&apos;" in result[0], "Should preserve apostrophe entities"
    assert "Tretyakov Gallery" in result[0], "Should preserve regular text"

def test_clean_malformed_xml():
    """Test cleaning of malformed XML by removing unmatched tags."""
    
    # Test case with unmatched closing tag
    xml1 = """<tool_calls>
        <update_section>
            <content>Some text</path>
        </update_section>
    </tool_calls>"""
    
    cleaned1 = clean_malformed_xml(xml1)
    assert "<content>Some text" in cleaned1, "Should preserve content"
    assert "</path>" not in cleaned1, "Should remove unmatched closing tag"
    
    # Test case with unmatched closing tag in nested structure
    xml2 = """<tool_calls>
        <update_section>
            <content>Some text</wrong_tag>
            <next>More text</next>
        </update_section>
    </tool_calls>"""
    
    cleaned2 = clean_malformed_xml(xml2)
    assert "</wrong_tag>" not in cleaned2, "Should remove unmatched tag"
    assert "<next>More text</next>" in cleaned2, "Should preserve matched tags"

 