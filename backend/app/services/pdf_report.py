from __future__ import annotations

import textwrap
import zlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from reportlab.lib.utils import ImageReader

from app.schemas.mission import (
    ConstellationEstimate,
    DerivedRequirements,
    MissionInput,
    SolverSolution,
)
from app.schemas.mission_report import MissionReportJson
from app.services.branding import get_branding_logo_path


def _fmt(value: float | int | None, suffix: str = "", default: str = "—") -> str:
    if value is None:
        return default
    if isinstance(value, int):
        return f"{value:d}{suffix}"
    return f"{value:.2f}{suffix}"


def _plain(value: object) -> str:
    return str(value).replace("_", " ").title()


def _pdf_text(value: object) -> str:
    text = str(value)
    replacements = {
        "—": "-",
        "–": "-",
        "×": "x",
        "•": "-",
        "≤": "<=",
        "≥": ">=",
        "μ": "u",
    }
    for source, replacement in replacements.items():
        text = text.replace(source, replacement)
    encoded = text.encode("cp1252", errors="replace").decode("cp1252")
    return encoded.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


@dataclass
class _PdfPage:
    commands: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _PdfImage:
    name: str
    width: int
    height: int
    data: bytes


def _load_logo_image() -> _PdfImage | None:
    path = get_branding_logo_path(small=True)
    if path is None:
        return None
    try:
        reader = ImageReader(str(path))
        width, height = reader.getSize()
        rgb = reader.getRGBData()
    except OSError:
        return None
    return _PdfImage("Logo", int(width), int(height), zlib.compress(rgb))


