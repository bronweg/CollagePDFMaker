import sys
import os
import json
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog, QComboBox, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import (QIcon, QPixmap)
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PIL import Image

def cm_to_points(cm):
    inches = cm / 2.54
    return inches * 72

def resize_image(image_path, max_width_points, max_height_points):
    with Image.open(image_path) as img:
        img_ratio = img.width / img.height
        if img.width / img.height > max_width_points / max_height_points:
            new_width = min(img.width, max_width_points)
            new_height = int(new_width / img_ratio)
        else:
            new_height = min(img.height, max_height_points)
            new_width = int(new_height * img_ratio)
        return image_path, new_width, new_height

def collect_and_resize_images(directory, max_width_cm, max_height_cm):
    max_width_points = cm_to_points(max_width_cm)
    max_height_points = cm_to_points(max_height_cm)
    images = []
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp')):
                path = os.path.join(root, filename)
                images.append(resize_image(path, max_width_points, max_height_points))
    return images

def place_images_on_pdf(images, output_pdf_path, margin_points):
    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    page_width, page_height = A4
    margin = margin_points
    x, y = margin, page_height - margin
    max_row_height = 0

    for path, img_width, img_height in images:
        if x + img_width > page_width - margin:
            x = margin
            y -= max_row_height + margin
            max_row_height = 0
        if y - img_height < margin:
            c.showPage()
            x, y = margin, page_height - margin
            max_row_height = 0
        c.drawImage(path, x, y - img_height, width=img_width, height=img_height)
        x += img_width + margin
        max_row_height = max(max_row_height, img_height)
    c.save()

class ImageToPDFConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.texts = {
            "English": {
                "title": "Images to PDF Converter",
                "directory_label": "Directory with Images:",
                "output_label": "Output PDF Path:",
                "max_width": "Max Image Width (cm):",
                "max_height": "Max Image Height (cm):",
                "margin": "Margin (cm):",
                "process_button": "Process Images",
                "choose_directory": "Choose...",
                "choose_output": "Choose...",
                "success_message": "PDF has been created successfully!"
            },
            "עברית": {
                "title": "המרת תמונות ל-PDF",
                "directory_label": "תיקייה עם תמונות:",
                "output_label": "נתיב לקובץ PDF:",
                "max_width": "רוחב מקסימלי לתמונה (ס\"מ):",
                "max_height": "גובה מקסימלי לתמונה (ס\"מ):",
                "margin": "שוליים (ס\"מ):",
                "process_button": "עבד תמונות",
                "choose_directory": "בחר...",
                "choose_output": "בחר...",
                "success_message": "ה-PDF נוצר בהצלחה!"
            }
        }
        self.currentLanguage = self.loadSettings()
        self.setWindowTitle(self.tr("Images to PDF Converter"))
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.setupUI()
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
        self.langComboBox.addItems(list(self.texts.keys()))
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

    def saveSettings(self, language):
        settings = {'language': language}
        with open('settings.json', 'w') as f:
            json.dump(settings, f)

    def loadSettings(self):
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                return settings.get('language', 'English')
        except FileNotFoundError:
            return 'English'

    def chooseDirectory(self):
        dirPath = QFileDialog.getExistingDirectory(self, self.tr("Select Directory"))
        self.dirLineEdit.setText(dirPath)

    def chooseOutputFile(self):
        filePath, _ = QFileDialog.getSaveFileName(self, self.tr("Select Output PDF"), filter="PDF files (*.pdf)")
        self.fileLineEdit.setText(filePath)

    def processImages(self):
        directory = self.dirLineEdit.text()
        output_pdf_path = self.fileLineEdit.text()
        max_width_cm = float(self.maxWidthLineEdit.text())
        max_height_cm = float(self.maxHeightLineEdit.text())
        margin_cm = float(self.marginLineEdit.text())
        margin_points = cm_to_points(margin_cm)

        images = collect_and_resize_images(directory, max_width_cm, max_height_cm)
        place_images_on_pdf(images, output_pdf_path, margin_points)
        QMessageBox.information(self, self.tr("Success"), self.tr("PDF has been created successfully!"))

    def changeLanguage(self, language):
        self.currentLanguage = language
        self.saveSettings(language)
        is_rtl = (language == "עברית")

        # Update texts
        self.setWindowTitle(self.tr(self.texts[language]["title"]))
        self.dirLabel.setText(self.tr(self.texts[language]["directory_label"]))
        self.fileLabel.setText(self.tr(self.texts[language]["output_label"]))
        self.maxWidthLabel.setText(self.tr(self.texts[language]["max_width"]))
        self.maxHeightLabel.setText(self.tr(self.texts[language]["max_height"]))
        self.marginLabel.setText(self.tr(self.texts[language]["margin"]))
        self.processButton.setText(self.tr(self.texts[language]["process_button"]))
        self.dirButton.setText(self.tr(self.texts[language]["choose_directory"]))
        self.fileButton.setText(self.tr(self.texts[language]["choose_output"]))

        # Update layout
        self.dirLayout.setDirection(QHBoxLayout.RightToLeft if is_rtl else QHBoxLayout.LeftToRight)
        self.fileLayout.setDirection(QHBoxLayout.RightToLeft if is_rtl else QHBoxLayout.LeftToRight)

    def tr(self, text):
        return self.texts[self.currentLanguage].get(text, text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageToPDFConverter()
    window.show()
    sys.exit(app.exec_())
