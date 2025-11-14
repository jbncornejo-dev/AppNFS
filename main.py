# main.py
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

# bloque: ruta base
ruta_base = os.path.dirname(os.path.abspath(__file__))
os.chdir(ruta_base)

class CargarHostDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi('Ui/add_host_dialog.ui', self)

        # bloque: mapping opciones
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

        # bloque: grupos (permiten desmarcar)
        self.group_acceso = QButtonGroup(self)
        self.group_acceso.addButton(self.rw)
        self.group_acceso.addButton(self.ro)
        self._configurar_grupo(self.group_acceso)

        self.group_sync = QButtonGroup(self)
        self.group_sync.addButton(self.sync)
        self.group_sync.addButton(self.async_opt)
        self._configurar_grupo(self.group_sync)

        self.group_root = QButtonGroup(self)
        self.group_root.addButton(self.root_squash)
        self.group_root.addButton(self.no_root_squash)
        self._configurar_grupo(self.group_root)

        self.group_subtree = QButtonGroup(self)
        self.group_subtree.addButton(self.subtree_check)
        self.group_subtree.addButton(self.no_subtree_check)
        self._configurar_grupo(self.group_subtree)

        self.group_secure = QButtonGroup(self)
        self.group_secure.addButton(self.secure)
        self.group_secure.addButton(self.insecure)
        self._configurar_grupo(self.group_secure)

        # Observa: agregamos line edits para anonuid/anongid en la UI y los usamos
        # self.le_anonuid y self.le_anongid están definidos en el .ui

    def _configurar_grupo(self, group):
        group.setExclusive(False)
        group.buttonToggled.connect(self._on_button_toggled)

    def _on_button_toggled(self, button, checked):
        if checked:
            group = button.group()
            for btn in group.buttons():
                if btn is not button:
                    btn.setChecked(False)

    # bloque: obtener opciones seleccionadas (ahora con values para anonuid/anongid)
    def get_opciones_seleccionadas(self):
        opciones_lista = []

        for nombre_opcion, checkbox_widget in self.checkboxes.items():
            if checkbox_widget.isChecked():
                if nombre_opcion == 'anonuid':
                    # si hay valor en el textfield, úsalo
                    val = ""
                    try:
                        val = self.le_anonuid.text().strip()
                    except:
                        val = ""
                    if val and val.isdigit():
                        opciones_lista.append(f"anonuid={val}")
                    else:
                        # si no puso valor, no añadimos anonuid por defecto
                        opciones_lista.append("anonuid=65534")
                elif nombre_opcion == 'anongid':
                    val = ""
                    try:
                        val = self.le_anongid.text().strip()
                    except:
                        val = ""
                    if val and val.isdigit():
                        opciones_lista.append(f"anongid={val}")
                    else:
                        opciones_lista.append("anongid=65534")
                else:
                    opciones_lista.append(nombre_opcion)

        return ",".join(opciones_lista)

    def set_datos(self, host, opciones_str):
        self.le_host.setText(host)
        for cb in self.checkboxes.values():
            cb.setChecked(False)

        # limpiar line edits
        try:
            self.le_anonuid.setText("")
            self.le_anongid.setText("")
        except:
            pass

        opciones_lista = [o.strip() for o in opciones_str.split(',') if o.strip()]
        for opcion in opciones_lista:
            if opcion.startswith("anonuid="):
                self.anonuid.setChecked(True)
                val = opcion.split('=',1)[1]
                try:
                    self.le_anonuid.setText(val)
                except:
                    pass
            elif opcion.startswith("anongid="):
                self.anongid.setChecked(True)
                val = opcion.split('=',1)[1]
                try:
                    self.le_anongid.setText(val)
                except:
                    pass
            elif opcion in self.checkboxes:
                self.checkboxes[opcion].setChecked(True)
            else:
                # Si es una opción válida pero no tiene checkbox (ej. fsid=, subtree_check negado, etc.)
                # la añadimos como texto temporal en anonuid si hay valor numérico (no ideal pero evita pérdida)
                pass


