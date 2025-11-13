import sys
import os
from PyQt6.QtCore import Qt
from PyQt6 import QtWidgets, uic
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QDialog, 
    QMessageBox, QInputDialog, QButtonGroup
)

import nfs_logic

# --- BLOQUE MÁGICO PARA CORREGIR RUTAS ---
# Obtiene la ruta absoluta de donde está guardado este archivo main.py
ruta_base = os.path.dirname(os.path.abspath(__file__))

# Cambia el directorio de trabajo a esa ruta
os.chdir(ruta_base)
# -----------------------------------------

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
        
        # --- APLICANDO LA LÓGICA DE OPUESTOS ---
        
        # Grupo 1: Acceso (rw vs ro)
        self.group_acceso = QButtonGroup(self)
        self.group_acceso.addButton(self.rw)
        self.group_acceso.addButton(self.ro)
        # Opcional: Marcar uno por defecto para que no estén ambos vacíos
        self.ro.setChecked(True) 

        # Grupo 2: Sincronización (sync vs async)
        self.group_sync = QButtonGroup(self)
        self.group_sync.addButton(self.sync)
        self.group_sync.addButton(self.async_opt) # Recuerda usar el nombre corregido
        self.sync.setChecked(True) # Default recomendado

        # Grupo 3: Privilegios Root (root_squash vs no_root_squash)
        self.group_root = QButtonGroup(self)
        self.group_root.addButton(self.root_squash)
        self.group_root.addButton(self.no_root_squash)
        self.root_squash.setChecked(True) # Default seguro

        # Grupo 4: Subárbol (subtree_check vs no_subtree_check)
        self.group_subtree = QButtonGroup(self)
        self.group_subtree.addButton(self.subtree_check)
        self.group_subtree.addButton(self.no_subtree_check)
        self.no_subtree_check.setChecked(True) # Default común

        # Grupo 5: Puerto (secure vs insecure)
        self.group_secure = QButtonGroup(self)
        self.group_secure.addButton(self.secure)
        self.group_secure.addButton(self.insecure)
        self.secure.setChecked(True)

    def get_opciones_seleccionadas(self):
        """
        Revisa los checkboxes. Si anonuid/anongid están marcados,
        les añade el valor '=1000' automáticamente.
        """
        opciones_lista = []
        
        # 1. Recorremos el diccionario de checkboxes
        for nombre_opcion, checkbox_widget in self.checkboxes.items():
            
            if checkbox_widget.isChecked():
                
                # CASO ESPECIAL: Si es anonuid, escribimos "anonuid=1000"
                if nombre_opcion == 'anonuid':
                    opciones_lista.append("anonuid=1000")
                
                # CASO ESPECIAL: Si es anongid, escribimos "anongid=1000"
                elif nombre_opcion == 'anongid':
                    opciones_lista.append("anongid=1000")
                
                # CASO NORMAL: Escribimos el nombre tal cual (ej. "rw")
                else:
                    opciones_lista.append(nombre_opcion)

        return ",".join(opciones_lista)

    def set_datos(self, host, opciones_str):
        """Rellena el diálogo con datos existentes (para editar)."""
        # 1. Poner el texto del host
        self.le_host.setText(host)
        
        # 2. Marcar los checkboxes correspondientes
        opciones_lista = opciones_str.split(',')
        for opcion in opciones_lista:
            # Limpiamos espacios por si acaso
            opcion = opcion.strip()
            if opcion in self.checkboxes:
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
            "¿Desea intentar iniciar el servidor NFS ahora?\n\n"
            "• Sí: Intenta arrancar el servicio (systemctl).\n"
            "• No: Entra a la app sin iniciar el servicio (Modo Seguro).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if respuesta == QMessageBox.StandardButton.Yes:
            # Opción SI: Intentamos iniciar
            
            # Ponemos cursor de espera y forzamos actualización visual
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            QApplication.processEvents() 
            
            try:
                exito, mensaje = nfs_logic.habilitar_servicio_nfs()
                
                # Quitamos el cursor de espera
                QApplication.restoreOverrideCursor()
                
                if not exito:
                    QMessageBox.warning(self, "Resultado", f"No se pudo iniciar NFS:\n{mensaje}")
                else:
                    # Opcional: Avisar que todo salió bien (o no hacer nada para ser rápido)
                    pass 

            except Exception as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, "Error Crítico", f"Falló la lógica de NFS: {e}")
                
        else:
            # Opción NO: El usuario eligió saltar esto.
            # Esto permite entrar a la app aunque el servidor NFS esté roto.
            print("Usuario omitió el inicio del servicio NFS.")
        
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
        """Flujo para añadir un nuevo directorio (como lo definimos antes)."""
        
        directorio, ok = QInputDialog.getText(self, "Añadir Directorio", "Ruta del directorio:")
        if not (ok and directorio):
            return # El usuario canceló
        
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
        """
        Edita la ruta de un directorio seleccionado.
        """
        
        # 1. Obtener el item seleccionado de la lista (el "Maestro")
        item_actual = self.listaDirectorios.currentItem()
        
        if not item_actual:
            QMessageBox.warning(self, "Nada seleccionado", 
                                "Por favor, selecciona un directorio de la lista para editar.")
            return

        directorio_viejo = item_actual.text()

        # 2. Mostrar el QInputDialog, pero esta vez con el texto actual rellenado
        directorio_nuevo, ok = QInputDialog.getText(self, 
                                                  "Editar Directorio", 
                                                  "Ruta del directorio:", 
                                                  text=directorio_viejo)

        # 3. Validar la entrada del usuario
        if not (ok and directorio_nuevo):
            return  # El usuario canceló o dejó el campo vacío

        if directorio_viejo == directorio_nuevo:
            return  # No se hizo ningún cambio

        if directorio_nuevo in self.config_data:
            QMessageBox.warning(self, "Error", 
                                f"El directorio '{directorio_nuevo}' ya existe en la configuración.")
            return

        # 4. Verificar si el NUEVO directorio existe en el disco
        if not nfs_logic.verificar_directorio(directorio_nuevo):
            respuesta = QMessageBox.question(self, "Directorio no encontrado",
                                             f"El directorio '{directorio_nuevo}' no existe. ¿Desea crearlo?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if respuesta == QMessageBox.StandardButton.Yes:
                exito, mensaje = nfs_logic.crear_directorio(directorio_nuevo)
                if not exito:
                    QMessageBox.critical(self, "Error al crear", mensaje)
                    return 
            else:
                return  # El usuario no quiso crear el nuevo directorio

        # 5. Actualizar el "cerebro" (self.config_data)
        #    Copiamos los datos del host, borramos la clave vieja y creamos la nueva.
        datos_hosts = self.config_data.pop(directorio_viejo)  # .pop() obtiene el valor Y borra la clave
        self.config_data[directorio_nuevo] = datos_hosts

        # 6. Actualizar la UI
        item_actual.setText(directorio_nuevo)

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
        
        # 1. Obtener el directorio seleccionado (el "Maestro")
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
            
            if not opciones:
                # Opcional: Preguntar si están seguros de no poner opciones.
                # Para NFS, casi siempre se necesita 'rw' o 'ro'.
                QMessageBox.warning(self, "Sin Opciones", 
                                    "No seleccionaste ninguna opción. "
                                    "Asegúrate de añadir opciones (ej. 'rw') más tarde.")
                # Si quieres, puedes añadir un 'return' aquí para forzar 
                # a que pongan opciones.

            # 4. Crear la nueva entrada de datos
            nuevo_host_info = {"host": host, "options": opciones}
            
            # 5. Añadir al "cerebro" (self.config_data)
            # (No es necesario 'if key in...', ya que no se puede
            # llegar aquí sin un directorio que ya existe)
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
    
    
