SIMILAR_QUESTIONS_WARNING = """\
<similar_questions_warning>
Warning: Some of your proposed questions are similar to previously asked questions.

Previous Tool Calls:
<previous_tool_call>
{previous_tool_call}
</previous_tool_call>

Similar Questions Already Asked:
<similar_questions>
{similar_questions_formatted}
</similar_questions>

Choose ONE of these actions:
1. Regenerate new tool calls with alternative questions
   - Explain why these questions bring new insights besides the ones already captured in <thinking> </thinking>
   - Add <proceed>true</proceed> at the end of your thinking tag to proceed with the regeneration
2. Leave empty inside <tool_calls> </tool_calls> tags if you don't want to propose any follow-up questions

</similar_questions_warning>
"""

MISSING_MEMORIES_WARNING = """\
<missing_memories_warning>
Warning: Some memories from the interview session are not yet incorporated into the biography.

Previous Tool Calls:
<previous_tool_call>
{previous_tool_call}
</previous_tool_call>

Uncovered Memories:
<missing_memory_ids>
{missing_memory_ids}
</missing_memory_ids>

You need to **regenerate tool calls from scratch**.

If you believe some memories can be excluded, explain why within the `<thinking></thinking>` tags and add `<proceed>true</proceed>` at the end of your thinking.

- **Example Reasons:**
  * The memory is already covered in another section.
  * The memory is trivial and not relevant.

**Note:** Do not leave the `<tool_calls></tool_calls>` tags empty; otherwise, no action will be taken.

</missing_memories_warning>
"""

WARNING_OUTPUT_FORMAT = """
If you decide to proceed with the warning, please include the following XML tag after providing your explanation:
<proceed>true</proceed>
"""