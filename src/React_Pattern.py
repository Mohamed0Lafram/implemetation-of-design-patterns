from decorator import tool
from Utils.utils import llm
import re
import json 


default_prompt =  """
You are a function calling AI model. You operate by running a loop with the following steps: Thought, Action, Observation.
You are provided with function signatures within <tools></tools> XML tags.
You may call one or more functions to assist with the user query. Don' make assumptions about what values to plug
into functions. Pay special attention to the properties 'types'. You should use those types as in a Python dict.

For each function call return a json object with function name and arguments within <tool_call></tool_call> XML tags as follows:

<tool_call>
{"name": <function-name>,"arguments": <args-dict>}
</tool_call>

Here are the available tools / actions:

<tools> 
%5
</tools>

Example session:

<question>What's the current temperature in Madrid?</question>
<thought>I need to get the current weather in Madrid</thought>
<tool_call>{"name": "get_current_weather","arguments": {"location": "Madrid", "unit": "celsius"}, "id": 0}</tool_call>

You will be called again with this:

<observation>{0: {"temperature": 25, "unit": "celsius"}}</observation>

You then output:

<response>The current temperature in Madrid is 25 degrees Celsius</response>

Additional constraints:

- If the user asks you something unrelated to any of the tools above, answer freely enclosing your answer with <response></response> tags.
"""

class React_Agent:
    def __init__(self, Tools):
        """Initialize tool agent with a list of decorated tool functions."""
        self.chat_history = []
        self.tools = {}
        for t in Tools:
            tool_object = tool(t)
            self.tools[tool_object.name] = tool_object
        self.system_prompt = self.__adjust_system_prompt(default_prompt, self.tools)


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
                'role': 'system',
                'content': f'<observation>{result}</observation>'
            })

        return tool_results
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
    
    def run(self,prompt,iteration_max=6):
        iteration = 0
        qyery_history = []
        qyery_history.append(self.system_prompt)

        #save the prompt into the chat history
        user_prompt = {
                    'role' : 'user',
                    'content' : prompt
                    }
        self.chat_history.append(user_prompt)
        qyery_history.append(user_prompt)
        #if the llm response has a <response></response> tag then return the reponse else stay in the loop where you are thinking and action

        while True:
            iteration += 1
            #ask the llm
            llm_responce = llm(str(qyery_history))

            #save the responce 
            qyery_history.append(
                    {
                    'role' : 'assistant',
                    'content' : llm_responce
                })
            #
            final_response = re.search(r"<response>(.*?)</response>", llm_responce, re.DOTALL)
            if final_response or iteration == iteration_max:
                result = {
                    'role' : 'assistant',
                    'content' : llm_responce
                    }
                self.chat_history.append(result)
                return result
            else : 
                #call the tools 
                tool_result = self.__functions_call(llm_responce)

                #add tools result into the qyry history
                for result in tool_result:
                    qyery_history.append(result)
