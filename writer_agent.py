import os
import json
from openai import OpenAI
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from info_bank import InfoBank
import logging

logger = logging.getLogger(__name__)

class WriterAgent:
    def __init__(self, info_bank: InfoBank):
        self.info_bank = info_bank
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.chat_history: List[dict] = [
            {"role": "system", "content": "You are an experienced writer, skilled in crafting compelling autobiographies."}
        ]
        self.current_draft = ""

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
            
            # Ensure response is wrapped in XML if it isn't already
            if not ai_response.startswith('<?xml') and not ai_response.startswith('<'):
                ai_response = f"<response>\n{ai_response}\n</response>"
                
            self.chat_history.append({"role": "assistant", "content": ai_response})
            
            # Validate XML format
            try:
                ET.fromstring(ai_response)
                return ai_response
            except ET.ParseError:
                # If XML parsing fails, wrap the response in valid XML
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
    
    def explain_thinking(self) -> str:
        """Explains the writer's thought process"""
        thinking_prompt = f"""
        <task>Explain writing strategy</task>
        <info_bank_state>
        {self.info_bank.get_formatted_state()}
        </info_bank_state>
        <instructions>
        Explain your writing process:
        1. How you'll organize the information
        2. Key themes to emphasize
        3. Narrative structure planning
        4. Style and tone considerations
        
        Format your response in XML tags.
        </instructions>
        """
        return self.generate_response(thinking_prompt)
    
    def _explain_draft_updates(self) -> str:
        """Explains the draft update process"""
        update_prompt = f"""
        <task>Explain draft updates</task>
        <current_draft>{self.current_draft}</current_draft>
        <info_bank_state>
        {self.info_bank.get_formatted_state()}
        </info_bank_state>
        <instructions>
        Explain your update process:
        1. What new information you're incorporating
        2. How you're restructuring the narrative
        3. Specific improvements made
        4. Reasoning behind changes
        
        Format your response in XML tags.
        </instructions>
        """
        return self.generate_response(update_prompt)

    def update_draft(self, save_thinking: bool = False) -> None:
        logger.info("Updating autobiography draft")
        if save_thinking:
            return self._explain_draft_updates()
        
        info_bank_schema = self.info_bank.get_schema()
        
        update_prompt = f"""
        <task>Update autobiography draft</task>
        <current_draft>
        {self.current_draft}
        </current_draft>
        <info_bank_schema>
        {info_bank_schema}
        </info_bank_schema>
        <instructions>
        1. Review the current draft and the updated info bank schema.
        2. Incorporate new information from the info bank into the draft.
        3. Ensure a coherent narrative flow and consistent style.
        4. Output the updated draft in the following XML format:
        <updated_draft>
            <chapter title="Chapter Title">
                <content>Chapter content...</content>
            </chapter>
            <!-- Repeat for each chapter -->
        </updated_draft>
        </instructions>
        """

        update_response = self.generate_response(update_prompt)
        root = ET.fromstring(update_response)

        updated_draft = ""
        for chapter in root.findall(".//chapter"):
            title = chapter.get("title", "Untitled Chapter")
            content = chapter.find("content").text if chapter.find("content") is not None else ""
            updated_draft += f"\n\n{title}\n\n{content}"

        self.current_draft = updated_draft.strip()
        logger.info("Draft updated successfully")
        return self.current_draft

    def finalize_autobiography(self, save_thinking: bool = False) -> str:
        """Finalizes autobiography with optional explanation of changes"""
        logger.info("Finalizing autobiography")
        
        if save_thinking:
            thinking_prompt = f"""
            <task>Explain final revisions</task>
            <current_draft>
            {self.current_draft}
            </current_draft>
            <instructions>
            Explain your finalization process:
            1. What final improvements you're making
            2. How you're ensuring narrative coherence
            3. Your approach to introduction and conclusion
            4. Final style and tone adjustments
            
            Format your response in XML tags.
            <thinking>
                <process>Your explanation here</process>
                <improvements>List specific improvements</improvements>
                <structure>Explain structural changes</structure>
                <style>Explain style adjustments</style>
            </thinking>
            </instructions>
            """
            return self.generate_response(thinking_prompt)
        
        finalize_prompt = f"""
        <task>Write final autobiography</task>
        <info_bank_state>
        {self.info_bank.get_formatted_state()}
        </info_bank_state>
        <instructions>
        Based on all the information collected, write a complete autobiography.
        Your response MUST be formatted as valid XML like this:
        <final_autobiography>
            <chapter title="Introduction">
                <content>
                    [Detailed introduction content here]
                </content>
            </chapter>
            <chapter title="Early Life">
                <content>
                    [Detailed early life content here]
                </content>
            </chapter>
            <chapter title="Conclusion">
                <content>
                    [Detailed conclusion content here]
                </content>
            </chapter>
        </final_autobiography>
        
        Make sure each chapter has substantial content within the content tags.
        </instructions>
        """

        try:
            final_response = self.generate_response(finalize_prompt)
            
            # Try to parse the XML response
            try:
                root = ET.fromstring(final_response)
                
                # Extract chapters and format them
                final_text = ""
                for chapter in root.findall(".//chapter"):
                    title = chapter.get("title", "Untitled Chapter")
                    # Look for content within the content tags
                    content_elem = chapter.find("content")
                    content = content_elem.text.strip() if content_elem is not None and content_elem.text else "No content available"
                    final_text += f"\n\n{title}\n\n{content}"
                
                return final_text.strip()
                
            except ET.ParseError as e:
                error_message = f"""
                <error>
                    <message>Failed to parse autobiography XML: {str(e)}</message>
                    <raw_response>{final_response}</raw_response>
                </error>
                """
                logger.error(error_message)
                return error_message
                
        except Exception as e:
            error_message = f"An error occurred while generating the autobiography: {str(e)}"
            logger.error(error_message)
            return f"""
            <error>
                <message>{error_message}</message>
            </error>
            """