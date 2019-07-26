import os
import re
import signal
import sys

from PySide2.QtCore import *
from PySide2 import QtCore
from PySide2.QtGui import *
from PySide2.QtWidgets import *
from ui_gui import Ui_MainWindow
from parseGUI import LoadInterfaces, FileChecker
from CDSLDocument import CDSLDocument
from parseCDSL import CDSLParsing

# DETECT THE ROBOCOMP INSTALLATION TO IMPORT RCPORTCHECKER CLASS
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROBOCOMP = ''
ROBOCOMP_COMP_DIR = os.path.join(os.path.expanduser("~"), "robocomp", "components")
ROBOCOMPDSL_DIR = os.path.join(CURRENT_DIR, "..", "robocompdsl")

try:
    ROBOCOMP = os.environ['ROBOCOMP']
except:
    default_robocomp_path = '/opt/robocomp'
    print('ROBOCOMP environment variable not set! Trying default directory (%s)' % (default_robocomp_path))
    if os.path.exists(default_robocomp_path) and os.path.isdir(default_robocomp_path):
        if not os.listdir(default_robocomp_path):
            print("Default Robocomp directory (%s) exists but it's empty. Exiting!" % (default_robocomp_path))
            sys.exit()
        else:
            ROBOCOMP = default_robocomp_path
    else:
        print("Default Robocomp directory (%s) doesn't exists. Exiting!" % (default_robocomp_path))
        sys.exit()
# sys.path.append(os.path.join(ROBOCOMP, "tools/rcportchecker"))

ROBOCOMP_INTERFACES = os.path.join(ROBOCOMP, "interfaces")
if not os.path.isdir(ROBOCOMP_INTERFACES):
    new_path = os.path.join(os.path.expanduser("~"), "robocomp", "interfaces")
    print('ROBOCOMP INTERFACES not found at %s! Trying HOME directory (%s)' % (ROBOCOMP_INTERFACES, new_path))
    ROBOCOMP_INTERFACES = new_path
    if not os.path.isdir(ROBOCOMP_INTERFACES):
        print("Default Robocomp INTERFACES directory (%s) doesn't exists. Exiting!" % (ROBOCOMP_INTERFACES))
        sys.exit()

class CDSLLanguage:
    CPP = "CPP"
    PYTHON = "Python"

class CDSLGui:
    QWIDGET = "QWidget"
    QDIALOG = "QDialog"
    QMAINWINDOW = "QMainWindow"

class Highlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super(Highlighter, self).__init__(parent)

        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(Qt.darkBlue)
        keywordFormat.setFontWeight(QFont.Bold)

        keywordPatterns = ["\\bimport\\b", "\\bcomponent\\b", "\\bcommunications\\b",
                "\\bpublishes\\b", "\\bimplements\\b", "\\bsubscribesTo\\b", "\\brequires\\b",
                "\\blanguage\\b", "\\bgui\\b", "\\boptions\\b","\\binnerModelViewer\\b","\\bstateMachine\\b","\\bmodules\\b","\\bagmagent\\b"]

        self.highlightingRules = [(QRegExp(pattern), keywordFormat)
                for pattern in keywordPatterns]

        self.multiLineCommentFormat = QTextCharFormat()
        self.multiLineCommentFormat.setForeground(Qt.red)

        self.commentStartExpression = QRegExp("/\\*")
        self.commentEndExpression = QRegExp("\\*/")

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)

        startIndex = 0
        if self.previousBlockState() != 1:
            startIndex = self.commentStartExpression.indexIn(text)

        while startIndex >= 0:
            endIndex = self.commentEndExpression.indexIn(text, startIndex)

            if endIndex == -1:
                self.setCurrentBlockState(1)
                commentLength = len(text) - startIndex
            else:
                commentLength = endIndex - startIndex + self.commentEndExpression.matchedLength()

            self.setFormat(startIndex, commentLength,
                    self.multiLineCommentFormat)
            startIndex = self.commentStartExpression.indexIn(text,
                    startIndex + commentLength);


