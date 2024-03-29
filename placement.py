from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PIL import Image
import math
import bisect
from time import time
import os



class VirtualImage:
    def __init__(self, path, width, height, rotated):
        self.path = path
        self.width = width
        self.height = height
        self.rotated = rotated
        print(f'TRACE: {self}')
    def __eq__(self, other):
        return (self.width == other.width) and (self.height == other.height)
    def __lt__(self, other):
        return (self.height < other.height) or ((self.height == other.height) and (self.width < other.width))
    def __repr__(self):
        return f'{str(self.width)}x{str(self.height)}({str(self.rotated)})'

class VirtualPlacement:
    def __init__(self, image, x, y):
        self.image = image
        self.x = x
        self.y = y

class VirtualCanvas:
    def __init__(self, progress_callback):
        self.canvas = [[]]
        self.current_page = 0
        self.length = 0
        self.progress_callback = progress_callback

    def showPage(self):
        self.canvas.append([])
        self.current_page += 1

    def drawImage(self, image, x, y, page=None):
        if page is None:
            page = self.current_page
        self.canvas[page].append(VirtualPlacement(image, x, y))
        self.length += 1

    def makeItReal(self, output_pdf_path):
        real = canvas.Canvas(output_pdf_path, pagesize=A4)
        done = 0
        placed_progress = 0
        if not self.canvas[-1]:
            self.canvas.pop()
        start_time = time()
        real.saveState()
        print(f'TRACE: placing {str(self.length) } images on {str(len(self.canvas))} pages')
        self.progress_callback(placed_progress, 'placement')
        for page in self.canvas:
            for placement in page:
                self.drawReal(real, placement)
                done = self.updateProgress(done)
            real.showPage()
        real.save()
        duration = time() - start_time
        print(f'TRACE: Overall placement duration = {str(duration)}')

    def updateProgress(self, done):
        done += 1
        placed_progress = math.floor((done / self.length)*100)
        print(f'PLACEMENT IS DONE for {str(placed_progress)}%: {str(done)} of {str(self.length)}')
        self.progress_callback(placed_progress)
        return done


    @classmethod
    def drawReal(cls, real, placement):
        if placement.image.rotated:
            cls.drawRealRotated(real, placement)
        else:
            cls.drawRealDirect(real, placement)

    @staticmethod
    def drawRealRotated(real, placement):
        start_time = time()
        real.saveState()
        real.rotate(90)
        #real.rect(y, -x-w, h, w, fill=0)
        real.drawImage(placement.image.path, placement.y, -(placement.image.width+placement.x), placement.image.height, placement.image.width)
        real.restoreState()
        duration = time() - start_time
        print(f'TRACE: drawRealRotated-placement duration = {str(duration)}')

    @staticmethod
    def drawRealDirect(real, placement):
        start_time = time()
        real.drawImage(placement.image.path, placement.x, placement.y, width=placement.image.width, height=placement.image.height)
        duration = time() - start_time
        print(f'TRACE: drawRealDirect duration = {str(duration)}')


class VirtualDocument:
    def __init__(self, margin):
        self.margin = margin
        self.padding = margin
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

        rotated = False
        width = img.width
        height = img.height

        if (width - height) * (max_width_points - max_height_points) < 0:
            rotated = True
            width = img.height
            height = img.width

        img_ratio = width / height
        if img_ratio > max_width_points / max_height_points:
            new_width = min(width, max_width_points)
            new_height = int(new_width / img_ratio)
        else:
            new_height = min(height, max_height_points)
            new_width = int(new_height * img_ratio)

        return VirtualImage(image_path, new_width, new_height, rotated)

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
    images.sort(reverse=True)
    return images, min_size


def try_use_unused_right(virtual_canvas, right_unused, image, document, min_size):
    wide_index = bisect.bisect_left(right_unused, image.width, key = lambda vs:vs.space)
    wide_count = len(right_unused)
    if wide_index < wide_count:
        put_here = right_unused.pop(wide_index)
        print(f'The image with rotation={image.rotated} of width {str(image.width)} can be inserted at free right space: {str(put_here)}')
        virtual_canvas.drawImage(image, put_here.x, put_here.y - image.height, page=put_here.page)

        new_x = put_here.x + image.width + document.padding
        new_space = document.page_right-new_x
        if new_x + min_size <= document.page_right:
            bisect.insort_right(right_unused, VirtualSpace(new_space, new_x, put_here.y, put_here.page), key = lambda vs:vs.space)
        return True

    return False

