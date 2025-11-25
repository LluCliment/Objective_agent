import streamlit as st
import os
import shutil # Importamos shutil para inyectarlo en el entorno de ejecución
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from typing import Dict, Any

# --- 1. CONFIGURACIÓN INICIAL Y ESTADO ---
# ADVERTENCIA DE SEGURIDAD: Nunca uses la clave API hardcodeada en un entorno de producción o público.
# Es solo para testeo rápido local.
GEMINI_API_KEY_LOCAL = ''


# Usamos la memoria de sesión de Streamlit como estado global
if 'global_state' not in st.session_state:
    st.session_state.global_state = {
        "latest_extracted_text": None,
        "latest_output_path": None,
        "chat_history": []
    }

GLOBAL_STATE = st.session_state.global_state

# --- 2. HERRAMIENTA ÚNICA: Generador y Ejecutor de Código ---

class CodeInput(BaseModel):
    """Define el esquema de entrada de la herramienta para el LLM."""
    code_to_execute: str = Field(
        description="El código Python completo que realiza la tarea. Debe usar las variables globales GLOBAL_STATE, las librerías 'os' y 'shutil' y la función 'print_to_chat'."
    )
    expected_output_var: str = Field(
        description="El nombre de la variable local en el código Python cuyo valor final debe ser retornado (ej. 'extracted_data' o 'final_path')."
    )

@tool(args_schema=CodeInput)
def CodeGeneratorAndExecutor(code_to_execute: str, expected_output_var: str) -> str:
    """
    Herramienta única que genera (escribe) y ejecuta código Python dinámicamente. 
    Debe ser usada para todas las operaciones de manejo de archivos o manipulación de datos.
    """
    global GLOBAL_STATE
    
    # 1. Definir entorno de ejecución local (controlado)
    local_env = {
        # Función para reportar mensajes al chat
        "print_to_chat": lambda msg: GLOBAL_STATE["chat_history"].append({"role": "tool_output", "content": msg}),
        "GLOBAL_STATE": GLOBAL_STATE,
        "os": os,
        "shutil": shutil, # <--- ¡CORRECCIÓN CLAVE! Ahora shutil está disponible.
        # SIMULACIÓN de lectura de DOCX para que funcione sin librerías externas
        "docx_reader_sim": lambda path: "Contenido de Proyecciones Financieras: 2025: +12%; 2026: +9%." 
    }
    
    try:
        GLOBAL_STATE["chat_history"].append({"role": "agent_thought", "content": "Generando y ejecutando código..."})
        
        # 2. Ejecutar el código generado por el LLM
        exec(code_to_execute, local_env)
        
        # 3. Obtener el resultado final de la variable esperada
        # Buscamos la variable en el entorno local después de la ejecución
        result = local_env.get(expected_output_var, f"Error: Variable '{expected_output_var}' no encontrada después de la ejecución.")
        
        # Convertir listas o estructuras complejas a string para la salida de LangChain
        if not isinstance(result, str):
             result = str(result)
        
        # 4. Actualizar el estado global con el resultado si aplica
        if expected_output_var == 'final_path' and isinstance(result, str):
             GLOBAL_STATE["latest_output_path"] = result
        if expected_output_var == 'extracted_data' and isinstance(result, str):
             GLOBAL_STATE["latest_extracted_text"] = result
        
        return f"Código ejecutado con éxito. El LLM puede continuar. Resultado de '{expected_output_var}': {result}"
    
    except Exception as e:
        # Reportar errores de ejecución al LLM para que pueda auto-corregirse
        return f"ERROR DE EJECUCIÓN del código: {str(e)}. El LLM debe revisar el código Python generado y re-planificar."

# --- 3. CREACIÓN DEL AGENTE GENERATIVO (LangChain + Gemini) ---

