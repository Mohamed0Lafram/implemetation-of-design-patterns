import re
import json
from decorator import tool
from Utils.utils import llm

# Default system prompt template to guide the LLM on how to use tools
default_prompt = '''
        You are a function calling AI model. You are provided with function signatures within <tools></tools> XML tags. 
        You may call one or more functions to assist with the user query. Don't make assumptions about what values to plug 
        into functions. Pay special attention to the properties 'types'. You should use those types as in a Python dict. 
        For each function call return a json object with function name and arguments within <tool_call></tool_call> ,ypu can call multiple tools if you need to,your awnser should contain only the tools calls as follows:

        <tool_call>
        {"name": <function-name>,"arguments": <args-dict>}
        </tool_call> 

        Here are the available tools:

        <tools>
        %5
        </tools>
        if you cant call any tool awnser with only this string "NO_TOOL_NEDDED".
'''

class tool_agent:
    def __init__(self, Tools):
        """Initialize tool agent with a list of decorated tool functions."""
        self.chat_history = []
        self.tools = {}
        for t in Tools:
            tool_object = tool(t)
            self.tools[tool_object.name] = tool_object
        self.system_prompt = self.__adjust_system_prompt(default_prompt, self.tools)

    def __adjust_system_prompt(self, default_prompt, avaliable_tools):
        """
        Insert all function signatures into the default system prompt.
        Returns the full system prompt as a dict with role and content.
        """
        all_tools_info = ''
        for t in avaliable_tools:
            all_tools_info += str(avaliable_tools[t].func_information) + '\n'
        system_prompt = default_prompt.replace('%5', all_tools_info)
        return {
            'role': 'system',
            'content': system_prompt
        }

    def __functions_call(self, llm_response):
        """
        Parse the tool call(s) from LLM response, execute each function,
        and return their results as a list of message dicts.
        """

        matchs = re.findall(r"<tool_call>(.*?)</tool_call>", llm_response, re.DOTALL)
        if not matchs:
            raise ValueError("NO TOOL CALL FROM THE LLM")

        tool_calls = [json.loads(M.strip()) for M in matchs]
        llm_calls_dict = {call['name']: call['arguments'] for call in tool_calls}

        tool_results = []
        for func_name in llm_calls_dict:
            print(f'-- TOOL CALL : {func_name.upper()} --')
            result = self.tools[func_name].run(**llm_calls_dict[func_name])
            tool_results.append({
                'role': 'tool_result',
                'content': result
            })

        return tool_results

    def run(self, prompt):
        """
        Main entry point to handle user input.
        Decides whether tools are needed, executes tools if required,
        and generates the final response using the LLM.
        """
        user_prompt = {
            'role': 'user',
            'content': prompt
        }
        self.chat_history.append(user_prompt)

        final_system_prompt = {
            'role': 'system',
            'content': 'use the tools results to awnser this question '
        }

        # Ask LLM to choose tool(s) if needed
        llm_tool_calls = llm(str(self.system_prompt) + str(user_prompt))
        print(f'llm tool calls : {llm_tool_calls}')
        if llm_tool_calls.strip().upper() == 'NO_TOOL_NEDDED':
            # No tool needed, get direct response from LLM
            llm_call = llm(str(user_prompt))
            response = {
                'role': 'assistant',
                'content': llm_call
            }
        else:
            # Tool(s) needed, execute them and get response
            tool_results = self.__functions_call(llm_tool_calls)
            qyery = str(final_system_prompt) + str(user_prompt) + str(tool_results)
            llm_call = llm(qyery)
            response = {
                'role': 'assistant',
                'content': llm_call
            }

        self.chat_history.append(response)
        return response
