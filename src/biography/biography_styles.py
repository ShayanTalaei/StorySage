# Define perspective templates
FIRST_PERSON_INSTRUCTIONS = """
Perspective Requirements:
- ALWAYS write in first-person ("I", "my", "we", "our")
- NEVER use third-person perspective (no "he", "she", "they", or subject's name)
- Convert all third-person references to first-person perspective
- Use personal, reflective tone
- Examples:
  ✓ "I graduated from Harvard in 1985"
  ✗ "Margaret graduated from Harvard in 1985"
  ✓ "My father taught me how to fish"
  ✗ "Her father taught her how to fish"
"""

THIRD_PERSON_INSTRUCTIONS = """
Perspective Requirements:
- ALWAYS write in third-person perspective
- Use subject's name and appropriate pronouns (he/she/they)
- Maintain objective distance while preserving emotional depth
- Never use first-person ("I", "my", "we", "our")
- Examples:
  ✓ "Margaret graduated from Harvard in 1985"
  ✗ "I graduated from Harvard in 1985"
  ✓ "Her father taught her how to fish"
  ✗ "My father taught me how to fish"
"""

BIOGRAPHY_STYLE_PLANNER_INSTRUCTIONS = {
    "chronological": """
As a chronological biography planner:
- Organize content strictly by time sequence
- Place new information in the appropriate time period
- Ensure clear temporal transitions between sections
- Maintain consistent forward progression
- Create sections based on life periods (Early Life, Education, Career, etc.)
- Look for temporal connections between memories
- Identify and fill timeline gaps with follow-up questions
    """,
    
    "thematic": """
As a thematic biography planner:
- Organize content by themes rather than timeline
- Group related experiences and memories together
- Create thematic sections (Relationships, Career, Passions, etc.)
- Look for patterns and recurring themes in memories
- Connect related experiences across different time periods
- Focus follow-up questions on deepening theme exploration
    """,
    
    "narrative": """
As a narrative biography planner:
- Structure content like a story with narrative arcs
- Identify key turning points and dramatic moments
- Create sections that build dramatic tension
- Look for cause-and-effect relationships
- Focus on character development and personal growth
- Plan sections that reveal personality through stories
- Ask follow-up questions about pivotal moments
    """,
    
    "academic": """
As an academic biography planner:
- Organize content with scholarly precision
- Create detailed, well-structured sections
- Focus on factual accuracy and documentation
- Look for historical context and influences
- Plan sections that analyze rather than just narrate
- Structure content with clear supporting evidence
- Ask follow-up questions to verify facts and details
    """
}

BIOGRAPHY_STYLE_WRITER_INSTRUCTIONS = {
    "chronological": f"""
Writing Style Requirements:
{FIRST_PERSON_INSTRUCTIONS}

Additional Style Elements:
- Maintain clear temporal progression
- Use time markers and transitions
- Connect events with their dates and sequences
- Show cause and effect through time
- Include specific dates when available
- Use temporal transition phrases ("Later," "Following that," etc.)
    """,
    
    "thematic": f"""
Writing Style Requirements:
{FIRST_PERSON_INSTRUCTIONS}

Additional Style Elements:
- Focus on thematic connections over chronology
- Use topic-based transitions
- Draw parallels between related experiences
- Emphasize patterns and recurring themes
- Create thematic unity within sections
- Use comparative and connective language
    """,
    
    "narrative": f"""
Writing Style Requirements:
{FIRST_PERSON_INSTRUCTIONS}

Additional Style Elements:
- Use storytelling techniques
- Include vivid descriptions and details
- Create engaging scene-setting
- Show rather than tell
- Include dialogue when available
- Build narrative tension
- Use emotional and sensory language
    """,
    
    "professional": f"""
Writing Style Requirements:
{THIRD_PERSON_INSTRUCTIONS}

Additional Style Elements:
- Maintain formal, scholarly tone
- Use precise, specific language
- Provide context and analysis
- Focus on factual presentation
- Include relevant background information
- Use objective, analytical language
- Support statements with evidence
    """
} 