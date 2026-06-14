"""Generate application icon — monitor themed, clean and sharp."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("PIL not available — skipping icon generation")
    sys.exit(0)


def _rounded_rectangle_mask(size, radius):
    """Create a rounded-rect mask."""
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [(0, 0), (size[0] - 1, size[1] - 1)],
        radius=radius, fill=255,
    )
    return mask


def draw_monitor(draw, x1, y1, x2, y2, fill, outline, width):
    """Draw a monitor shape: screen + stand."""
    w = x2 - x1
    h = y2 - y1

    # Monitor bezel (outer rounded rect)
    bezel_margin = w * 0.10
    stand_h = h * 0.18
    stand_w = w * 0.22
    screen_top = y1
    screen_bottom = y2 - stand_h

    # Stand base
    base_w = w * 0.32
    base_h = w * 0.06
    base_y = y2 - base_h
    draw.rounded_rectangle(
        [x1 + (w - base_w) / 2, base_y, x1 + (w + base_w) / 2, y2],
        radius=int(w * 0.04), fill=fill, outline=None,
    )

    # Stand neck
    neck_w = stand_w
    neck_x1 = x1 + (w - neck_w) / 2
    neck_x2 = neck_x1 + neck_w
    neck_y1 = screen_bottom - h * 0.02
    draw.rectangle(
        [neck_x1, neck_y1, neck_x2, base_y + base_h * 0.3],
        fill=fill,
    )

    # Screen bezel
    bezel_r = int(w * 0.12)
    draw.rounded_rectangle(
        [x1, screen_top, x2, screen_bottom],
        radius=bezel_r, fill=fill, outline=None,
    )

    # Screen inner (darker area)
    inner_margin = w * 0.10
    inner_x1 = x1 + inner_margin
    inner_x2 = x2 - inner_margin
    inner_y1 = screen_top + inner_margin
    inner_y2 = screen_bottom - inner_margin * 0.8
    inner_r = int(bezel_r * 0.6)
    draw.rounded_rectangle(
        [inner_x1, inner_y1, inner_x2, inner_y2],
        radius=inner_r, fill=outline,
    )

    # Bright line (graph/signal) inside screen
    line_y_base = inner_y1 + (inner_y2 - inner_y1) * 0.55
    line_h = (inner_y2 - inner_y1) * 0.20
    for i, (lx, lw_frac) in enumerate([
        (inner_x1 + inner_margin * 1.0, 0.25),
        (inner_x1 + inner_margin * 1.8, 0.40),
        (inner_x1 + inner_margin * 2.6, 0.18),
        (inner_x1 + inner_margin * 3.4, 0.50),
        (inner_x1 + inner_margin * 4.2, 0.30),
    ]):
        lw_actual = (inner_x2 - inner_x1 - inner_margin * 2) * lw_frac
        ly = line_y_base - i * line_h * 0.6
        lh = line_h
        lx_end = min(lx + lw_actual, inner_x2 - inner_margin)
        draw.rounded_rectangle(
            [lx, ly, lx_end, ly + lh],
            radius=int(lh * 0.45), fill=fill,
        )

    # Small dot indicators
    dot_r = int(inner_margin * 0.30)
    dot_y = inner_y1 + inner_margin * 0.6
    for dx in [inner_x1 + inner_margin * 1.5, inner_x1 + inner_margin * 2.3]:
        draw.ellipse(
            [dx - dot_r, dot_y - dot_r, dx + dot_r, dot_y + dot_r],
            fill=fill,
        )


def generate_icon(out_path: Path):
    """Generate a multi-resolution .ico file."""
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = []

    BG = "#1e1e2e"      # dark background
    ACCENT = "#89b4fa"   # blue accent

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        margin = max(1, size // 24)
        radius = max(3, size // 6)

        if size <= 24:
            # Simple design for tiny sizes — bold rounded rect with accent dot
            d.rounded_rectangle(
                [margin, margin, size - margin, size - margin],
                radius=radius, fill=BG,
            )
            # Monitor shape simplified to a screen rectangle
            sm = size * 0.22
            sr = max(2, int(size * 0.15))
            d.rounded_rectangle(
                [sm, sm, size - sm, size - sm - size * 0.1],
                radius=sr, fill=ACCENT,
            )
            # stand
            sw = size * 0.18
            sx = (size - sw) / 2
            d.rectangle(
                [sx, size - sm - size * 0.1, sx + sw, size - margin],
                fill=ACCENT,
            )
        else:
            # Full monitor design for larger sizes
            d.rounded_rectangle(
                [margin, margin, size - margin, size - margin],
                radius=radius, fill=BG,
            )
            mon_margin = size * 0.18
            draw_monitor(
                d,
                mon_margin, mon_margin,
                size - mon_margin, size - mon_margin * 0.85,
                fill=ACCENT, outline="#45475a",
                width=max(1, size // 40),
            )

        frames.append(img)

    # Build ICO manually (PIL's ICO save is unreliable with append_images)
    import struct as _struct
    import io as _io

    png_list = []
    for frame in frames:
        buf = _io.BytesIO()
        frame.save(buf, format="PNG")
        png_list.append(buf.getvalue())

    with open(str(out_path), "wb") as fh:
        # ICO header: reserved(2) + type(2=ICO) + count(2)
        fh.write(_struct.pack("<HHH", 0, 1, len(frames)))
        # Image entry table
        data_offset = 6 + 16 * len(frames)
        for s, png in zip(sizes, png_list):
            w = 0 if s >= 256 else s
            h = 0 if s >= 256 else s
            fh.write(_struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(png), data_offset))
            data_offset += len(png)
        # PNG data for each frame
        for png in png_list:
            fh.write(png)

    print(f"Icon saved to {out_path}  ({len(frames)} frames: {sizes})")


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "icon.ico"
    generate_icon(out)
