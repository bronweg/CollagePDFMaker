import sys
import os
import json
import placement
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QLineEdit, QFileDialog, QComboBox, QMessageBox, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import (QIcon, QPixmap)

def load_language_codes():
    path = "locales/language_codes.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_language_names():
    language_codes = load_language_codes()
    return list(language_codes.keys())

def load_translations(language_name):
    language_codes = load_language_codes()
    language_code = language_codes.get(language_name, "en")
    path = f"locales/{language_code}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

class PDFCreatorThread(QThread):
    creationStarted = Signal()
    progressUpdated = Signal(int, str)
    creationFinished = Signal()

    def __init__(self, images, output_pdf_path, margin, min_size):
        super().__init__()
        self.images = images
        self.output_pdf_path = output_pdf_path
        self.margin = margin
        self.min_size = min_size

    def run(self):
        self.creationStarted.emit()
        placement.place_images_on_pdf(self.images, self.output_pdf_path, self.margin, self.min_size, self.updateProgress)
        self.creationFinished.emit()

    def updateProgress(self, value, label=None):
        self.progressUpdated.emit(value, label)

class ImageToPDFConverter(QWidget):
    def __init__(self):
        super().__init__()
        settings = self.loadSettings()
        self.setLanguage(settings)
        self.translations = load_translations(self.currentLanguage)
        self.setWindowTitle(self.tr("CollagePDFMaker"))
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.setupUI()
        self.applySettings(settings)
        self.langComboBox.setCurrentText(self.currentLanguage)
        self.changeLanguage(self.currentLanguage)

    def setupUI(self):
        # Update Logo
        self.logoLabel = QLabel(self)
        self.logoPixmap = QPixmap("images/logo.png")
        scaledLogoPixmap = self.logoPixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logoLabel.setPixmap(scaledLogoPixmap)
        self.logoLabel.setFixedSize(scaledLogoPixmap.size())
        self.layout.addWidget(self.logoLabel)

        # Language selection
        self.languageLabel = QLabel(self.tr("Language:"))
        self.langComboBox = QComboBox()
        language_names = load_language_names()
        self.langComboBox.addItems(language_names)
        self.langComboBox.currentTextChanged.connect(self.changeLanguage)
        langLayout = QHBoxLayout()
        langLayout.addWidget(self.languageLabel)
        langLayout.addWidget(self.langComboBox)
        self.layout.addLayout(langLayout)

        # Directory selection
        self.dirLabel = QLabel(self.tr("Directory with Images:"))
        self.dirLineEdit = QLineEdit()
        self.dirButton = QPushButton(self.tr("Choose..."))
        self.dirButton.clicked.connect(self.chooseDirectory)
        self.dirLayout = QHBoxLayout()
        self.dirLayout.addWidget(self.dirLabel)
        self.dirLayout.addWidget(self.dirLineEdit)
        self.dirLayout.addWidget(self.dirButton)
        self.layout.addLayout(self.dirLayout)

        # Output file selection
        self.fileLabel = QLabel(self.tr("Output PDF Path:"))
        self.fileLineEdit = QLineEdit()
        self.fileButton = QPushButton(self.tr("Choose..."))
        self.fileButton.clicked.connect(self.chooseOutputFile)
        self.fileLayout = QHBoxLayout()
        self.fileLayout.addWidget(self.fileLabel)
        self.fileLayout.addWidget(self.fileLineEdit)
        self.fileLayout.addWidget(self.fileButton)
        self.layout.addLayout(self.fileLayout)

        # Max width and height
        self.maxWidthLabel = QLabel(self.tr("Max Image Width (cm):"))
        self.maxWidthLineEdit = QLineEdit()
        self.maxHeightLabel = QLabel(self.tr("Max Image Height (cm):"))
        self.maxHeightLineEdit = QLineEdit()
        self.layout.addWidget(self.maxWidthLabel)
        self.layout.addWidget(self.maxWidthLineEdit)
        self.layout.addWidget(self.maxHeightLabel)
        self.layout.addWidget(self.maxHeightLineEdit)

        # Margin
        self.marginLabel = QLabel(self.tr("Margin (cm):"))
        self.marginLineEdit = QLineEdit("0.3")
        self.layout.addWidget(self.marginLabel)
        self.layout.addWidget(self.marginLineEdit)

        # Process button
        self.processButton = QPushButton(self.tr("Process Images"))
        self.processButton.clicked.connect(self.processImages)
        self.layout.addWidget(self.processButton)

        # Progress Bar Label
        self.progressLabel = QLabel("")
        self.layout.addWidget(self.progressLabel)

        # Progress Bar
        self.progressBar = QProgressBar(self)
        self.progressBar.setMaximum(100)  # 100% completion
        self.progressBar.setValue(0)  # start value
        self.layout.addWidget(self.progressBar)

    def onPDFCreationStarted(self):
        self.processButton.setEnabled(False)
        self.saveSettings(self.currentLanguage, self.dirLineEdit.text(), self.fileLineEdit.text(),
                          self.maxWidthLineEdit.text(), self.maxHeightLineEdit.text())

    def updateProgressBar(self, value, label):
        if label:
            self.progressLabel.setText(self.tr(label))
        self.progressBar.setValue(value)

    def onPDFCreationFinished(self):
        QMessageBox.information(self, self.tr("success_title"), self.tr("success_message"))
        self.progressLabel.setText(self.tr("finished"))
        self.processButton.setEnabled(True)

    def isValidNumber(self, value):
        try:
            val = float(value)
            return val > 0
        except ValueError:
            return False

    def saveSettings(self, language, directory="", outputPath="", maxWidth="", maxHeight=""):
        settings = {
        'language': language,
        'directory': directory,
        'outputPath': outputPath,
        'maxWidth': maxWidth,
        'maxHeight': maxHeight
        }
        with open('settings.json', 'w') as f:
            json.dump(settings, f)

    def loadSettings(self):
        default_settings = {
            'language': 'English',
            'directory': '',
            'outputPath': '',
            'maxWidth': '',
            'maxHeight': ''
        }
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
        except FileNotFoundError:
            settings = default_settings

        return settings

    def setLanguage(self, settings):
        self.currentLanguage = settings.get('language', 'English')

    def applySettings(self, settings):
        self.dirLineEdit.setText(settings.get('directory', ''))
        self.fileLineEdit.setText(settings.get('outputPath', ''))
        self.maxWidthLineEdit.setText(settings.get('maxWidth', ''))
        self.maxHeightLineEdit.setText(settings.get('maxHeight', ''))

    def chooseDirectory(self):
        dirPath = QFileDialog.getExistingDirectory(self, self.tr("Select Directory"))
        self.dirLineEdit.setText(dirPath)

    def chooseOutputFile(self):
        filePath, _ = QFileDialog.getSaveFileName(self, self.tr("Select Output PDF"), filter="PDF files (*.pdf)")
        self.fileLineEdit.setText(filePath)

    def processImages(self):
        if not os.path.isdir(self.dirLineEdit.text()):
            QMessageBox.warning(self, self.tr("error_title"), self.tr("directory_not_found"))
            return

        if not self.dirLineEdit.text() or not self.fileLineEdit.text():
            QMessageBox.warning(self, self.tr("error_title"), self.tr("no_in_or_out"))
            return

        if not self.isValidNumber(self.maxWidthLineEdit.text()) or not self.isValidNumber(
                self.maxHeightLineEdit.text()):
            QMessageBox.warning(self, self.tr("error_title"), self.tr("invalid_input"))
            return

        directory = self.dirLineEdit.text()
        output_pdf_path = self.fileLineEdit.text()
        max_width_cm = float(self.maxWidthLineEdit.text())
        max_height_cm = float(self.maxHeightLineEdit.text())
        margin_cm = float(self.marginLineEdit.text())
        margin_points = placement.cm_to_points(margin_cm)
        images, min_size = placement.collect_and_resize_images(directory, max_width_cm, max_height_cm)

        if not images:
            QMessageBox.warning(self, self.tr("error_title"), self.tr("no_images_found"))
            return
        try:
            self.pdfThread = PDFCreatorThread(images, output_pdf_path, margin_points, min_size)
            self.pdfThread.creationStarted.connect(self.onPDFCreationStarted)
            self.pdfThread.progressUpdated.connect(self.updateProgressBar)
            self.pdfThread.creationFinished.connect(self.onPDFCreationFinished)
            self.pdfThread.start()
        except Exception as e:
            errorMessage = f"{self.tr('pdf_creation_failed')} {str(e)}"
            QMessageBox.warning(self, self.tr("error_title"), errorMessage)

    def changeLanguage(self, language):
        self.currentLanguage = language
        self.translations = load_translations(language)
        self.saveSettings(language, self.dirLineEdit.text(), self.fileLineEdit.text(),
                      self.maxWidthLineEdit.text(), self.maxHeightLineEdit.text())

        # Update texts
        self.setWindowTitle(self.tr("title"))
        self.dirLabel.setText(self.tr("directory_label"))
        self.fileLabel.setText(self.tr("output_label"))
        self.maxWidthLabel.setText(self.tr("max_width"))
        self.maxHeightLabel.setText(self.tr("max_height"))
        self.marginLabel.setText(self.tr("margin"))
        self.processButton.setText(self.tr("process_button"))
        self.dirButton.setText(self.tr("choose_directory"))
        self.fileButton.setText(self.tr("choose_output"))

        # Update layout
        is_rtl = (language == "עברית")
        self.dirLayout.setDirection(QHBoxLayout.RightToLeft if is_rtl else QHBoxLayout.LeftToRight)
        self.fileLayout.setDirection(QHBoxLayout.RightToLeft if is_rtl else QHBoxLayout.LeftToRight)

    def tr(self, text_key):
        return self.translations.get(text_key, text_key)

if __name__ == "__main__":
    if hasattr(sys, '_MEIPASS'):
        os.chdir(sys._MEIPASS)
    app = QApplication(sys.argv)
    window = ImageToPDFConverter()
    window.show()
    sys.exit(app.exec())

