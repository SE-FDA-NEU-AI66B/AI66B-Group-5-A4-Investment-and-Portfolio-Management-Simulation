"""Rebuild editable SVG and PNG diagrams: pip install Pillow; python scripts/diagram.py."""

from html import escape
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


class Canvas:
    def __init__(self, width, height):
        self.image = Image.new("RGB", (width, height), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="white"/>',
        ]

    def text(self, x, y, value, size=22, fill="#243b44"):
        candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        font = next(
            (ImageFont.truetype(p, size) for p in candidates if Path(p).exists()),
            ImageFont.load_default(),
        )
        self.draw.text((x, y), value, font=font, fill=fill)
        self.svg.append(
            f'<text x="{x}" y="{y + size}" font-family="Arial,sans-serif" font-size="{size}" fill="{fill}">{escape(value)}</text>'
        )

    def box(self, x, y, w, h, fill="#f4f8fa", ellipse=False):
        shape = self.draw.ellipse if ellipse else self.draw.rectangle
        shape((x, y, x + w, y + h), fill=fill, outline="#35566a", width=2)
        if ellipse:
            self.svg.append(
                f'<ellipse cx="{x + w / 2}" cy="{y + h / 2}" rx="{w / 2}" ry="{h / 2}" fill="{fill}" stroke="#35566a" stroke-width="2"/>'
            )
        else:
            self.svg.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="#35566a" stroke-width="2"/>'
            )

    def line(self, points, color="#6c8290", width=2):
        self.draw.line(points, fill=color, width=width)
        coordinates = " ".join(f"{x},{y}" for x, y in points)
        self.svg.append(
            f'<polyline points="{coordinates}" fill="none" stroke="{color}" stroke-width="{width}"/>'
        )

    def save(self, stem, png_folder="images"):
        (ROOT / "docs" / png_folder).mkdir(parents=True, exist_ok=True)
        self.image.save(ROOT / "docs" / png_folder / (stem + ".png"))
        (ROOT / "docs/diagrams" / (stem + ".svg")).write_text(
            "\n".join(self.svg + ["</svg>"]), encoding="utf-8"
        )


def entity(c, name, x, y, columns):
    c.box(x, y, 530, 65 + 35 * len(columns))
    c.text(x + 20, y + 12, name, 28)
    c.line([(x, y + 55), (x + 530, y + 55)])
    for index, column in enumerate(columns):
        c.text(x + 18, y + 65 + index * 35, column, 21)


def erd():
    c = Canvas(2140, 1480)
    c.text(60, 30, "VirtuTrade / M2 data model", 38)
    c.text(
        60,
        85,
        "PK = primary key    FK = foreign key    UQ = unique    All FKs required",
        23,
    )
    entity(
        c,
        "account",
        60,
        160,
        [
            "PK id: INTEGER",
            "UQ email: TEXT (NOCASE)",
            "password_hash: TEXT",
            "role: TEXT",
            "status: TEXT",
            "cash_vnd: INTEGER",
            "created_at: TEXT",
        ],
    )
    entity(
        c,
        "holding",
        760,
        160,
        [
            "PK id: INTEGER",
            "FK account_id: INTEGER",
            "FK instrument_id: INTEGER",
            "quantity: INTEGER",
            "cost_basis_vnd: INTEGER",
            "UQ (account_id, instrument_id)",
        ],
    )
    entity(
        c,
        "trade",
        760,
        560,
        [
            "PK id: INTEGER",
            "FK account_id: INTEGER",
            "FK instrument_id: INTEGER",
            "side: TEXT",
            "quantity: INTEGER",
            "fill_price_vnd: INTEGER",
            "realised_pnl_vnd: INTEGER NULL",
            "executed_at: TEXT",
        ],
    )
    entity(
        c,
        "audit_event",
        760,
        1050,
        [
            "PK id: INTEGER",
            "FK admin_id: INTEGER",
            "FK target_account_id: INTEGER",
            "previous_status: TEXT",
            "new_status: TEXT",
            "occurred_at: TEXT",
        ],
    )
    entity(
        c, "instrument", 1540, 160, ["PK id: INTEGER", "UQ symbol: TEXT", "name: TEXT"]
    )
    entity(
        c,
        "price_quote",
        1540,
        650,
        [
            "PK id: INTEGER",
            "FK UQ instrument_id: INTEGER",
            "price_vnd: INTEGER",
            "previous_close_vnd: INTEGER",
            "quoted_at: TEXT",
            "source: TEXT",
        ],
    )
    c.line([(590, 260), (760, 260)])
    c.text(608, 224, "1        0..*", 20)
    c.line([(590, 360), (655, 360), (655, 660), (760, 660)])
    c.text(605, 333, "1", 20)
    c.text(696, 627, "0..*", 20)
    c.line([(1540, 260), (1290, 260)])
    c.text(1340, 224, "0..*             1", 20)
    c.line([(1540, 300), (1420, 300), (1420, 660), (1290, 660)])
    c.text(1470, 304, "1", 20)
    c.text(1310, 627, "0..*", 20)
    c.line([(1800, 330), (1800, 650)])
    c.text(1815, 350, "1", 20)
    c.text(1815, 607, "0..1", 20)
    c.text(1570, 480, "latest snapshot only", 21)
    c.line([(190, 470), (190, 1125), (760, 1125)], "#47786c")
    c.text(208, 487, "1", 20)
    c.text(610, 1090, "0..*", 20)
    c.text(240, 1090, "admin_id", 21)
    c.line([(400, 470), (400, 1195), (760, 1195)], "#a1734c")
    c.text(417, 487, "1", 20)
    c.text(696, 1160, "0..*", 20)
    c.text(440, 1207, "target_account_id", 20)
    c.text(
        60,
        1390,
        "Source: database.py::SCHEMA. Only instrument and price_quote are seeded; other services are not implemented.",
        22,
    )
    c.save("erd")


