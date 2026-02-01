"""Test QR service center image functionality."""

import base64
import io
from pathlib import Path
from typing import cast

from PIL import Image

from wifiqr.services.qr_service import CENTER_IMAGE_SIZE, generate_qr_image, save_qr_image


def test_generate_qr_without_center_image() -> None:
    """Verify QR generation works without center image."""
    payload = "WIFI:T:WPA;S:TestNet;P:password123;H:false;;"
    image = generate_qr_image(payload)
    assert image is not None
    assert isinstance(image, Image.Image)
    assert image.mode == "RGB"


def test_generate_qr_with_valid_center_image() -> None:
    """Verify QR generation works with a valid center image."""
    # Create a simple test image (red square)
    test_img = Image.new("RGB", (50, 50), color="red")
    buffer = io.BytesIO()
    test_img.save(buffer, format="PNG")
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    payload = "WIFI:T:WPA;S:TestNet;P:password123;H:false;;"
    image = generate_qr_image(payload, center_image_data=image_base64)

    assert image is not None
    assert isinstance(image, Image.Image)
    assert image.mode == "RGB"
    # Image should have the center area modified
    # Check that center pixels are different from pure white/black QR pattern
    center_x = image.width // 2
    center_y = image.height // 2
    center_pixel = image.getpixel((center_x, center_y))
    # Should not be pure white (255, 255, 255) or pure black (0, 0, 0)
    # since we embedded a red image
    assert center_pixel != (255, 255, 255) and center_pixel != (0, 0, 0)


def test_generate_qr_with_custom_size() -> None:
    """Verify QR generation respects custom size parameter."""
    payload = "WIFI:T:WPA;S:TestNet;P:password123;H:false;;"
    custom_size = 500
    image = generate_qr_image(payload, size=custom_size)

    assert image.width == custom_size
    assert image.height == custom_size


def test_generate_qr_with_invalid_center_image() -> None:
    """Verify QR generation rejects invalid center image data."""
    payload = "WIFI:T:WPA;S:TestNet;P:password123;H:false;;"
    # Invalid base64 data
    invalid_image_data = "not_valid_base64_!@#$"

    try:
        generate_qr_image(payload, center_image_data=invalid_image_data)
        raise AssertionError("Expected ValueError for invalid base64 data")
    except ValueError:
        assert True


def test_generate_qr_with_corrupted_image_data() -> None:
    """Verify QR generation rejects corrupted image data."""
    payload = "WIFI:T:WPA;S:TestNet;P:password123;H:false;;"
    # Valid base64 but not a valid image
    corrupted_data = base64.b64encode(b"this is not an image").decode("utf-8")

    try:
        generate_qr_image(payload, center_image_data=corrupted_data)
        raise AssertionError("Expected ValueError for corrupted image data")
    except ValueError:
        assert True


def test_center_image_is_resized_correctly() -> None:
    """Verify center image is resized to CENTER_IMAGE_SIZE."""
    # Create a large test image
    large_img = Image.new("RGB", (500, 500), color="blue")
    buffer = io.BytesIO()
    large_img.save(buffer, format="PNG")
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    payload = "WIFI:T:WPA;S:TestNet;P:password123;H:false;;"
    image = generate_qr_image(payload, size=400, center_image_data=image_base64)

    # The center should contain blue pixels from our embedded image
    # Check pixels around the center area
    center_x = image.width // 2
    center_y = image.height // 2

    # Sample a few pixels in the center region
    has_blue_component = False
    for dx in range(-CENTER_IMAGE_SIZE // 4, CENTER_IMAGE_SIZE // 4, 10):
        for dy in range(-CENTER_IMAGE_SIZE // 4, CENTER_IMAGE_SIZE // 4, 10):
            pixel = cast(tuple[int, int, int], image.getpixel((center_x + dx, center_y + dy)))
            # Check if pixel has blue component (our embedded image is blue)
            if pixel[2] > 100:  # Blue channel
                has_blue_component = True
                break
        if has_blue_component:
            break

    assert has_blue_component, "Center image should be embedded in QR code"


def test_generate_qr_with_rgba_center_image() -> None:
    """Verify QR generation handles RGBA center images correctly."""
    # Create an RGBA image with transparency
    rgba_img = Image.new("RGBA", (100, 100), color=(255, 0, 255, 128))
    buffer = io.BytesIO()
    rgba_img.save(buffer, format="PNG")
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    payload = "WIFI:T:WPA;S:TestNet;P:password123;H:false;;"
    image = generate_qr_image(payload, center_image_data=image_base64)

    assert image is not None
    assert isinstance(image, Image.Image)
    assert image.mode == "RGB"  # Should be converted back to RGB


def test_save_qr_image(tmp_path: Path) -> None:
    """Verify QR image can be saved to disk."""
    payload = "WIFI:T:WPA;S:TestNet;P:password123;H:false;;"
    image = generate_qr_image(payload)

    output_path = tmp_path / "test_qr.png"
    save_qr_image(image, str(output_path))

    assert output_path.exists()
    # Verify the saved image can be loaded
    loaded_image = Image.open(output_path)
    assert loaded_image.size == image.size

