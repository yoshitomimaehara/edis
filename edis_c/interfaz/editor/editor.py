#-*- coding: utf-8 -*-

# <Editor.>
# Copyright (C) <2014>  <Gabriel Acosta>
# This file is part of EDIS-C.

# EDIS-C is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# EDIS-C is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with EDIS-C.  If not, see <http://www.gnu.org/licenses/>.

import re

from tokenize import generate_tokens, TokenError
import token as tkn
#lint:disable
try:
    from StringIO import StringIO
except:
    # Python 3
    from io import StringIO
#lint:enable

from PyQt4.QtGui import QPlainTextEdit
from PyQt4.QtGui import QTextEdit
from PyQt4.QtGui import QColor
from PyQt4.QtGui import QFontMetricsF
from PyQt4.QtGui import QPainter
from PyQt4.QtGui import QFont
from PyQt4.QtGui import QTextCursor
from PyQt4.QtGui import QTextOption
from PyQt4.QtGui import QTextDocument
from PyQt4.QtGui import QCompleter

from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL
from PyQt4.QtCore import QRect
from PyQt4.QtCore import QString

from PyQt4.Qt import QVariant
from PyQt4.Qt import QTextFormat

from edis_c import recursos
from edis_c.nucleo import configuraciones
from edis_c.interfaz import tabitem
from edis_c.interfaz.editor import widget_numero_lineas
from edis_c.interfaz.editor import minimapa
from edis_c.interfaz.editor import acciones_
from edis_c.interfaz.editor.highlighter import Highlighter
from edis_c.interfaz import completador

# Diccionario teclas
TECLA = {
    'TABULACION': Qt.Key_Tab,
    'ENTER': Qt.Key_Return,
    'LLAVE': Qt.Key_BraceLeft,
    'PARENTESIS': Qt.Key_ParenLeft,
    'CORCHETE': Qt.Key_BracketLeft,
    'BACKSPACE': Qt.Key_Backspace
    }


