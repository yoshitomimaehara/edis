# -*- coding: utf-8 -*-
# EDIS - a simple cross-platform IDE for C
#
# This file is part of Edis
# Copyright 2014-2015 - Edis Team
# License: GPLv3 (see http://www.gnu.org/licenses/gpl.html)

import os

from PyQt4.QtGui import (
    QWidget,
    QVBoxLayout,
    QFileDialog,
    QMessageBox,
    QStackedWidget
    )

from PyQt4.QtCore import (
    SIGNAL,
    QFileInfo,
    pyqtSignal
    )

from src.helpers import file_manager
from src.helpers.exceptions import EdisIOException
from src.helpers.configurations import ESettings
from src.ui.editor import editor
from src.ui.main import EDIS
from src.ui.widgets import (
    find_popup,
    replace_widget,
    goto_line_widget
    )
from src.ui.containers import selector
from src.ui.dialogs import file_properties
from src.ui.containers import editor_widget
from src.ui import start_page
from src.helpers import logger

log = logger.edis_logger.get_logger(__name__)
ERROR = log.error

#FIXME: Mejorar la forma en la que se muestra/oculta el stacked del editor


class EditorContainer(QWidget):

    # Señales
    closedFile = pyqtSignal(int)
    cursorPosition = pyqtSignal(int, int, int)
    updateSymbols = pyqtSignal('PyQt_PyObject')
    fileChanged = pyqtSignal('QString')
    openedFile = pyqtSignal('QString')

    def __init__(self, edis=None):
        QWidget.__init__(self, edis)
        self.setAcceptDrops(True)
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(0, 0, 0, 0)
        self.box.setSpacing(0)

        # Stacked
        self.stack = QStackedWidget()
        self.box.addWidget(self.stack)

        # Replace widget
        self._replace_widget = replace_widget.ReplaceWidget()
        self._replace_widget.hide()
        self.box.addWidget(self._replace_widget)

        # Editor widget
        self.editor_widget = editor_widget.EditorWidget()
        self.stack.addWidget(self.editor_widget)

        if not ESettings.get('general/show-start-page'):
            self.editor_widget.combo.hide()

        # Conexiones
        self.connect(self.editor_widget, SIGNAL("saveCurrentFile()"),
                     self.save_file)
        self.connect(self.editor_widget, SIGNAL("fileClosed(int)"),
                     self._file_closed)
        self.connect(self.editor_widget, SIGNAL("recentFile(QStringList)"),
                     self.update_recents_files)
        self.connect(self.editor_widget, SIGNAL("allFilesClosed()"),
                     self.add_start_page)

        EDIS.cargar_componente("principal", self)

    def update_recents_files(self, recents_files):
        """ Actualiza el submenú de archivos recientes """

        menu = EDIS.componente("menu_recent_file")
        self.connect(menu, SIGNAL("triggered(QAction*)"),
                     self._open_recent_file)
        menu.clear()
        for _file in recents_files:
            menu.addAction(_file)

    def _open_recent_file(self, accion):
        """ Abre el archivo desde el menú """

        self.open_file(accion.text())

    def get_recents_files(self):
        """ Devuelve una lista con los archivos recientes en el menú """

        menu = EDIS.componente('menu_recent_file')
        actions = menu.actions()
        recents_files = []
        for filename in actions:
            recents_files.append(filename.text())
        return recents_files

    def _file_closed(self, index):
        self.closedFile.emit(index)

    def _file_modified(self, value):
        #FIXME:
        self.editor_widget.editor_modified(value)

    def _file_saved(self, weditor):
        self.editor_widget.editor_modified(False)
        filename = weditor.filename
        self.emit(SIGNAL("updateSymbols(QString)"), filename)

    def change_widget(self, index, fromCombo=False):
        if not fromCombo:
            self.editor_widget.change_item(index)
        weditor = self.get_active_editor()
        if weditor is not None and not weditor.is_new:
            self.fileChanged.emit(weditor.filename)
            self.emit(SIGNAL("updateSymbols(QString)"), weditor.filename)
            weditor.setFocus()

    def add_editor(self, filename=""):
        if not filename:
            filename = "Nuevo_archivo"
        weditor = editor.Editor()
        self.editor_widget.add_item_combo(filename)
        self.editor_widget.add_widget(weditor)
        if isinstance(self.stack.widget(0), start_page.StartPage):
            self.stack.removeWidget(self.stack.widget(0))
        symbols_widget = EDIS.lateral('symbols')
        if not symbols_widget.isVisible():
            symbols_widget.show()
        # Conexiones
        self.connect(weditor, SIGNAL("cursorPositionChanged(int, int)"),
                     self.update_cursor)
        self.connect(weditor, SIGNAL("modificationChanged(bool)"),
                     #self.editor_widget.editor_modified)
                     self._file_modified)
        self.connect(weditor, SIGNAL("fileSaved(PyQt_PyObject)"),
                     self._file_saved)
        self.connect(weditor, SIGNAL("linesChanged(int)"),
                     self.editor_widget.combo.move_to_symbol)
        weditor.dropSignal.connect(self._drop_editor)
        weditor.setFocus()
        return weditor

    def reload_file(self):
        """ Recarga el archivo """

        weditor = self.get_active_editor()
        if weditor is not None:
            filename = weditor.filename
            content = file_manager.get_file_content(filename)
            weditor.setText(content)
            weditor.setModified(False)

    def open_file(self, filename="", cursor_position=None):
        filter_files = "Archivos C(*.cpp *.c);;ASM(*.s);;HEADERS(*.h);;(*.*)"
        if not filename:
            working_directory = os.path.expanduser("~")
            weditor = self.get_active_editor()
            if weditor and weditor.filename:
                working_directory = self._last_folder(weditor.filename)
            filenames = QFileDialog.getOpenFileNames(self, self.tr("Open file"),
                                                     working_directory,
                                                     filter_files)
        else:
            filenames = [filename]
        try:
            for _file in filenames:
                if not self._is_open(_file):
                    self.editor_widget.not_open = False
                    content = file_manager.get_file_content(_file)
                    weditor = self.add_editor(_file)
                    weditor.texto = content
                    weditor.filename = _file
                    if cursor_position is not None:
                        line, row = cursor_position
                        weditor.setCursorPosition(line, row)
                    weditor.setModified(False)
                    self.fileChanged.emit(_file)
                    self.openedFile.emit(_file)
                    self.emit(SIGNAL("updateSymbols(QString)"), _file)
        except EdisIOException as error:
            ERROR('Error opening file: %s', error)
            QMessageBox.critical(self, self.tr('Could not open file'),
                                    str(error))
        self.editor_widget.not_open = True

    def _last_folder(self, path):
        """ Devuelve la última carpeta a la que se accedió """

        return QFileInfo(path).absolutePath()

    def _is_open(self, archivo):
        """
        Retorna True si un archivo ya esta abierto,
        False en caso contrario

        """

        for index in range(self.editor_widget.count()):
            widget = self.editor_widget.widget(index)
            if widget.filename == archivo:
                return True
        return False

    def add_widget(self, widget):
        """ Agrega @widget al stacked """

        self.editor_widget.add_widget(widget)

    def add_start_page(self):
        """ Agrega la página de inicio al stack """

        if ESettings.get('general/show-start-page'):
            _start_page = start_page.StartPage()
            self.stack.insertWidget(0, _start_page)
            self.stack.setCurrentIndex(0)
            symbols = EDIS.lateral('symbols')
            symbols.hide()
        else:
            self.editor_widget.combo.setVisible(False)

    def remove_widget(self, widget):
        """ Elimina el @widget del stacked """

        self.stack.removeWidget(widget)

    def current_widget(self):
        """ Widget actual """

        return self.editor_widget.current_widget()

    def current_index(self):
        return self.editor_widget.current_index()

    def get_active_editor(self):
        """ Devuelve el Editor si el widget actual es una instancia de él,
        de lo contrario devuelve None. """

        widget = self.current_widget()
        if isinstance(widget, editor.Editor):
            return widget
        return None

    def close_file(self):
        self.editor_widget.close_file()

    def close_all(self):
        self.editor_widget.close_all()

    def show_selector(self):
        if self.get_active_editor() is not None:
            selector_ = selector.Selector(self)
            selector_.show()

    def save_file(self, weditor=None):
        #FIXME: Controlar con try-except
        if weditor is None:
            weditor = self.get_active_editor()
        if weditor.is_new:
            return self.save_file_as(weditor)
        filename = weditor.filename
        source_code = weditor.texto
        filename = file_manager.write_file(filename, source_code)
        weditor.filename = filename
        weditor.guardado()

    def save_file_as(self, weditor=None):
        #FIXME: Controlar con try-except
        if weditor is None:
            weditor = self.get_active_editor()
        working_directory = os.path.expanduser("~")
        filename = QFileDialog.getSaveFileName(self, self.tr("Save file"),
                                               working_directory)
        if not filename:
            return False
        filename = file_manager.write_file(filename, weditor.texto)
        weditor.filename = filename
        self.fileChanged.emit(filename)
        weditor.guardado()

    def save_selected(self, filename):
        for index in range(self.editor_widget.count()):
            if self.editor_widget.widget(index).filename == filename:
                self.save_file(self.editor_widget.widget(index))

    def files_not_saved(self):
        return self.editor_widget.files_not_saved()

    def check_files_not_saved(self):
        return self.editor_widget.check_files_not_saved()

    def find(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            dialog = find_popup.PopupBusqueda(self.get_active_editor())
            dialog.show()

    def find_and_replace(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            if self._replace_widget.isVisible():
                self._replace_widget.hide()
                weditor.setFocus()
            else:
                self._replace_widget.show()

    def action_undo(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.undo()

    def action_redo(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.redo()

    def action_cut(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.cut()

    def action_copy(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.copy()

    def action_paste(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.paste()

    def show_tabs_and_spaces(self):
        tabs_spaces = ESettings.get('editor/show-tabs-spaces')
        ESettings.set('editor/show-tabs-spaces', not tabs_spaces)
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.actualizar()

    def show_indentation_guides(self):
        guides = ESettings.get('editor/show-guides')
        ESettings.set('editor/show-guides', not guides)
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.actualizar()

    def action_zoom_in(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.zoom_in()

    def action_zoom_out(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.zoom_out()

    def action_normal_size(self):
        """ Carga el tamaño por default de la fuente """

        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.zoomTo(0)

    def action_select_all(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.selectAll()

    def opened_files(self):
        return self.editor_widget.opened_files()

    def file_properties(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            dialog = file_properties.FileProperty(weditor, self)
            dialog.show()

    def update_cursor(self, line, row):
        weditor = self.get_active_editor()
        lines = weditor.lineas
        self.editor_widget.combo.update_cursor_position(
            line + 1, row + 1, lines)
        self.cursorPosition.emit(line + 1, row + 1, lines)

    def build_source_code(self):
        output = EDIS.componente("output")
        weditor = self.get_active_editor()
        if weditor is not None:
            self.save_file()
            output.build(weditor.filename)

    def run_binary(self):
        """ Ejecuta el programa objeto """

        output = EDIS.componente("output")
        output.run()

    def build_and_run(self):
        output = EDIS.componente("output")
        weditor = self.get_active_editor()
        if weditor is not None:
            self.save_file()
            output.build_and_run(weditor.filename)

    def clean_construction(self):
        output = EDIS.componente("output")
        output.clean()

    def stop_program(self):
        output = EDIS.componente("output")
        output.stop()

    def action_comment(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.comment()

    def action_uncomment(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.uncomment()

    def action_indent(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.indent_more()

    def action_unindent(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.indent_less()

    def action_to_lowercase(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.to_lowercase()

    def action_to_uppercase(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.to_uppercase()

    def action_to_title(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.to_title()

    def action_duplicate_line(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.duplicate_line()

    def action_delete_line(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.delete_line()

    def action_move_down(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.move_down()

    def action_move_up(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.move_up()

    def go_to_line(self, line):
        weditor = self.get_active_editor()
        if weditor is not None:
            weditor.setCursorPosition(line, 0)

    def show_go_to_line(self):
        weditor = self.get_active_editor()
        if weditor is not None:
            dialog = goto_line_widget.GoToLineDialog(weditor)
            dialog.show()

    def add_symbols_combo(self, symbols):
        self.editor_widget.add_symbols(symbols)

    def dragEnterEvent(self, event):
        data = event.mimeData()
        if data.hasText():
            # Se acepta el evento de arrastrado
            event.accept()

    def dropEvent(self, event):
        self._drop_event(event)

    def _drop_editor(self, event):
        self._drop_event(event)

    def _drop_event(self, event):
        data = event.mimeData()
        filename = data.urls()[0].toLocalFile()
        self.open_file(filename)


editor_container = EditorContainer()