class _PdfReport:
    width = 595.28
    height = 841.89
    margin = 42.0
    bottom = 54.0

    def __init__(self, title: str, subtitle: str) -> None:
        self.title = title
        self.subtitle = subtitle
        self.pages: list[_PdfPage] = []
        self.images = [_load_logo_image()]
        self.page = _PdfPage()
        self.pages.append(self.page)
        self.y = self.margin
        self._paint_header()

    def build(self) -> bytes:
        objects: list[bytes] = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        ]
        image_refs: dict[str, int] = {}
        for image in [item for item in self.images if item is not None]:
            image_id = len(objects) + 1
            image_refs[image.name] = image_id
            objects.append(
                (
                    f"<< /Type /XObject /Subtype /Image /Width {image.width} "
                    f"/Height {image.height} /ColorSpace /DeviceRGB "
                    f"/BitsPerComponent 8 /Filter /FlateDecode /Length {len(image.data)} >>"
                ).encode("ascii")
                + b"\nstream\n"
                + image.data
                + b"\nendstream"
            )
        page_refs: list[str] = []
        for page in self.pages:
            page_id = len(objects) + 1
            content_id = len(objects) + 2
            page_refs.append(f"{page_id} 0 R")
            stream = "\n".join(page.commands).encode("cp1252", errors="replace")
            xobjects = ""
            if image_refs:
                xobject_items = " ".join(
                    f"/{name} {object_id} 0 R" for name, object_id in image_refs.items()
                )
                xobjects = f" /XObject << {xobject_items} >>"
            objects.append(
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width:.2f} "
                    f"{self.height:.2f}] /Resources << /Font << /F1 3 0 R /F2 4 0 R >>"
                    f"{xobjects} >> "
                    f"/Contents {content_id} 0 R >>"
                ).encode("ascii")
            )
            objects.append(
                b"<< /Length "
                + str(len(stream)).encode("ascii")
                + b" >>\nstream\n"
                + stream
                + b"\nendstream"
            )
        objects[1] = (
            f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(page_refs)} >>"
        ).encode("ascii")

        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(len(output))
            output.extend(f"{index} 0 obj\n".encode("ascii"))
            output.extend(obj)
            output.extend(b"\nendobj\n")
        xref_at = len(output)
        output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        output.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        output.extend(
            (
                f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref_at}\n%%EOF\n"
            ).encode("ascii")
        )
        return bytes(output)

    def _cmd(self, command: str) -> None:
        self.page.commands.append(command)

    def _pdf_y(self, y: float) -> float:
        return self.height - y

    def _new_page(self) -> None:
        self.page = _PdfPage()
        self.pages.append(self.page)
        self.y = self.margin
        self._paint_header(continued=True)

    def _ensure(self, height: float) -> None:
        if self.y + height > self.height - self.bottom:
            self._new_page()

    def _paint_header(self, continued: bool = False) -> None:
        self.rect(0, 0, self.width, 94, fill=(10, 26, 48), stroke=None)
        self.rect(0, 90, self.width, 4, fill=(0, 122, 204), stroke=None)
        self.image(self.width - self.margin - 44, 25, 36, 36)
        heading = self.title if not continued else f"{self.title} (continued)"
        self.text(self.margin, 39, heading, size=22, bold=True, color=(255, 255, 255))
        self.text(self.margin, 63, self.subtitle, size=10, color=(198, 214, 232))
        self.y = 122

    def image(self, x: float, y: float, width: float, height: float, name: str = "Logo") -> None:
        if not any(item is not None and item.name == name for item in self.images):
            return
        self._cmd(
            f"q {width:.2f} 0 0 {height:.2f} {x:.2f} {self._pdf_y(y + height):.2f} cm /{name} Do Q"
        )

    def rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        fill: tuple[int, int, int] | None,
        stroke: tuple[int, int, int] | None = (218, 226, 236),
    ) -> None:
        if fill is not None:
            self._cmd(f"{fill[0] / 255:.3f} {fill[1] / 255:.3f} {fill[2] / 255:.3f} rg")
        if stroke is not None:
            self._cmd(f"{stroke[0] / 255:.3f} {stroke[1] / 255:.3f} {stroke[2] / 255:.3f} RG")
        op = "B" if fill is not None and stroke is not None else "f" if fill is not None else "S"
        self._cmd(f"{x:.2f} {self._pdf_y(y + height):.2f} {width:.2f} {height:.2f} re {op}")

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        color: tuple[int, int, int] = (218, 226, 236),
    ) -> None:
        self._cmd(f"{color[0] / 255:.3f} {color[1] / 255:.3f} {color[2] / 255:.3f} RG")
        self._cmd(f"{x1:.2f} {self._pdf_y(y1):.2f} m {x2:.2f} {self._pdf_y(y2):.2f} l S")

    def text(
        self,
        x: float,
        y: float,
        value: object,
        *,
        size: float = 10,
        bold: bool = False,
        color: tuple[int, int, int] = (28, 38, 52),
    ) -> None:
        font = "F2" if bold else "F1"
        self._cmd(f"{color[0] / 255:.3f} {color[1] / 255:.3f} {color[2] / 255:.3f} rg")
        self._cmd(
            f"BT /{font} {size:.2f} Tf {x:.2f} {self._pdf_y(y):.2f} Td ({_pdf_text(value)}) Tj ET"
        )

    def section(self, title: str) -> None:
        self._ensure(42)
        self.text(self.margin, self.y, title.upper(), size=11, bold=True, color=(0, 91, 156))
        self.line(
            self.margin,
            self.y + 8,
            self.width - self.margin,
            self.y + 8,
            color=(0, 122, 204),
        )
        self.y += 25

    def key_values(self, items: Sequence[tuple[str, object]], columns: int = 2) -> None:
        column_width = (self.width - 2 * self.margin - 14 * (columns - 1)) / columns
        rows = [items[i : i + columns] for i in range(0, len(items), columns)]
        self._ensure(max(1, len(rows)) * 39 + 10)
        for row in rows:
            x = self.margin
            row_y = self.y
            for label, value in row:
                self.rect(x, row_y - 6, column_width, 30, fill=(247, 250, 253))
                self.text(x + 9, row_y + 7, label, size=7.5, bold=True, color=(91, 104, 120))
                self.text(x + 9, row_y + 22, value, size=10.5, bold=True)
                x += column_width + 14
            self.y += 39

    def bullets(self, items: Iterable[object]) -> None:
        values = [str(item) for item in items] or ["None"]
        for value in values:
            wrapped = self.wrap(value, 92)
            self._ensure(13 * len(wrapped) + 7)
            for index, line in enumerate(wrapped):
                prefix = "- " if index == 0 else "  "
                self.text(self.margin + 6, self.y, f"{prefix}{line}", size=9.2, color=(47, 58, 74))
                self.y += 13
        self.y += 5

    def table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[object]],
        widths: Sequence[float],
    ) -> None:
        self._ensure(34)
        x = self.margin
        self.rect(
            self.margin,
            self.y - 7,
            sum(widths),
            24,
            fill=(232, 241, 250),
            stroke=(190, 210, 229),
        )
        for header, width in zip(headers, widths, strict=True):
            self.text(x + 5, self.y + 8, header, size=7.5, bold=True, color=(42, 65, 92))
            x += width
        self.y += 24

        for row in rows:
            wrapped_cells = [
                self.wrap(cell, max(8, int((width - 10) / 4.8)))
                for cell, width in zip(row, widths, strict=True)
            ]
            row_height = max(22, 12 * max(len(cell) for cell in wrapped_cells) + 9)
            self._ensure(row_height + 2)
            self.rect(
                self.margin,
                self.y - 6,
                sum(widths),
                row_height,
                fill=(255, 255, 255),
                stroke=(224, 231, 238),
            )
            x = self.margin
            for cell_lines, width in zip(wrapped_cells, widths, strict=True):
                for index, line in enumerate(cell_lines[:4]):
                    self.text(x + 5, self.y + 8 + index * 11, line, size=8.2, color=(38, 48, 63))
                x += width
            self.y += row_height
        self.y += 8

    @staticmethod
    def wrap(value: object, max_chars: int) -> list[str]:
        text = str(value)
        if not text:
            return [""]
        return textwrap.wrap(text, width=max_chars, break_long_words=False) or [text[:max_chars]]