class NFSApp(QMainWindow):
    def __init__(self):
        super().__init__()
        ruta_base = os.path.dirname(os.path.abspath(__file__))
        os.chdir(ruta_base)
        uic.loadUi('Ui/MainWindow.ui', self)

        if os.path.exists('assets/app_icon.ico'):
            self.setWindowIcon(QIcon('assets/app_icon.ico'))

        # pregunta inicial para intentar iniciar servicio
        respuesta = QMessageBox.question(
            self,
            "Control de Servicio NFS",
            "¿Desea intentar iniciar el servidor NFS ahora?\n",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if respuesta == QMessageBox.StandardButton.Yes:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            QApplication.processEvents()
            try:
                exito, mensaje = nfs_logic.habilitar_servicio_nfs()
                QApplication.restoreOverrideCursor()
                if not exito:
                    QMessageBox.warning(self, "Resultado", f"No se pudo iniciar NFS:\n{mensaje}")
            except Exception as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, "Error Crítico", f"Falló la lógica de NFS: {e}")
        else:
            sys.exit(0)

        self.config_data = {}

        # botones
        self.AniadirDirectorio.clicked.connect(self.on_anadir_directorio_clicked)
        self.EditarDirectorio.clicked.connect(self.on_editar_directorio_clicked)
        self.EliminarDirectorio.clicked.connect(self.on_suprimir_directorio_clicked)

        self.AniadirHost.clicked.connect(self.on_anadir_host_clicked)
        self.EditarHost.clicked.connect(self.on_editar_host_clicked)
        self.EliminarHost.clicked.connect(self.on_suprimir_host_clicked)

        self.Finalizar.clicked.connect(self.on_finalizar_clicked)
        self.Cancelar.clicked.connect(self.on_cancelar_clicked)

        self.listaDirectorios.currentItemChanged.connect(self.actualizar_tabla_hosts)

        self.cargar_configuracion_inicial()

    # bloque: cargar configuración
    def cargar_configuracion_inicial(self):
        self.config_data = nfs_logic.leer_configuracion_exports()
        self.listaDirectorios.clear()
        for directorio in self.config_data.keys():
            self.listaDirectorios.addItem(directorio)

    def on_anadir_directorio_clicked(self):
        directorio, ok = QInputDialog.getText(self, "Añadir Directorio", "Ruta del directorio:")
        if not (ok and directorio):
            return

        patron_dir = r'^/[a-zA-Z0-9._\-/]+$'
        if not re.match(patron_dir, directorio):
            QMessageBox.warning(self, "Formato Inválido",
                                "La ruta debe ser absoluta (empezar con /) y puede contener ., _, - y /")
            return

        if not nfs_logic.verificar_directorio(directorio):
            respuesta = QMessageBox.question(self, "Directorio no encontrado",
                                             f"El directorio '{directorio}' no existe. ¿Desea crearlo?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

            if respuesta == QMessageBox.StandardButton.Yes:
                exito, mensaje = nfs_logic.crear_directorio(directorio)
                if not exito:
                    QMessageBox.critical(self, "Error al crear", mensaje)
                    return
            else:
                return

        dialog = CargarHostDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            host = dialog.le_host.text().strip()
            opciones = dialog.get_opciones_seleccionadas()

            if not host:
                QMessageBox.warning(self, "Dato Faltante", "El campo 'Host' no puede estar vacío.")
                return

            # validación de host mejorada: acepta '*' o IP o IP/CIDR o IP/netmask
            if not _is_valid_gui_host(host):
                QMessageBox.warning(self, "Host Inválido",
                                    "El host debe ser '*' o una IP válida (ej. 192.168.1.10) o una máscara (ej. 192.168.1.0/24).")
                return

            nuevo_host_info = {"host": host, "options": opciones}

            if directorio in self.config_data:
                self.config_data[directorio].append(nuevo_host_info)
            else:
                self.config_data[directorio] = [nuevo_host_info]
                self.listaDirectorios.addItem(directorio)

            self.actualizar_tabla_hosts(self.listaDirectorios.currentItem())

    def on_editar_directorio_clicked(self):
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
            return

        patron_dir = r'^/[a-zA-Z0-9._\-/]+$'
        if not re.match(patron_dir, directorio_nuevo):
            QMessageBox.warning(self, "Formato Inválido",
                                "La ruta debe empezar con / y solo contener ., letras, números, _ y -")
            return

        if directorio_nuevo in self.config_data:
            QMessageBox.warning(self, "Error", f"El directorio '{directorio_nuevo}' ya existe en la configuración.")
            return

        carpeta_renombrada = False
        if nfs_logic.verificar_directorio(directorio_viejo) and not nfs_logic.verificar_directorio(directorio_nuevo):
            resp_rename = QMessageBox.question(
                self,
                "Renombrar Carpeta",
                f"¿Desea renombrar físicamente '{directorio_viejo}' a '{directorio_nuevo}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resp_rename == QMessageBox.StandardButton.Yes:
                exito, msg = nfs_logic.renombrar_directorio_fs(directorio_viejo, directorio_nuevo)
                if exito:
                    QMessageBox.information(self, "Éxito", msg)
                    carpeta_renombrada = True
                else:
                    QMessageBox.critical(self, "Error", f"No se pudo renombrar:\n{msg}")
                    return

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
                return

        datos_hosts = self.config_data.pop(directorio_viejo)
        self.config_data[directorio_nuevo] = datos_hosts
        item_actual.setText(directorio_nuevo)
        self.actualizar_tabla_hosts(item_actual)

    def on_suprimir_directorio_clicked(self):
        item_actual = self.listaDirectorios.currentItem()
        if not item_actual:
            QMessageBox.warning(self, "Nada seleccionado",
                                "Por favor, selecciona un directorio de la lista para eliminar.")
            return

        directorio_a_borrar = item_actual.text()

        respuesta = QMessageBox.question(self,
                                         "Confirmar Eliminación",
                                         f"¿Estás seguro de que deseas eliminar el directorio '{directorio_a_borrar}' de tu configuración de NFS?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)

        if respuesta == QMessageBox.StandardButton.Yes:
            if directorio_a_borrar in self.config_data:
                del self.config_data[directorio_a_borrar]
            self.listaDirectorios.takeItem(self.listaDirectorios.row(item_actual))

    def on_anadir_host_clicked(self):
        item_directorio_actual = self.listaDirectorios.currentItem()
        if not item_directorio_actual:
            QMessageBox.warning(self, "Ningún Directorio Seleccionado",
                                "Por favor, selecciona un directorio antes de añadir un host.")
            return

        directorio_key = item_directorio_actual.text()
        dialog = CargarHostDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            host = dialog.le_host.text().strip()
            opciones = dialog.get_opciones_seleccionadas()
            if not host:
                QMessageBox.warning(self, "Dato Faltante", "El campo 'Host' no puede estar vacío.")
                return
            if not _is_valid_gui_host(host):
                QMessageBox.warning(self, "Host Inválido",
                                    "El host debe ser '*' o IP válida o IP/mascara (CIDR).")
                return
            if not opciones:
                QMessageBox.warning(self, "Sin Opciones",
                                    "No seleccionaste ninguna opción. Puedes añadir opciones (ej. 'rw').")
            nuevo_host_info = {"host": host, "options": opciones}
            self.config_data[directorio_key].append(nuevo_host_info)
            self.actualizar_tabla_hosts(item_directorio_actual)

    def on_editar_host_clicked(self):
        item_dir = self.listaDirectorios.currentItem()
        if not item_dir:
            return
        current_row = self.tableHost.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Nada seleccionado", "Selecciona un host para editar.")
            return
        dir_key = item_dir.text()
        lista_hosts = self.config_data[dir_key]
        datos_host_actual = lista_hosts[current_row]
        dialog = CargarHostDialog(self)
        dialog.set_datos(datos_host_actual['host'], datos_host_actual['options'])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            nuevo_host = dialog.le_host.text().strip()
            nuevas_opciones = dialog.get_opciones_seleccionadas()
            if not nuevo_host:
                QMessageBox.warning(self, "Error", "El host no puede estar vacío.")
                return
            if not _is_valid_gui_host(nuevo_host):
                QMessageBox.warning(self, "Host Inválido",
                                    "El host debe ser '*' o una IP válida o IP/mascara.")
                return
            self.config_data[dir_key][current_row] = {
                'host': nuevo_host,
                'options': nuevas_opciones
            }
            self.actualizar_tabla_hosts(item_dir)

    def on_suprimir_host_clicked(self):
        item_dir = self.listaDirectorios.currentItem()
        if not item_dir:
            return
        current_row = self.tableHost.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Nada seleccionado",
                                "Por favor, selecciona un host para eliminar.")
            return
        dir_key = item_dir.text()
        lista_hosts = self.config_data[dir_key]
        host_info = lista_hosts[current_row]
        nombre_host = host_info['host']
        respuesta = QMessageBox.question(self,
                                         "Confirmar Eliminación",
                                         f"¿Eliminar host '{nombre_host}' del directorio '{dir_key}'?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
        if respuesta == QMessageBox.StandardButton.Yes:
            del self.config_data[dir_key][current_row]
            self.actualizar_tabla_hosts(item_dir)

    def actualizar_tabla_hosts(self, item_directorio_actual):
        self.tableHost.clearContents()
        self.tableHost.setRowCount(0)
        if not item_directorio_actual:
            return
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
        exito_escritura, mensaje = nfs_logic.escribir_configuracion_exports(self.config_data)
        if not exito_escritura:
            QMessageBox.critical(self, "Error al Guardar", mensaje)
            return
        exito_aplicar, mensaje = nfs_logic.aplicar_cambios_nfs()
        if not exito_aplicar:
            QMessageBox.critical(self, "Error al Aplicar", mensaje)
            return
        QMessageBox.information(self, "Éxito",
                                "La configuración de NFS se ha guardado y aplicado correctamente.")
        self.close()

    def on_cancelar_clicked(self):
        respuesta = QMessageBox.question(self,
                                         "Salir",
                                         "¿Deseas salir? Los cambios no guardados se perderán.",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
        if respuesta == QMessageBox.StandardButton.Yes:
            self.close()


def _is_valid_gui_host(host):
    # permitir '*' o IPv4 o IPv4/CIDR o IPv4/netmask
    return nfs_logic._is_valid_export_host(host)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    if os.geteuid() != 0:
        QMessageBox.critical(
            None,
            "Error de Permisos",
            "Esta aplicación necesita privilegios de administrador (root). Ejecuta con sudo."
        )
        sys.exit(1)
    print("Permisos root detectados. Iniciando aplicación...")
    window = NFSApp()
    window.show()
    sys.exit(app.exec())
