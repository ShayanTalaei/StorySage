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
    Existing: "Could you share more about the challenges you've faced in working on the XX project?"
- Proposed: "What was the most rewarding discovery about the XX experience?"
    Existing: "Can you describe a particular moment that was particularly rewarding about the XX experience?"

2. Acceptable Questions (Provide New Insights):
Examples of Good Variations:
- Different Time Period/Context:
    Existing: "What was your daily routine in college?"
    ✓ OK: "What was your daily routine in your first job?" *(different context)*

- Different Aspect/Angle:
    Existing: "How did you feel about moving to a new city?"
    ✓ OK: "What unexpected challenges did you face when moving to the new city?" *(specific challenges)*
    ✓ OK: "Who were the first friends you made in the new city?" *(focuses on relationships)*

- Different Depth:
    Existing: "Tell me about your favorite teacher."
    ✓ OK: "What specific lessons or advice from that teacher influenced your later life?" *(explores impact)*

## Action Required

Choose ONE of the following actions:
1. Regenerate New Tool Calls with Alternative Questions
   - Explain why these questions provide new insights beyond those already captured in `<thinking></thinking>`.
   - Add `<proceed>true</proceed>` at the end of your thinking tag to proceed with the regeneration.
2. Leave Blank within `<tool_calls></tool_calls>` Tags if you do not wish to propose any follow-up questions.

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

**Action Required:**
- Generate tool calls to cover all memories
- Ensure both previous plans in <previous_tool_call>...</previous_tool_call> and missing memories in <missing_memory_ids>...</missing_memory_ids> are included.

If you believe some memories can be excluded, explain why within the `<thinking></thinking>` tags and add `<proceed>true</proceed>` at the end of your thinking.

- Example Reasons:
  * The memory is already covered in another section.
  * The memory is trivial and not relevant.

Note: Do not leave the `<tool_calls></tool_calls>` tags empty; otherwise, no action will be taken.

</missing_memories_warning>
"""

WARNING_OUTPUT_FORMAT = """
About the warning:

If you decide to proceed with the warning, please include the following XML tag after providing your explanation:

<proceed>true</proceed>
"""