import tools
from agente_evaluador_simple import crear_agente_evaluador
from drive_utils import authenticate_google_drive

# -------------------------------------------------------------------
# Ejemplo de inicialización del servicio y ejecución del agente
# -------------------------------------------------------------------
def main():
    """
    Ejecuta el agente evaluador de herramientas.
    Analiza si una tarea puede realizarse con las herramientas disponibles.
    """

    # 🔧 1. Simula o inicializa el servicio de Google Drive
    # (Aquí deberías pasar el servicio real si ya lo tienes configurado)
    drive_service = authenticate_google_drive()  # o tu método real para conectar

    # 🧠 2. Crear el agente evaluador
    agente = crear_agente_evaluador(drive_service)

    if agente is None:
        print("No se pudo crear el agente evaluador. Revisa el servicio de Drive.")
        return

    # 🗣️ 3. Solicitud del usuario (puedes cambiarlo libremente)
    consulta = input("👉 Ingresa la tarea que quieres evaluar: ")

    # 🚀 4. Ejecutar el agente con la consulta
    print("\n🧩 Analizando la tarea...\n")
    try:
        respuesta = agente.invoke({"input": consulta})
        print("✅ Resultado estructurado:")
        print(f" - result: {respuesta.result}")
        print(f" - explicación:\n{respuesta.explicacion}")
    except Exception as e:
        print(f"⚠️ Error al ejecutar el agente evaluador: {e}")

# -------------------------------------------------------------------
# Punto de entrada
# -------------------------------------------------------------------
if __name__ == "__main__":
    main()
