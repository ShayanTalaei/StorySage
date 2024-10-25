import os
import json
from openai import OpenAI
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

class BiographyAgent:
    def __init__(self):
        # A list to store the conversation history, starting with a system message.
        self.chat_history: List[Dict[str, str]] = [
            {"role": "system", "content": "You are an experienced biographer, skilled in interviewing and crafting compelling life stories."}
        ]
        # A dictionary to store collected information
        self.info_bank: Dict[str, Any] = {}
        # A list to store the questions that will be asked during the interview
        self.question_bank: List[str] = []
        # A counter to track the number of interactions with the user
        self.interaction_count = 0

    def store_information(self, path: str, info: Any) -> None:
        """Store information in the info bank."""
        keys = path.split('/')
        current = self.info_bank
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = info

    def retrieve_information(self, path: str) -> Any:
        """Retrieve information from the info bank."""
        keys = path.split('/')
        current = self.info_bank
        for key in keys:
            if key not in current:
                return None
            current = current[key]
        return current

    def get_info_bank_schema(self) -> Dict[str, Any]:
        """Return the current structure of the info bank."""
        return self.info_bank

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the chat history specifying the role (e.g., "human" or "assistant") and the content of the message."""
        self.chat_history.append({"role": role, "content": content})

    def generate_response(self, user_input: str) -> str:
        """Generate a response based on the current context and user input using GPT-4o."""
        self.add_message("human", user_input)
        
        try:
            response = OpenAI.ChatCompletion.create(
                model="gpt-4o",  
                messages=self.chat_history,
                max_tokens=150,  
                n=1,
                stop=None,
                temperature=0.7,
            )
            
            ai_response = response.choices[0].message['content'].strip()
            self.add_message("assistant", ai_response)
            return ai_response
        
        except Exception as e:
            error_message = f"An error occurred while generating the response: {str(e)}"
            print(error_message)
            return error_message

    def collect_initial_information(self) -> None:
        """Collect initial information from the user about their autobiography goals."""
        questions = [
            "What are your main motivations for writing this autobiography?",
            "What key life events would you like to focus on?",
            "Are there specific themes (e.g., career, family, personal growth) you want to emphasize?",
            "What time period of your life do you want to cover in this autobiography?",
            "Are there any specific achievements or challenges you want to highlight?"
        ]
        for question in questions:
            response = self.generate_response(question)
            self.store_information(f"initial_info/{question}", response)

    def develop_question_plan(self) -> None:
        """Develop a personalized question plan based on initial information."""
        initial_info = self.retrieve_information("initial_info")
        
        # Generate a prompt for GPT to create personalized questions
        prompt = "Based on the following initial information, generate 10 personalized and insightful questions for an autobiography interview:\n\n"
        for question, answer in initial_info.items():
            prompt += f"{question}\nAnswer: {answer}\n\n"
        prompt += "Please provide 10 questions, one per line, without numbering."
        
        # Generate questions using GPT
        response = self.generate_response(prompt)
        
        # Split the response into individual questions
        generated_questions = response.strip().split('\n')
    
        # Add generated questions to the question bank
        self.question_bank = generated_questions
    
        # Add some general questions to ensure coverage
        general_questions = [
            "Can you tell me about your earliest childhood memory?",
            "Who were the most influential people in your early life?",
            "What was a major turning point in your life and how did it affect you?",
            "What do you consider your greatest achievement and why?",
            "If you could change one decision in your life, what would it be and why?"
        ]
        
        self.question_bank.extend(general_questions)


    def conduct_interview(self) -> None:
        """Conduct the interview using adaptive questioning."""
        asked_questions = set()
        follow_up_questions = []

        while len(asked_questions) < len(self.question_bank) or follow_up_questions:
            # Choose the next question
            if follow_up_questions:
                question = follow_up_questions.pop(0)
            else:
                question = next(q for q in self.question_bank if q not in asked_questions)
            
            asked_questions.add(question)

            # Ask the question and get user response
            print(f"Interviewer: {question}")
            user_response = input("You: ")

            # Store the response
            self.store_information(f"interview_responses/{question}", user_response)

            # Analyze the response and generate follow-up questions
            analysis_prompt = f"""
            <task>Analyze interview response</task>
            <question>{question}</question>
            <response>{user_response}</response>
            <instructions>
            1. Identify any gaps or inconsistencies in the response.
            2. Suggest up to 2 follow-up questions to clarify or expand on the response.
            3. Determine if any themes or areas of interest have emerged that warrant further exploration.
            4. Output your analysis in the following XML format:
            <analysis>
                <gaps_and_inconsistencies>List any gaps or inconsistencies here</gaps_and_inconsistencies>
                <follow_up_questions>
                    <question>Follow-up question 1</question>
                    <question>Follow-up question 2</question>
                </follow_up_questions>
                <emerging_themes>List any emerging themes or areas of interest</emerging_themes>
            </analysis>
            </instructions>
            """

            analysis_response = self.generate_response(analysis_prompt)

            # Parse the analysis response
            root = ET.fromstring(analysis_response)
            
            # Add follow-up questions
            for follow_up in root.findall(".//follow_up_questions/question"):
                if follow_up.text and follow_up.text.strip():
                    follow_up_questions.append(follow_up.text.strip())

            # Store emerging themes
            emerging_themes = root.find("emerging_themes")
            if emerging_themes is not None and emerging_themes.text:
                self.store_information("emerging_themes", emerging_themes.text.strip())

            # Adapt question bank based on emerging themes
            if emerging_themes is not None and emerging_themes.text:
                theme_question_prompt = f"""
                <task>Generate theme-based questions</task>
                <emerging_themes>{emerging_themes.text}</emerging_themes>
                <instructions>
                Based on the emerging themes, generate 2 new interview questions that explore these areas further.
                Provide the questions in the following XML format:
                <new_questions>
                    <question>New question 1</question>
                    <question>New question 2</question>
                </new_questions>
                </instructions>
                """
                theme_questions_response = self.generate_response(theme_question_prompt)
                theme_questions_root = ET.fromstring(theme_questions_response)
                for new_question in theme_questions_root.findall(".//new_questions/question"):
                    if new_question.text and new_question.text.strip():
                        self.question_bank.append(new_question.text.strip())

        print("Interview completed.")

    def build_story(self) -> str:
        """Build the autobiography based on collected information."""
        # Step 1: Compile and categorize information
        categorization_prompt = f"""
        <task>Categorize autobiography information</task>
        <collected_info>
        {json.dumps(self.info_bank, indent=2)}
        </collected_info>
        <instructions>
        Analyze the collected information and categorize it into the following sections:
        1. Early Life
        2. Education and Career
        3. Relationships and Family
        4. Challenges and Obstacles
        5. Achievements and Milestones
        6. Personal Growth and Lessons Learned
        7. Future Aspirations
        
        For each category, provide a brief summary of key points and events.
        Output your categorization in the following XML format:
        <categorized_info>
            <category name="Early Life">
                <summary>Key points about early life...</summary>
            </category>
            <!-- Repeat for each category -->
        </categorized_info>
        </instructions>
        """
        categorized_info = self.generate_response(categorization_prompt)
        
        # Step 2: Refine narrative flow
        narrative_prompt = f"""
        <task>Refine autobiography narrative</task>
        <categorized_info>
        {categorized_info}
        </categorized_info>
        <instructions>
        Based on the categorized information, create a coherent narrative for the autobiography.
        Ensure a smooth flow between sections, highlighting connections between key life events.
        Output your narrative in the following XML format:
        <autobiography>
            <chapter title="Chapter 1: The Early Years">
                <content>Narrative content for early life...</content>
            </chapter>
            <!-- Repeat for each chapter -->
        </autobiography>
        </instructions>
        """
        initial_narrative = self.generate_response(narrative_prompt)
        
        # Step 3: Review and revise with user
        review_cycles = 3  # Number of review cycles
        current_narrative = initial_narrative
        
        for cycle in range(review_cycles):
            print(f"\nReview Cycle {cycle + 1}:")
            print("Please review the current version of your autobiography:")
            print(current_narrative)
            
            user_feedback = input("Please provide any feedback or suggestions for changes: ")
            
            if not user_feedback.strip():
                print("No changes requested. Moving to the next step.")
                break
            
            revision_prompt = f"""
            <task>Revise autobiography based on user feedback</task>
            <current_narrative>
            {current_narrative}
            </current_narrative>
            <user_feedback>
            {user_feedback}
            </user_feedback>
            <instructions>
            Revise the autobiography based on the user's feedback.
            Ensure that the changes align with the user's vision while maintaining narrative coherence.
            Output the revised autobiography in the same XML format as before.
            </instructions>
            """
            current_narrative = self.generate_response(revision_prompt)
        
        # Final formatting
        root = ET.fromstring(current_narrative)
        final_autobiography = ""
        
        for chapter in root.findall(".//chapter"):
            title = chapter.get("title", "Untitled Chapter")
            content = chapter.find("content").text if chapter.find("content") is not None else ""
            final_autobiography += f"\n\n{title}\n\n{content}"
        
        return final_autobiography.strip()

    def finalize_autobiography(self) -> str:
        """Finalize the autobiography with user review and edits."""
        draft = self.build_story()
        
        # Review the draft with the user
        print("Here's the draft of your autobiography. Please review it carefully.")
        print(draft)
        
        user_feedback = input("Please provide any final feedback, changes, or preferences for style and tone: ")
        
        if user_feedback.strip():
            # Incorporate user feedback and make final edits
            edit_prompt = f"""
            <task>Finalize autobiography</task>
            <draft>
            {draft}
            </draft>
            <user_feedback>
            {user_feedback}
            </user_feedback>
            <instructions>
            1. Incorporate the user's final feedback into the autobiography.
            2. Ensure consistency in style and tone throughout the document.
            3. Make any necessary edits to improve flow, clarity, and impact.
            4. Maintain the overall structure and key events of the life story.
            5. Output the final version in the following XML format:
            <final_autobiography>
                <chapter title="Chapter Title">
                    <content>Chapter content...</content>
                </chapter>
                <!-- Repeat for each chapter -->
            </final_autobiography>
            </instructions>
            """
            final_version_xml = self.generate_response(edit_prompt)
            
            # Parse the XML and format the final version
            root = ET.fromstring(final_version_xml)
            final_version = ""
            for chapter in root.findall(".//chapter"):
                title = chapter.get("title", "Untitled Chapter")
                content = chapter.find("content").text if chapter.find("content") is not None else ""
                final_version += f"\n\n{title}\n\n{content}"
            
            final_version = final_version.strip()
        else:
            final_version = draft
        
        # Ask user for desired output format
        print("\nHow would you like to receive your finalized autobiography?")
        print("1. Plain text")
        print("2. PDF document")
        print("3. Word document")
        format_choice = input("Enter the number of your choice: ")
        
        if format_choice == "1":
            # Deliver as plain text
            with open("autobiography.txt", "w", encoding="utf-8") as f:
                f.write(final_version)
            print("Your autobiography has been saved as 'autobiography.txt'.")
        elif format_choice == "2":
            # Deliver as PDF (requires additional library, e.g., reportlab)
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.platypus import SimpleDocTemplate, Paragraph
                from reportlab.lib.styles import getSampleStyleSheet

                doc = SimpleDocTemplate("autobiography.pdf", pagesize=letter)
                styles = getSampleStyleSheet()
                story = [Paragraph(line, styles["Normal"]) for line in final_version.split("\n")]
                doc.build(story)
                print("Your autobiography has been saved as 'autobiography.pdf'.")
            except ImportError:
                print("PDF generation requires the 'reportlab' library. Please install it or choose another format.")
        elif format_choice == "3":
            # Deliver as Word document (requires additional library, e.g., python-docx)
            try:
                from docx import Document

                doc = Document()
                for line in final_version.split("\n"):
                    if line.strip():
                        doc.add_paragraph(line)
                doc.save("autobiography.docx")
                print("Your autobiography has been saved as 'autobiography.docx'.")
            except ImportError:
                print("Word document generation requires the 'python-docx' library. Please install it or choose another format.")
        else:
            print("Invalid choice. The autobiography will be delivered as plain text.")
            with open("autobiography.txt", "w", encoding="utf-8") as f:
                f.write(final_version)
            print("Your autobiography has been saved as 'autobiography.txt'.")
        
        return "Your finalized autobiography has been created and saved in your chosen format."

    def run_autobiography_process(self) -> str:
        """Run the complete autobiography creation process."""
        print("Welcome to the Autobiography Creation Process!")
        
        # Step 1: Collect initial information
        print("\nStep 1: Collecting initial information...")
        self.collect_initial_information()
        
        # Step 2: Develop question plan
        print("\nStep 2: Developing personalized question plan...")
        self.develop_question_plan()
        
        # Step 3: Conduct interview
        print("\nStep 3: Conducting the interview...")
        self.conduct_interview()
        
        # Step 4: Build the story
        print("\nStep 4: Building your life story...")
        draft = self.build_story()
        
        # Step 5: Finalize the autobiography
        print("\nStep 5: Finalizing your autobiography...")
        final_result = self.finalize_autobiography()
        
        print("\nAutobiography creation process completed!")
        return final_result

# Example usage
agent = BiographyAgent()
final_autobiography = agent.run_autobiography_process()
print(final_autobiography)
