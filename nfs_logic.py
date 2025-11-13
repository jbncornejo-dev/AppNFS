import os
import subprocess
import shlex # Para ejecutar comandos de forma segura

# La ruta al archivo de configuración
EXPORTS_FILE = '/etc/exports' 

def verificar_directorio(path):
    """Comprueba si una ruta de directorio existe."""
    return os.path.exists(path)

def crear_directorio(path):
    """
    Intenta crear un directorio.
    Devuelve (True, "Éxito") o (False, "Mensaje de error").
    """
    try:
        os.makedirs(path)
        return True, f"Directorio {path} creado."
    except PermissionError:
        return False, "Error de Permisos: No se pudo crear el directorio."
    except Exception as e:
        return False, f"Error inesperado: {e}"

def leer_configuracion_exports():
    """
    Lee /etc/exports y lo convierte en una estructura de datos fácil de usar.
    
    Estructura de datos devuelta:
    {
        "/opt/docus": [
            {"host": "*", "options": "rw,sync"},
            {"host": "192.168.1.1", "options": "ro,all_squash"}
        ],
        "/home/public": [
            {"host": "*.miempresa.com", "options": "rw,no_root_squash"}
        ]
    }
    """
    config_data = {}
    try:
        with open(EXPORTS_FILE, 'r') as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith('#'):
                    continue
                
                # Análisis (parsing) de la línea
                partes = linea.split()
                directorio = partes[0]
                hosts_info = partes[1:]
                
                if directorio not in config_data:
                    config_data[directorio] = []
                
                for host_info in hosts_info:
                    try:
                        # host_info es como "*(rw,sync)"
                        host, opciones_bruto = host_info.split('(', 1)
                        opciones = opciones_bruto.replace(')', '')
                        config_data[directorio].append({"host": host, "options": opciones})
                    except ValueError:
                        print(f"Advertencia: Ignorando línea mal formada: {host_info}")
                        
    except FileNotFoundError:
        print(f"Advertencia: {EXPORTS_FILE} no encontrado. Se creará uno nuevo al guardar.")
    except PermissionError:
        # Esto no debería pasar si la comprobación en main.py funciona
        raise PermissionError(f"¡Error fatal! No se pudo leer {EXPORTS_FILE}.")
        
    return config_data

def escribir_configuracion_exports(config_data):
    """
    Toma la estructura de datos y la escribe de vuelta en /etc/exports.
    """
    try:
        lineas_a_escribir = ["# Archivo de configuración de NFS generado por MiAppNFS\n"]
        
        for directorio, hosts_lista in config_data.items():
            hosts_str_lista = []
            for host_info in hosts_lista:
                hosts_str_lista.append(f"{host_info['host']}({host_info['options']})")
            
            # Une todos los hosts para ese directorio en una línea
            linea_final = f"{directorio} {' '.join(hosts_str_lista)}"
            lineas_a_escribir.append(linea_final)
            
        with open(EXPORTS_FILE, 'w') as f:
            f.write("\n".join(lineas_a_escribir))
        return True, "Configuración guardada."
        
    except PermissionError:
        return False, f"Error de Permisos: No se pudo escribir en {EXPORTS_FILE}."
    except Exception as e:
        return False, f"Error inesperado al guardar: {e}"

def aplicar_cambios_nfs():
    """
    Ejecuta 'exportfs -ra' para aplicar la nueva configuración.
    """
    try:
        subprocess.run(shlex.split("exportfs -ra"), check=True, capture_output=True)
        return True, "Configuración de NFS aplicada exitosamente."
    except subprocess.CalledProcessError as e:
        return False, f"Error al ejecutar 'exportfs -ra': {e.stderr.decode()}"
    except FileNotFoundError:
        return False, "Error: El comando 'exportfs' no se encontró en el PATH."
