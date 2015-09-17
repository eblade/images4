"""Take care of Image imports, exports and proxy generation"""

import logging, os
from PIL import Image
import exifread
from datetime import datetime

from .. import PROXY_SIZE, THUMB_SIZE, Entry, Location
from ..import_job import GenericImportModule, register_import_module
from ..localfile import FileCopy
from ..entry import EntryDescriptor, FileDescriptor
from ..location import get_location_by_type
from ..exif import exif_position, exif_orientation, exif_string, exif_int, exif_ratio
from ..types import Property
from ..metadata import register_metadata_schema


class JPEGImportModule(GenericImportModule):
    def run(self):
        self.entry = EntryDescriptor()
        self.entry.original_filename = os.path.basename(self.job_descriptor.path)

        self.image_location = get_location_by_type(Location.Type.image)
        self.thumb_location = get_location_by_type(Location.Type.thumb)
        self.proxy_location = get_location_by_type(Location.Type.proxy)

        self.copy_original()
        phmd = JPEGMetadata(**(self.analyse()))

        self.correct_folder(phmd)

        self.entry.files.append(FileDescriptor(path=self.image_rel_path,
                                               location_id=self.image_location.id,
                                               size=self.image_file_size,
                                               purpose=FileDescriptor.Purpose.primary,
                                               mime=self.job_descriptor.mime_type))

        angle, mirror = phmd.Angle, phmd.Mirror
        self.create_thumbnail(angle, mirror)
        self.create_proxy(angle, mirror)

        self.entry.physical_metadata = phmd

    def copy_original(self):
        filecopy = FileCopy(self.job_descriptor.location, self.job_descriptor.path, 
                            self.image_location, self.job_descriptor.safe_filename, link=True)
        filecopy.run()
        self.image_path = filecopy.destination_full_path
        self.image_rel_path = filecopy.destination_rel_path
        self.image_file_size = os.path.getsize(filecopy.destination_full_path)

    def correct_folder(self, phmd):
        real_date = phmd.DateTimeOriginal
        if not real_date: return

        self.entry.taken_ts = (datetime.strptime(
                real_date, '%Y:%m:%d %H:%M:%S').replace(microsecond=0)
                .strftime('%Y-%m-%d %H:%M:%S')
        )

        better_folder = self.image_location.suggest_folder(
            date=real_date.split(' ')[0].replace(':', '-')
        )
        if not self.image_rel_path.startswith(better_folder):
            filecopy = FileCopy(None, self.image_path,
                                self.image_location, self.job_descriptor.safe_filename,
                                link=True, keep_original=False, dest_folder=better_folder)
            filecopy.run()
            self.image_path = filecopy.destination_full_path
            self.image_rel_path = filecopy.destination_rel_path

    def create_thumbnail(self, angle, mirror):
        thumb_path = os.path.join(self.thumb_location.get_root(), self.image_rel_path)
        create_thumbnail(self.image_path, thumb_path, angle=angle, mirror=mirror)
        s = os.stat(thumb_path)
        self.entry.files.append(FileDescriptor(path=self.image_rel_path,
                                               size=s.st_size, created=datetime.fromtimestamp(s.st_ctime),
                                               location_id=self.thumb_location.id,
                                               purpose=FileDescriptor.Purpose.thumb,
                                               mime="image/jpeg"))


    def create_proxy(self, angle, mirror):
        proxy_path = os.path.join(self.proxy_location.get_root(), self.image_rel_path)
        convert(self.image_path, proxy_path, angle=angle, mirror=mirror)
        s = os.stat(proxy_path)
        self.entry.files.append(FileDescriptor(path=self.image_rel_path,
                                               size=s.st_size, created=datetime.fromtimestamp(s.st_ctime),
                                               location_id=self.proxy_location.id,
                                               purpose=FileDescriptor.Purpose.proxy,
                                               mime="image/jpeg"))

    def analyse(self):
        infile = self.image_path
        
        exif = None
        with open(infile, 'rb') as f:
            exif = exifread.process_file(f)

        orientation, mirror, angle = exif_orientation(exif)
        lon, lat = exif_position(exif)
        logging.debug(exif)
        
        return {
            "Artist": exif_string(exif, "Image Artist"),
            "ColorSpace": exif_string(exif, "EXIF ColorSpace"),
            "Copyright": exif_string(exif, "Image Copyright"),
            "Geometry": (exif_int(exif, "EXIF ExifImageWidth"), exif_int(exif, "EXIF ExifImageLength")),
            "DateTime": exif_string(exif, "EXIF DateTime"),
            "DateTimeDigitized": exif_string(exif, "EXIF DateTimeDigitized"),
            "DateTimeOriginal": exif_string(exif, "EXIF DateTimeOriginal"),
            "ExposureTime": exif_ratio(exif, "EXIF ExposureTime"),
            "FNumber": exif_ratio(exif, "EXIF FNumber"),
            "Flash": exif_string(exif, "EXIF Flash"),
            "FocalLength": exif_ratio(exif, "EXIF FocalLength"),
            "FocalLengthIn35mmFilm": exif_int(exif, "EXIF FocalLengthIn35mmFilm"),
            "ISOSpeedRatings": exif_int(exif, "EXIF ISOSpeedRatings"),
            "Make": exif_string(exif, "Image Make"),
            "Model": exif_string(exif, "Image Model"),
            "Orientation": orientation,
            "Mirror": mirror,
            "Angle": angle,
            "Saturation": exif_string(exif, "EXIF Saturation"),
            "Software": exif_string(exif, "Software"),
            "SubjectDistanceRange": exif_int(exif, "EXIF SubjectDistanceRange"),
            "WhiteBalance": exif_string(exif, "WhiteBalance"),
            "Latitude": lat,
            "Longitude": lon
        }

