import os
import json
from openai import OpenAI
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from info_bank import InfoBank
import logging

logger = logging.getLogger(__name__)

class InterviewerAgent:
    def __init__(self, info_bank: InfoBank):
        self.info_bank = info_bank
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.chat_history: List[dict] = [
            {"role": "system", "content": "You are an experienced interviewer, skilled in conducting in-depth interviews for autobiographies."}
        ]
        self.question_bank: List[str] = []
        self.session_count = 0

    def generate_response(self, prompt: str) -> str:
        self.chat_history.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self.chat_history,
                max_tokens=1000,
                temperature=0.7,
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Ensure response is wrapped in a root XML element if it isn't already
            if not ai_response.startswith('<?xml') and not ai_response.startswith('<'):
                ai_response = f"<response>\n{ai_response}\n</response>"
                
            self.chat_history.append({"role": "assistant", "content": ai_response})
            logger.debug(f"AI Response: {ai_response}")
            
            # Validate XML format
            try:
                ET.fromstring(ai_response)
                return ai_response
            except ET.ParseError:
                # If XML parsing fails, return a properly formatted XML
                return f"""
                <response>
                    <content>{ai_response}</content>
                </response>
                """
                
        except Exception as e:
            error_message = f"An error occurred while generating the response: {str(e)}"
            logger.error(error_message)
            return f"""
            <response>
                <error>{error_message}</error>
            </response>
            """

    def develop_question_plan(self) -> None:
        logger.info("Developing question plan")
        prompt = """
        <task>Develop interview questions</task>
        <context>
        This is for an autobiography interview. We need to create a comprehensive set of questions
        that will help us gather detailed information about the person's life.
        </context>
        <instructions>
        Generate 20 open-ended questions that cover various aspects of a person's life, including:
        1. Early life and childhood
        2. Education and career
        3. Relationships and family
        4. Major life events and turning points
        5. Achievements and challenges
        6. Personal growth and life lessons
        7. Future aspirations
        
        Provide the questions in the following XML format:
        <questions>
            <question>Your question here</question>
            <!-- Repeat for each question -->
        </questions>
        </instructions>
        """
        
        response = self.generate_response(prompt)
        root = ET.fromstring(response)
        self.question_bank = [q.text for q in root.findall(".//question") if q.text]
        logger.info(f"Generated {len(self.question_bank)} questions for the interview")

    def conduct_interview_session(self) -> None:
        self.session_count += 1
        print(f"Interview Session {self.session_count}")
        logger.info(f"Starting Interview Session {self.session_count}")

        if not self.question_bank:
            self.develop_question_plan()
        
        # Simulated user responses for the demo
        simulated_responses = [
        "I was born in a small town in 1980. My childhood was pretty typical, with loving parents and two siblings.",
        "I attended the local public schools and then went to State University for my degree in Computer Science.",
        "My first job was at a tech startup. It was challenging but exciting, and I learned a lot about the industry.",
        "I met my spouse at a friend's wedding. We hit it off immediately and got married two years later.",
        "One of my biggest achievements was launching my own software company. It was a huge risk, but it paid off."
        ]

        for i in range(5):  # Ask 5 questions per session
            if not self.question_bank:
                break

            question = self.question_bank.pop(0)
            logger.info(f"Interviewer: {question}")
            print(f"Interviewer: {question}")
            # user_response = input("You: ")
            user_response = simulated_responses[i] #For demo purposes
            logger.info(f"User: {user_response}")

            self.analyze_and_store_response(question, user_response)

        logger.info(f"Completed Interview Session {self.session_count}")

    def explain_thinking(self, question: str) -> str:
        """Explains the agent's thinking process for asking a question"""
        thinking_prompt = f"""
        <task>Explain interview strategy</task>
        <question>{question}</question>
        <instructions>
        Explain your thinking process:
        1. Why this question is important
        2. What information you hope to gather
        3. How you plan to use this information
        4. Potential follow-up directions
        
        Format your response in XML tags.
        </instructions>
        """
        return self.generate_response(thinking_prompt)

    def analyze_and_store_response(self, question: str, response: str, save_analysis: bool = False) -> str:
        logger.info("Analyzing and storing response")
        analysis_prompt = f"""
        <task>Analyze interview response</task>
        <question>{question}</question>
        <response>{response}</response>
        <instructions>
        1. Identify the main topics or themes in the response.
        2. Suggest up to 2 follow-up questions to gather more information.
        3. Determine which section(s) of the autobiography this information belongs to.
        4. Output your analysis in the following XML format:
        <analysis>
            <themes>
                <theme>Theme 1</theme>
                <theme>Theme 2</theme>
            </themes>
            <follow_up_questions>
                <question>Follow-up question 1</question>
                <question>Follow-up question 2</question>
            </follow_up_questions>
            <sections>
                <section>Section name 1</section>
                <section>Section name 2</section>
            </sections>
        </analysis>
        """

        analysis_response = self.generate_response(analysis_prompt)
        
        try:
            # Try to parse the XML response
            root = ET.fromstring(analysis_response)
            
            # Store the response in the info bank
            for section in root.findall(".//sections/section"):
                if section is not None and section.text:
                    self.info_bank.add_section(section.text, response)
                    logger.info(f"Stored response in section: {section.text}")

            # Add follow-up questions to the question bank
            for follow_up in root.findall(".//follow_up_questions/question"):
                if follow_up is not None and follow_up.text:
                    self.question_bank.append(follow_up.text)
                    logger.info(f"Added follow-up question: {follow_up.text}")

            return analysis_response if save_analysis else ""
            
        except ET.ParseError as e:
            error_message = f"""
            <error>
                <message>Failed to parse XML response: {str(e)}</message>
                <raw_response>{analysis_response}</raw_response>
            </error>
            """
            logger.error(error_message)
            return error_message

    def is_interview_complete(self) -> bool:
        # For simplicity, we say that the interview is complete after 5 sessions
        return self.session_count >= 5
