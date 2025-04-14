SIMILAR_QUESTIONS_WARNING = """\
<similar_questions_warning>

## Warning

Some of your proposed questions are similar to those previously asked.

Previous Tool Calls:
<previous_tool_call>
{previous_tool_call}
</previous_tool_call>

Similar Questions Already Asked:
<similar_questions>
{similar_questions}
</similar_questions>

## Guidelines to Address the Warning

Please avoid asking questions that are identical or too similar to ones already posed.

1. Do Not Propose Duplicate Questions:
Examples of Duplicates (Not Allowed):
- Proposed: "Can you describe a specific challenge you encountered in working on the XX project?"
    - Existing: "Could you share more about the challenges you've faced in working on the XX project?"
- Proposed: "What was the most rewarding discovery about the XX experience?"
    - Existing: "Can you describe a particular moment that was particularly rewarding about the XX experience?"

2. Acceptable Questions (Provide New Insights):
Examples of Good Variations:
- Different Time Period/Context:
    - Existing: "What was your daily routine in college?"
    ✓ OK: "What was your daily routine in your first job?" *(different context)*

- Different Aspect/Angle:
    - Existing: "How did you feel about moving to a new city?"
    ✓ OK: "What unexpected challenges did you face when moving to the new city?" *(specific challenges)*
    ✓ OK: "Who were the first friends you made in the new city?" *(focuses on relationships)*

- Different Depth:
    - Existing: "Tell me about your favorite teacher."
    ✓ OK: "What specific lessons or advice from that teacher influenced your later life?" *(explores impact)*

## Action Required

Choose ONE of the following actions:
1. Regenerate New Tool Calls with Alternative Questions
- Explain why these questions provide new insights beyond those already captured in `<thinking></thinking>`.
- Add `<proceed>true</proceed>` at the end of your thinking tag to proceed with the regeneration.
2. Leave Blank within `<tool_calls></tool_calls>` Tags if you do not wish to propose any follow-up questions.

</similar_questions_warning>
"""

PLANNER_MISSING_MEMORIES_WARNING = """\
<missing_memories_warning>
Warning: Some memories from the interview session are not yet incorporated into the plans you have generated.

Previous tool calls failed due to missing memories:
<previous_tool_call>
{previous_tool_call}
</previous_tool_call>

Uncovered memories that are not yet incorporated:
<missing_memory_ids>
{missing_memory_ids}
</missing_memory_ids>

Action Required:
- Generate add_plan tool calls to cover the missing memories since previous tool calls failed.
- If excluding any memories, explain why in `<thinking></thinking>` tags:
  - Example Reasons:
    * Memory is trivial or not relevant
</missing_memories_warning>
"""

MISSING_MEMORIES_WARNING = """\
<missing_memories_warning>
Warning: Some memories from the interview session are not yet incorporated into the section content..

Previous tool calls that already have been executed:
<previous_tool_call>
{previous_tool_call}
</previous_tool_call>

Uncovered memories that are not yet incorporated:
<missing_memory_ids>
{missing_memory_ids}
</missing_memory_ids>

Action Required:
- Update the section content to incorporate the citation links for the missing memories.
- If excluding any memories, explain why in `<thinking></thinking>` tags:
  - Example Reasons:
    * Memory already covered in another section
    * Memory is trivial or not relevant

</missing_memories_warning>
"""

QUESTION_WARNING_OUTPUT_FORMAT = """
## Addressing the Warning

If you've addressed the warning and want to proceed:
1. Add the tag <proceed>true</proceed> inside your <thinking></thinking> section
2. This confirms you've resolved the issues identified in the warning

Important: This is not a tool call - it must be placed within your thinking tags.
"""

SECTION_WRITER_TOOL_CALL_ERROR = """\
<tool_call_error_warning>
This is your previous tool call:
<previous_tool_call>
{previous_tool_call}
</previous_tool_call>

<error>{tool_call_error}</error>

## Guidelines to Fix Writing Errors

1. Section Path vs Title - Important Distinction:
   • Path: Full hierarchy with '/' separators (Example: '1 Early Life/1.1 Childhood')
   • Title: Only the section heading (Example: '1.1 Childhood')

2. Update vs Create - Important Distinction:
   • Update: Use the `update_section` tool to modify an existing section.
   • Create: Use the `add_section` tool to add a new section.

3. Always Include Section Numbers:
   • Incorrect: 'Early Childhood Experiences'
   • Correct: '1.1 Early Childhood Experiences'

3. Ensure Perfect Accuracy:
   • Use exact section paths/titles from the <biography_structure> tag
   • Check for typos, spacing, and formatting errors
   • Sections not found in <biography_structure> will cause errors

Review your tool call based on these guidelines. If the plan instructions caused this error, you may disregard those specific instructions.
</tool_call_error_warning>
"""