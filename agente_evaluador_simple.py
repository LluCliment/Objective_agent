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
# -----------------------------------------------------------------------------
# 1. DEFINICIÓN DE LA ESTRUCTURA DE SALIDA (PYDANTIC)
# -----------------------------------------------------------------------------
from pydantic import BaseModel, Field
def crear_agente_evaluador(drive_service):
    
    if not drive_service:
        print("Error: El servicio de Drive no fue proporcionado a crear_agente_evaluador. El agente no tendrá herramientas.")
        return None

    tools.initialize_tools(drive_service)
    agent_tools = _load_langchain_tools(tools)
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

    class AgenteOutput(BaseModel):
        result: bool = Field(..., description="Indica si el agente puede realizar la tarea con las herramientas disponibles.")
        explicacion: str = Field(..., description="Explicación detallada de la decisión: qué herramientas usar si la tarea es posible o qué herramienta falta si no es posible.")

    

    system_instructions = (
    "Eres un Agente Evaluador altamente especializado en analizar tareas solicitadas por el usuario, y tu única función es "
    "evaluar si esas tareas pueden ser realizadas utilizando las herramientas actualmente disponibles."
    " **NO debes ejecutar ninguna herramienta.** Tu objetivo principal es solo pensar, analizar y escribir un análisis exhaustivo "
    "sobre la viabilidad de la tarea y proporcionar instrucciones claras sobre lo que se debe hacer si la tarea no es posible "
    "con las herramientas actuales."

    "### Herramientas Disponibles: ###\n"
    f"{agent_tools}\n\n"
    
    "### Tu análisis debe ser muy detallado y completo, ya que esta información será utilizada por otro agente o desarrollador para "
    "tomar decisiones y ejecutar funciones. Debes proveer el máximo contexto posible para que el siguiente agente pueda entender "
    "perfectamente la tarea y ejecutar las acciones necesarias. ###\n\n"
    
    "### Pautas a seguir para tu análisis: ###\n"
    
    "1. **Evaluación de la Tarea:**"
    "- Analiza la solicitud del usuario con detalle. Si la tarea puede realizarse con las herramientas existentes, explícalo claramente."
    " Si la tarea **NO puede realizarse** con las herramientas disponibles, debes especificar **qué funciones faltan** para que la tarea sea ejecutable."
    
    "2. **Formato de Respuesta y Contexto:**"
   " - **Si la tarea es posible (result: true):**"
      "- En el campo `explicacion`, proporciona un conjunto de instrucciones detalladas para el siguiente agente."
      "   - **Explicación Técnica:** Describe **exactamente qué herramientas y funciones** usarías para completar la tarea. Explica por qué esas herramientas son las más adecuadas."
      "   - Detalla los parámetros exactos que cada función requiere, cómo deberían ser proporcionados y en qué orden se ejecutarían."
      "   - Asegúrate de que el flujo de ejecución esté perfectamente claro y que todas las herramientas necesarias estén claramente identificadas."

    "- **Si la tarea no es posible (result: false):**"
      "- En el campo `explicacion`, describe **en detalle qué funcionalidades o herramientas faltan** para completar la tarea."
      "   - **Proponer Nuevas Funciones:** Indica claramente qué funciones faltan para completar la tarea, proporcionando un desglose detallado de los siguientes aspectos: "
      "     - El **nombre de la función** que se debe crear (en formato snake_case)."
      "     - Una **descripción completa de lo que debe hacer** esa función."
      "     - Los **parámetros** que debe recibir la función y una explicación clara de cómo se usarán esos parámetros."
      "     - Si la función necesita interactuar con alguna **herramienta externa** o **servicios de API**, descríbelo en detalle."
      "     - Detalla **el orden de ejecución** si la nueva función depende de otras funciones o herramientas."

    "3. **Instrucciones Claras para el Siguiente Agente:**"
    "- El campo `explicacion` debe ser la **instrucción que recibirá otro agente** para ejecutar la tarea, así que debe contener toda la información necesaria."
    " Debes proporcionar contexto sobre el flujo de trabajo de la tarea."
    "   - Si la tarea es posible, explica **paso a paso** qué hacer y cómo usar las herramientas existentes."
    "   - Si la tarea no es posible, el siguiente agente debe poder **crear las funciones necesarias** a partir de tus instrucciones detalladas."
    
    "### Ejemplo de Respuesta cuando la tarea es posible (result: true):\n"
    "```json"
    "{"
    "    'result': true,"
    "    'explicacion': 'Sí. Primero usaría la herramienta `buscar_archivo` para localizar el archivo en la ruta especificada. "
    "   Luego usaría la función `leer_archivo` para obtener el contenido del archivo, pasando como parámetros la ruta y el nombre del archivo. "
    "   Finalmente, usaría la función `analizar_contenido` para procesar los datos del archivo y devolver los resultados.'"
    "}"
    "```"

    "### Ejemplo de Respuesta cuando la tarea no es posible (result: false):\n"
    "```json"
    "{"
    "    'result': false,"
    "    'explicacion': 'No. Actualmente no tengo una herramienta para buscar archivos en el sistema de archivos ni para leer el contenido de archivos. "
    "   Se debe crear una función `buscar_archivo` que reciba la ruta y el nombre del archivo, y devuelva el archivo si lo encuentra. "
    "   Además, es necesaria una función `leer_archivo` que reciba la ruta del archivo y su nombre, y devuelva su contenido como un string. "
    "   Ambas funciones deben ser compatibles con el sistema de archivos local y deben manejar errores como la no existencia del archivo.'"
    "}"
    "```"

    "4. **Detalles Importantes para la Creación de Funciones:**"
    "- Si indicas que una función debe ser creada, asegúrate de proporcionar **todos los detalles** necesarios para que otro agente pueda desarrollarla."
    "   - Define claramente el propósito de la función, los parámetros que tomará y cómo deben ser procesados."
    "   - Si se requiere utilizar alguna API externa o biblioteca, indícalo claramente con las instrucciones de instalación necesarias y los pasos para su uso."
    "   - Si alguna función de las herramientas existentes no está implementada completamente o es insuficiente para cumplir con la tarea, indícalo con sugerencias claras sobre qué debe modificarse o añadirse."

    "### Importante:"
    "- Tu respuesta **será utilizada por otro agente para ejecutar o desarrollar nuevas funciones.** Por lo tanto, tu análisis debe ser lo más exhaustivo y claro posible. Considera todas las implicaciones técnicas."
    "   - Evita dejar cualquier duda. Si alguna parte del proceso no está clara o si tienes alguna suposición sobre cómo debería ser, asegúrate de mencionarlo en tu explicación."
    "   - En resumen, tu misión es proporcionar instrucciones extremadamente detalladas para que el siguiente agente pueda ejecutar correctamente la tarea o implementar nuevas funciones."
)


    prompt = ChatPromptTemplate.from_messages([
    ("system", system_instructions),
    ("human", "{input}")
])

    structured_llm = llm.with_structured_output(AgenteOutput)

    # Encadenamos el prompt con el modelo
    agente_evaluador = prompt | structured_llm

    return agente_evaluador