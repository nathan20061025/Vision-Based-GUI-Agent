import pytest
from PIL import Image

from agent.pixel_rule import changed_share, looks_successful


def image(colour, size=(100, 100)):
    return Image.new("RGB", size, colour)


def test_identical_images_have_no_change():
    assert changed_share(image("white"), image("white")) == 0.0


def test_completely_different_images():
    assert changed_share(image("white"), image("black")) == 1.0


def test_part_of_the_image_changes():
    after = image("white")
    after.paste(image("black", (10, 10)), (0, 0))
    assert changed_share(image("white"), after) == pytest.approx(0.01)


def test_different_sizes_are_rejected():
    with pytest.raises(ValueError):
        changed_share(image("white"), image("white", (50, 50)))


def test_threshold():
    assert looks_successful(0.5, threshold=0.01)
    assert not looks_successful(0.0, threshold=0.01)
