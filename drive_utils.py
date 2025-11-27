import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Se define SCOPES en el mismo módulo donde se usa.
SCOPES = ["https://www.googleapis.com/auth/drive"] 

def authenticate_google_drive():
    """Autentica con la API de Google Drive y retorna el objeto 'service'."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    try:
        service = build("drive", "v3", credentials=creds)
        return service
    except HttpError as error:
        print(f"Ocurrió un error al construir el servicio de Drive: {error}")
        return None