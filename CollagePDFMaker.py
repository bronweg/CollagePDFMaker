from talelle_setup import Path, TALELLE_DIR, config_log
TALELLE_TOOL = Path(__file__).stem
config_log(TALELLE_TOOL)

import sys
import os
import json
import datetime
import placement

import logging
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QLineEdit, QFileDialog, QComboBox, QMessageBox, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap

logger = logging.getLogger(__name__)
logger.info(f'{TALELLE_TOOL} started')


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
        settings = self.load_settings()
        self.current_language = self.get_language(settings)
        self.translations = self.load_translations(self.current_language)
        self.project_path, self.project_folder = self.get_project_path(settings)
        self.images_folder = self.get_images_folder(settings)

        # declare QComponent groups
        self.locale_subjects = dict()
        self.direction_subjects = list()

        # declare QComponents
        self.langComboBox = None
        self.projLineEdit = None
        self.dirLineEdit = None
        self.fileLineEdit = None
        self.maxWidthLineEdit = None
        self.maxHeightLineEdit = None
        self.marginLineEdit = None
        self.processButton = None
        self.progressLabel = None
        self.progressStatus = None
        self.progressBar = None

        self.setup_ui()
        self.apply_settings(settings)
        self.change_language(self.current_language)


    @staticmethod
    def get_settings_file():
        return os.path.join(TALELLE_DIR, f'{TALELLE_TOOL}.json')

    def save_settings(self, language, maxWidth="", maxHeight="", margin=""):
        settings = {
            'language': language,
            'projectPath': self.project_path,
            'projectFolder': self.project_folder,
            'imagesFolder': self.images_folder,
            'maxWidth': maxWidth,
            'maxHeight': maxHeight,
            'margin': margin
        }
        try:
            with open(self.get_settings_file(), 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            QMessageBox.warning(self, self.translate_key("Something went wrong while saving settings"), str(e))

    def load_settings(self):
        settings = {
            'language': 'English',
            'margin': '0.3'
        }
        try:
            with open(self.get_settings_file(), 'r') as f:
                settings.update(json.load(f))
        except FileNotFoundError:
            pass

        return settings

    @staticmethod
    def get_project_path(settings) -> tuple[str, str]:
        return \
            settings.get('projectPath', os.path.expanduser("~")), \
                settings.get('projectFolder', 'projects')

    @staticmethod
    def get_images_folder(settings) -> str:
        return settings.get('imagesFolder', 'images')

    @staticmethod
    def get_current_date():
        return datetime.datetime.now().strftime('%Y-%m-%d')

    def apply_settings(self, settings):
        self.langComboBox.setCurrentText(self.current_language)
        self.maxWidthLineEdit.setText(settings.get('maxWidth', ''))
        self.maxHeightLineEdit.setText(settings.get('maxHeight', ''))
        self.marginLineEdit.setText(settings.get('margin', ''))

        date_project_path = os.path.join(self.project_path, self.project_folder)
        self.projLineEdit.setText(date_project_path)


    @staticmethod
    def get_language(settings):
        return settings.get('language', 'English')

    @staticmethod
    def load_language_codes():
        path = "locales/language_codes.json"
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def load_language_names(cls):
        language_codes = cls.load_language_codes()
        return list(language_codes.keys())

    @classmethod
    def load_translations(cls, language_name):
        language_codes = cls.load_language_codes()
        language_code = language_codes.get(language_name, "en")
        path = f"locales/{language_code}.json"
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def translate_key(self, text_key):
        return self.translations.get(text_key, text_key)


    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Update Logo
        logoLabel = QLabel(self)
        logoPixmap = QPixmap("images/logo.png")
        scaledLogoPixmap = logoPixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation)
        logoLabel.setPixmap(scaledLogoPixmap)
        logoLabel.setFixedSize(scaledLogoPixmap.size())
        layout.addWidget(logoLabel)

        # Language selection
        languageLabel = QLabel()
        langComboBox = QComboBox()
        langComboBox.addItems(self.load_language_names())
        langComboBox.currentTextChanged.connect(self.change_language)
        langLayout = QHBoxLayout()
        langLayout.addWidget(languageLabel)
        langLayout.addWidget(langComboBox)
        layout.addLayout(langLayout)

        # Project selection
        projLabel = QLabel()
        projLineEdit = QLineEdit()
        projButton = QPushButton()
        projButton.clicked.connect(self.choose_project)
        projLayout = QHBoxLayout()
        projLayout.addWidget(projLabel)
        projLayout.addWidget(projLineEdit)
        projLayout.addWidget(projButton)
        layout.addLayout(projLayout)

        # Directory selection
        dirLabel = QLabel()
        dirLineEdit = QLineEdit()
        dirLineEdit.setMinimumWidth(400)
        dirButton = QPushButton()
        dirButton.clicked.connect(self.choose_directory)
        dirLayout = QHBoxLayout()
        dirLayout.addWidget(dirLabel)
        dirLayout.addWidget(dirLineEdit)
        dirLayout.addWidget(dirButton)
        layout.addLayout(dirLayout)

        # Output file selection
        fileLabel = QLabel()
        fileLineEdit = QLineEdit()
        fileButton = QPushButton()
        fileButton.clicked.connect(self.choose_output_file)
        fileLayout = QHBoxLayout()
        fileLayout.addWidget(fileLabel)
        fileLayout.addWidget(fileLineEdit)
        fileLayout.addWidget(fileButton)
        layout.addLayout(fileLayout)

        # Max width and height
        maxWidthLabel = QLabel()
        maxWidthLineEdit = QLineEdit()
        maxHeightLabel = QLabel()
        maxHeightLineEdit = QLineEdit()
        layout.addWidget(maxWidthLabel)
        layout.addWidget(maxWidthLineEdit)
        layout.addWidget(maxHeightLabel)
        layout.addWidget(maxHeightLineEdit)

        # Margin
        marginLabel = QLabel()
        marginLineEdit = QLineEdit()
        layout.addWidget(marginLabel)
        layout.addWidget(marginLineEdit)

        # Process button
        processButton = QPushButton(self.translate_key("Process Images"))
        processButton.clicked.connect(self.process_images)
        layout.addWidget(processButton)

        # Progress Bar
        progressLabel = QLabel("")
        progressStatus = ''
        layout.addWidget(progressLabel)
        progressBar = QProgressBar(self)
        progressBar.setMaximum(100)  # 100% completion
        progressBar.setValue(0)  # start value
        layout.addWidget(progressBar)

        self.locale_subjects['language_label'] = languageLabel
        self.locale_subjects['project_label'] = projLabel
        self.locale_subjects['choose_project'] = projButton
        self.locale_subjects['directory_label'] = dirLabel
        self.locale_subjects['choose_directory'] = dirButton
        self.locale_subjects['output_label'] = fileLabel
        self.locale_subjects['choose_output'] = fileButton
        self.locale_subjects['max_width'] = maxWidthLabel
        self.locale_subjects['max_height'] = maxHeightLabel
        self.locale_subjects['margin'] = marginLabel
        self.locale_subjects['process_button'] = processButton

        self.direction_subjects.append(langLayout)
        self.direction_subjects.append(projLayout)
        self.direction_subjects.append(dirLayout)
        self.direction_subjects.append(fileLayout)

        self.langComboBox = langComboBox
        self.projLineEdit = projLineEdit
        self.dirLineEdit = dirLineEdit
        self.fileLineEdit = fileLineEdit
        self.maxWidthLineEdit = maxWidthLineEdit
        self.maxHeightLineEdit = maxHeightLineEdit
        self.marginLineEdit = marginLineEdit
        self.processButton = processButton
        self.progressLabel = progressLabel
        self.progressStatus = progressStatus
        self.progressBar = progressBar




    def reset_progress(self):
        self.progressLabel.setText('')
        self.progressBar.setValue(0)

    def is_valid_number(self, value):
        try:
            val = float(value)
            return val > 0
        except ValueError:
            return False

    def choose_project(self):
        proj_path = QFileDialog.getExistingDirectory(self,
                                                    self.translate_key('choose_project'),
                                                    dir=self.projLineEdit.text())
        if proj_path:
            proj_path = os.path.normpath(proj_path)
            self.projLineEdit.setText(proj_path)

            images_path = os.path.join(proj_path, self.images_folder)
            self.dirLineEdit.setText(images_path)

            proj_name = os.path.basename(proj_path)
            proj_parent_name = os.path.basename(os.path.dirname(proj_path))


            output_path = os.path.join(proj_path, f'{proj_parent_name}_{proj_name}.pdf')
            self.fileLineEdit.setText(output_path)

        self.reset_progress()

    def choose_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self,
                                                    self.translate_key('choose_directory'),
                                                    dir=self.dirLineEdit.text())

        if dir_path:
            self.dirLineEdit.setText(dir_path)

        self.reset_progress()

    def choose_output_file(self):
        filePath, _ = QFileDialog.getSaveFileName(self,
                                                  self.translate_key('choose_output'),
                                                  dir=self.fileLineEdit.text(),
                                                  filter="PDF files (*.pdf)"
                                                  )
        self.fileLineEdit.setText(filePath)
        self.reset_progress()

    def change_language(self, language):
        self.current_language = language
        self.translations = self.load_translations(language)

        # Update texts
        self.setWindowTitle(self.translate_key('title'))

        if self.progressStatus:
            self.progressLabel.setText(self.translate_key(self.progressStatus))

        for locale_key in self.locale_subjects:
            self.locale_subjects[locale_key].setText(self.translate_key(locale_key))

        # Update layout
        is_rtl = (language == 'עברית')
        for direction_subject in self.direction_subjects:
            direction_subject.setDirection(QHBoxLayout.Direction.RightToLeft if is_rtl else QHBoxLayout.Direction.LeftToRight)

    def process_images(self):
        if not os.path.isdir(self.dirLineEdit.text()):
            QMessageBox.warning(self, self.translate_key("error_title"), self.translate_key("directory_not_found"))
            return

        if not self.dirLineEdit.text() or not self.fileLineEdit.text():
            QMessageBox.warning(self, self.translate_key("error_title"), self.translate_key("no_in_or_out"))
            return

        if not self.is_valid_number(self.maxWidthLineEdit.text()) or not self.is_valid_number(
                self.maxHeightLineEdit.text()):
            QMessageBox.warning(self, self.translate_key("error_title"), self.translate_key("invalid_input"))
            return

        directory = self.dirLineEdit.text()
        output_pdf_path = self.fileLineEdit.text()
        max_width_cm = float(self.maxWidthLineEdit.text())
        max_height_cm = float(self.maxHeightLineEdit.text())
        margin_cm = float(self.marginLineEdit.text())
        margin_points = placement.cm_to_points(margin_cm)
        images, min_size = placement.collect_and_resize_images(directory, max_width_cm, max_height_cm)

        if not images:
            QMessageBox.warning(self, self.translate_key("error_title"), self.translate_key("no_images_found"))
            return
        try:
            self.pdfThread = PDFCreatorThread(images, output_pdf_path, margin_points, min_size)
            self.pdfThread.creationStarted.connect(self.on_pdf_creation_started)
            self.pdfThread.progressUpdated.connect(self.update_progress_bar)
            self.pdfThread.creationFinished.connect(self.on_pdf_creation_finished)
            self.pdfThread.start()
        except Exception as e:
            errorMessage = f"{self.translate_key('pdf_creation_failed')} {str(e)}"
            QMessageBox.warning(self, self.translate_key("error_title"), errorMessage)


    def on_pdf_creation_started(self):
        self.processButton.setEnabled(False)
        self.save_settings(self.current_language,
                            self.maxWidthLineEdit.text(), self.maxHeightLineEdit.text(), self.marginLineEdit.text())
        self.progressLabel.setText(self.translate_key("started"))


    def update_progress_bar(self, value, label):
        if label:
            self.progressLabel.setText(self.translate_key(label))
        self.progressBar.setValue(value)


    def on_pdf_creation_finished(self):
        QMessageBox.information(self, self.translate_key("success_title"), self.translate_key("success_message"),
                                QMessageBox.StandardButton.Ok)
        self.progressLabel.setText(self.translate_key("finished"))
        self.processButton.setEnabled(True)


if __name__ == "__main__":
    if hasattr(sys, '_MEIPASS'):
        os.chdir(sys._MEIPASS)
    app = QApplication(sys.argv)
    window = ImageToPDFConverter()
    window.show()
    sys.exit(app.exec())

