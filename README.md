# CollagePDFMaker

CollagePDFMaker is a desktop application designed to create PDF documents from images. It allows users to select a directory with images, specify maximum dimensions for the images in the PDF, and efficiently arrange them on multiple pages to minimize paper usage when printing.

## Features

- **Image Directory Selection**: Choose a folder with your images.
- **Customizable Dimensions**: Set maximum width and height for images to ensure they fit on the pages as expected.
- **Efficient Arrangement**: Automatically arranges images to use as few pages as possible.
- **Multi-Language Support**: Comes with English, Russian, and Hebrew localization.

## Getting Started

### Prerequisites

Before you begin, ensure you have met the following requirements:
- Python 3.8 or higher
- PyQt6
- Pillow for image processing
- ReportLab for PDF generation

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/bronweg/CollagePDFMaker.git
```

2. **Navigate to the cloned repository:**
```bash
cd CollagePDFMaker
```

3. **Install the required dependencies:**
```bash
pip install -r requirements.txt
```

### Running the Application

To run CollagePDFMaker, execute the following command from the root of the repository:
```bash
python CollagePDFCreator.py
```


## Usage

1. **Select the Image Directory**: Click the "Choose..." button to select the directory containing your images.
2. **Specify Output PDF Path**: Choose where you want the generated PDF to be saved.
3. **Set Maximum Image Dimensions**: Enter the maximum width and height for the images in centimeters.
4. **Generate PDF**: Click "Process Images" to create the PDF. The application will notify you once the PDF is successfully created or if an error occurs.

## Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

To contribute:
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the GPL3 License. See `LICENSE` for more information.

## Acknowledgments

- Icons and images used in the application are courtesy of [Flaticon](https://flaticon.com).
- Special thanks to the open-source community for supporting projects like this.

