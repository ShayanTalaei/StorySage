import logging
from pathlib import Path
from datetime import datetime
from interviewer_agent import InterviewerAgent
from writer_agent import WriterAgent
from info_bank import InfoBank
import os
import shutil

os.environ['OPENAI_API_KEY'] = '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'

def cleanup_outputs():
    """Clean up all previous output files and directories"""
    if os.path.exists('demo_outputs'):
        shutil.rmtree('demo_outputs')
    # if os.path.exists('demo_output.log'):
    #     os.remove('demo_output.log')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('demo_output.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DemoRunner:
    def __init__(self):
        self.info_bank = InfoBank()
        self.interviewer = InterviewerAgent(self.info_bank)
        self.writer = WriterAgent(self.info_bank)
        self.output_dir = Path('demo_outputs')
        self.output_dir.mkdir(exist_ok=True)

    def save_snapshot(self, filename: str, content: str):
        """Save a snapshot of the current state to a file"""
        filepath = self.output_dir / f"{filename}_{datetime.now().strftime('%H%M%S')}.txt"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Saved snapshot to {filepath}")

    def run_demo(self):
        logger.info("\n=== Starting Autobiography Generation Demo ===\n")
        
        # Simulate a focused interview session with 3 questions
        demo_qa = [
            {
                "question": "Could you tell me about a pivotal moment in your career that changed your perspective?",
                "answer": "When I started my first startup, we failed within a year. This taught me that failure isn't the end - it's a stepping stone. I learned more from that failure than from any success."
            },
            {
                "question": "How did that experience influence your future decisions?",
                "answer": "I became more calculated in my risks, but also more resilient. I started my second company with clearer vision and better planning."
            },
            {
                "question": "What advice would you give to others based on these experiences?",
                "answer": "Don't fear failure, but learn from it. Document your mistakes, analyze them, and use them as building blocks for future success."
            }
        ]

        # Part 1: Interview Process
        logger.info("=== Part 1: Interview Process ===")
        
        for i, qa in enumerate(demo_qa, 1):
            logger.info(f"\nQuestion {i}: {qa['question']}")
            logger.info(f"User Response: {qa['answer']}")
            
            # Show interviewer's thinking process
            logger.info("\nInterviewer's Thinking Process:")
            thinking_process = self.interviewer.explain_thinking(qa["question"])
            self.save_snapshot(f"q{i}_interviewer_thinking", thinking_process)
            print(thinking_process)  # Display in console
            
            # Show response analysis
            logger.info("\nAnalyzing Response:")
            response_analysis = self.interviewer.analyze_and_store_response(
                qa["question"], 
                qa["answer"],
                save_analysis=True
            )
            self.save_snapshot(f"q{i}_response_analysis", response_analysis)
            print(response_analysis)  # Display in console
            
            # Show updated info bank state
            logger.info("\nUpdated Information Bank State:")
            info_bank_state = self.info_bank.get_formatted_state()
            self.save_snapshot(f"q{i}_info_bank_state", info_bank_state)
            print(info_bank_state)  # Display in console

        # Part 2: Writing Process
        logger.info("\n=== Part 2: Writing Process ===\n")
        
        # Show writer's initial thinking
        logger.info("Writer's Initial Thinking Process:")
        writing_process = self.writer.explain_thinking()
        self.save_snapshot("writer_thinking", writing_process)
        print(writing_process)  # Display in console
        
        # Show draft creation process
        logger.info("\nCreating Initial Draft:")
        initial_draft = self.writer.update_draft(save_thinking=True)
        self.save_snapshot("initial_draft", initial_draft)
        print(initial_draft)  # Display in console
        
        # Show final version creation
        logger.info("\nCreating Final Version:")
        
        # First show the thinking process
        logger.info("Final Revision Thinking Process:")
        final_thinking = self.writer.finalize_autobiography(save_thinking=True)
        self.save_snapshot("final_thinking", final_thinking)
        print(final_thinking)  # Display in console
        
        # Then show the actual final autobiography
        logger.info("\nFinal Autobiography:")
        final_version = self.writer.finalize_autobiography(save_thinking=False)
        self.save_snapshot("final_autobiography", final_version)
        print(final_version)  # Display in console
        
        logger.info("\n=== Demo Completed ===")

def main():
    # Clean up previous outputs
    cleanup_outputs()
    
    # Run the demo
    demo = DemoRunner()
    demo.run_demo()

if __name__ == "__main__":
    main()