def render_mission_report_pdf(
    mission_input: MissionInput,
    requirements: DerivedRequirements,
    constellation: ConstellationEstimate,
    solution: SolverSolution,
) -> bytes:
    report = _PdfReport(
        "Mission Report",
        "ONE V3 mission configuration summary and selected spacecraft architecture",
    )
    report.section("Executive Summary")
    report.key_values(
        [
            ("Mission family", _plain(mission_input.family.value)),
            ("ROI", _plain(mission_input.roi.type)),
            ("Revisit target", _fmt(mission_input.parameters.revisit_time_hours, " h")),
            ("Selected platform", f"{solution.platform.name} ({solution.platform.bus_size_u:g}U)"),
            ("Constellation", f"{constellation.satellites} sats / {constellation.planes} planes"),
            ("Indicative cost", _fmt(solution.budgets.total_cost_kusd, " kUSD")),
        ],
        columns=2,
    )

    report.section("Derived Requirements")
    report.key_values(
        [
            ("Payload mass", _fmt(requirements.payload_mass_kg, " kg")),
            ("Payload volume", _fmt(requirements.payload_volume_cm3, " cm3")),
            ("Payload avg power", _fmt(requirements.payload_avg_power_w, " W")),
            ("Payload peak power", _fmt(requirements.payload_peak_power_w, " W")),
            ("Min downlink", _fmt(requirements.min_downlink_mbps, " Mbps")),
            ("Pointing error", _fmt(requirements.max_pointing_error_deg, " deg")),
            ("Thermal class", _plain(requirements.thermal_class.value)),
        ],
        columns=2,
    )

    report.section("Constellation Estimate")
    report.key_values(
        [
            ("Orbit", f"{constellation.orbit_type} at {constellation.altitude_km} km"),
            ("Satellites", constellation.satellites),
            ("Planes", constellation.planes),
            ("Satellites/plane", constellation.satellites_per_plane),
        ],
        columns=2,
    )
    if constellation.notes:
        report.bullets(constellation.notes)

    report.section("Selected Subsystems")
    report.table(
        ["Domain", "Component", "Mass kg", "Avg W", "Peak W", "Cost kUSD"],
        [
            [
                subsystem.domain,
                subsystem.name,
                _fmt(subsystem.mass_kg),
                _fmt(subsystem.avg_power_w),
                _fmt(subsystem.peak_power_w),
                _fmt(subsystem.cost_kusd),
            ]
            for subsystem in solution.subsystems
        ],
        [70, 205, 58, 58, 58, 74],
    )

    report.section("Budgets and Margins")
    budgets = solution.budgets
    report.key_values(
        [
            ("Total mass", _fmt(budgets.total_mass_kg, " kg")),
            ("Mass margin", _fmt(budgets.mass_margin_kg, " kg")),
            ("Avg power", _fmt(budgets.total_avg_power_w, " W")),
            ("Avg power margin", _fmt(budgets.avg_power_margin_w, " W")),
            ("Peak power", _fmt(budgets.total_peak_power_w, " W")),
            ("Peak power margin", _fmt(budgets.peak_power_margin_w, " W")),
        ],
        columns=2,
    )

    if solution.warnings:
        report.section("Warnings")
        report.bullets(solution.warnings)

    report.section("Trace")
    report.bullets(solution.trace)
    return report.build()


