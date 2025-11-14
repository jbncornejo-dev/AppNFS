# nfs_logic.py
import os
import subprocess
import shlex
import re

EXPORTS_FILE = '/etc/exports'

# bloque: verificar directorio
def verificar_directorio(path):
    return os.path.exists(path)

# bloque: crear directorio
def crear_directorio(path):
    try:
        os.makedirs(path, exist_ok=True)
        os.chmod(path, 0o777)
        return True, f"Directorio {path} creado/asegurado con permisos."
    except PermissionError:
        return False, "Error de Permisos: No se pudo crear/cambiar permisos."
    except Exception as e:
        return False, f"Error inesperado: {e}"

# bloque: leer exports (parse simple, acepta IPs y máscaras, ignora dominios con letras)
def leer_configuracion_exports():
    config_data = {}
    try:
        with open(EXPORTS_FILE, 'r') as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith('#'):
                    continue

                partes = linea.split()
                if len(partes) < 2:
                    continue

                directorio = partes[0]
                hosts_info = partes[1:]

                if directorio not in config_data:
                    config_data[directorio] = []

                for host_info in hosts_info:
                    try:
                        host, opciones_bruto = host_info.split('(', 1)
                        opciones = opciones_bruto.replace(')', '')
                        host = host.strip()

                        # Validar host: aceptar '*', IPv4, IPv4/CIDR o IPv4/netmask
                        if _is_valid_export_host(host):
                            config_data[directorio].append({"host": host, "options": opciones})
                        else:
                            # Ignorar hosts que sean nombres de dominio con letras
                            print(f"Aviso: host ignorado (no permitido por validación): {host}")
                    except ValueError:
                        print(f"Advertencia: Ignorando parte mal formada: {host_info}")

    except FileNotFoundError:
        print(f"Advertencia: {EXPORTS_FILE} no encontrado. Se creará al guardar.")
    except PermissionError:
        raise PermissionError(f"¡Error fatal! No se pudo leer {EXPORTS_FILE}.")
    return config_data

# bloque: helper validación host
def _is_valid_export_host(host):
    if host == '*':
        return True
    # IPv4 simple
    ipv4_re = r'^(\d{1,3}\.){3}\d{1,3}$'
    # CIDR
    cidr_re = r'^(\d{1,3}\.){3}\d{1,3}/([0-9]|[12][0-9]|3[0-2])$'
    # netmask form e.g. 192.168.1.0/255.255.255.0
    netmask_re = r'^(\d{1,3}\.){3}\d{1,3}/((\d{1,3}\.){3}\d{1,3})$'

    if re.match(ipv4_re, host):
        return _ipv4_octets_valid(host)
    if re.match(cidr_re, host):
        addr, prefix = host.split('/')
        return _ipv4_octets_valid(addr)
    if re.match(netmask_re, host):
        addr, mask = host.split('/')
        return _ipv4_octets_valid(addr) and _ipv4_octets_valid(mask)
    return False  # no aceptamos dominios con letras

def _ipv4_octets_valid(addr):
    parts = addr.split('.')
    if len(parts) != 4:
        return False
    try:
        for p in parts:
            n = int(p)
            if n < 0 or n > 255:
                return False
        return True
    except:
        return False

# bloque: escribir exports (simple)
def escribir_configuracion_exports(config_data):
    try:
        lineas_a_escribir = ["# Archivo de configuración de NFS generado por MiAppNFS\n"]
        for directorio, hosts_lista in config_data.items():
            hosts_str_lista = []
            for host_info in hosts_lista:
                hosts_str_lista.append(f"{host_info['host']}({host_info['options']})")
            linea_final = f"{directorio} {' '.join(hosts_str_lista)}"
            lineas_a_escribir.append(linea_final)
        with open(EXPORTS_FILE, 'w') as f:
            f.write("\n".join(lineas_a_escribir))
        return True, "Configuración guardada."
    except PermissionError:
        return False, f"Error de Permisos: No se pudo escribir en {EXPORTS_FILE}."
    except Exception as e:
        return False, f"Error inesperado al guardar: {e}"

# bloque: aplicar exportfs
def aplicar_cambios_nfs():
    try:
        subprocess.run(shlex.split("exportfs -ra"), check=True, capture_output=True, text=True)
        return True, "Configuración de NFS aplicada exitosamente."
    except subprocess.CalledProcessError as e:
        stderr = e.stderr or e.stdout or ""
        return False, f"Error al ejecutar 'exportfs -ra': {stderr}"
    except FileNotFoundError:
        return False, "Error: El comando 'exportfs' no se encontró en el PATH."

# bloque: habilitar servicio NFS (intenta enable --now, luego enable + start si hace falta)
def habilitar_servicio_nfs():
    servicios = ["nfs-server", "nfs-kernel-server", "nfs"]
    for svc in servicios:
        try:
            check = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True)
            if check.stdout.strip() == "active":
                return True, f"El servicio {svc} ya estaba activo."

            # Intento combinado: enable --now (prefierido)
            try:
                subprocess.run(["systemctl", "enable", "--now", svc], check=True, capture_output=True, timeout=20, text=True)
                return True, f"Servicio {svc} habilitado e iniciado correctamente."
            except subprocess.CalledProcessError:
                # Si falla, intento enable + start
                try:
                    subprocess.run(["systemctl", "enable", svc], check=True, capture_output=True, timeout=10, text=True)
                    subprocess.run(["systemctl", "start", svc], check=True, capture_output=True, timeout=20, text=True)
                    return True, f"Servicio {svc} habilitado y arrancado con enable+start."
                except subprocess.CalledProcessError as e2:
                    # sigue al siguiente nombre de servicio
                    continue
            except subprocess.TimeoutExpired:
                return False, "Error: El inicio del servicio tardó demasiado (Timeout)."

        except FileNotFoundError:
            return False, "Error: systemctl no disponible en este sistema."
        except Exception:
            continue

    return False, "Error: No se pudo encontrar o arrancar un servicio NFS conocido."

# bloque: renombrar carpeta
def renombrar_directorio_fs(ruta_vieja, ruta_nueva):
    import shutil
    try:
        # shutil.move maneja cross-filesystem mejor que os.rename
        shutil.move(ruta_vieja, ruta_nueva)
        return True, f"Carpeta renombrada de '{ruta_vieja}' a '{ruta_nueva}'."
    except OSError as e:
        return False, f"Error al renombrar carpeta: {e}"
