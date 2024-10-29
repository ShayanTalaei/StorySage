import os
import json
from openai import OpenAI
import logging
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from interviewer_agent import InterviewerAgent
from writer_agent import WriterAgent
from info_bank import InfoBank

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BiographyAgent:
    def __init__(self):
        self.info_bank = InfoBank()
        self.interviewer = InterviewerAgent(self.info_bank)
        self.writer = WriterAgent(self.info_bank)

    def run_autobiography_process(self) -> str:
        # print("Welcome to the Autobiography Creation Process!")
        logger.info("Starting the Autobiography Creation Process")
        
        while not self.interviewer.is_interview_complete():
            # print("\nConducting interview session...")
            logger.info("Conducting interview session...")
            self.interviewer.conduct_interview_session()
            
            # print("\nUpdating autobiography draft...")
            logger.info("Updating autobiography draft...")
            self.writer.update_draft()
        
        # print("\nFinalizing autobiography...")
        logger.info("Finalizing autobiography...")
        final_autobiography = self.writer.finalize_autobiography()
        
        # print("\nAutobiography creation process completed!")
        logger.info("Autobiography creation process completed!")
        return final_autobiography


# agent = BiographyAgent()
# final_autobiography = agent.run_autobiography_process()
# print(final_autobiography)

# Demo function
def run_demo():
    logger.info("Starting demo of the Autobiography Creation Process")
    agent = BiographyAgent()
    final_autobiography = agent.run_autobiography_process()
    
    logger.info("Final Autobiography:")
    print(final_autobiography)

if __name__ == "__main__":
    run_demo()