register_import_module('image/jpeg', JPEGImportModule)
register_import_module('image/tiff', JPEGImportModule)


class JPEGMetadata(Entry.DefaultPhysicalMetadata):
    Artist = Property()
    ColorSpace = Property()
    Copyright = Property()
    DateTime = Property()
    DateTimeDigitized = Property()
    DateTimeOriginal = Property()
    ExposureTime = Property(tuple)
    FNumber = Property(tuple)
    Flash = Property()
    FocalLength = Property(tuple)
    FocalLengthIn35mmFilm = Property(int)
    Geometry = Property(tuple)
    ISOSpeedRatings = Property(int)
    Make = Property()
    Model = Property()
    Orientation = Property()
    Mirror = Property()
    Angle = Property(int, default=0)
    Saturation = Property()
    Software = Property()
    SubjectDistanceRange = Property(int)
    WhiteBalance = Property()
    Latitude = Property()
    Longitude = Property()


register_metadata_schema(JPEGMetadata)


def create_thumbnail(path_in, path_out, override=False, size=THUMB_SIZE, angle=None, mirror=None):
    if os.path.exists(path_out) and not override:
        logging.debug("Thumbnail already exists, keeping")
        return
    try:
        os.makedirs(os.path.dirname(path_out))
    except FileExistsError as e:
        pass
    with open(path_out, 'w') as out:
        im = Image.open(path_in)
        _resize(im, (size, size), True, out, angle, mirror)
        im.close()
        logging.info("Created thumbnail %s", path_out)


def convert(path_in, path_out, longest_edge=PROXY_SIZE, angle=None, mirror=None):
    try:
        os.makedirs(os.path.dirname(path_out))
    except FileExistsError as e:
        pass

    with open(path_out, 'w') as out:
        im = Image.open(path_in)
        width, height = im.size
        if width > height:
            scale = float(longest_edge) / float(width)
        else:
            scale = float(longest_edge) / float(height)
        w = int(width * scale)
        h = int(height * scale)
        _resize(im, (w, h), False, out, angle, mirror)
        im.close()
        logging.info("Created image %s", path_out)


def _resize(img, box, fit, out, angle, mirror):
    '''Downsample the image.
    @param img: Image -  an Image-object
    @param box: tuple(x, y) - the bounding box of the result image
    @param fit: boolean - crop the image to fill the box
    @param out: file-like-object - save the image into the output stream
    @param angle: int - rotate with this angle
    @param mirror: str - mirror in this direction, None, "H" or "V"
    '''
    #preresize image with factor 2, 4, 8 and fast algorithm
    factor = 1
    bw, bh = box
    iw, ih = img.size
    while (iw*2/factor > 2*bw) and (ih*2/factor > 2*bh):
        factor *=2
    factor /= 2
    if factor > 1:
        img.thumbnail((iw/factor, ih/factor), Image.NEAREST)

    #calculate the cropping box and get the cropped part
    if fit:
        x1 = y1 = 0
        x2, y2 = img.size
        wRatio = 1.0 * x2/box[0]
        hRatio = 1.0 * y2/box[1]
        if hRatio > wRatio:
            y1 = int(y2/2-box[1]*wRatio/2)
            y2 = int(y2/2+box[1]*wRatio/2)
        else:
            x1 = int(x2/2-box[0]*hRatio/2)
            x2 = int(x2/2+box[0]*hRatio/2)
        img = img.crop((x1,y1,x2,y2))

    #Resize the image with best quality algorithm ANTI-ALIAS
    img.thumbnail(box, Image.ANTIALIAS)
    if mirror == 'H':
        img = img.transpose(Image.FLIP_RIGHT_LEFT)
    elif mirror == 'V':
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    if angle:
        img = img.rotate(angle)

    #save it into a file-like object
    img.save(out, "JPEG", quality=75)

