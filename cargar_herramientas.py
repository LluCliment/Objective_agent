from langchain.tools import Tool
from typing import List
import inspect

def _load_langchain_tools(module) -> List[Tool]:
    """Carga funciones con docstrings del módulo tools.py como objetos Tool de LangChain."""
    loaded_tools = []
    for name, func in inspect.getmembers(module, inspect.isfunction):
        if func.__doc__ and name not in ["initialize_tools", "_get_folder_id_from_path"]:
            tool_object = Tool(
                name=name, 
                func=func, 
                description=func.__doc__.strip()
            )
            loaded_tools.append(tool_object)
    return loaded_tools