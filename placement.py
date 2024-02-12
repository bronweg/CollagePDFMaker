from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import A4
from PIL import Image
import math
import bisect
import os


class VirtualImage:
    def __init__(self, path, width, height):
        self.path = path
        self.width = width
        self.height = height

class VirtualPlacement:
    def __init__(self, image, x, y, rotated):
        self.image = image
        self.x = x
        self.y = y
        self.rotated = rotated

class VirtualCanvas:
    def __init__(self):
        self.canvas = [[]]
        self.current_page = 0
        self.length = 0

    def showPage(self):
        self.canvas.append([])
        self.current_page += 1

    def drawImage(self, image, x, y, rotated=False, page=None):
        if page is None:
            page = self.current_page
        self.canvas[page].append(VirtualPlacement(image, x, y,rotated))
        self.length += 1

    def makeItReal(self, output_pdf_path):
        real = canvas.Canvas(output_pdf_path, pagesize=A4)
        done = 0
        placed_progress = 0
        for page in self.canvas:
            for placement in page:
                self.drawReal(real, placement)
                done = self.updateProgress(done)
            real.showPage()
        real.save()

    def updateProgress(self, done):
        done += 1
        placed_progress = math.floor((done / self.length)*100)
        print(f'PLACEMENT IS DONE for {str(placed_progress)}%: {str(done)} of {str(self.length)}')
        return done


    @classmethod
    def drawReal(cls, real, placement):
        if placement.rotated:
            cls.drawRealRotated(real, placement)
        else:
            cls.drawRealDirect(real, placement)

    @staticmethod
    def drawRealRotated(real, placement):
        with Image.open(placement.image.path) as be_rotated:
            rotated = be_rotated.transpose(Image.ROTATE_90)
            real.drawImage(ImageReader(rotated), placement.x, placement.y, width=placement.image.width, height=placement.image.height)

    @staticmethod
    def drawRealDirect(real, placement):
        real.drawImage(placement.image.path, placement.x, placement.y, width=placement.image.width, height=placement.image.height)

class VirtualDocument:
    def __init__(self, margin):
        self.margin = margin
        self.page_width, self.page_height = A4
        self.page_right = self.page_width - self.margin

class VirtualPosition:
    def __init__(self, x, y, max_row_height, page):
        self.x = x
        self.y = y
        self.max_row_height = max_row_height
        self.page = page

class VirtualSpace:
    def __init__(self, space, x, y, page):
        self.space = space
        self.x = x
        self.y = y
        self.page = page
    def __repr__(self):
        return f'{str(self.page)}x{str(self.x)}x{str(self.y)}({str(self.space)})'


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
        return VirtualImage(image_path, new_width, new_height)

def collect_and_resize_images(directory, max_width_cm, max_height_cm):
    max_width_points = cm_to_points(max_width_cm)
    max_height_points = cm_to_points(max_height_cm)
    images = []
    min_size = min(max_width_points, max_height_points)
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp')):
                path = os.path.join(root, filename)
                image = resize_image(path, max_width_points, max_height_points)
                min_size = min(min_size, image.width, image.height)
                images.append(image)
    images.sort(reverse=True, key=lambda image : image.height)
    return images, min_size


def try_use_unused_right(virtual_canvas, right_unused, image, document, min_size, rotated=False):
    wide_index = bisect.bisect_left(right_unused, image.width, key = lambda vs:vs.space)
    wide_count = len(right_unused)
    if wide_index < wide_count:
        put_here = right_unused.pop(wide_index)
        print(f'The image with rotation={rotated} of width {str(image.width)} can be inserted at free right space: {str(put_here)}')
        virtual_canvas.drawImage(image, put_here.x, put_here.y - image.height,
                                 rotated=rotated, page=put_here.page)

        new_x = put_here.x + image.width + document.margin
        new_space = document.page_right-new_x
        if new_x + min_size <= document.page_right:
            bisect.insort_right(right_unused, VirtualSpace(new_space, new_x, put_here.y, put_here.page), key = lambda vs:vs.space)
        return True

    return False