class Editor(QPlainTextEdit, tabitem.TabItem):
    """ Editor """

    def __init__(self, nombre_archivo):
        QPlainTextEdit.__init__(self)
        tabitem.TabItem.__init__(self)

        self.set_flags()
        font_metrics = QFontMetricsF(self.document().defaultFont())
        self.posicion_margen = font_metrics.width('#') * 80
        #self.widget_num_lineas = widget_numero_lineas.NumeroDeLineaBar(self)

        self.texto_modificado = False
        self.guia_indentacion = 0
        self.nuevo_archivo = True
        self.patronEsPalabra = re.compile('\w+')
        self.guardado_actualmente = False
        self.widget_num_lineas = None
        self.highlighter = None
        self.palabra_seleccionada = ''
        self.minimapa = None
        self.braces = None
        self.extraSelections = []
        # Carga el tema de editor
        self.estilo_editor()
        # Completador
        self.completador = None
        if not self.completador:
            self.set_completador(completador.Completador())
        # Carga el tipo de letra
        self._cargar_fuente(configuraciones.FUENTE, configuraciones.TAM_FUENTE)

        # Sidebar
        if configuraciones.SIDEBAR:
            self.widget_num_lineas = widget_numero_lineas.NumeroDeLineaBar(self)

        # Resaltado de sintáxis
        if self.highlighter is None:
            self.highlighter = Highlighter(self.document())

        # Resaltado en posición del cursor
        self.resaltar_linea_actual()

        self.prePresionado = {
            TECLA.get('TABULACION'): self._indentar,
            TECLA.get('BACKSPACE'): self.__tecla_backspace
            }

        self.postPresionado = {
            TECLA.get('ENTER'): self._auto_indentar,
            TECLA.get('LLAVE'): self._completar_braces,
            TECLA.get('CORCHETE'): self._completar_braces,
            TECLA.get('PARENTESIS'): self._completar_braces
            }

        self.connect(self, SIGNAL("undoAvailable(bool)"), self._guardado)
        self.connect(self, SIGNAL("cursorPositionChanged()"),
            self.resaltar_linea_actual)
        #self.connect(self, SIGNAL("blockCountChanged(int)"),
            #self.actualizar_metadata)
        if self.widget_num_lineas is not None:
            self.connect(self, SIGNAL("updateRequest(const QRect&, int)"),
                self.widget_num_lineas.actualizar_area)

        # Minimapa
        if configuraciones.MINIMAPA:
            self.minimapa = minimapa.MiniMapa(self)
            self.minimapa.show()
            self.connect(self, SIGNAL("updateRequest(const QRect&, int)"),
                self.minimapa.actualizar_area_visible)
            self.minimapa.highlighter = Highlighter(self.minimapa.document())

    def cargar_id(self, id_):
        super(Editor, self).cargar_id(id_)
        self.minimapa.set_code(self.toPlainText())

    def estilo_editor(self):
        """ Aplica estilos de colores al editor """

        tema_editor = 'QPlainTextEdit {color: %s; background-color: %s;' \
        'selection-background-color: %s; selection-color: %s;}' \
        % (recursos.NUEVO_TEMA.get('texto-editor',
        recursos.TEMA_EDITOR['texto-editor']),
        recursos.NUEVO_TEMA.get('fondo-editor',
        recursos.TEMA_EDITOR['fondo-editor']),
        recursos.NUEVO_TEMA.get('fondo-seleccion-editor',
        recursos.TEMA_EDITOR['fondo-seleccion-editor']),
        recursos.NUEVO_TEMA.get('seleccion-editor',
        recursos.TEMA_EDITOR['seleccion-editor']))
        self.setStyleSheet(tema_editor)

    def set_flags(self):
        if not configuraciones.MODO_ENVOLVER:
            self.setWordWrapMode(QTextOption.NoWrap)
        else:
            self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.setMouseTracking(True)
        doc = self.document()
        op = QTextOption()
        if configuraciones.MOSTRAR_TABS:
            op.setFlags(QTextOption.ShowTabsAndSpaces)
        doc.setDefaultTextOption(op)
        self.setDocument(doc)

    def mouseReleaseEvent(self, event):
        """ Actualiza highlight según un evento del mouse. """

        QPlainTextEdit.mouseReleaseEvent(self, event)

    def resizeEvent(self, event):
        """ Redimensiona la altura del widget. """

        QPlainTextEdit.resizeEvent(self, event)
        if self.widget_num_lineas is not None:
            self.widget_num_lineas.setFixedHeight(self.height())
        if self.minimapa:
            self.minimapa.ajustar_()

    def wheelEvent(self, evento):
        if evento.modifiers() == Qt.ControlModifier:
            if evento.delta() == 120:
                self.zoom_mas()
            elif evento.delta() == -120:
                self.zoom_menos()
            evento.ignore()
        QPlainTextEdit.wheelEvent(self, evento)

    def devolver_cantidad_de_lineas(self):
        return self.blockCount()

    def texto_abajo(self):
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        palabra = cursor.selectedText()
        r = self.patronEsPalabra.findall(palabra)
        palabra = r[0] if r else ''
        return palabra

    def buscar_match(self, palabra, banderas, buscarSgt=False):
        banderas = QTextDocument.FindFlags(banderas)
        if buscarSgt:
            self.moveCursor(QTextCursor.NoMove, QTextCursor.KeepAnchor)
        else:
            self.moveCursor(QTextCursor.StartOfWord, QTextCursor.KeepAnchor)
        f = self.find(palabra, banderas)
        if not f:
            cursor = self.textCursor()
            self.moveCursor(QTextCursor.Start)
            f = self.find(palabra, banderas)
            if not f:
                self.setTextCursor(cursor)

    def set_selection_from_pair(self, inicio, fin):
        cursor = self.textCursor()
        cursor.setPosition(inicio)
        cursor.setPosition(fin, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)

    def paintEvent(self, event):
        """ Evento que dibuja el margen de línea."""

        QPlainTextEdit.paintEvent(self, event)
        if configuraciones.MOSTRAR_MARGEN:
            pintar = QPainter()
            pintar.begin(self.viewport())
            pintar.setPen(QColor(recursos.NUEVO_TEMA.get('margen-linea',
                recursos.TEMA_EDITOR['margen-linea'])))
            offset = self.contentOffset()
            ancho = self.viewport().width() - (self.posicion_margen +
                offset.x())
            rect = QRect(self.posicion_margen + offset.x(), -1,
                ancho + 1, self.viewport().height() + 3)
            fondo = QColor(recursos.NUEVO_TEMA.get('fondo-margen',
                recursos.TEMA_EDITOR['fondo-margen']))
            fondo.setAlpha(recursos.TEMA_EDITOR['opacidad'])
            pintar.fillRect(rect, fondo)
            pintar.drawRect(rect)
            pintar.drawLine(self.posicion_margen + offset.x(), 0,
                self.posicion_margen + offset.x(), self.viewport().height())
            pintar.end()

        altura = self.viewport().height()
        offset = self.contentOffset()
        pintar = QPainter()
        pintar.begin(self.viewport())
        color = QColor(200, 200, 0)
        color.setAlpha(100)
        pintar.setPen(color)
        pintar.pen().setCosmetic(True)
        altura_char = self.fontMetrics().height()
        bloque = self.firstVisibleBlock()
        previous_line = []

        while bloque.isValid():
            geo = self.blockBoundingGeometry(bloque)
            geo.translate(offset)
            posicion_y = geo.top()
            if posicion_y > altura:
                break
            col = (len(acciones_.devolver_espacios(
                bloque.text())) // configuraciones.INDENTACION)
            if col == 0:
                for l in previous_line:
                    pintar.drawLine(l, posicion_y, l, posicion_y + altura_char)
            else:
                previous_line = []
            for i in range(1, col):
                posicion_linea = self.inicio_indentacion + (
                    self.guia_indentacion * (i - 1))
                pintar.drawLine(posicion_linea, posicion_y, posicion_linea,
                    posicion_y + altura_char)
                previous_line.append(posicion_linea)
            bloque = bloque.next()
        pintar.end()

    def resaltar_linea_actual(self):
        """ Pinta la linea actual en donde está posicionado el cursor. """

        self.emit(SIGNAL("cursorPositionChange(int, int)"),
            self.textCursor().blockNumber() + 1,
            self.textCursor().columnNumber())
        self.extraSelections = []

        seleccion = QTextEdit.ExtraSelection()
        color = QColor(recursos.NUEVO_TEMA.get('linea-actual',
            recursos.TEMA_EDITOR['linea-actual']))
        color.setAlpha(40)
        seleccion.format.setBackground(color)
        seleccion.format.setProperty(
            QTextFormat.FullWidthSelection, QVariant(True))
        seleccion.cursor = self.textCursor()
        seleccion.cursor.clearSelection()
        self.extraSelections.append(seleccion)

        self.setExtraSelections(self.extraSelections)

        # Resaltado de braces
        if self.braces is not None:
            self.braces = None
        cursor = self.textCursor()
        if cursor.position() == 0:
            self.setExtraSelections(self.extraSelections)
            return
        cursor.movePosition(QTextCursor.PreviousCharacter,
            QTextCursor.KeepAnchor)

        texto = unicode(cursor.selectedText())
        p1 = cursor.position()
        if texto in (")", "]", "}"):
            p2 = self.m_braces(p1, texto, adelante=False)
        elif texto in ("(", "[", "{"):
            p2 = self.m_braces(p1, texto, adelante=True)
        else:
            self.setExtraSelections(self.extraSelections)
            return

        if p2 is not None:
            self.braces = (p1, p2)
            seleccion = QTextEdit.ExtraSelection()
            #brush = QBrush(Qt.blue, Qt.SolidPattern)
            seleccion.format.setForeground(QColor(Qt.blue))
            seleccion.cursor = cursor
            self.extraSelections.append(seleccion)
            seleccion = QTextEdit.ExtraSelection()
            seleccion.format.setForeground(QColor(Qt.blue))
            seleccion.format.setBackground(QColor(255, 0, 0))
            seleccion.cursor = self.textCursor()
            seleccion.cursor.setPosition(p2)
            seleccion.cursor.movePosition(QTextCursor.NextCharacter,
                QTextCursor.KeepAnchor)
            self.extraSelections.append(seleccion)
        else:
            self.braces = (p1,)
            seleccion = QTextEdit.ExtraSelection()
            seleccion.format.setBackground(QColor(255, 0, 0))
            seleccion.format.setForeground(QColor(Qt.blue))
            seleccion.cursor = cursor
            self.extraSelections.append(seleccion)
        self.setExtraSelections(self.extraSelections)

    def devolver_seleccion(self, inicio, fin):
        cursor = self.textCursor()
        cursor.setPosition(inicio)
        cursor2 = self.textCursor()
        if fin == QTextCursor.End:
            cursor2.movePosition(fin)
            cursor.setPosition(cursor2.position(), QTextCursor.KeepAnchor)
        else:
            cursor.setPosition(fin, QTextCursor.KeepAnchor)
        return unicode(cursor.selection().toPlainText())

    def __posicion_absoluta_en_texto(self, texto, pos):
        linea, pos_relativa = pos
        div_linea = linea - 1
        longitud = 0
        for cada_linea in texto.splitlines()[:div_linea]:
            longitud += len(cada_linea)
        return longitud + div_linea + pos_relativa

    def tokenize_text(self, texto):
        sintaxis_invalida = False
        token_buffer = []
        try:
        #texto = str(texto)
            for tkn_type, tkn_rep, tkn_begin, tkn_end, _ in \
                        generate_tokens(StringIO(texto).readline):
                token_buffer.append((tkn_type, tkn_rep, tkn_begin, tkn_end))
        except (TokenError, SyntaxError):
            sintaxis_invalida = True
        return (sintaxis_invalida, token_buffer)

    def m_braces(self, pos, brace, adelante):
        # de NINJA-IDE
        brace_d = {')': '(', ']': '[', '}': '{', '(': ')', '[': ']',
        '{': '}'}
        braceM = brace_d[brace]
        if adelante:
            texto = self.devolver_seleccion(pos, QTextCursor.End)
        else:
            texto = self.devolver_seleccion(QTextCursor.Start, pos)

        braces = []
        brace_buffer = []
        sintaxis_invalida, tokens = self.tokenize_text(texto)
        for tkn_tipo, tkn_rep, tkn_inicio, tkn_fin in tokens:
            if(tkn_tipo == tkn.OP) and (tkn_rep in brace_d):
                tkn_pos = adelante and tkn_inicio or tkn_fin
                brace_buffer.append((tkn_rep, tkn_pos))
        if not adelante:
            brace_buffer.reverse()
        if adelante and (not sintaxis_invalida):
            brace_buffer = brace_buffer[1:]

        for tkn_rep, tkn_posicion in brace_buffer:
            if (tkn_rep == braceM) and not braces:
                hl_position = \
                self.__posicion_absoluta_en_texto(texto, tkn_posicion)
                return adelante and hl_position + pos or hl_position
            elif braces and \
                (brace_d.get(tkn_rep, '') == braces[-1]):
                braces.pop(-1)
            else:
                braces.append(tkn_rep)

    def keyPressEvent(self, evento):
        #if self.completador and self.completador.popup().isVisible():
            #if evento.key() in (
            #Qt.Key_Enter,
            #Qt.Key_Return,
            #Qt.Key_Escape,
            #Qt.Key_Tab,
            #Qt.Key_Backtab):
                #evento.ignore()
                #return

        #isShortcut = (evento.modifiers() == Qt.ControlModifier and
                      #evento.key() == Qt.Key_E)
        #if (not self.completador or not isShortcut):

            #QPlainTextEdit.keyPressEvent(self, evento)

        #ctrlOrShift = evento.modifiers() in (Qt.ControlModifier,
                #Qt.ShiftModifier)
        #if ctrlOrShift and evento.text().isEmpty():
            #return

        #eow = QString("~!@#$%^&*()_+{}|:\"<>?,./;'[]\\-=")  # fin de palabra

        #hasModifier = ((evento.modifiers() != Qt.NoModifier) and
                        #not ctrlOrShift)

        #completionPrefix = QString(self.texto_abajo())

        #if (not isShortcut and (hasModifier or evento.text().isEmpty() or
        #completionPrefix.length() < 3 or
        #eow.contains(evento.text().right(1)))):
            #self.completador.popup().hide()
            #return

        #if (completionPrefix != self.completador.completionPrefix()):
            #self.completador.setCompletionPrefix(completionPrefix)
            #popup = self.completador.popup()
            #popup.setCurrentIndex(
                #self.completador.completionModel().index(0, 0))

        #cr = self.cursorRect()
        #cr.setWidth(self.completador.popup().sizeHintForColumn(0)
            #+ self.completador.popup().verticalScrollBar().sizeHint().width())
        #self.completador.complete(cr)

        if self.prePresionado.get(evento.key(), lambda a: False)(evento):
            self.emit(SIGNAL("keyPressEvent(QEvent)"), evento)
            return
        QPlainTextEdit.keyPressEvent(self, evento)

        self.postPresionado.get(evento.key(), lambda a: False)(evento)
        self.emit(SIGNAL("keyPressEvent(QEvent)"), evento)

    def _indentar(self, evento):
        """ Inserta 4 espacios si se presiona la tecla Tab """

        if configuraciones.CHECK_INDENTACION:
            self.textCursor().insertText(' ' * configuraciones.INDENTACION)
            return True
        return False

    def _auto_indentar(self, evento):
        """ Inserta automáticamente 4 espacios después de presionar Enter,
        previamente escrito '{' """
        if configuraciones.CHECK_AUTO_INDENTACION:
            texto = self.textCursor().block().previous().text()
            espacios = self.__indentacion(texto, configuraciones.INDENTACION)
            self.textCursor().insertText(espacios)

            cursor = self.textCursor()
            cursor.setPosition(cursor.position())
            self.setTextCursor(cursor)
            #self.moveCursor(QTextCursor.Left)

    def _completar_braces(self, evento):
        dic_braces = {'(': ')', '{': '}', '[': ']'}

        brace = str(evento.text())
        brac = QString(dic_braces.get(brace))
        self.textCursor().insertText(brac)
        self.moveCursor(QTextCursor.Left)

    def devolver_texto(self):
        """ Retorna todo el contenido del editor """

        return unicode(self.toPlainText())

    def __tecla_backspace(self, event):
        if self.textCursor().hasSelection():
            return False

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
        texto = unicode(cursor.selection().toPlainText())

        if(len(texto) % configuraciones.INDENTACION == 0) and texto.isspace():
            cursor.movePosition(QTextCursor.StartOfLine)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor,
                configuraciones.INDENTACION)
            cursor.removeSelectedText()

            return True

    def tabulaciones_por_espacios_en_blanco(self):
        acciones_.tabulaciones_por_espacios_en_blanco(self)

    def _cargar_fuente(self, fuente_=configuraciones.FUENTE,
        tam=configuraciones.TAM_FUENTE):

            fuente = QFont(fuente_, tam)
            self.document().setDefaultFont(fuente)
            self.actualizar_margen_linea(fuente)

    def zoom_mas(self):
        fuente = self.document().defaultFont()
        tam = fuente.pointSize()

        if tam < configuraciones.FUENTE_MAX_TAM:
            tam += 1
            fuente.setPointSize(tam)

        self.setFont(fuente)
        self.actualizar_margen_linea(fuente)

    def zoom_menos(self):
        fuente = self.document().defaultFont()
        tam = fuente.pointSize()

        if tam > configuraciones.FUENTE_MIN_TAM:
            tam -= 1
            fuente.setPointSize(tam)

        self.setFont(fuente)
        self.actualizar_margen_linea(fuente)

    def actualizar_margen_linea(self, fuente=None):
        if not fuente:
            fuente = self.document().defaultFont()
        if "ForceIntegerMetrics" in dir(QFont):
            self.document().defaultFont().setStyleStrategy(
                QFont.ForceIntegerMetrics)

        f_metrics = QFontMetricsF(self.document().defaultFont())
        if (f_metrics.width("#") * configuraciones.MARGEN) == \
        (f_metrics.width(" ") * configuraciones.MARGEN):
            self.posicion_margen = f_metrics.width('#') * \
               configuraciones.MARGEN
        else:
            c_width = f_metrics.averageCharWidth()
            self.posicion_margen = c_width * configuraciones.MARGEN

        self.char_width = f_metrics.averageCharWidth()
        if configuraciones.INDENTACION:
            self.guia_indentacion = self.char_width * \
                configuraciones.INDENTACION
            self.inicio_indentacion = (-(self.char_width / 2) +
                                self.guia_indentacion + self.char_width)

    def saltar_a_linea(self, linea=None):
        if linea is not None:
            self.emit(SIGNAL("addBackItemNavigation()"))
            self.ir_a_linea(linea)
            return

    def ir_a_linea(self, linea):
        self.unfold_blocks_for_jump(linea)
        if self.blockCount() >= linea:
            cursor = self.textCursor()
            cursor.setPosition(self.document().findBlockByLineNumber(
                linea).position())
            self.setTextCursor(cursor)

    def unfold_blocks_for_jump(self, linea):
        for l in self.widget_num_lineas._foldedBlocks:
            if linea >= l:
                self.widget_num_lineas.code_folding_event(l + 1)
            else:
                break

    def indentar_mas(self):
        cursor = self.textCursor()
        bloque = self.document().findBlock(cursor.selectionStart())
        fin = self.document().findBlock(cursor.selectionEnd()).next()

        cursor.beginEditBlock()

        cursor.setPosition(bloque.position())

        while bloque != fin:
            cursor.setPosition(bloque.position())
            cursor.insertText(' ' * configuraciones.INDENTACION)
            bloque = bloque.next()

        cursor.endEditBlock()

    def indentar_menos(self):
        cursor = self.textCursor()
        if not cursor.hasSelection():
            cursor.movePosition(QTextCursor.EndOfLine)

        bloque = self.document().findBlock(cursor.selectionStart())
        fin = self.document().findBlock(cursor.selectionEnd()).next()

        cursor.beginEditBlock()

        cursor.setPosition(bloque.position())

        while bloque != fin:
            cursor.setPosition(bloque.position())
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor,
                configuraciones.INDENTACION)
            texto = cursor.selectedText()
            if texto == ' ' * configuraciones.INDENTACION:
                cursor.removeSelectedText()
            bloque = bloque.next()

        cursor.endEditBlock()

    def _guardado(self, uA=False):
        if not uA:
            self.emit(SIGNAL("fileSaved(QPlainTextEdit)"), self)
            self.nuevo_archivo = False
            self.texto_modificado = False
            self.document().setModified(self.texto_modificado)

    def __indentacion(self, linea, ind=configuraciones.INDENTACION):
        import re
        patronInd = re.compile('^\s+')
        indentacion = ''

        if len(linea) > 0 and linea[-1] == '{':
            indentacion = ' ' * ind
        espacio = patronInd.match(linea)
        if espacio is not None:
            return espacio.group() + indentacion

        return indentacion

    def set_completador(self, completador):
        if self.completador:
            self.disconnect(self.completador, 0, self, 0)
        if not completador:
            return

        completador.setWidget(self)
        completador.setCompletionMode(QCompleter.PopupCompletion)
        completador.setCaseSensitivity(Qt.CaseInsensitive)
        self.completador = completador
        self.connect(self.completador,
            SIGNAL("activated(const QString&)"), self.insertar_completado)

    def insertar_completado(self, completion):
        tc = self.textCursor()
        extra = (completion.length() -
            self.completador.completionPrefix().length())
        tc.movePosition(QTextCursor.Left)
        tc.movePosition(QTextCursor.EndOfWord)
        tc.insertText(completion.right(extra))
        self.setTextCursor(tc)


def crear_editor(nombre_archivo=''):
    editor = Editor(nombre_archivo)

    return editor