def try_use_unused_bottom(virtual_canvas, bottom_unused, image, document, min_size):
    height_index = bisect.bisect_left(bottom_unused, image.height, key = lambda vs:vs.space)
    height_count = len(bottom_unused)
    while height_index < height_count:
        put_here = bottom_unused[height_index]
        if put_here.x + image.width <= document.page_right:
            print(f'The image with rotation={image.rotated} of height {str(image.height)} can be inserted at free bottom space: {str(put_here)}')
            virtual_canvas.drawImage(image, put_here.x, put_here.y - image.height, page=put_here.page)
            new_x = put_here.x + image.width + document.padding
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
    return VirtualImage(image.path, image.height, image.width, not image.rotated)

def use_unused(virtual_canvas, right_unused, bottom_unused, image, document, min_size):
    return try_use_unused_right(
        virtual_canvas, right_unused, image, document, min_size
    ) or try_use_unused_bottom(
        virtual_canvas, bottom_unused, image, document, min_size
    ) or try_use_unused_right(
        virtual_canvas, right_unused, rotate(image), document, min_size
    ) or try_use_unused_bottom(
        virtual_canvas, bottom_unused, rotate(image), document, min_size
    )


def reposition(virtual_canvas, position, right_unused, bottom_unused, image, document, min_size):
    if position.max_row_height == 0:
        position.max_row_height = image.height
    elif position.x + image.width > document.page_right:
        space = document.page_right-position.x
        if space >= min_size:
            vs = VirtualSpace(document.page_right-position.x, position.x, position.y, position.page)
            rooms = len(bottom_unused)
            bisect.insort_right(right_unused, vs, key = lambda vs:vs.space)
            print(f'TRACE: add HORIZONTAL virtual space {str(vs)}; current number of rooms: {str(rooms)} => {str(len(right_unused))}')
        position.x = document.margin
        position.y -= position.max_row_height + document.padding
        position.max_row_height = image.height

        if position.y - image.height < document.margin:
            space = position.y - document.margin
            if space >= min_size:
                vs = VirtualSpace(position.y - document.margin, document.margin, position.y, position.page)
                rooms = len(bottom_unused)
                bisect.insort_right(bottom_unused,
                                    vs,
                                    key = lambda vs:vs.space)
                print(f'TRACE: add VERTICAL virtual space {str(vs)}; current number of rooms: {str(rooms)} => {str(len(bottom_unused))}')
            virtual_canvas.showPage()
            position.page += 1
            position.x, position.y = document.margin, document.page_height - document.margin


def draw_image(virtual_canvas, position, image, document):
    virtual_canvas.drawImage(image, position.x, position.y - image.height)
    position.x += image.width + document.padding

def default_progress_callback(value, label=None):
    if label:
        print(f'START REPORTING ON {label}')
    for _ in range(value):
        print('+', end = '')
    for _ in range(value, 100):
        print('-', end = '')
    print()


def updateProgress(done, total, progress_callback):
    done += 1
    calculated_progress = math.floor((done / total)*100)
    print(f'CALCULATION IS DONE for {str(calculated_progress)}%: {str(done)} of {str(total)}')
    progress_callback(calculated_progress)
    return done


def place_images_on_pdf(images, output_pdf_path, margin, min_size, progress_callback=default_progress_callback):
    virtual_canvas = VirtualCanvas(progress_callback)
    document = VirtualDocument(margin)
    position = VirtualPosition(document.margin, document.page_height - document.margin, 0, 0)

    right_unused = []
    bottom_unused = []

    done = 0
    total = len(images)
    calculated_progress = 0
    progress_callback(calculated_progress, 'calculation')

    for image in images:
        reposition(virtual_canvas, position, right_unused, bottom_unused, image, document, min_size)
        if not use_unused(virtual_canvas, right_unused, bottom_unused, image, document, min_size):
            draw_image(virtual_canvas, position, image, document)

        done = updateProgress(done, total, progress_callback)


    virtual_canvas.makeItReal(output_pdf_path)
    print(f'\n\nRight still unused\n {str(right_unused)}')
    print(f'\n\nBottom still bottom unused\n {str(bottom_unused)}')
    print()



if __name__ == "__main__":
    #directory = "/Users/betty/PythonProjects/image_resize/photos"
    directory = "/Users/betty/PythonProjects/image_resize/bat-mizvush-all"
    #directory = "/Users/betty/PythonProjects/image_resize/bat-mizvush-6"
    max_width_cm, max_height_cm = 10, 15.5
    # output_pdf_path = "/Users/betty/PythonProjects/image_resize/output_images.pdf"
    output_pdf_path = "/Users/betty/PythonProjects/image_resize/output_images.pdf"
    start_time = time()
    images, min_size = collect_and_resize_images(directory, max_width_cm, max_height_cm)
    place_images_on_pdf(images, output_pdf_path, cm_to_points(0.2), min_size)
    #rotate_fun(output_pdf_path)
    print(f"PDF document '{output_pdf_path}' has been created with images.")
    duration = time() - start_time
    print(f'TRACE: overall duration = {str(duration)}')
