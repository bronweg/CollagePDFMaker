import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Optional

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PIL import Image, UnidentifiedImageError
import math
import bisect
from time import time
import os

from reportlab.pdfgen.canvas import Canvas

logger = logging.getLogger(__name__)


@dataclass
class VirtualImage:
    path: str
    width: float
    height: float
    rotated: bool

    def __post_init__(self):
        logger.debug(f'Resized image to be placed {self}')
    def __eq__(self, other):
        return (self.width == other.width) and (self.height == other.height)
    def __lt__(self, other):
        return (self.height < other.height) or ((self.height == other.height) and (self.width < other.width))
    def __repr__(self):
        return f'{str(self.width)}x{str(self.height)}(rotated={str(self.rotated)})'

@dataclass
class VirtualPlacement:
    image: VirtualImage
    x: float
    y: float


class VirtualCanvas:
    def __init__(self, progress_callback: Callable):
        self.canvas = [[]]
        self.current_page = 0
        self.length = 0
        self.progress_callback = progress_callback

    def showPage(self):
        self.canvas.append([])
        self.current_page += 1

    def drawImage(self, image: VirtualImage, x: float, y: float, page: int=None):
        if page is None:
            page = self.current_page
        self.canvas[page].append(VirtualPlacement(image, x, y))
        self.length += 1

    def makeItReal(self, output_pdf_path: str):
        real = canvas.Canvas(output_pdf_path, pagesize=A4)
        done = 0
        placed_progress = 0
        if not self.canvas[-1]:
            self.canvas.pop()
        start_time = time()
        real.saveState()
        logger.debug(f'Placing {self.length} images on {len(self.canvas)} pages')
        self.progress_callback(placed_progress, 'placement')
        for page in self.canvas:
            for placement in page:
                self.drawReal(real, placement)
                done = self.updateProgress(done)
            real.showPage()
        real.save()
        duration = time() - start_time
        logger.debug(f'Overall placement duration = {duration}')

    def updateProgress(self, done: int) -> int:
        done += 1
        placed_progress = math.floor((done / self.length)*100)
        logger.debug(f'PLACEMENT IS DONE for {placed_progress}%: {done} of {self.length}')
        self.progress_callback(placed_progress)
        return done

    @classmethod
    def drawReal(cls, real: Canvas, placement: VirtualPlacement):
        if placement.image.rotated:
            cls.drawRealRotated(real, placement)
        else:
            cls.drawRealDirect(real, placement)

    @staticmethod
    def drawRealRotated(real: Canvas, placement: VirtualPlacement):
        start_time = time()
        real.saveState()
        real.rotate(90)
        #real.rect(y, -x-w, h, w, fill=0)
        real.drawImage(placement.image.path, placement.y, -(placement.image.width+placement.x),
                       width=placement.image.height, height=placement.image.width)
        real.restoreState()
        duration = time() - start_time
        logger.debug(f'drawRealRotated-placement duration = {duration}')

    @staticmethod
    def drawRealDirect(real: Canvas, placement: VirtualPlacement):
        start_time = time()
        real.drawImage(placement.image.path, placement.x, placement.y,
                       width=placement.image.width, height=placement.image.height)
        duration = time() - start_time
        logger.debug(f'drawRealDirect duration = {duration}')


@dataclass
class VirtualDocument:
    margin: float
    padding: float = field(init=False)
    page_width: float = A4[0]
    page_height: float = A4[1]
    page_right: float = field(init=False)

    def __post_init__(self):
        self.padding = self.margin
        self.page_right = self.page_width - self.margin


@dataclass
class VirtualPosition:
    x: float
    y: float
    max_row_height: float
    page: int


@dataclass
class VirtualSpace:
    space: float
    x: float
    y: float
    page: int

    def __repr__(self):
        return f'{str(self.page)}x{str(self.x)}x{str(self.y)}({str(self.space)})'


def cm_to_points(cm):
    inches = cm / 2.54
    return inches * 72


def resize_image(image_path: str, max_width_points: float, max_height_points: float) -> Optional[VirtualImage]:
    try:
        with Image.open(image_path) as img:
            if img.height >= img.width:
                rotated = False
                width = img.width
                height = img.height
            else:
                rotated = True
                width = img.height
                height = img.width

            img_ratio = width / height
            if img_ratio > max_width_points / max_height_points:
                new_width = min(max_width_points, width)
                new_height = int(new_width / img_ratio)
            else:
                new_height = min(max_height_points, height)
                new_width = int(new_height * img_ratio)

            return VirtualImage(image_path, new_width, new_height, rotated)
    except UnidentifiedImageError:
        logger.warning(f'The file {image_path} could not be identified as an image.')
        return None


def collect_and_resize_images(directory: str, max_width_cm: float, max_height_cm: float
                              ) -> tuple[list[VirtualImage], float]:
    if max_width_cm <= max_height_cm:
        max_width_points = cm_to_points(max_width_cm)
        max_height_points = cm_to_points(max_height_cm)
    else:
        max_width_points = cm_to_points(max_height_cm)
        max_height_points = cm_to_points(max_width_cm)
    images = []
    min_size = min(max_width_points, max_height_points)
    for root, _, files in os.walk(directory):
        for filename in files:
            path = f'{os.path.join(root, filename)}'
            image = resize_image(path, max_width_points, max_height_points)
            if image is not None:
                min_size = min(min_size, image.width, image.height)
                images.append(image)
    images.sort(reverse=True)
    return images, min_size