def try_use_unused_bottom(virtual_canvas, bottom_unused, image, document, min_size, rotated=False):
    height_index = bisect.bisect_left(bottom_unused, image.height, key = lambda vs:vs.space)
    height_count = len(bottom_unused)
    while height_index < height_count:
        put_here = bottom_unused[height_index]
        if put_here.x + image.width <= document.page_right:
            print(f'The image with rotation={rotated} of height {str(image.height)} can be inserted at free bottom space: {str(put_here)}')
            virtual_canvas.drawImage(image, put_here.x, put_here.y - image.height,
                                     rotated=rotated, page=put_here.page)
            new_x = put_here.x + image.width + document.margin
            if new_x + min_size <= document.page_right:
                bottom_unused[height_index] = VirtualSpace(put_here.space, new_x, put_here.y, put_here.page)
            else:
                bottom_unused.pop(height_index)
            break
        else:
            height_index += 1
    if height_index < height_count:
        return True
    return False

def rotate(image):
    return VirtualImage(image.path, image.height, image.width)

def try_use_unused(virtual_canvas, right_unused, bottom_unused, image, document, min_size):
    return try_use_unused_right(
        virtual_canvas, right_unused, image, document, min_size
    ) or try_use_unused_bottom(
        virtual_canvas, bottom_unused, image, document, min_size
    ) or try_use_unused_right(
        virtual_canvas, right_unused, rotate(image), document, min_size, True
    ) or try_use_unused_bottom(
        virtual_canvas, bottom_unused, rotate(image), document, min_size, True
    )


def reposition(virtual_canvas, position, right_unused, bottom_unused, image, document, min_size):

    if position.x + image.width > document.page_right:
        space = document.page_right-position.x
        if space >= min_size:
            bisect.insort_right(right_unused, VirtualSpace(document.page_right-position.x, position.x, position.y, position.page), key = lambda vs:vs.space)
        position.x = document.margin
        position.y -= position.max_row_height + document.margin
        position.max_row_height = 0

        if position.y - image.height < document.margin:
            space = position.y - document.margin
            if space >= min_size:
                bisect.insort_right(bottom_unused,
                                    VirtualSpace(position.y - document.margin, document.margin, position.y, position.page),
                                    key = lambda vs:vs.space)
            virtual_canvas.showPage()
            position.page += 1
            position.x, position.y = document.margin, document.page_height - document.margin
            position.max_row_height = 0


def place_images_on_pdf(images, output_pdf_path, margin, min_size):
    virtual_canvas = VirtualCanvas()

    document = VirtualDocument(margin)

    position = VirtualPosition(document.margin, document.page_height - document.margin, 0, 0)

    right_unused = []
    bottom_unused = []

    done = 0
    calculated_progress = 0

    for image in images:
        calculated_progress = math.floor((done / len(images))*100)
        print(f'CALCULATION IS DONE for {str(calculated_progress)}%: {str(done)} of {str(len(images))}')
        done += 1

        if try_use_unused(virtual_canvas, right_unused, bottom_unused, image, document, min_size):
            continue

        reposition(virtual_canvas, position, right_unused, bottom_unused, image, document, min_size)

        virtual_canvas.drawImage(image, position.x, position.y - image.height)
        position.x += image.width + document.margin
        position.max_row_height = max(position.max_row_height, image.height)

    calculated_progress = math.floor((done / len(images))*100)
    print(f'CALCULATION IS DONE for {str(calculated_progress)}%: {str(done)} of {str(len(images))}')

    virtual_canvas.makeItReal(output_pdf_path)
    print(f'\n\nStill right unused\n {str(right_unused)}')
    print(f'\n\nStill bottom unused\n {str(right_unused)}')
    print()


if __name__ == "__main__":
    directory = "photos"
    max_width_cm, max_height_cm = 5, 10
    margin = cm_to_points(0.3)
    output_pdf_path = "output_images.pdf"
    images, min_size = collect_and_resize_images(directory, max_width_cm, max_height_cm)
    place_images_on_pdf(images, output_pdf_path, margin, min_size)
    print(f"PDF document '{output_pdf_path}' has been created with images.")
