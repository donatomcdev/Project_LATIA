from io import BytesIO

from PIL import Image, ImageOps

MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_PHOTO_PIXELS = 25_000_000
PHOTO_FORMATS = ("JPEG", "PNG", "WEBP")


def normalize_photo(upload):
    raw = upload.stream.read(MAX_PHOTO_BYTES + 1)
    if len(raw) > MAX_PHOTO_BYTES:
        raise ValueError("La foto debe pesar como máximo 5 MB.")

    try:
        with Image.open(BytesIO(raw), formats=PHOTO_FORMATS) as image:
            if image.width * image.height > MAX_PHOTO_PIXELS:
                raise ValueError("La foto debe tener como máximo 25 megapíxeles.")
            if getattr(image, "is_animated", False):
                raise ValueError("Selecciona una foto sin animación.")
            image = ImageOps.exif_transpose(image)
            image.thumbnail((512, 512), Image.Resampling.LANCZOS)
            photo = image.convert("RGB")
            photo.info.clear()
            output = BytesIO()
            photo.save(output, "JPEG", quality=88, optimize=True)
            return output.getvalue()
    except (OSError, SyntaxError, Image.DecompressionBombError):
        raise ValueError("No se pudo abrir la foto. Usa un archivo JPG, PNG o WebP válido.") from None
