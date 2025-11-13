import sys
import os
import re
from PyQt6.QtCore import Qt
from PyQt6 import QtWidgets, uic
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QDialog, 
    QMessageBox, QInputDialog, QButtonGroup
)

import nfs_logic

# --- BLOQUE PARA CORREGIR RUTAS ---
# Obtiene la ruta absoluta de donde está guardado este archivo main.py
ruta_base = os.path.dirname(os.path.abspath(__file__))

# Cambia el directorio de trabajo a esa ruta
os.chdir(ruta_base)

# --- Clase para el Diálogo de Añadir/Editar Host ---
class CargarHostDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi('Ui/add_host_dialog.ui', self)

        # Mapea los nombres de las opciones a los widgets checkbox
        self.checkboxes = {
            'rw': self.rw, 'ro': self.ro,
            'sync': self.sync, 'async': self.async_opt,
            'no_root_squash': self.no_root_squash,
            'root_squash': self.root_squash,
            'all_squash': self.all_squash,
            'no_subtree_check': self.no_subtree_check,
            'subtree_check': self.subtree_check,
            'insecure': self.insecure, 'secure': self.secure,
            'anonuid': self.anonuid, 'anongid': self.anongid
        }
        
        # --- GRUPOS DE OPCIONES ---
        
        # Grupo 1: Acceso
        self.group_acceso = QButtonGroup(self)
        self.group_acceso.addButton(self.rw)
        self.group_acceso.addButton(self.ro)
        self._configurar_grupo(self.group_acceso)

        # Grupo 2: Sincronización
        self.group_sync = QButtonGroup(self)
        self.group_sync.addButton(self.sync)
        self.group_sync.addButton(self.async_opt)
        self._configurar_grupo(self.group_sync)

        # Grupo 3: Privilegios Root
        self.group_root = QButtonGroup(self)
        self.group_root.addButton(self.root_squash)
        self.group_root.addButton(self.no_root_squash)
        self._configurar_grupo(self.group_root)

        # Grupo 4: Subárbol
        self.group_subtree = QButtonGroup(self)
        self.group_subtree.addButton(self.subtree_check)
        self.group_subtree.addButton(self.no_subtree_check)
        self._configurar_grupo(self.group_subtree)

        # Grupo 5: Puerto
        self.group_secure = QButtonGroup(self)
        self.group_secure.addButton(self.secure)
        self.group_secure.addButton(self.insecure)
        self._configurar_grupo(self.group_secure)
        
        # NOTA: He quitado los .setChecked(True) por defecto para que 
        # empiecen vacíos si así lo prefieres.

    def _configurar_grupo(self, group):
        """
        Configura un grupo para que permita desmarcar todos (0 seleccionados)
        pero impida tener más de uno (máximo 1 seleccionado).
        """
        group.setExclusive(False) # Permite desmarcar el que ya está marcado
        
        # Conectamos la señal para hacer la exclusión manual
        group.buttonToggled.connect(self._on_button_toggled)

    def _on_button_toggled(self, button, checked):
        """
        Lógica manual: Si un botón se ENCIENDE, apagamos a su opuesto.
        Si un botón se APAGA, no hacemos nada (permitimos que quede vacío).
        """
        if checked:
            group = button.group()
            for btn in group.buttons():
                if btn is not button:
                    btn.setChecked(False)

    def get_opciones_seleccionadas(self):
        """
        Revisa los checkboxes y genera la cadena de texto.
        """
        opciones_lista = []
        
        for nombre_opcion, checkbox_widget in self.checkboxes.items():
            if checkbox_widget.isChecked():
                # CASOS ESPECIALES
                if nombre_opcion == 'anonuid':
                    opciones_lista.append("anonuid=1000")
                elif nombre_opcion == 'anongid':
                    opciones_lista.append("anongid=1000")
                else:
                    opciones_lista.append(nombre_opcion)

        return ",".join(opciones_lista)

    def set_datos(self, host, opciones_str):
        """Rellena el diálogo con datos existentes."""
        self.le_host.setText(host)
        
        # Primero limpiamos todo (por si acaso)
        for cb in self.checkboxes.values():
            cb.setChecked(False)

        opciones_lista = opciones_str.split(',')
        for opcion in opciones_lista:
            opcion = opcion.strip()
            
            if opcion.startswith("anonuid="):
                if 'anonuid' in self.checkboxes: self.checkboxes['anonuid'].setChecked(True)
            
            elif opcion.startswith("anongid="):
                if 'anongid' in self.checkboxes: self.checkboxes['anongid'].setChecked(True)
            
            elif opcion in self.checkboxes:
                self.checkboxes[opcion].setChecked(True)