def try_use_unused_right(
    virtual_canvas: VirtualCanvas,
    right_unused: list[VirtualSpace],
    image: VirtualImage,
    document: VirtualDocument,
    min_size: float
) -> bool:
    wide_index = bisect.bisect_left(right_unused, image.width, key = lambda vs:vs.space)
    wide_count = len(right_unused)
    if wide_index < wide_count:
        put_here = right_unused.pop(wide_index)
        logger.debug(f'The image with rotation={image.rotated} of width {image.width} '
                     f'can be inserted at free right space: {put_here}')
        virtual_canvas.drawImage(image, put_here.x, put_here.y - image.height, page=put_here.page)

        new_x = put_here.x + image.width + document.padding
        new_space = document.page_right-new_x
        if new_x + min_size <= document.page_right:
            bisect.insort_right(right_unused, VirtualSpace(new_space, new_x, put_here.y, put_here.page),
                                key = lambda vs:vs.space)
        return True

    return False


def try_use_unused_bottom(
    virtual_canvas: VirtualCanvas,
    bottom_unused: list[VirtualSpace],
    image: VirtualImage,
    document: VirtualDocument,
    min_size: float
) -> bool:
    height_index = bisect.bisect_left(bottom_unused, image.height, key = lambda vs:vs.space)
    height_count = len(bottom_unused)
    while height_index < height_count:
        put_here = bottom_unused[height_index]
        if put_here.x + image.width <= document.page_right:
            logger.debug(f'The image with rotation={image.rotated} of height {image.height} '
                         f'can be inserted at free bottom space: {put_here}')
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


def rotate(image: VirtualImage) -> VirtualImage:
    return VirtualImage(image.path, image.height, image.width, not image.rotated)


def use_unused(
    virtual_canvas: VirtualCanvas,
    right_unused: list[VirtualSpace],
    bottom_unused: list[VirtualSpace],
    image: VirtualImage,
    document: VirtualDocument,
    min_size: float
) -> bool:
    return try_use_unused_right(
        virtual_canvas, right_unused, image, document, min_size
    ) or try_use_unused_bottom(
        virtual_canvas, bottom_unused, image, document, min_size
    ) or try_use_unused_right(
        virtual_canvas, right_unused, rotate(image), document, min_size
    ) or try_use_unused_bottom(
        virtual_canvas, bottom_unused, rotate(image), document, min_size
    )


def reposition(
    virtual_canvas: VirtualCanvas,
    position: VirtualPosition,
    right_unused: list[VirtualSpace],
    bottom_unused: list[VirtualSpace],
    image: VirtualImage,
    document: VirtualDocument,
    min_size: float
):
    if position.max_row_height == 0:
        position.max_row_height = image.height
    elif position.x + image.width > document.page_right:
        space = document.page_right-position.x
        if space >= min_size:
            vs = VirtualSpace(document.page_right-position.x, position.x, position.y, position.page)
            rooms = len(bottom_unused)
            bisect.insort_right(right_unused, vs, key = lambda vs:vs.space)
            logger.debug(f'add HORIZONTAL virtual space {vs}; current number of rooms: {rooms} => {len(right_unused)}')
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
                logger.debug(f'add VERTICAL virtual space {vs}; '
                             f'current number of rooms: {rooms} => {len(bottom_unused)}')
            virtual_canvas.showPage()
            position.page += 1
            position.x, position.y = document.margin, document.page_height - document.margin


def draw_image(virtual_canvas: VirtualCanvas, position: VirtualPosition,
               image: VirtualImage, document: VirtualDocument):
    virtual_canvas.drawImage(image, position.x, position.y - image.height)
    position.x += image.width + document.padding


def default_progress_callback(value: int, label: str=None):
    if label:
        print(f'START REPORTING ON {label}')
    for _ in range(value):
        print('+', end = '')
    for _ in range(value, 100):
        print('-', end = '')
    print()


def updateProgress(done: int, total: int, progress_callback: Callable):
    done += 1
    calculated_progress = math.floor((done / total)*100)
    logger.debug(f'CALCULATION IS DONE for {calculated_progress}%: {str(done)} of {total}')
    progress_callback(calculated_progress)
    return done


def place_images_on_pdf(images: list[VirtualImage], output_pdf_path: str,
                        margin: float, min_size: float,
                        progress_callback: Callable[[int, Optional[str]], None] = default_progress_callback):

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
    logger.info(f'Right still unused {right_unused}')
    logger.info(f'Bottom still bottom unused {bottom_unused}')


def config_default_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )


if __name__ == "__main__":
    config_default_logging()
    logger.info('STARTING PDF MAKER')
    directory = "/Users/betty/projects/2025-03-25/vetochka/images"
    max_width_cm, max_height_cm = 10, 15.5
    # output_pdf_path = "/Users/betty/PythonProjects/image_resize/output_images.pdf"
    output_pdf_path = "/Users/betty/projects/2025-03-25/vetochka/images/output_imagess.pdf"
    start_time = time()
    images, min_size = collect_and_resize_images(directory, max_width_cm, max_height_cm)
    place_images_on_pdf(images, output_pdf_path, cm_to_points(0.2), min_size)
    #rotate_fun(output_pdf_path)
    logger.info(f"PDF document '{output_pdf_path}' has been created with images.")
    duration = time() - start_time
    logger.debug(f'overall duration = {duration}')
