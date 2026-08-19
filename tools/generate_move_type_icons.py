# tools/generate_move_type_icons.py — Pokédex V10
"""Generate transparent, type-coloured move icons from the original type tiles."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import struct
import zlib


PROJECT_DIRECTORY = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = PROJECT_DIRECTORY / "assets" / "types"
DESTINATION_DIRECTORY = PROJECT_DIRECTORY / "assets" / "move-types"

TYPE_COLORS = {
    "normal": "#9FA19F",
    "grass": "#3FA129",
    "fire": "#E62829",
    "water": "#2980EF",
    "electric": "#FAC000",
    "bug": "#91A119",
    "flying": "#81B9EF",
    "rock": "#AFA981",
    "poison": "#9141CB",
    "ground": "#915121",
    "ice": "#3FD8FF",
    "fighting": "#FF8000",
    "psychic": "#EF4179",
    "ghost": "#704170",
    "dragon": "#5060E1",
    "dark": "#50413F",
    "steel": "#60A1B8",
    "fairy": "#EF70EF",
}

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
BYTES_PER_PIXEL = 4


def paeth_predictor(left: int, above: int, upper_left: int) -> int:
    prediction = left + above - upper_left
    left_distance = abs(prediction - left)
    above_distance = abs(prediction - above)
    upper_left_distance = abs(prediction - upper_left)
    if left_distance <= above_distance and left_distance <= upper_left_distance:
        return left
    if above_distance <= upper_left_distance:
        return above
    return upper_left


def decode_rgba_png(path: Path) -> tuple[int, int, bytearray]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"{path} is not a PNG file")

    offset = len(PNG_SIGNATURE)
    width = height = 0
    compressed = bytearray()

    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        offset += 12 + length

        if chunk_type == b"IHDR":
            width, height, bit_depth, colour_type, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
            if (bit_depth, colour_type, compression, filtering, interlace) != (8, 6, 0, 0, 0):
                raise ValueError(f"Unsupported PNG format in {path}")
        elif chunk_type == b"IDAT":
            compressed.extend(payload)
        elif chunk_type == b"IEND":
            break

    stride = width * BYTES_PER_PIXEL
    raw = zlib.decompress(bytes(compressed))
    expected_length = height * (stride + 1)
    if len(raw) != expected_length:
        raise ValueError(f"Unexpected image data length in {path}")

    pixels = bytearray(width * height * BYTES_PER_PIXEL)
    previous = bytearray(stride)
    source_offset = 0

    for row_index in range(height):
        filter_type = raw[source_offset]
        source_offset += 1
        encoded_row = raw[source_offset:source_offset + stride]
        source_offset += stride
        row = bytearray(stride)

        for index, encoded_value in enumerate(encoded_row):
            left = row[index - BYTES_PER_PIXEL] if index >= BYTES_PER_PIXEL else 0
            above = previous[index]
            upper_left = previous[index - BYTES_PER_PIXEL] if index >= BYTES_PER_PIXEL else 0

            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = above
            elif filter_type == 3:
                predictor = (left + above) // 2
            elif filter_type == 4:
                predictor = paeth_predictor(left, above, upper_left)
            else:
                raise ValueError(f"Unsupported PNG filter {filter_type} in {path}")

            row[index] = (encoded_value + predictor) & 0xFF

        start = row_index * stride
        pixels[start:start + stride] = row
        previous = row

    return width, height, pixels


def png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", checksum)


def encode_rgba_png(path: Path, width: int, height: int, pixels: bytearray) -> None:
    stride = width * BYTES_PER_PIXEL
    scanlines = bytearray()
    for row_index in range(height):
        start = row_index * stride
        scanlines.append(0)
        scanlines.extend(pixels[start:start + stride])

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = (
        PNG_SIGNATURE
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", zlib.compress(bytes(scanlines), level=9))
        + png_chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def hex_colour(value: str) -> tuple[int, int, int]:
    return tuple(int(value[index:index + 2], 16) for index in (1, 3, 5))


def convert_icon(source: Path, destination: Path, target_colour: str) -> None:
    width, height, source_pixels = decode_rgba_png(source)
    opaque_colours = Counter(
        tuple(source_pixels[index:index + 3])
        for index in range(0, len(source_pixels), BYTES_PER_PIXEL)
        if source_pixels[index + 3] >= 250
    )
    background = opaque_colours.most_common(1)[0][0]
    white_direction = tuple(255 - channel for channel in background)
    direction_length = sum(channel * channel for channel in white_direction)
    target_red, target_green, target_blue = hex_colour(target_colour)
    output = bytearray(len(source_pixels))

    for index in range(0, len(source_pixels), BYTES_PER_PIXEL):
        red, green, blue, source_alpha = source_pixels[index:index + 4]
        numerator = sum(
            (channel - background_channel) * direction
            for channel, background_channel, direction in zip(
                (red, green, blue), background, white_direction, strict=True
            )
        )
        coverage = max(0.0, min(1.0, numerator / direction_length))

        # Remove tiny background variations, then gently strengthen antialiased edges.
        coverage = max(0.0, (coverage - 0.01) / 0.99) ** 0.85
        alpha = round(source_alpha * coverage)
        if alpha == 0:
            output[index:index + 4] = (0, 0, 0, 0)
        else:
            output[index:index + 4] = (target_red, target_green, target_blue, alpha)

    encode_rgba_png(destination, width, height, output)


def main() -> None:
    DESTINATION_DIRECTORY.mkdir(parents=True, exist_ok=True)
    generated = 0
    for type_name, colour in TYPE_COLORS.items():
        source = SOURCE_DIRECTORY / f"{type_name}.png"
        destination = DESTINATION_DIRECTORY / source.name
        convert_icon(source, destination, colour)
        generated += 1
    print(f"{generated} transparent move type icons generated.")


if __name__ == "__main__":
    main()
