# AI Friend/ Biographer

The idea is to have a system that interacts with the user throughout multiple sessions, as an engaging friend, asks about their life stories, and writes them a memoir/autobiography.

# Main Components

## Agents

### Interviewer
- Primary agent that conducts interview sessions with users
- Maintains natural conversation flow and asks relevant questions
- Uses memory recall to maintain context across sessions
- Adapts questions based on user responses and session notes
- Tools: recall, respond_to_user, end_conversation

### Memory Manager
- Observes conversations and manages the user's memory bank
- Identifies and stores important information shared by users
- Updates session notes with relevant information
- Maintains metadata and importance scores for memories
- Tools: update_memory_bank, update_session_note

### Biographer
- Writes and maintains the user's biography
- Reviews interview sessions and updates biography sections
- Creates session notes for future interviews
- Manages biography structure and content
- Tools: recall, get_section, add_section, update_section

### UserAgent
- AI simulation of a user for testing purposes
- Maintains consistent responses based on a predefined profile
- Generates natural, conversational responses
- Useful for system testing and development

## Models and Data Structures

### Memory Bank
- Vector database storing user memories and information
- Supports semantic search for relevant memories
- Maintains metadata, importance scores, and timestamps
- Alternative implementation using NetworkX for graph-based storage (TODO: LightRAG?)
- Stores relationships between entities (people, places, events)

### Biography
- Hierarchical document structure
- Organized into sections and subsections
- Maintains version history and edit timestamps
- Supports different biography styles (chronological, thematic)

### Session Note
- Maintains structure for interview sessions
- Stores user information and session summaries
- Organizes questions by topics with hierarchical IDs
- Tracks notes and responses for each question
- Supports additional unstructured notes

## Processes

### Interview Session
- Orchestrates interaction between agents and user
- Manages message flow and participant subscriptions
- Maintains chat history and session state
- Coordinates between interviewer and memory manager
- Handles both real users and AI user agents

### Memory Update
- Continuous monitoring of conversations
- Identification of important information
- Storage in vector database with metadata
- Assignment of importance scores
- Update of session notes and questions

### Memory Retrieval
- Semantic search of stored memories
- Context-aware recall during interviews
- Support for specific entity queries
- Integration with interview flow
- Maintains conversation coherence


