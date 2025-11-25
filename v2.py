import os
from dotenv import load_dotenv

# --- Carga de la API Key de forma segura ---
load_dotenv()

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Importaciones de LangChain ---
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain import hub
from langchain.memory import ConversationBufferMemory

# Alcance completo para permitir todas las acciones necesarias
SCOPES = ["https://www.googleapis.com/auth/drive"]

# --- Funciones de Autenticación y API ---

def authenticate_google_drive():
    """Autentica con la API de Google Drive y retorna el objeto 'service'."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    
    try:
        service = build("drive", "v3", credentials=creds)
        return service
    except HttpError as error:
        print(f"Ocurrió un error al construir el servicio de Drive: {error}")
        return None

# --- HERRAMIENTAS PARA EL AGENTE DE LANGCHAIN ---

DRIVE_SERVICE = authenticate_google_drive()

def list_files(query: str = "") -> str:
    """Lista archivos en Google Drive basándose en un query de la API."""
    if not DRIVE_SERVICE:
        return "Error: El servicio de Google Drive no está autenticado."
    list_params = {
        "pageSize": 25,
        "fields": "nextPageToken, files(id, name)"
    }
    if query:
        list_params['q'] = query

    try:
        results = DRIVE_SERVICE.files().list(**list_params).execute()
        items = results.get("files", [])
        if not items:
            return "No se encontraron archivos que coincidan con la búsqueda."
        
        file_list = [(item["name"], item["id"]) for item in items]
        return f"Archivos encontrados: {file_list}"
    except HttpError as error:
        return f"Ocurrió un error al listar archivos: {error}"

def move_to_trash(file_id: str) -> str:
    """
    Mueve un archivo a la papelera de Google Drive. El archivo puede ser recuperado.
    Esta es la opción de borrado por defecto y más segura.
    Requiere el ID del archivo (file_id).
    """
    if not DRIVE_SERVICE:
        return "Error: El servicio de Google Drive no está autenticado."
    try:
        body = {'trashed': True}
        DRIVE_SERVICE.files().update(fileId=file_id, body=body).execute()
        return f"Archivo con ID '{file_id}' movido a la papelera exitosamente."
    except HttpError as error:
        return f"Ocurrió un error al mover el archivo a la papelera: {error}"

def delete_permanently(file_id: str) -> str:
    """
    Elimina un archivo de forma PERMANENTE e IRRECUPERABLE.
    Esta acción se salta la papelera y no se puede deshacer.
    Solo debe usarse cuando el usuario lo pida explícitamente (ej: 'para siempre', 'permanentemente').
    Requiere el ID del archivo (file_id).
    """
    if not DRIVE_SERVICE:
        return "Error: El servicio de Google Drive no está autenticado."
    try:
        DRIVE_SERVICE.files().delete(fileId=file_id).execute()
        return f"Archivo con ID '{file_id}' eliminado permanentemente."
    except HttpError as error:
        if error.resp.status == 404:
            return f"Error: No se encontró ningún archivo con el ID '{file_id}'."
        return f"Ocurrió un error en la eliminación permanente: {error}"

def create_file(file_name: str) -> str:
    """Crea un nuevo documento de Google Docs vacío en Google Drive."""
    if not DRIVE_SERVICE:
        return "Error: El servicio de Google Drive no está autenticado."
    try:
        file_metadata = {"name": file_name, "mimeType": "application/vnd.google-apps.document"}
        file = DRIVE_SERVICE.files().create(body=file_metadata, fields="id, name").execute()
        return f"Archivo '{file.get('name')}' creado con éxito. ID: {file.get('id')}"
    except HttpError as error:
        return f"Ocurrió un error al crear el archivo: {error}"

# --- CONFIGURACIÓN DEL AGENTE LANGCHAIN ---

def run_agent():
    tools = [
        Tool(
            name="list_files",
            func=list_files,
            description=(
                "Útil para buscar y listar archivos en Google Drive para encontrar sus nombres y IDs. "
                "Si el usuario solo pregunta qué archivos tiene, llama a esta función sin input. "
                "Si el usuario quiere filtrar, el input DEBE SER UNA ÚNICA CADENA DE TEXTO que sea un query de búsqueda válido para la API de Google Drive. "
                "Ejemplos de input para filtrar: \"name = 'Mi Documento'\" o \"mimeType = 'application/vnd.google-apps.spreadsheet'\"."
            ),
        ),
        Tool(
            name="move_to_trash",
            func=move_to_trash,
            description="Útil para borrar un archivo enviándolo a la papelera. Es la opción preferida y segura si el usuario solo dice 'borra' o 'elimina'. Requiere el ID del archivo (file_id).",
        ),
        Tool(
            name="delete_permanently",
            func=delete_permanently,
            description="Útil para borrar un archivo de forma PERMANENTE. Solo se debe usar si el usuario lo pide explícitamente con palabras como 'permanentemente', 'para siempre', 'del todo'. Requiere el ID del archivo (file_id).",
        ),
        Tool(
            name="create_file",
            func=create_file,
            description="Útil para crear un nuevo documento de Google Docs. Requiere el nombre del archivo (file_name).",
        ),
    ]

    # Usando el modelo que solicitaste
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    
    prompt_template = hub.pull("hwchase17/react-chat")

    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

    agent = create_react_agent(llm, tools, prompt_template)

    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True, 
        handle_parsing_errors=True,
        memory=memory
    )

    print("Agente de Google Drive (con borrado dual y memoria) iniciado. Escribe 'salir' para terminar.")
    while True:
        prompt = input("¿Qué te gustaría hacer en Google Drive?: ")
        if prompt.lower() == 'salir':
            break
        
        try:
            result = agent_executor.invoke({"input": prompt})
            
            print("\nRespuesta del Agente:")
            print(result["output"])
            print("-" * 30)
        except Exception as e:
            print(f"\nHa ocurrido un error durante la ejecución del agente: {e}")
            print("Por favor, intenta reformular la pregunta.")
            print("-" * 30)


if __name__ == "__main__":
    if DRIVE_SERVICE:
        run_agent()
    else:
        print("No se pudo iniciar el agente debido a un fallo en la autenticación con Google Drive.")