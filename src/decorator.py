import inspect

def tool_parser(func):
    """
    Parse a function's name, docstring, and parameter types.

    Returns:
        dict: A dictionary containing:
            - name: Function name
            - description: Docstring of the function
            - parameters: A dictionary with parameter names and their types
    """
    function_parameters = inspect.signature(func)

    # Extract parameter types (default to 'any' if not annotated)
    properties = {
        name: {
            "type": param.annotation.__name__ if param.annotation != inspect._empty else "any"
        }
        for name, param in function_parameters.parameters.items()
    }

    properties = {
        "propreties": properties
    }

    function_info = {
        "name": func.__name__,
        "description": func.__doc__,
        "parameters": properties
    }

    return function_info


class Tool:
    """
    Wraps a function and stores its metadata for tool calling agents.
    """
    def __init__(self, name, func: callable, func_information):
        self.name = name
        self.func = func
        self.func_information = func_information

    def __str__(self):
        # Return string representation of the tool metadata
        return str(self.func_information)

    def run(self, **kwarg):
        # Execute the tool with keyword arguments
        try:
            return self.func(**kwarg)
        except TypeError as e:
            raise TypeError(f"[{self.name}] Argument mismatch: {str(e)}") from e
        except Exception as e:
            raise Exception(f"[{self.name}] Unexpected error during execution: {str(e)}") from e


def tool(func):
    """
    Decorator to convert a function into a Tool object.
    Automatically extracts function metadata via `tool_parser`.
    """
    def wrapper():
        return Tool(tool_parser(func)['name'], func, tool_parser(func))
    
    return wrapper()
