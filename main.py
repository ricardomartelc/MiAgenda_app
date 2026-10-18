"""
Mi Agenda v2 - agenda de escritorio moderna
Python + CustomTkinter + SQLite

Instalar:   pip install customtkinter pillow winotify matplotlib pystray
Ejecutar:   python main.py
Crear .exe: python -m PyInstaller --noconsole --onefile --collect-all customtkinter
            --hidden-import pystray._win32 --name MiAgenda main.py
"""
import socket
import sys

print("[1/4] Cargando configuraciones y dependencias...")
from src.config import PORT
from src.ui.app import App


def single_instance():
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", PORT))
        s.listen(2)
        return s
    except OSError:
        print("[AVISO] El puerto está ocupado. Comprobando si ya hay una instancia abierta...")
        try:
            c = socket.create_connection(("127.0.0.1", PORT), timeout=1)
            c.send(b"show")
            c.close()
        except OSError:
            pass
        return None


if __name__ == "__main__":
    print("[2/4] Comprobando instancia única de la app...")
    sock = single_instance()
    if sock is None:
        print("[ERROR/SALIDA] Se detectó otra instancia abierta o el puerto está bloqueado. Cerrando script.")
        sys.exit(0)
    
    print("[3/4] Inicializando la interfaz gráfica (CustomTkinter)...")
    app = App(sock=sock, hidden="--minimizado" in sys.argv)
    
    print("[4/4] ¡Aplicación lista y en ejecución!")
    app.mainloop()