# --- Clase de la Ventana Principal ---
class NFSApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 1. Cargar Rutas y UI
        ruta_base = os.path.dirname(os.path.abspath(__file__))
        os.chdir(ruta_base)
        uic.loadUi('Ui/MainWindow.ui', self)
        
        if os.path.exists('assets/app_icon.png'):
            self.setWindowIcon(QIcon('assets/app_icon.png'))

        # --- PREGUNTA DE SEGURIDAD AL INICIO ---
        
        respuesta = QMessageBox.question(
            self, 
            "Control de Servicio NFS", 
            "Para usar esta aplicación, es recomendable verificar el servidor NFS.\n\n"
            "¿Desea intentar iniciar el servidor NFS ahora?\n",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if respuesta == QMessageBox.StandardButton.Yes:
            # Opción SI: Intentamos iniciar
            
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            QApplication.processEvents() 
            
            try:
                exito, mensaje = nfs_logic.habilitar_servicio_nfs()
                
                QApplication.restoreOverrideCursor()
                
                if not exito:
                    # Si falla al iniciar
                    QMessageBox.warning(self, "Resultado", f"No se pudo iniciar NFS:\n{mensaje}")
                
            except Exception as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, "Error Crítico", f"Falló la lógica de NFS: {e}")
                
        else:
            # Opción NO: El usuario no quiere iniciar el servicio.
            # CERRAMOS LA APLICACIÓN INMEDIATAMENTE.
            sys.exit(0)
        
        # Almacén de datos en memoria
        self.config_data = {}

        # --- Conectar signals a slots (botones) ---
        
        # Botones de Directorio
        self.AniadirDirectorio.clicked.connect(self.on_anadir_directorio_clicked)
        self.EditarDirectorio.clicked.connect(self.on_editar_directorio_clicked)
        self.EliminarDirectorio.clicked.connect(self.on_suprimir_directorio_clicked)

        # Botones de Host
        self.AniadirHost.clicked.connect(self.on_anadir_host_clicked)
        self.EditarHost.clicked.connect(self.on_editar_host_clicked)
        self.EliminarHost.clicked.connect(self.on_suprimir_host_clicked)

        # Botones principales
        self.Finalizar.clicked.connect(self.on_finalizar_clicked)
        self.Cancelar.clicked.connect(self.on_cancelar_clicked)

        # Conectar la lista "Maestro" a la tabla "Detalle"
        self.listaDirectorios.currentItemChanged.connect(self.actualizar_tabla_hosts)

        # Cargar la configuración inicial
        self.cargar_configuracion_inicial()

    def cargar_configuracion_inicial(self):
        """Lee el /etc/exports y rellena la lista de directorios."""
        self.config_data = nfs_logic.leer_configuracion_exports()
        
        self.listaDirectorios.clear()
        for directorio in self.config_data.keys():
            self.listaDirectorios.addItem(directorio)

    def on_anadir_directorio_clicked(self):
        """Flujo para añadir un nuevo directorio."""
        
        directorio, ok = QInputDialog.getText(self, "Añadir Directorio", "Ruta del directorio:")
        if not (ok and directorio):
            return # El usuario canceló
        
        # --- VALIDACIÓN DE DIRECTORIO ---
        # Regex: ^/ indica que debe empezar con barra
        # [a-zA-Z0-9_\-/]+ indica que solo acepta letras, números, _, - y /
        patron_dir = r'^/[a-zA-Z0-9_\-/]+$'
        
        if not re.match(patron_dir, directorio):
            QMessageBox.warning(self, "Formato Inválido", 
                                "La ruta debe ser absoluta (empezar con /).\n"
                                "Solo se permiten letras, números, guiones y guiones bajos.\n\n"
                                "Ejemplo válido: /opt/mis_archivos-1")
            return
        # --------------------------------
        
        # 1. Verificar si existe
        if not nfs_logic.verificar_directorio(directorio):
            respuesta = QMessageBox.question(self, "Directorio no encontrado",
                                             f"El directorio '{directorio}' no existe. ¿Desea crearlo?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if respuesta == QMessageBox.StandardButton.Yes:
                # 2. Intentar crear
                exito, mensaje = nfs_logic.crear_directorio(directorio)
                if not exito:
                    QMessageBox.critical(self, "Error al crear", mensaje)
                    return # Detener si no se pudo crear
            else:
                return # El usuario no quiso crearlo

        # 3. Pedir el primer Host y Opciones
        dialog = CargarHostDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            host = dialog.le_host.text()
            opciones = dialog.get_opciones_seleccionadas()
            
            # --- VALIDACIÓN DE HOST (También aquí) ---
            # Acepta "*" O formato IP (0-255.0-255...)
            patron_ip = r'^(\d{1,3}\.){3}\d{1,3}$'
            if host != "*" and not re.match(patron_ip, host):
                QMessageBox.warning(self, "Host Inválido", "El host debe ser '*' o una IP válida (ej. 192.168.1.50)")
                return
            # -----------------------------------------
            
            if not host:
                QMessageBox.warning(self, "Dato Faltante", "El campo 'Host' no puede estar vacío.")
                return

            # 4. Actualizar la UI y los datos en memoria
            nuevo_host_info = {"host": host, "options": opciones}
            
            if directorio in self.config_data:
                self.config_data[directorio].append(nuevo_host_info)
            else:
                self.config_data[directorio] = [nuevo_host_info]
                self.listaDirectorios.addItem(directorio) # Añadir a la lista
            
            # Actualizar la tabla de hosts para el directorio actual
            self.actualizar_tabla_hosts(self.listaDirectorios.currentItem())

    def on_editar_directorio_clicked(self):
        """Edita la ruta de un directorio con opción de renombrado físico."""
        
        item_actual = self.listaDirectorios.currentItem()
        if not item_actual:
            QMessageBox.warning(self, "Nada seleccionado", "Por favor, selecciona un directorio para editar.")
            return

        directorio_viejo = item_actual.text()

        directorio_nuevo, ok = QInputDialog.getText(self, 
                                                    "Editar Directorio", 
                                                    "Ruta del directorio:", 
                                                    text=directorio_viejo)

        if not (ok and directorio_nuevo):
            return
        
        if directorio_viejo == directorio_nuevo:
            return # No hubo cambios

        # --- VALIDACIÓN DE DIRECTORIO ---
        patron_dir = r'^/[a-zA-Z0-9_\-/]+$'
        if not re.match(patron_dir, directorio_nuevo):
            QMessageBox.warning(self, "Formato Inválido", 
                                "La ruta debe empezar con / y solo contener letras, números, _ y -")
            return
        # --------------------------------

        if directorio_nuevo in self.config_data:
            QMessageBox.warning(self, "Error", f"El directorio '{directorio_nuevo}' ya existe en la configuración.")
            return

        # --- LÓGICA DE RENOMBRADO ---
        carpeta_renombrada = False
        
        # 1. Verificamos si la carpeta VIEJA existe físicamente y la NUEVA no existe
        if nfs_logic.verificar_directorio(directorio_viejo) and not nfs_logic.verificar_directorio(directorio_nuevo):
            
            # Preguntamos al usuario
            resp_rename = QMessageBox.question(
                self, 
                "Renombrar Carpeta",
                f"La carpeta antigua '{directorio_viejo}' existe en el disco.\n\n"
                f"¿Desea renombrarla físicamente a '{directorio_nuevo}'?\n"
                "(Esto moverá todos los archivos dentro).",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if resp_rename == QMessageBox.StandardButton.Yes:
                exito, msg = nfs_logic.renombrar_directorio_fs(directorio_viejo, directorio_nuevo)
                if exito:
                    QMessageBox.information(self, "Éxito", msg)
                    carpeta_renombrada = True
                else:
                    QMessageBox.critical(self, "Error", f"No se pudo renombrar:\n{msg}")
                    return # Cancelamos la operación si falla el renombrado

        # 2. Si NO se renombró (porque no existía la vieja o el usuario dijo NO),
        #    entonces verificamos si hace falta CREAR la nueva.
        if not carpeta_renombrada and not nfs_logic.verificar_directorio(directorio_nuevo):
            respuesta = QMessageBox.question(self, "Directorio no encontrado",
                                             f"El directorio '{directorio_nuevo}' no existe. ¿Desea crearlo?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if respuesta == QMessageBox.StandardButton.Yes:
                exito, mensaje = nfs_logic.crear_directorio(directorio_nuevo)
                if not exito:
                    QMessageBox.critical(self, "Error al crear", mensaje)
                    return 
            else:
                return # El usuario no quiso crear el nuevo directorio ni existe

        # ----------------------------------

        # 3. Actualizar la memoria (configuración)
        datos_hosts = self.config_data.pop(directorio_viejo) 
        self.config_data[directorio_nuevo] = datos_hosts
        
        # 4. Actualizar UI
        item_actual.setText(directorio_nuevo)
        
        # Actualizar título del grupo de detalles
        self.actualizar_tabla_hosts(item_actual)

    def on_suprimir_directorio_clicked(self):
        """
        Elimina un directorio seleccionado de la configuración.
        """
        
        # 1. Obtener el item seleccionado de la lista
        item_actual = self.listaDirectorios.currentItem()
        
        if not item_actual:
            QMessageBox.warning(self, "Nada seleccionado", 
                                "Por favor, selecciona un directorio de la lista para eliminar.")
            return

        directorio_a_borrar = item_actual.text()

        # 2. Pedir confirmación al usuario
        respuesta = QMessageBox.question(self, 
                                         "Confirmar Eliminación", 
                                         f"¿Estás seguro de que deseas eliminar el directorio '{directorio_a_borrar}' de tu configuración de NFS?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No) # Botón por defecto

        if respuesta == QMessageBox.StandardButton.Yes:
            # 3. Eliminar del "cerebro" (self.config_data)
            if directorio_a_borrar in self.config_data:
                del self.config_data[directorio_a_borrar]

            # 4. Eliminar de la lista de la UI (listaDirectorios)
            #    Esto automáticamente disparará la señal 'currentItemChanged',
            #    que llamará a 'actualizar_tabla_hosts' y limpiará la tabla de abajo.
            self.listaDirectorios.takeItem(self.listaDirectorios.row(item_actual))
            
    def on_anadir_host_clicked(self):
        """
        Añade una nueva entrada de host/opciones al directorio 
        actualmente seleccionado.
        """
        
        # 1. Obtener el directorio seleccionado 
        item_directorio_actual = self.listaDirectorios.currentItem()
        
        if not item_directorio_actual:
            QMessageBox.warning(self, "Ningún Directorio Seleccionado", 
                                "Por favor, selecciona un directorio de la lista de arriba "
                                "antes de añadir un host.")
            return

        directorio_key = item_directorio_actual.text()

        # 2. Lanzar el diálogo de host (vacío)
        dialog = CargarHostDialog(self)
        
        # 3. Si el usuario presiona "Aceptar"
        if dialog.exec() == QDialog.DialogCode.Accepted:
            host = dialog.le_host.text()
            opciones = dialog.get_opciones_seleccionadas()

            if not host:
                QMessageBox.warning(self, "Dato Faltante", 
                                    "El campo 'Host' no puede estar vacío.")
                return
                
            # --- VALIDACIÓN DE HOST ---
            # Regex simple para IP: 4 grupos de números separados por puntos
            patron_ip = r'^(\d{1,3}\.){3}\d{1,3}$'
            
            if host != "*" and not re.match(patron_ip, host):
                QMessageBox.warning(self, "Host Inválido", 
                                    "El host debe ser el comodín '*' o una IP válida (ej. 192.168.1.10).\n"
                                    "No se aceptan nombres de dominio ni texto arbitrario.")
                return
            # --------------------------
            
            if not opciones:
                
                QMessageBox.warning(self, "Sin Opciones", 
                                    "No seleccionaste ninguna opción. "
                                    "Asegúrate de añadir opciones (ej. 'rw') más tarde.")

            # 4. Crear la nueva entrada de datos
            nuevo_host_info = {"host": host, "options": opciones}
            
            # 5. Añadir al "cerebro" (self.config_data)
            self.config_data[directorio_key].append(nuevo_host_info)
            
            # 6. Refrescar la tabla de hosts (el "Detalle")
            #    Llamamos a la función que ya teníamos para actualizar la tabla.
            self.actualizar_tabla_hosts(item_directorio_actual)   
            
    def on_editar_host_clicked(self):
        """
        Abre el diálogo de Host pre-rellenado con los datos de la fila seleccionada.
        """
        
        # 1. Validar que haya un Directorio seleccionado (Maestro)
        item_dir = self.listaDirectorios.currentItem()
        if not item_dir:
            return 
            
        # 2. Validar que haya una fila de Host seleccionada (Detalle)
        current_row = self.tableHost.currentRow()
        
        if current_row < 0:
            QMessageBox.warning(self, "Nada seleccionado", 
                                "Por favor, selecciona un host de la tabla de abajo para editar.")
            return

        # 3. Recuperar los datos actuales de la memoria (self.config_data)
        #    Usamos el índice de la fila (current_row) para encontrar el dato exacto en la lista
        dir_key = item_dir.text()
        lista_hosts = self.config_data[dir_key]
        datos_host_actual = lista_hosts[current_row] # Es un dict: {'host': '...', 'options': '...'}

        # 4. Crear el diálogo y PRE-RELLENARLO
        dialog = CargarHostDialog(self)
        
        # Llamamos a la función auxiliar para marcar los checkboxes y poner el texto
        dialog.set_datos(datos_host_actual['host'], datos_host_actual['options'])

        # 5. Mostrar el diálogo
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 6. Obtener los NUEVOS datos
            nuevo_host = dialog.le_host.text()
            nuevas_opciones = dialog.get_opciones_seleccionadas()

            if not nuevo_host:
                QMessageBox.warning(self, "Error", "El host no puede estar vacío.")
                return
                
            # --- VALIDACIÓN DE HOST ---
            patron_ip = r'^(\d{1,3}\.){3}\d{1,3}$'
            if nuevo_host != "*" and not re.match(patron_ip, nuevo_host):
                QMessageBox.warning(self, "Host Inválido", 
                                    "El host debe ser '*' o una IP válida (ej. 192.168.1.10).")
                return
            # --------------------------

            # 7. Actualizar la memoria
            #    Reemplazamos el diccionario viejo por el nuevo en la misma posición
            self.config_data[dir_key][current_row] = {
                'host': nuevo_host, 
                'options': nuevas_opciones
            }

            # 8. Refrescar la tabla visualmente
            self.actualizar_tabla_hosts(item_dir)    
            
    def on_suprimir_host_clicked(self):
        """
        Elimina el host seleccionado de la lista del directorio actual.
        """
        
        # 1. Validar selección de Directorio (Maestro)
        item_dir = self.listaDirectorios.currentItem()
        if not item_dir:
            return

        # 2. Validar selección de Host (Detalle)
        current_row = self.tableHost.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Nada seleccionado", 
                                "Por favor, selecciona un host de la tabla de abajo para eliminar.")
            return

        # 3. Obtener datos para mostrar en la pregunta
        dir_key = item_dir.text()
        lista_hosts = self.config_data[dir_key]
        host_info = lista_hosts[current_row] # {'host': '...', 'options': '...'}
        nombre_host = host_info['host']

        # 4. Pedir confirmación
        respuesta = QMessageBox.question(self, 
                                         "Confirmar Eliminación", 
                                         f"¿Estás seguro de que deseas eliminar el host '{nombre_host}' del directorio '{dir_key}'?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)

        if respuesta == QMessageBox.StandardButton.Yes:
            # 5. Eliminar de la memoria
            #    Usamos 'del' con el índice de la lista
            del self.config_data[dir_key][current_row]

            # 6. Refrescar la tabla visualmente
            self.actualizar_tabla_hosts(item_dir) 
            
    def actualizar_tabla_hosts(self, item_directorio_actual):
        """
        Limpia y rellena la tabla de hosts (el "Detalle")
        basado en el directorio seleccionado (el "Maestro").
        """
        self.tableHost.clearContents()
        self.tableHost.setRowCount(0)

        if not item_directorio_actual:
            return # No hay nada seleccionado

        directorio_key = item_directorio_actual.text()
        if directorio_key in self.config_data:
            hosts_lista = self.config_data[directorio_key]
            
            self.tableHost.setRowCount(len(hosts_lista))
            
            for fila_idx, host_info in enumerate(hosts_lista):
                item_host = QtWidgets.QTableWidgetItem(host_info["host"])
                item_opciones = QtWidgets.QTableWidgetItem(host_info["options"])
                
                self.tableHost.setItem(fila_idx, 0, item_host)
                self.tableHost.setItem(fila_idx, 1, item_opciones)

    def on_finalizar_clicked(self):
        """
        Guarda la configuración actual en /etc/exports,
        aplica los cambios y cierra la aplicación.
        """
        
        # 1. Guardar los datos de la memoria (self.config_data) en el archivo
        exito_escritura, mensaje = nfs_logic.escribir_configuracion_exports(self.config_data)
        
        if not exito_escritura:
            # Si algo sale mal al escribir, muestra un error y NO continúes
            QMessageBox.critical(self, "Error al Guardar", mensaje)
            return

        # 2. Aplicar los cambios (ejecutar 'exportfs -ra')
        exito_aplicar, mensaje = nfs_logic.aplicar_cambios_nfs()
        
        if not exito_aplicar:
            # Si algo sale mal al aplicar, muestra un error
            QMessageBox.critical(self, "Error al Aplicar", mensaje)
            return

        # 3. Si todo salió bien, informa al usuario y cierra la app
        QMessageBox.information(self, "Éxito", 
                                "La configuración de NFS se ha guardado y aplicado correctamente.")
        self.close() # Cierra la ventana de la aplicación
    
    
    def on_cancelar_clicked(self):
        """
        Pregunta al usuario si realmente desea salir sin guardar.
        """
        respuesta = QMessageBox.question(self, 
                                         "Salir", 
                                         "¿Estás seguro de que deseas salir? Los cambios no guardados se perderán.",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)

        if respuesta == QMessageBox.StandardButton.Yes:
            self.close() # Cierra la aplicación
    

# --- PUNTO DE ENTRADA PRINCIPAL DE LA APLICACIÓN ---
if __name__ == "__main__":
    
    # Crea la aplicación ANTES de cualquier lógica
    app = QApplication(sys.argv)

    # --- ESTA ES TU COMPROBACIÓN DE "LOGIN" ROOT ---
    if os.geteuid() != 0:
        # Si el ID de usuario NO es 0 (no es root)
        QMessageBox.critical(
            None,  # No tiene ventana "padre" todavía
            "Error de Permisos",
            "Esta aplicación necesita privilegios de administrador (root) para funcionar.\n"
            "Por favor, ejecútela usando 'sudo'.\n\n"
            "Ejemplo: sudo python3.11 main.py"
        )
        sys.exit(1)  # Salir con código de error
    # ------------------------------------------------
    
    # Si la comprobación de root es exitosa, continúa:
    print("Permisos de root detectados. Iniciando aplicación...")
    
    window = NFSApp()
    window.show()
    sys.exit(app.exec())
    
    
