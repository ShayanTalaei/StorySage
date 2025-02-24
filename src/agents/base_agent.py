# Python standard library imports
from datetime import datetime
from typing import Dict, List
import asyncio
from functools import partial

# Third-party imports
from dotenv import load_dotenv
from pydantic import BaseModel

# Local imports
from utils.llm.engines import get_engine, invoke_engine
from utils.llm.xml_formatter import format_tool_as_xml_v2, parse_tool_calls
from utils.logger.session_logger import SessionLogger

# Load environment variables
load_dotenv(override=True)


class BaseAgent:
    """Base class for all agents. All agents inherits from this class."""

    class Event(BaseModel):
        """Event class for all events. All events inherits from this class."""
        sender: str
        tag: str
        content: str
        timestamp: datetime
    
    def __init__(self, name: str, description: str, config: Dict):
        self.name = name
        self.description = description
        self.config = config
        
        # Initialize the LLM engine
        self.engine = get_engine(model_name="gpt-4o",
                                 temperature=0.0)
        self.tools = {}

        # Each agent has an event stream. 
        # This contains all the events that have been sent to and by the agent.
        self.event_stream: list[BaseAgent.Event] = []
        
    def workout(self):
        pass

    def _call_engine(self, prompt: str):
        '''Calls the LLM engine with the given prompt.'''
        for attempt in range(10):
            try:
                output = invoke_engine(self.engine, prompt)
                return output
            except Exception as e:
                SessionLogger.log_to_file(
                    "execution_log", 
                    f"({self.name}) Failed to invoke the chain "
                    f"{attempt + 1} times.\n{type(e)} <{e}>", 
                    log_level="error"
                )
        raise e
    
    async def call_engine_async(self, prompt: str) -> str:
        '''Asynchronously call the LLM engine with the given prompt.'''
        # Run call_engine in a thread pool since it's a blocking operation
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            partial(self._call_engine, prompt)
        )
        
    def add_event(self, sender: str, tag: str, content: str):
        '''Adds an event to the event stream. 
        Args:
            sender: The sender of the event (interviewer, user, system)
            tag: The tag of the event 
                (interviewer_response, user_response, system_response, etc.)
            content: The content of the event.
        '''
        self.event_stream.append(BaseAgent.Event(sender=sender, 
                                                 tag=tag,
                                                 content=content, 
                                                 timestamp=datetime.now()))
        # Log the event to the interviewer event stream file
        SessionLogger.log_to_file(f"{self.name}_event_stream", 
                                  f"({self.name}) Sender: {sender}, "
                                  f"Tag: {tag}\nContent: {content}")
        
    def get_event_stream_str(self, filter: List[Dict[str, str]] = None, as_list: bool = False):
        '''Gets the event stream that passes the filter. 
        Important for ensuring that the event stream only 
        contains events that are relevant to the agent.
        
        Args:
            filter: A list of dictionaries with sender and tag keys 
            to filter the events.
            as_list: Whether to return the events as a list of strings.
        '''
        events = []
        for event in self.event_stream:
            if self._passes_filter(event, filter):
                event_str = f"<{event.sender}>\n{event.content}\n</{event.sender}>"
                events.append(event_str)
        
        if as_list:
            return events
        return "\n".join(events)
    
    def _passes_filter(self, event: Event, filter: List[Dict[str, str]]):
        '''Helper function to check if an event passes the filter.
        
        Args:
            event: The event to check.
            filter: A list of dictionaries with sender 
            and tag keys to filter the events.
        '''
        if filter:
            for filter_item in filter:
                if not filter_item.get("sender", None) \
                      or event.sender == filter_item["sender"]:
                    if not filter_item.get("tag", None) \
                          or event.tag == filter_item["tag"]:
                        return True
            return False
        return True
    
    def get_tools_description(self, selected_tools: List[str] = None):
        '''Gets the tools description as a string.
        
        Args:
            selected_tools: A list of tool names to include a description for.
        '''
        if selected_tools:
            return "\n".join([format_tool_as_xml_v2(tool) \
                               for tool in self.tools.values() \
                               if tool.name in selected_tools])
        else:
            return "\n".join([format_tool_as_xml_v2(tool) \
                               for tool in self.tools.values()])
    
    def handle_tool_calls(self, response: str):
        """Synchronous tool handling for non-I/O bound operations"""
        result = None
        if "<tool_calls>" in response:
            tool_calls_start = response.find("<tool_calls>")
            tool_calls_end = response.find("</tool_calls>")
            if tool_calls_start != -1 and tool_calls_end != -1:
                tool_calls_xml = response[
                    tool_calls_start:tool_calls_end + len("</tool_calls>")
                ]
                
                parsed_calls = parse_tool_calls(tool_calls_xml)
                for call in parsed_calls:
                    try:
                        tool_name = call['tool_name']
                        arguments = call['arguments']
                        tool = self.tools[tool_name]
                        
                        # Only handle sync tools here
                        if not asyncio.iscoroutinefunction(tool._run):
                            result = tool._run(**arguments)
                            self.add_event(sender="system", 
                                           tag=tool_name, 
                                           content=result)
                        else:
                            raise ValueError(
                                f"Tool {tool_name} is async and "
                                "should use handle_tool_calls_async"
                            )
                    except Exception as e:
                        self.add_event(sender="system", tag="error", 
                                       content=f"Error calling tool " \
                                       f"{tool_name}: {e}")
                        SessionLogger.log_to_file(
                            "execution_log", 
                            f"({self.name}) Error calling tool " \
                            f"{tool_name}: {e}", 
                            log_level="error"
                        )
        return result

    async def handle_tool_calls_async(self, response: str):
        """Asynchronous tool handling for I/O bound operations"""
        result = None
        if "<tool_calls>" in response:
            tool_calls_start = response.find("<tool_calls>")
            tool_calls_end = response.find("</tool_calls>")
            if tool_calls_start != -1 and tool_calls_end != -1:
                tool_calls_xml = response[
                    tool_calls_start:tool_calls_end + len("</tool_calls>")
                ]
                
                parsed_calls = parse_tool_calls(tool_calls_xml)
                for call in parsed_calls:
                    try:
                        tool_name = call['tool_name']
                        arguments = call['arguments']
                        tool = self.tools[tool_name]
                        
                        # Handle both sync and async tools
                        if asyncio.iscoroutinefunction(tool._run):
                            result = await tool._run(**arguments)
                        else:
                            result = tool._run(**arguments)
                        self.add_event(sender="system", 
                                       tag=tool_name, content=result)
                    except Exception as e:
                        self.add_event(sender="system", tag="error",
                                       content=f"Error calling tool " \
                                       f"{tool_name}: {e}")
                        SessionLogger.log_to_file(
                            "execution_log", 
                            f"({self.name}) Error calling tool " \
                            f"{tool_name}: {e}", 
                            log_level="error"
                        )
        return result
