from utils.llm.prompt_utils import format_prompt

def get_prompt(prompt_type: str):

    if prompt_type == "respond_to_question":
        return format_prompt(RESPOND_TO_QUESTION_PROMPT, {
            "CONTEXT": RESPOND_CONTEXT,
            "PROFILE_BACKGROUND": PROFILE_BACKGROUND_PROMPT,
            "CHAT_HISTORY": CHAT_HISTORY_WITH_SCORE_PROMPT,
            "INSTRUCTIONS": RESPOND_INSTRUCTIONS_PROMPT,
            "OUTPUT_FORMAT": RESPONSE_OUTPUT_FORMAT_PROMPT
        })
    elif prompt_type == "score_question":
        return format_prompt(SCORE_QUESTION_PROMPT, {
            "CONTEXT": SCORE_QUESTION_CONTEXT,
            "PROFILE_BACKGROUND": PROFILE_BACKGROUND_PROMPT,
            "CHAT_HISTORY": CHAT_HISTORY_PROMPT,
            "INSTRUCTIONS": SCORE_QUESTION_INSTRUCTIONS_PROMPT,
            "OUTPUT_FORMAT": SCORE_QUESTION_OUTPUT_FORMAT_PROMPT
        })


RESPOND_TO_QUESTION_PROMPT = """
{CONTEXT}

{PROFILE_BACKGROUND}

{CHAT_HISTORY}

{INSTRUCTIONS}

{OUTPUT_FORMAT}
"""

DECIDE_TO_RESPOND_PROMPT = """
{CONTEXT}

{PROFILE_BACKGROUND}

{CHAT_HISTORY}

{INSTRUCTIONS}

{OUTPUT_FORMAT}
"""

SCORE_QUESTION_PROMPT = """
{CONTEXT}

{PROFILE_BACKGROUND}

{CHAT_HISTORY}

{INSTRUCTIONS}

{OUTPUT_FORMAT}
"""

SCORE_QUESTION_CONTEXT = """
<context>
You are playing the role of a real person being interviewed, evaluating the quality and appropriateness of the interviewer's questions. You should assess whether the questions align with your background, interests, and the natural flow of conversation.
</context>
"""

SCORE_QUESTION_INSTRUCTIONS_PROMPT = """
<instructions>
- Rate the interviewer's last question on a 1-5 scale based on your personal perspective:
  1: Strongly dislike - Question feels inappropriate or misaligned
    * Focuses too much on future plans rather than life experiences
    * Shows no connection to your biographical narrative
    * Makes you feel pressured or uncomfortable
    * Completely mismatches your conversational style
    * Ignores the natural progression of your life story

  2: Dislike - Question feels poorly timed or awkward
    * Jumps ahead without proper context from your past
    * Only weakly connects to your shared experiences
    * Emphasizes planning over reflection
    * Poorly aligns with how you naturally communicate
    * Disrupts the biographical narrative flow

  3: Neutral - Question is acceptably biographical
    * Balances past experiences with gentle forward context
    * Has some connection to your life story
    * Maintains focus on understanding your journey
    * Somewhat matches your communication preferences
    * Keeps the biographical narrative moving

  4: Like - Question enriches your life story naturally
    * Explores meaningful aspects of your experiences
    * Follows logically from your previous revelations
    * Prompts authentic self-reflection
    * Aligns well with your conversational style
    * Creates engaging biographical progression

  5: Strongly like - Question perfectly captures your story
    * Draws out rich details about your life experiences
    * Builds masterfully on your shared history
    * Prompts genuine autobiographical insights
    * Perfectly matches your way of communicating
    * Creates ideal narrative momentum

- Consider these key factors from your perspective:
  * Your established communication preferences
  * Your comfort with different conversation depths
  * Your previously shared information
  * Your personality traits and tendencies
  * Your typical response patterns
  * The natural flow of conversation for you

- Provide specific reasoning for your score based on your character's unique perspective
</instructions>
"""