@st.cache_resource
def get_agent_executor():
    """Inicializa el agente de LangChain una sola vez."""
    
    # 1. Autenticación (usando la clave local pegada)
    api_key = GEMINI_API_KEY_LOCAL
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        temperature=0.0,
        google_api_key=api_key 
    )

    # 2. Definir la herramienta
    tools = [CodeGeneratorAndExecutor] 
    
    # 3. Prompt System/Template para el Agente
    template = """
    Eres un Agente Orquestador Generativo altamente eficiente. Tu objetivo es ayudar al usuario a realizar tareas
    complejas de manejo de archivos o datos.

    **Herramientas disponibles:**
    {tools}
    
    **Instrucciones clave:**
    1. Siempre sigue el patrón ReAct: Thought, Action, Observation.
    2. En tu 'Thought', describe el código Python que planeas generar para usar la única herramienta disponible: {tool_names}.
    3. Utiliza la herramienta CodeGeneratorAndExecutor para todas las acciones externas (lectura/escritura).
    
    **Estado Actual (para tu referencia. Úsalo en tus 'Thoughts'):**
    - Último texto extraído: {latest_extracted_text}
    - Última ruta de archivo: {latest_output_path}

    **Historial de Acción-Observación del Agente (No lo modifiques):**
    {agent_scratchpad}
    
    **Conversación (para contexto):**
    {chat_history}

    **Tarea del usuario:** {input}
    """

    prompt = PromptTemplate.from_template(template)
    
    # 4. Crear el Agente (LangChain inyecta automáticamente 'tools', 'tool_names' y 'agent_scratchpad')
    agent = create_react_agent(llm, tools, prompt)
    
    # handle_parsing_errors=True permite al LLM intentar auto-corregir el formato si falla
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)
    return agent_executor

# --- 4. INTERFAZ STREAMLIT ---

st.title("🤖 Agente Generativo (LangChain + Gemini) con Chatbot")
st.caption("El agente genera código Python en tiempo real para resolver tus peticiones.")

# Inicializar el AgentExecutor
executor = get_agent_executor()

# Función para ejecutar el ciclo del agente y actualizar el chat
def handle_user_input():
    user_input = st.session_state.user_input
    if not user_input:
        return

    GLOBAL_STATE["chat_history"].append({"role": "user", "content": user_input})

    # Construir el contexto para el prompt
    context = {
        "latest_extracted_text": GLOBAL_STATE["latest_extracted_text"][:50] + "..." if GLOBAL_STATE["latest_extracted_text"] else "None",
        "latest_output_path": GLOBAL_STATE["latest_output_path"] if GLOBAL_STATE["latest_output_path"] else "None",
        "chat_history": "\n".join([f"[{m['role'].upper()}]: {m['content']}" for m in GLOBAL_STATE["chat_history"][-5:]]),
        "input": user_input
    }

    try:
        # Ejecución del agente (el LLM piensa y usa la herramienta CodeGeneratorAndExecutor)
        with st.spinner("El Agente Generativo está pensando y ejecutando código..."):
            final_output = executor.invoke(context)
        
        agent_response = final_output.get("output", "No se pudo generar una respuesta final.")
        GLOBAL_STATE["chat_history"].append({"role": "agent", "content": agent_response})
        
    except Exception as e:
        error_msg = f"ERROR CRÍTICO: Fallo al invocar el agente. ¿Está la GEMINI_API_KEY configurada correctamente? Detalle: {e}"
        GLOBAL_STATE["chat_history"].append({"role": "system_error", "content": error_msg})
        st.error(error_msg)

    # Limpiar el input de usuario
    st.session_state.user_input = ""

# Mostrar el historial de chat
for message in GLOBAL_STATE["chat_history"]:
    role = message["role"]
    content = message["content"]
    
    if role == "user":
        st.chat_message("user").write(content)
    elif role == "agent":
        st.chat_message("assistant").markdown(content)
    elif role == "tool_output":
        # Usamos código para mostrar la salida de la herramienta de forma clara
        st.chat_message("assistant").code(content, language='text')
    elif role == "agent_thought":
        st.chat_message("assistant").info(f"**[Procesando]** {content}")
    elif role == "system_error":
        st.chat_message("system").error(content)


# Entrada del usuario en la interfaz de chat
with st.container():
    st.text_input(
        "Escribe tu petición o corrección:", 
        key="user_input", 
        on_change=handle_user_input
    )

st.sidebar.title("Instrucciones")
st.sidebar.markdown(
    """
    **El Agente usará la herramienta `CodeGeneratorAndExecutor` para escribir código Python que cumpla tu petición.**
    
    ### Ejemplo de Interacción (2 Pasos):
    
    1. **Petición Inicial:**
        > `Quiero que cojas el documento 'informe_ventas.docx' que está en C:/datos/temporales, extraigas la sección de 'Proyecciones Financieras' y crees un archivo nuevo llamado 'proyecciones.txt' con el texto extraído.`
        
    2. **Corrección (Feedback):**
        > `Olvidé mencionar que no lo pongas en .txt, sino que lo guardes como 'proyecciones_finales.md' y añadas el texto 'Revisar Urgente' al inicio.`
        
    """
)
st.sidebar.info("El LLM usado es **Gemini 2.5 Flash** (modelo gratuito en el nivel de desarrollo).")

