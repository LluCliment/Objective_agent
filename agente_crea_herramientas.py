import inspect
import tools
from typing import List

# Importaciones de LangChain y Pydantic
from langchain.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnableLambda
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent
from pydantic import BaseModel, Field
from cargar_herramientas import _load_langchain_tools
from pydantic import BaseModel, Field
# -----------------------------------------------------------------------------
# 1. DEFINICIÓN DE LA ESTRUCTURA DE SALIDA (PYDANTIC)
# -----------------------------------------------------------------------------