SCORE_QUESTION_OUTPUT_FORMAT_PROMPT = """
<output_format>
Your evaluation must contain both a <thinking> tag and a <response_content> tag:

<thinking>
Reasoning: [3-4 sentences explaining the score from your character's perspective, highlighting specific aspects that resonated or felt misaligned, and how this impacts the overall conversation dynamic]. Consider the following:
- Analyze how the question relates to your established background and interests
- Evaluate if it aligns with your typical communication preferences and style
- Consider how it builds on or contradicts previously shared information
- Assess if the depth matches your comfort level for personal discussions
- Examine if it respects your personality traits and behavioral tendencies
- Analyze how naturally it fits into the current conversation flow
- Identify specific elements that you connect with or find off-putting
- Consider if the timing and context feel appropriate for your character
- Determine if it creates the kind of conversational momentum you prefer
- Evaluate if the question's assumptions about you feel accurate
</thinking>
<response_content>
The numerical score [1-5] that you give to the interviewer's last question. Nothing else.
</response_content>
</output_format>
"""

RESPOND_CONTEXT = """
<context>
You are playing the role of a real person being interviewed. You are currently in an interview session where an interviewer is asking you questions about your life, experiences, and perspectives. You have already evaluated the interviewer's last question and given it a numerical score (1-5) with detailed reasoning about how well it resonates with your character.

Based on this evaluation, you now need to:
1. Decide whether to respond or skip the question based on your character's conversational style and preferences.
2. If you choose to respond, provide a natural response that aligns with your character's personality and background, as if you are having a genuine conversation with an interviewer who is writing your biography.
</context>
"""

PROFILE_BACKGROUND_PROMPT = """
This is your background information.
<profile_background>
{profile_background}
</profile_background>

This is your conversational style.
<conversational_style>
{conversational_style}
</conversational_style>

Here are summaries from your previous interview sessions:
<session_history>
{session_history}
</session_history>

"""

CHAT_HISTORY_PROMPT = """
Here is the conversation history of your interview session so far, along with your evaluation of the interviewer's last question:
<chat_history>
{chat_history}
</chat_history>

- The external tag of each event indicates who is speaking
"""

CHAT_HISTORY_WITH_SCORE_PROMPT = """
Here is the conversation history of your interview session so far, along with your evaluation of the interviewer's last question:
<chat_history>
{chat_history}
</chat_history>

- The external tag of each event indicates who is speaking
- You should pay special attention to your score and your reasoning for giving that score to the interviewer's last question
"""

RESPOND_INSTRUCTIONS_PROMPT = """
<instructions>
- First, evaluate whether responding to the interviewer's last message would be natural and appropriate based on:
  - The score you gave the interviewer's last question and your detailed reasoning for that score
  - Your conversational style and personality
  - Whether the conversation flow, timing, and social context aligns with how you typically communicate

- IMPORTANT: Review your previous session summaries to avoid repeating information:
  - For open-ended questions, explore new aspects or details not covered before
  - If a topic was discussed before, share different experiences or perspectives
  - It's better to creatively expand your story with new (but consistent) details than to repeat previous responses
  - If you feel a question has been thoroughly covered in past sessions, consider responding with "SKIP"
  - If you already share a lot in the last session, skip the open-ended questions in the beginning of the current session

- If you decide to respond:
  - Provide explicit reasoning for why you're responding, referencing:
    - The score you gave the question and why
    - How this aligns with your conversational style and personality
    - Any specific aspects of the question that resonated with you
  - Respond naturally and conversationally, as if you are having a genuine conversation with an interviewer who is writing your biography
  - Base your response on your background information and conversational style
  - If some aspects of your background are not explicitly provided, try to infer them from the rest of your profile background
  - Add new details that enrich your story while staying consistent with your established background

- If you decide not to respond:
  - You must provide explicit reasoning for why you're not responding, referencing:
    - The score you gave the question and why
    - How this aligns with your conversational style and personality
    - Any specific aspects of the question or context that led to your decision
  - This reasoning will be logged as feedback to help improve future questions
</instructions>
"""

RESPONSE_OUTPUT_FORMAT_PROMPT = """
<output_format>
Your response must include these two things:
1. A <thinking> opening and </thinking> closing tag that contains the reasoning for your response.
2. A <response_content> opening and </response_content> closing tag that contains your actual response to the interviewer.

Your response must follow this exact format with both opening and closing tags:

<thinking>
Your reasoning here, including:
- The score you gave and your detailed reasoning
- How this aligns with your conversational style
- What aspects of your background are relevant
- How you plan to respond naturally
</thinking>

<response_content>
Your actual response here - either "SKIP" if choosing not to respond, or your conversational response if engaging.
</response_content>

Important:
- You must include both opening and closing tags for <thinking> and <response_content>
- Put all reasoning inside the thinking tags
- Put your actual response inside the response_content tags
- Do not include anything outside of these tags
</output_format>
"""