def use_cases():
    c = Canvas(2050, 1480)
    c.text(50, 25, "VirtuTrade / use cases after Sprint 2 refinement", 36)
    c.box(430, 110, 1130, 1280, "#ffffff")
    c.text(660, 125, "Investment & Portfolio Simulation", 27)
    names = [
        ("US01", "Register / log in"),
        ("US02", "Receive initial capital"),
        ("US03", "View reference prices"),
        ("US04", "Buy shares"),
        ("US05", "Sell shares"),
        ("US06", "View portfolio"),
        ("US07", "Set stop-loss / take-profit"),
        ("US08", "View transaction history"),
        ("US09", "View performance"),
        ("US10", "Warn over-budget order"),
        ("US11", "Compare benchmark"),
        ("US12", "View leaderboard"),
        ("US13", "Manage account status"),
        ("US14", "Ingest validated quotes"),
    ]
    for index, (number, title) in enumerate(names):
        column = index // 7
        row = index % 7
        x = 480 + column * 545
        y = 200 + row * 160
        c.box(x, y, 480, 105, ellipse=True)
        c.text(x + 28, y + 24, number + "  " + title, 21)
    # Human and machine actors are kept outside the system boundary.
    for title, y in [("Guest", 230), ("Investor", 620), ("Admin", 1170)]:
        c.box(45, y, 240, 85, "#e9f3ed")
        c.text(75, y + 7, "<<actor>>", 17)
        c.text(75, y + 34, title, 26)
    c.box(1610, 1170, 400, 130, "#eef0fa")
    c.text(1630, 1190, "DNSE Websocket API", 26)
    c.text(1665, 1235, "<<Machine User>>", 23)
    c.line([(285, 270), (480, 250)])
    c.line([(285, 270), (370, 270), (370, 570), (480, 570)])
    for row in [0, 2, 3, 4, 5, 6]:
        c.line([(285, 660), (400, 660), (400, 250 + row * 160), (480, 250 + row * 160)])
    for row in [0, 1, 2, 3, 4]:
        c.line(
            [
                (285, 660),
                (330, 660),
                (330, 1360),
                (1535, 1360),
                (1535, 250 + row * 160),
                (1505, 250 + row * 160),
            ]
        )
    c.line(
        [
            (285, 1210),
            (350, 1210),
            (350, 1380),
            (1545, 1380),
            (1545, 1050),
            (1505, 1050),
        ],
        "#47786c",
    )
    c.line([(1610, 1210), (1505, 1210)], "#605aa0")
    # These relationships are between use cases, not provider-to-human UI.
    for y in range(305, 352, 10):
        c.line([(720, y), (720, y + 5)])
    c.line([(712, 350), (720, 360), (728, 350)])
    c.text(730, 307, "<<include>>", 16)
    c.text(730, 332, "registration only", 16)
    c.text(
        50,
        1430,
        "US01-US14; Admin is human; DNSE is external. Solid lines = association. Most use cases remain backlog.",
        22,
    )
    c.save("use-case-diagram", "diagrams")


if __name__ == "__main__":
    erd()
    use_cases()