def render_report_pdf(report_json: MissionReportJson) -> bytes:
    summary = report_json.mission_summary
    payload = report_json.payload.summary
    selection = report_json.subsystem_selection
    totals = selection.totals
    margins = selection.margins

    report = _PdfReport(
        "Mission Report",
        "ONE V3 deterministic engineering report for mission review and download",
    )
    report.section("Executive Summary")
    report.key_values(
        [
            ("Mission family", _plain(summary.family.value)),
            ("ROI", _plain(summary.roi.type)),
            ("Payload", payload.name),
            ("Feasibility", f"{selection.feasible} ({selection.status})"),
            ("Chosen bus", _fmt(report_json.bus_platform.chosen_bus_size_u, " U")),
            ("Estimated satellites", _fmt(report_json.constellation.estimated_satellites)),
        ],
        columns=2,
    )

    report.section("Payload")
    report.key_values(
        [
            (
                "Envelope",
                f"{_fmt(payload.length_mm)} x {_fmt(payload.width_mm)} x "
                f"{_fmt(payload.height_mm)} mm",
            ),
            ("Mass", _fmt(payload.mass_kg, " kg")),
            ("Avg power", _fmt(payload.avg_power_w, " W")),
            ("Peak power", _fmt(payload.peak_power_w, " W")),
            ("Data rate", _fmt(payload.data_rate_mbps, " Mbps")),
            ("Pointing", _fmt(payload.pointing_accuracy_deg, " deg")),
        ],
        columns=2,
    )

    report.section("Constellation Estimate")
    if report_json.constellation.available:
        report.key_values(
            [
                ("Orbit family", report_json.constellation.orbit_family or "—"),
                ("Satellites", _fmt(report_json.constellation.estimated_satellites)),
                ("Planes", _fmt(report_json.constellation.planes)),
                ("Satellites/plane", _fmt(report_json.constellation.satellites_per_plane)),
            ],
            columns=2,
        )
    else:
        report.bullets(["Constellation estimate is not available for this solve."])

    report.section("Derived Requirements")
    derived = report_json.derived_requirements
    report.key_values(
        [
            ("Required bus volume", _fmt(derived.required_bus_volume_u, " U")),
            ("Mass budget", _fmt(derived.estimated_total_mass_budget_kg, " kg")),
            ("Downlink class", _plain(derived.required_downlink_class.value)),
            ("Storage", _fmt(derived.required_storage_gb, " GB")),
            ("Pointing accuracy", _fmt(derived.required_pointing_accuracy_deg, " deg")),
            ("Thermal mode", _plain(derived.required_thermal_mode.value)),
        ],
        columns=2,
    )

    report.section("Selected Subsystems")
    report.table(
        ["Domain", "Component", "Mass kg", "Avg W", "Peak W", "Cost kUSD"],
        [
            [
                component.domain,
                component.name,
                _fmt(component.mass_kg),
                _fmt(component.avg_power_w),
                _fmt(component.peak_power_w),
                _fmt(component.cost_kusd),
            ]
            for component in selection.selected
        ],
        [70, 205, 58, 58, 58, 74],
    )

    report.section("Totals and Margins")
    report.key_values(
        [
            ("Total mass", f"{_fmt(totals.total_mass_kg) if totals else '—'} kg"),
            ("Mass margin", f"{_fmt(margins.mass_margin_kg) if margins else '—'} kg"),
            ("Avg power", f"{_fmt(totals.total_avg_power_w) if totals else '—'} W"),
            ("Avg power margin", f"{_fmt(margins.avg_power_margin_w) if margins else '—'} W"),
            ("Peak power", f"{_fmt(totals.total_peak_power_w) if totals else '—'} W"),
            ("Peak power margin", f"{_fmt(margins.peak_power_margin_w) if margins else '—'} W"),
            ("Indicative cost", f"{_fmt(totals.total_cost_kusd) if totals else '—'} kUSD"),
            ("Bus volume margin", f"{_fmt(margins.bus_volume_margin_u) if margins else '—'} U"),
        ],
        columns=2,
    )

    report.section("Warnings")
    report.bullets(report_json.warnings)
    report.section("Assumptions")
    report.bullets(report_json.assumptions)
    return report.build()
