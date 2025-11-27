# tools.py
# Este archivo contiene las funciones que el agente puede usar.
# CUALQUIER FUNCIÓN CON UN DOCSTRING SERÁ CARGADA AUTOMÁTICamente COMO UNA HERRAMIENTA.

import io
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

DRIVE_SERVICE = None

def initialize_tools(service):
    # Esta función no tiene docstring, por lo que no será cargada como herramienta.
    global DRIVE_SERVICE
    DRIVE_SERVICE = service
    print("Herramientas inicializadas con el servicio de Drive.")

def _get_folder_id_from_path(path: str) -> str:
    # Función auxiliar sin docstring para que no sea cargada como herramienta.
    if not path or path == '/':
        return 'root'
    parts = path.strip('/').split('/')
    current_folder_id = 'root'
    for part in parts:
        query = f"mimeType = 'application/vnd.google-apps.folder' and name = '{part}' and '{current_folder_id}' in parents and trashed = false"
        results = DRIVE_SERVICE.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])
        if not items:
            raise FileNotFoundError(f"No se pudo encontrar la carpeta '{part}' dentro de la ruta '{path}'")
        current_folder_id = items[0]['id']
    return current_folder_id

# --- HERRAMIENTAS DETECTABLES ---
def get_file_id_by_name(file_name: str, folder_path: str = None) -> str:
    """
    Busca un archivo por su nombre exacto y devuelve su ID. 
    Si se encuentra más de un archivo con el mismo nombre, devuelve el primero.
    
    Parámetros:
    - file_name (obligatorio): El nombre exacto del archivo a buscar.
    - folder_path (opcional): La ruta de la carpeta donde buscar. Si no se especifica, busca en todo 'Mi Unidad'.
    """
    if not DRIVE_SERVICE:
        return "Error: El servicio de Google Drive no está autenticado."
    
    q_parts = [f"name = '{file_name}'", "trashed = false"]

    if folder_path:
        try:
            folder_id = _get_folder_id_from_path(folder_path)
            q_parts.append(f"'{folder_id}' in parents")
        except FileNotFoundError as e:
            return str(e)

    final_query = " and ".join(q_parts)
    
    # Solo necesitamos buscar el primer resultado (pageSize=1)
    list_params = {"pageSize": 1, "fields": "files(id, name)", "q": final_query}

    try:
        results = DRIVE_SERVICE.files().list(**list_params).execute()
        items = results.get("files", [])
        
        if not items:
            return f"Error: No se encontró ningún archivo llamado '{file_name}'."
        
        file_id = items[0]['id']
        file_name_found = items[0]['name']
        
        return f"Éxito: ID del archivo '{file_name_found}' es: {file_id}"
        
    except HttpError as error:
        return f"Ocurrió un error al buscar el archivo: {error}"
    
def list_files(file_type: str = None, folder_path: str = None, query: str = "") -> str:
    """
    Busca y lista archivos en Google Drive. Permite filtrar por tipo de archivo, por una ruta de carpeta, o con un query avanzado.
    
    Parámetros:
    - file_type (opcional): Filtra por un tipo de archivo común. Valores: 'spreadsheet', 'document', 'presentation', 'folder'.
    - folder_path (opcional): La ruta de la carpeta donde buscar, ej: 'Facturas/2024'. Si no se especifica, busca en todo 'Mi Unidad'.
    - query (opcional): Un query avanzado para la API de Google Drive, ej: "name contains 'informe'".
    """
    if not DRIVE_SERVICE:
        return "Error: El servicio de Google Drive no está autenticado."
    
    mime_types = {
        'spreadsheet': "mimeType='application/vnd.google-apps.spreadsheet'",
        'document': "mimeType='application/vnd.google-apps.document'",
        'presentation': "mimeType='application/vnd.google-apps.presentation'",
        'folder': "mimeType='application/vnd.google-apps.folder'"
    }
    q_parts = ["trashed = false"]
    if file_type and file_type in mime_types:
        q_parts.append(mime_types[file_type])
    
    if folder_path:
        try:
            folder_id = _get_folder_id_from_path(folder_path)
            q_parts.append(f"'{folder_id}' in parents")
        except FileNotFoundError as e:
            return str(e)

    if query:
        q_parts.append(query)
        
    final_query = " and ".join(q_parts)
    list_params = {"pageSize": 25, "fields": "nextPageToken, files(id, name)", "q": final_query}

    try:
        results = DRIVE_SERVICE.files().list(**list_params).execute()
        items = results.get("files", [])
        if not items:
            return "No se encontraron archivos que coincidan con los criterios de búsqueda."
        
        file_list = [(item["name"], item["id"]) for item in items]
        return f"Archivos encontrados: {file_list}"
    except HttpError as error:
        return f"Ocurrió un error al listar archivos: {error}"

def move_to_trash(file_id: str) -> str:
    """
    Mueve un archivo a la papelera. Es reversible.
    El input para esta herramienta debe ser únicamente el string del ID del archivo (file_id), sin el nombre del parámetro.
    Ejemplo CORRECTO de input: 'ID_DEL_ARCHIVO'.
    Ejemplo INCORRECTO de input: "file_id='ID_DEL_ARCHIVO'".
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
    Elimina un archivo de forma PERMANENTE. No se puede deshacer. Usar con extrema precaución.
    El input para esta herramienta debe ser únicamente el string del ID del archivo (file_id), sin el nombre del parámetro.
    Ejemplo CORRECTO de input: 'ID_DEL_ARCHIVO'.
    Ejemplo INCORRECTO de input: "file_id='ID_DEL_ARCHIVO'".
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

def create_file(file_name: str, folder_path: str = None) -> str:
    """
    Crea un nuevo documento de Google Docs vacío con un nombre específico.
    Opcionalmente, se puede especificar una 'folder_path' (ej: 'Proyectos/Activos') para crearlo dentro de una carpeta.
    """
    if not DRIVE_SERVICE:
        return "Error: El servicio de Google Drive no está autenticado."
    try:
        file_metadata = {"name": file_name, "mimeType": "application/vnd.google-apps.document"}
        if folder_path:
            try:
                folder_id = _get_folder_id_from_path(folder_path)
                file_metadata['parents'] = [folder_id]
            except FileNotFoundError as e:
                return str(e)
        file = DRIVE_SERVICE.files().create(body=file_metadata, fields="id, name").execute()
        return f"Archivo '{file.get('name')}' creado con éxito. ID: {file.get('id')}"
    except HttpError as error:
        return f"Ocurrió un error al crear el archivo: {error}"

def restore_file_from_trash(file_id: str) -> str:
    """
    Restaura un archivo que está en la papelera, moviéndolo de nuevo a 'Mi Unidad'.
    El input para esta herramienta debe ser únicamente el string del ID del archivo (file_id), sin el nombre del parámetro.
    Ejemplo CORRECTO de input: 'ID_DEL_ARCHIVO'.
    Ejemplo INCORRECTO de input: "file_id='ID_DEL_ARCHIVO'".
    """
    if not DRIVE_SERVICE:
        return "Error: El servicio de Google Drive no está autenticado."
    try:
        file_metadata = {'trashed': False}
        restored_file = DRIVE_SERVICE.files().update(
            fileId=file_id,
            body=file_metadata,
            fields='id, name, trashed'
        ).execute()
        return f"Archivo '{restored_file.get('name')}' (ID: {restored_file.get('id')}) restaurado de la papelera."
    except HttpError as error:
        return f"Ocurrió un error HTTP al restaurar el archivo {file_id}: {error}"