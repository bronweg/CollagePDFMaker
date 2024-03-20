import sys
import os
import json
import datetime
import placement
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QLineEdit, QFileDialog, QComboBox, QMessageBox, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import (QIcon, QPixmap)


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
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.locale_subjects = dict()
        self.direction_subjects = list()
        self.setup_ui()
        self.apply_settings(settings)
        self.change_language(self.current_language)


    @staticmethod
    def get_settings_file():
        home_dir = os.path.expanduser("~")
        filename = "CollagePDFMaker.json"
        return os.path.join(home_dir, filename)


    def save_settings(self, language, maxWidth="", maxHeight="", margin=""):
        settings = {
            'language': language,
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
        # Update Logo
        self.logoLabel = QLabel(self)
        self.logoPixmap = QPixmap("images/logo.png")
        scaledLogoPixmap = self.logoPixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logoLabel.setPixmap(scaledLogoPixmap)
        self.logoLabel.setFixedSize(scaledLogoPixmap.size())
        self.layout.addWidget(self.logoLabel)

        # Language selection
        self.languageLabel = QLabel()
        self.locale_subjects['language_label'] = self.languageLabel
        self.langComboBox = QComboBox()
        language_names = self.load_language_names()
        self.langComboBox.addItems(language_names)
        self.langComboBox.currentTextChanged.connect(self.change_language)
        langLayout = QHBoxLayout()
        langLayout.addWidget(self.languageLabel)
        langLayout.addWidget(self.langComboBox)
        self.direction_subjects.append(langLayout)
        self.layout.addLayout(langLayout)

        # Project selection
        self.projLabel = QLabel()
        self.locale_subjects['project_label'] = self.projLabel
        self.projLineEdit = QLineEdit()
        self.projButton = QPushButton()
        self.locale_subjects['choose_project'] = self.projButton
        self.projButton.clicked.connect(self.choose_project)
        self.projLayout = QHBoxLayout()
        self.projLayout.addWidget(self.projLabel)
        self.projLayout.addWidget(self.projLineEdit)
        self.projLayout.addWidget(self.projButton)
        self.direction_subjects.append(self.projLayout)
        self.layout.addLayout(self.projLayout)

        # Directory selection
        self.dirLabel = QLabel()
        self.locale_subjects['directory_label'] = self.dirLabel
        self.dirLineEdit = QLineEdit()
        self.dirLineEdit.setMinimumWidth(400)
        self.dirButton = QPushButton()
        self.locale_subjects['choose_directory'] = self.dirButton
        self.dirButton.clicked.connect(self.choose_directory)
        self.dirLayout = QHBoxLayout()
        self.dirLayout.addWidget(self.dirLabel)
        self.dirLayout.addWidget(self.dirLineEdit)
        self.dirLayout.addWidget(self.dirButton)
        self.direction_subjects.append(self.dirLayout)
        self.layout.addLayout(self.dirLayout)

        # Output file selection
        self.fileLabel = QLabel()
        self.locale_subjects['output_label'] = self.fileLabel
        self.fileLineEdit = QLineEdit()
        self.fileButton = QPushButton()
        self.locale_subjects['choose_output'] = self.fileButton
        self.fileButton.clicked.connect(self.choose_output_file)
        self.fileLayout = QHBoxLayout()
        self.fileLayout.addWidget(self.fileLabel)
        self.fileLayout.addWidget(self.fileLineEdit)
        self.fileLayout.addWidget(self.fileButton)
        self.direction_subjects.append(self.fileLayout)
        self.layout.addLayout(self.fileLayout)

        # Max width and height
        self.maxWidthLabel = QLabel()
        self.locale_subjects['max_width'] = self.maxWidthLabel
        self.maxWidthLineEdit = QLineEdit()
        self.maxHeightLabel = QLabel()
        self.locale_subjects['max_height'] = self.maxHeightLabel
        self.maxHeightLineEdit = QLineEdit()
        self.layout.addWidget(self.maxWidthLabel)
        self.layout.addWidget(self.maxWidthLineEdit)
        self.layout.addWidget(self.maxHeightLabel)
        self.layout.addWidget(self.maxHeightLineEdit)

        # Margin
        self.marginLabel = QLabel()
        self.locale_subjects['margin'] = self.marginLabel
        self.marginLineEdit = QLineEdit()
        self.layout.addWidget(self.marginLabel)
        self.layout.addWidget(self.marginLineEdit)

        # Process button
        self.processButton = QPushButton(self.translate_key("Process Images"))
        self.locale_subjects['process_button'] = self.processButton
        self.processButton.clicked.connect(self.process_images)
        self.layout.addWidget(self.processButton)

        # Progress Bar
        self.progressLabel = QLabel("")
        self.progressStatus = ''
        self.layout.addWidget(self.progressLabel)
        self.progressBar = QProgressBar(self)
        self.progressBar.setMaximum(100)  # 100% completion
        self.progressBar.setValue(0)  # start value
        self.layout.addWidget(self.progressBar)

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
            direction_subject.setDirection(QHBoxLayout.RightToLeft if is_rtl else QHBoxLayout.LeftToRight)

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
        QMessageBox.information(self, self.translate_key("success_title"), self.translate_key("success_message"))
        self.progressLabel.setText(self.translate_key("finished"))
        self.processButton.setEnabled(True)


if __name__ == "__main__":
    if hasattr(sys, '_MEIPASS'):
        os.chdir(sys._MEIPASS)
    app = QApplication(sys.argv)
    window = ImageToPDFConverter()
    window.show()
    sys.exit(app.exec())