class RoboCompDSLGui(QMainWindow):
    def __init__(self):
        self.newLines = 1 ########################################################################################
        super(RoboCompDSLGui, self).__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self._communications = {"implements": [], "requires": [], "subscribesTo": [], "publishes": []}
        self._interfaces = {}
        self._cdsl_doc = CDSLDocument()
        self._command_process = QProcess()

        #TESTING
        self._cdsl_doc.languageChange.connect(self.updateLanguageCombo)
        self.parser = CDSLParsing(self._cdsl_doc)
        self.file_checker = FileChecker()
        #TODO => Deleted when not needed
        self.ui.mainTextEdit.setPlainText("""import "DifferentialRobot.idsl";
        import "Laser.idsl";

        Component Comp1
        {
        	Communications

        	{
        		requires DifferentialRobot;
        		implements Laser;

        	};
        	language cpp;
        	gui Qt(QWidget);

        };""")
        self.ui.mainTextEdit.textChanged.connect(self.parseText)

        #COMPONENT NAME
        self.ui.nameLineEdit.textEdited.connect(self.update_component_name)

        #DIRECTORY SELECTION
        self._dir_completer = QCompleter()
        self._dir_completer_model = QFileSystemModel()
        if os.path.isdir(ROBOCOMP_COMP_DIR):
            self.ui.directoryLineEdit.setText(ROBOCOMP_COMP_DIR)
            self._dir_completer_model.setRootPath(ROBOCOMP_COMP_DIR)
        self._dir_completer.setModel(self._dir_completer_model)
        self.ui.directoryLineEdit.setCompleter(self._dir_completer)
        self.ui.directoryButton.clicked.connect(self.set_output_directory)

        #CUSTOM INTERFACES LIST WIDGET
        self._interface_list = customListWidget(self.ui.centralWidget)
        self.ui.gridLayout.addWidget(self._interface_list, 4, 0, 9, 2)
        self._interface_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._interface_list.customItemSelection.connect(self.set_comunication)

        #LIST OF CONNECTION TYPES
        self.ui.communicationsComboBox.currentIndexChanged.connect(self.reselect_existing)

        #LANGUAGE
        self.ui.languageComboBox.currentIndexChanged.connect(self.update_language)

        #GUI CHECKBOX
        self.ui.guiCheckBox.stateChanged.connect(self.update_gui)

        #GUI COMBOBOX
        self.ui.guiComboBox.currentIndexChanged.connect(self.update_gui_combo)

        #AGMAGENT CHECKBOX
        self.ui.agmagentCheckBox.stateChanged.connect(self.update_agmagent_selection)

        #INNERMODEL CHECKBOX
        self.ui.innermodelCheckBox.stateChanged.connect(self.update_innerModel_selection)

        #MAIN TEXT EDITOR
        #self.ui.mainTextEdit.setHtml("")
        self._document = self.ui.mainTextEdit.document()
        self._component_directory = None
        #self.ui.mainTextEdit.setText(self._cdsl_doc.generate_doc())
