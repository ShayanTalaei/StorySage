from typing import Type, Dict, Any
from langchain_core.tools import BaseTool
from pydantic import BaseModel
import xml.etree.ElementTree as ET
import json

GREEN = '\033[92m'
ORANGE = '\033[93m'
RESET = '\033[0m'
RED = '\033[91m'

def format_tool_as_xml_v2(tool: Type[BaseTool]) -> str:
    """
    Format a tool as XML with a different structure, including newlines for better readability.
    
    :param tool: A class that inherits from BaseTool
    :return: XML-formatted string describing the tool
    """
    lines = []
    lines.append(f"<{tool.name}>")
    lines.append(f"  <description>")
    lines.append(f"    {tool.description}")
    lines.append(f"  </description>")
    
    # Add arguments if present
    if tool.args_schema and issubclass(tool.args_schema, BaseModel):
        lines.append(f"  <arguments>")
        for field_name, field in tool.args_schema.model_fields.items():
            lines.append(f"    <{field_name}>")
            lines.append(f"      <type>{field.annotation.__name__}</type>")
            if field.description:
                lines.append(f"      <description>")
                lines.append(f"        {field.description}")
                lines.append(f"      </description>")
            lines.append(f"    </{field_name}>")
        lines.append(f"  </arguments>")
    
    lines.append(f"</{tool.name}>")
    
    return "\n".join(lines)

def parse_tool_calls(xml_string: str) -> Dict[str, Any]:
    """
    Parse XML tool calls in the format:
    <tool_calls>
        <tool_name>
            <arg_name>value</arg_name>
            ...
        </tool_name>
        ...
    </tool_calls>
    """
    root = ET.fromstring(xml_string)
    result = []
    
    # Iterate through each direct child of tool_calls (each is a tool name)
    for tool_element in root:
        tool_name = tool_element.tag
        arguments = {}
        
        # Each child of the tool element is an argument
        for arg in tool_element:
            try:
                # Try to parse as JSON
                arguments[arg.tag] = json.loads(arg.text)
            except (json.JSONDecodeError, TypeError):
                # If not valid JSON or None, treat as a simple string
                arguments[arg.tag] = arg.text.strip() if arg.text else ""
                
        result.append({
            'tool_name': tool_name,
            'arguments': arguments
        })
    
    return result

def call_tool_from_xml(tool_calls_xml_string: str, available_tools: Dict[str, BaseTool]) -> str:
    parsed_calls = parse_tool_calls(tool_calls_xml_string)
    print(f"{ORANGE}Parsed calls:\n{parsed_calls}{RESET}")
    results = []
    
    for call in parsed_calls:
        tool_name = call['tool_name']
        arguments = call['arguments']
        
        if tool_name not in available_tools:
            results.append(f"Error: Tool '{tool_name}' not found.")
            continue
        
        tool = available_tools[tool_name]
        try:
            result = tool._run(**arguments)
            results.append(f"Tool '{tool_name}' executed successfully. Result: {result}")
        except Exception as e:
            print(f"Error calling tool '{tool_name}': {str(e)}")
            results.append(f"Error calling tool '{tool_name}': {str(e)}")
    
    return "\n".join(results)

# # Example usage:
# if __name__ == "__main__":
#     from src.workflow.toolkits.sql.insert_row_tool import InsertRowTool
#     from src.workflow.toolkits.python.python_repl_tool import PythonREPLTool
    
#     insert_row_xml = format_tool_as_xml(InsertRowTool)
#     print(insert_row_xml)
#     print("\n" + "="*50 + "\n")
#     python_repl_xml = format_tool_as_xml(PythonREPLTool)
#     print(python_repl_xml)

# # Example usage:
# if __name__ == "__main__":
#     from src.workflow.toolkits.sql.insert_row_tool import InsertRowTool
#     from src.workflow.toolkits.python.python_repl_tool import PythonREPLTool

#     # Set up available tools
#     available_tools = {
#         "InsertRowIntoDB": InsertRowTool(db_path="path/to/your/database.db"),
#         "Python_REPL": PythonREPLTool()
#     }

#     # Example XML with comma in list item
#     xml_call = """
#     <tool_call>
#       <tool_name>InsertRowIntoDB</tool_name>
#       <arguments>
#         <table_name>users</table_name>
#         <data>["John Doe, Jr.",30,"john@example.com"]</data>
#       </arguments>
#     </tool_call>
#     """

#     result = call_tool_from_xml(xml_call, available_tools)
#     print(result)

#     # Example with Python_REPL
#     xml_call_python = """
#     <tool_call>
#       <tool_name>Python_REPL</tool_name>
#       <arguments>
#         <python_code>
# print("Hello, world!")
# data = ["item1", "item2, with comma", "item3"]
# print(f"The data is: {data}")
#         </python_code>
#       </arguments>
#     </tool_call>
#     """

#     result_python = call_tool_from_xml(xml_call_python, available_tools)
#     print(result_python)