#        self.ui.mainTextEdit.setPlainText(self._cdsl_doc.generate_doc())


        #CONSOLE
        self._console = QConsole(self.ui.centralWidget)
        self.ui.gridLayout.addWidget(self._console, 14, 0, 4, 3)
        self._command_process.readyReadStandardOutput.connect(self._console.standard_output)
        self._command_process.readyReadStandardError.connect(self._console.error_output)

        #RESET BUTTON
        self.ui.resetButton.clicked.connect(self.reset_cdsl_file)

        #CREATION BUTTON
        self.ui.createButton.clicked.connect(self.write_cdsl_file)

        #GENERATE BUTTON
        self.ui.generateButton.clicked.connect(self.robocompdsl_generate_component)

        self.setupEditor()
        self.load_idsl_files()

    def setupEditor(self):
        self.highlighter = Highlighter(self.ui.mainTextEdit.document())

    def load_idsl_files(self):
        idsls_dir = os.path.join(ROBOCOMP_INTERFACES, "IDSLs")
        self._interfaces = LoadInterfaces.load_all_interfaces(LoadInterfaces, idsls_dir)
        self._interface_list.addItems(list(self._interfaces.keys()))

    def set_comunication(self):
        interfaces_names = self._interface_list.customItemList()
        com_type = str(self.ui.communicationsComboBox.currentText())
        self._communications[com_type] = []
        self._cdsl_doc.clear_comunication(com_type)
        for iface_name_item in interfaces_names:
            iface_name = iface_name_item
            self._communications[com_type].append(iface_name)
            self._cdsl_doc.add_comunication(com_type, iface_name)
        self.update_imports()
        self.update_editor()

    def update_imports(self):
        self._cdsl_doc.clear_imports()
        for com_type in self._communications:
            for iface_name in self._communications[com_type]:
                imports_list = LoadInterfaces.get_files_from_interface(iface_name)
                for imp in imports_list:
                    idsl_full_filename = imp
                    self._cdsl_doc.add_import(idsl_full_filename)

    def update_gui(self):
        checked = self.ui.guiCheckBox.isChecked()
        if checked:
            self._cdsl_doc.set_qui(True)
            self.ui.guiComboBox.setEnabled(True)
        else:
            self._cdsl_doc.set_qui(False)
            self.ui.guiComboBox.setEnabled(False)
        self.update_editor()

    def update_gui_combo(self):
        gui_combo = self.ui.guiComboBox.currentText()
        self._cdsl_doc.set_gui_combo(str(gui_combo))
        self.update_editor()

    def update_agmagent_selection(self):
        checked = self.ui.agmagentCheckBox.isChecked()
        if checked:
            self._cdsl_doc.set_agmagent(True)
        else:
            self._cdsl_doc.set_agmagent(False)
        self.update_editor()

    def update_innerModel_selection(self):
        checked = self.ui.innermodelCheckBox.isChecked()
        if checked:
            self._cdsl_doc.set_innerModel(True)
        else:
            self._cdsl_doc.set_innerModel(False)
        self.update_editor()

    def update_component_name(self, name):
        self._cdsl_doc.set_name(name)
        self.update_editor()

    def update_editor(self):
        self.ui.mainTextEdit.setPlainText(self._cdsl_doc.generate_doc())

    def set_output_directory(self):
        dir_set = False
        while not dir_set:
            dir = QFileDialog.getExistingDirectory(self, "Select Directory",
                                                   ROBOCOMP_COMP_DIR,
                                                   QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
            if self.check_dir_is_empty(str(dir)):
                self.ui.directoryLineEdit.setText(dir)
                dir_set = True

    def reset_cdsl_file(self):
        self._communications = {"implements": [], "requires": [], "subscribesTo": [], "publishes": []}
        self._interfaces = {}
        self._cdsl_doc.clear()
        self._command_process = QProcess()
        self.update_editor()
        self._console.clear_console()

    def write_cdsl_file(self):
        component_dir = str(self.ui.directoryLineEdit.text())
        #text = self._cdsl_doc.generate_doc()
        text = self.ui.mainTextEdit.toPlainText() # read content from main text editor
        if not self.ui.nameLineEdit.text():
            component_name, ok = QInputDialog.getText(self, 'No component name set', 'Enter component name:')
            if ok:
                self.update_component_name(component_name)
                text = self.ui.mainTextEdit.toPlainText() #update text to avoid errors
                self.ui.nameLineEdit.setText(component_name)
            else:
                return False

        if not os.path.exists(component_dir):
            if QMessageBox.Yes == QMessageBox.question(self,
                                                       "Directory doesn't exist.",
                                                       "Do you want create the directory %s?" % component_dir,
                                                       QMessageBox.Yes | QMessageBox.No):
                os.makedirs(component_dir)
            else:
                QMessageBox.question(self,
                                     "Directory not exist",
                                     "Can't create a component without a valid directory")
                return False

        file_path = os.path.join(component_dir, str(self.ui.nameLineEdit.text()) + ".cdsl")
        if os.path.exists(file_path):
            if QMessageBox.No == QMessageBox.question(self,
                                                      "File already exists",
                                                      "Do you want to overwrite?",
                                                      QMessageBox.Yes | QMessageBox.No):
                return False
        with open(file_path, 'w') as the_file:
            #check if file is written correctly returning error list
            errors = FileChecker.check_text(FileChecker, text) #error list
            if errors:
                for err in errors:
                    # Get wrong word from error line
                    error_word = err[0]
                    error_word = error_word.lstrip()
                    error_word = error_word.rstrip()
                    # if wrong_word
                    if error_word != '0':
                        self.highlight_error(error_word)
                    msg = str(err)
                    self._console.append_error_text(msg)
                return False
            else: #create cdsl file
                the_file.write(text)
                msg = "CDSL file created correctly!"
                self._console.append_custom_text(msg)
        return True

    def robocompdsl_generate_component(self):
        self.write_cdsl_file()
        self.execute_robocomp_cdsl()

    def execute_robocomp_cdsl(self):
        cdsl_file_path = os.path.join(str(self.ui.directoryLineEdit.text()), str(self.ui.nameLineEdit.text()) + ".cdsl")
        command = "python -u %s/robocompdsl.py %s %s" % (
            ROBOCOMPDSL_DIR, cdsl_file_path, os.path.join(str(self.ui.directoryLineEdit.text())))
        self._console.append_custom_text("%s\n" % command)
        self._command_process.start(command, QProcess.Unbuffered | QProcess.ReadWrite)

    def reselect_existing(self):
        com_type = self.ui.communicationsComboBox.currentText()
        selected = self._communications[com_type]
        #self.ui.interfacesListWidget.clearSelection()
        self._interface_list.clearItems()

        for iface in selected:
            items = self._interface_list.findItems(iface, Qt.MatchFlag.MatchExactly)
            if len(items) > 0:
                item = items[0]
                item.setSelected(True)

    def check_dir_is_empty(self, dir_path):
        if len(os.listdir(dir_path)) > 0:
            msgBox = QMessageBox()
            msgBox.setWindowTitle("Directory not empty")
            msgBox.setText("The selected directory is not empty.\n"
                           "For a new Component you usually want a new directory.\n"
                           "Do you want to use this directory anyway?")
            msgBox.setStandardButtons(QMessageBox.Yes)
            msgBox.addButton(QMessageBox.No)
            msgBox.setDefaultButton(QMessageBox.No)
            if msgBox.exec_() == QMessageBox.Yes:
                return True
            else:
                return False
        else:
            return True

    def highlight_error(self, error_str):
        self.ui.mainTextEdit.blockSignals(True)
        cursor = self.ui.mainTextEdit.textCursor()

        # Setup the desired format for matches
        format = QTextCharFormat()
        format.setBackground(QBrush(QColor("red")))

        # Setup the regex engine
        pattern = error_str
        regex = QtCore.QRegExp(pattern)

        # Process the main editor
        pos = 0
        index = regex.indexIn(self.ui.mainTextEdit.toPlainText(), pos)
        while (index != -1):
            # Select the matched text and apply the desired format
            cursor.setPosition(index)
            cursor.movePosition(QTextCursor.EndOfWord, cursor.KeepAnchor, 1)
            cursor.mergeCharFormat(format)
            # Move to the next match
            pos = index + regex.matchedLength()
            index = regex.indexIn(self.ui.mainTextEdit.toPlainText(), pos)
        self.ui.mainTextEdit.blockSignals(False)

    def closeEvent(self, event):
        QApplication.quit()
    #TODO UNCOMMENT
#        quit_msg = "Are you sure you want to exit?"
#        reply = QMessageBox.question(self, 'Message', quit_msg, QMessageBox.Yes, QMessageBox.No)
#        if reply == QMessageBox.Yes:
#            QApplication.quit()
#        else:
#            if event is not None:
#                event.ignore()

#TESTING
    @Slot()
    def updateLanguageCombo(self, language):
        #TODO maybe we need to disconnect signals before changing combo value
        print ("UPDATE COMBO")
        for index in range(self.ui.languageComboBox.count()):
            if self.ui.languageComboBox.itemText(index).lower() == language.lower():
                self.ui.mainTextEdit.blockSignals(True)
                self.ui.languageComboBox.blockSignals(True)
                self.ui.languageComboBox.setCurrentIndex(index)
                self.ui.mainTextEdit.blockSignals(False)
                self.ui.languageComboBox.blockSignals(False)
                break

    def update_language(self):
        language = self.ui.languageComboBox.currentText()
        self.ui.mainTextEdit.blockSignals(True)
        self._cdsl_doc.set_language(str(language))
        self.ui.mainTextEdit.blockSignals(False)
        self.update_editor()


    @Slot()
    def parseText(self):
        text = self.ui.mainTextEdit.toPlainText()
        file_dict, error = self.parser.analizeText(text)
        errors = self.file_checker.check_text(file_dict, error)
        if errors:
            for err in errors:
                # Get wrong word from error line
                error_word = err[0]
                error_word = error_word.lstrip()
                error_word = error_word.rstrip()
                # if wrong_word
                if error_word != '0':
                    self.highlight_error(error_word)
                msg = str(err)
                self._console.append_error_text(msg)
            return False



class QConsole(QTextEdit):
    def __init__(self, parent=None):
        super(QConsole, self).__init__(parent)
        font = QFont("Monospace",9)
        font.setStyleHint(QFont.TypeWriter)
        self.setFont(font)
        self.setTextColor(QColor("LightGreen"))
        self.setReadOnly(True)
        self.setMinimumSize(QtCore.QSize(0, 130))
        self.setStyleSheet("background-color: rgb(4, 11, 50);")
        #self.setObjectName("console")
        self.setText("> Welcome to Robocompdsl.")

    def append_custom_text(self, text):
        self.setTextColor(QColor("white"))
        self.append("> " + text)

    def append_error_text(self, text):
        self.setTextColor(QColor("yellow"))
        self.append("> " + text)

    def standard_output(self):
        self.setTextColor(QColor("LightGreen"))
        process = self.sender()
        text = process.readAllStandardOutput()
        self.append(str(text))

    def error_output(self):
        self.setTextColor(QColor("red"))
        process = self.sender()
        text = process.readAllStandardError()
        self.append(str(text))

    def clear_console(self):
        self.setText(" ")

class customListWidget(QListWidget):
    customItemSelection = Signal()

    def __init__(self, parent=None):
        super(customListWidget, self).__init__(parent)
        self.itemList = []
        self.setMinimumSize(QtCore.QSize(160, 0))
        self.setMaximumSize(QtCore.QSize(245, 16777215))
        # self.setObjectName("customListWidget")

    def mousePressEvent(self, event):
        super(customListWidget, self).mousePressEvent(event)
        item = self.itemAt(event.pos())
        if item:
            text = item.text().split(":")[0]
            # check button clicked
            if event.button() == Qt.LeftButton:
                if (event.modifiers() == Qt.ShiftModifier) or (event.modifiers() == Qt.ControlModifier):
                    self.itemList.append(text)
                else:
                    count = self.itemList.count(text)
                    self.clearItems()
                    for c in range(count + 1):
                        self.itemList.append(text)
            elif event.button() == Qt.RightButton:
                if text in self.itemList:
                    self.itemList.remove(text)

            # update list text
            count = self.itemList.count(text)
            self.itemAt(event.pos()).setSelected(count)
            if count:
                self.itemAt(event.pos()).setText(text + ":" + str(count))
            else:
                self.itemAt(event.pos()).setPlainText(text)

            self.customItemSelection.emit()
        else:
            self.clearItems()

    def clearItems(self):
        self.itemList = []
        for pos in range(self.count()):
            self.item(pos).setText(self.item(pos).text().split(":")[0])

    # return our custom selected item list
    def customItemList(self):
        return self.itemList

    # just for testing
    @Slot()
    def print(self):
        print("Selected items\n", self.itemList)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    gui = RoboCompDSLGui()
    signal.signal(signal.SIGINT, lambda self_, event_: gui.closeEvent(None))
    gui.show()

    sys.exit(app.exec_())


