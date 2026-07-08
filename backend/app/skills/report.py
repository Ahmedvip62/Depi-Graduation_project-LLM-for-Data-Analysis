"""Professional PDF report generation for Universal Analyst sessions."""
import html
import io
import logging
import re
from datetime import datetime
from typing import Any, Iterable, List, Optional

import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

# Brand palette — aligned with the frontend's indigo/amber instrument theme so
# the PDF and the app read as one product.
INK = colors.HexColor("#17202A")
MUTED = colors.HexColor("#5E6A75")
FAINT = colors.HexColor("#8A98A6")
LINE = colors.HexColor("#D9E0E6")
SURFACE = colors.HexColor("#F5F7FA")
SURFACE_DARK = colors.HexColor("#E9EEF3")
BRAND = colors.HexColor("#6366F1")  # indigo (primary)
ACCENT = colors.HexColor("#F0A92B")  # amber (measurement emphasis)
DANGER = colors.HexColor("#BE123C")

CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
CONTROL_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")

MAX_CHARTS_IN_REPORT = 8
MAX_COLUMNS_IN_REPORT = 42
MAX_CONVERSATION_MESSAGES = 10


def _fmt(value: Any, suffix: str = "") -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}{suffix}"
    if isinstance(value, float):
        return f"{value:,.2f}{suffix}"
    return f"{value}{suffix}"


def _plain(value: Any, max_chars: int | None = None) -> str:
    text = "" if value is None else str(value)
    text = CONTROL_RE.sub(" ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if max_chars and len(text) > max_chars:
        text = text[: max_chars - 3].rstrip() + "..."
    return text


def _safe_text(value: Any, max_chars: int | None = None) -> str:
    return html.escape(_plain(value, max_chars=max_chars))


def _inline_markdown(text: Any, max_chars: int | None = None) -> str:
    escaped = _safe_text(text, max_chars=max_chars)
    escaped = LINK_RE.sub(r"\1 (\2)", escaped)
    return BOLD_RE.sub(r"<b>\1</b>", escaped)


def _chart_inner(spec: Any) -> Any:
    if isinstance(spec, dict):
        return spec.get("chart_spec") or spec.get("config") or spec
    return spec


def _top_value_text(top_values: Any) -> str:
    if not top_values:
        return "-"
    if isinstance(top_values, dict):
        return ", ".join(f"{k}: {v}" for k, v in list(top_values.items())[:4])
    if isinstance(top_values, list):
        parts: list[str] = []
        for item in top_values[:4]:
            if isinstance(item, dict):
                value = item.get("value")
                count = item.get("count")
                parts.append(f"{value}: {count}" if count is not None else str(value))
            else:
                parts.append(str(item))
        return ", ".join(parts) or "-"
    return str(top_values)


class ReportSkill:
    """Generate a branded PDF report from session profile, charts, and chat."""

    @staticmethod
    def _styles() -> dict[str, ParagraphStyle]:
        base = getSampleStyleSheet()
        return {
            "title": ParagraphStyle(
                "UA_Title",
                parent=base["Title"],
                fontName="Helvetica-Bold",
                fontSize=27,
                leading=31,
                textColor=INK,
                alignment=TA_CENTER,
                spaceAfter=8,
            ),
            "subtitle": ParagraphStyle(
                "UA_Subtitle",
                parent=base["Normal"],
                fontSize=10,
                leading=14,
                textColor=MUTED,
                alignment=TA_CENTER,
                spaceAfter=16,
            ),
            "eyebrow": ParagraphStyle(
                "UA_Eyebrow",
                parent=base["Normal"],
                fontName="Helvetica-Bold",
                fontSize=7.5,
                leading=10,
                textColor=BRAND,
                alignment=TA_CENTER,
                spaceAfter=6,
            ),
            "h1": ParagraphStyle(
                "UA_H1",
                parent=base["Heading1"],
                fontName="Helvetica-Bold",
                fontSize=16,
                leading=20,
                textColor=INK,
                spaceBefore=8,
                spaceAfter=8,
            ),
            "h2": ParagraphStyle(
                "UA_H2",
                parent=base["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=11.5,
                leading=15,
                textColor=INK,
                spaceBefore=5,
                spaceAfter=4,
            ),
            "body": ParagraphStyle(
                "UA_Body",
                parent=base["BodyText"],
                fontSize=9,
                leading=13,
                textColor=INK,
                alignment=TA_LEFT,
                spaceAfter=5,
            ),
            "muted": ParagraphStyle(
                "UA_Muted",
                parent=base["BodyText"],
                fontSize=8,
                leading=11,
                textColor=MUTED,
                spaceAfter=4,
            ),
            "small": ParagraphStyle(
                "UA_Small",
                parent=base["BodyText"],
                fontSize=7.5,
                leading=10,
                textColor=FAINT,
            ),
            "bullet": ParagraphStyle(
                "UA_Bullet",
                parent=base["BodyText"],
                fontSize=9,
                leading=12,
                leftIndent=13,
                bulletIndent=4,
                textColor=INK,
                spaceAfter=3,
            ),
            "table_header": ParagraphStyle(
                "UA_TableHeader",
                parent=base["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=7.5,
                leading=9.5,
                textColor=colors.white,
            ),
            "table_cell": ParagraphStyle(
                "UA_TableCell",
                parent=base["BodyText"],
                fontSize=7.4,
                leading=9.5,
                textColor=INK,
            ),
            "kpi_label": ParagraphStyle(
                "UA_KpiLabel",
                parent=base["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=7,
                leading=9,
                textColor=FAINT,
            ),
            "kpi_value": ParagraphStyle(
                "UA_KpiValue",
                parent=base["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=14,
                leading=17,
                textColor=INK,
            ),
        }

    @staticmethod
    def _cell(value: Any, style: ParagraphStyle) -> Paragraph:
        return Paragraph(_safe_text(value, max_chars=420), style)

    @staticmethod
    def _table(data: list[list[Any]], widths: list[float] | None = None) -> Table:
        styles = ReportSkill._styles()
        rows: list[list[Any]] = []
        for row_idx, row in enumerate(data):
            style = styles["table_header"] if row_idx == 0 else styles["table_cell"]
            rows.append([ReportSkill._cell(value, style) for value in row])

        table = Table(rows, colWidths=widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), INK),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.25, LINE),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SURFACE]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return table

    @staticmethod
    def _footer(canvas_obj, doc) -> None:
        canvas_obj.saveState()
        width, _ = A4
        y = 0.42 * inch
        canvas_obj.setStrokeColor(LINE)
        canvas_obj.setLineWidth(0.4)
        canvas_obj.line(doc.leftMargin, y + 0.08 * inch, width - doc.rightMargin, y + 0.08 * inch)
        canvas_obj.setFillColor(MUTED)
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.drawString(doc.leftMargin, y - 0.02 * inch, "Universal Analyst")
        canvas_obj.drawRightString(width - doc.rightMargin, y - 0.02 * inch, f"Page {doc.page}")
        canvas_obj.restoreState()

    @staticmethod
    def _draw_brand_mark(canvas_obj, cx: float, cy: float, scale: float = 1.0) -> None:
        """Draw the UA logo mark (query bracket + rising data ticks + amber signal)
        as vector shapes. Mirrors frontend/src/components/Logo.jsx on a 24-unit grid
        centered at (cx, cy)."""
        s = scale  # unit size; the mark spans roughly 24*s wide.
        canvas_obj.saveState()
        canvas_obj.translate(cx - 12 * s, cy - 12 * s)
        # Query bracket (ink).
        canvas_obj.setStrokeColor(INK)
        canvas_obj.setFillColor(INK)
        canvas_obj.setLineWidth(1.6 * s)
        canvas_obj.setLineCap(1)  # round
        canvas_obj.setLineJoin(1)
        p = canvas_obj.beginPath()
        p.moveTo(8.5 * s, 19.5 * s)
        p.lineTo(6.25 * s, 19.5 * s)
        # rounded corner
        p.curveTo(5.0 * s, 19.5 * s, 4.5 * s, 19.0 * s, 4.5 * s, 17.75 * s)
        p.lineTo(4.5 * s, 6.25 * s)
        p.curveTo(4.5 * s, 5.0 * s, 5.0 * s, 4.5 * s, 6.25 * s, 4.5 * s)
        p.lineTo(8.5 * s, 4.5 * s)
        canvas_obj.drawPath(p, stroke=1, fill=0)
        # Rising data ticks (indigo) - rising upward from y = 4.5*s baseline.
        canvas_obj.setFillColor(BRAND)
        for (x, y, w, h) in ((10.5, 4.5, 2.2, 4.5), (14.0, 4.5, 2.2, 8.5), (17.5, 4.5, 2.2, 12.5)):
            canvas_obj.roundRect(x * s, y * s, w * s, h * s, 0.7 * s, stroke=0, fill=1)
        # Lighter middle tick for depth.
        canvas_obj.setFillColor(colors.HexColor("#9098FB"))
        canvas_obj.roundRect(14.0 * s, 4.5 * s, 2.2 * s, 8.5 * s, 0.7 * s, stroke=0, fill=1)
        # Signal point at the peak (amber).
        canvas_obj.setFillColor(ACCENT)
        canvas_obj.circle(18.6 * s, 19.3 * s, 1.5 * s, stroke=0, fill=1)
        canvas_obj.restoreState()

    @staticmethod
    def _cover_page(
        canvas_obj,
        doc,
        title: str,
        file_name: str,
        generated_at: str,
    ) -> None:
        """A full-bleed cover page: brand mark, title, dataset, date, divider."""
        width, height = A4
        canvas_obj.saveState()
        # Solid ink background for a confident, branded cover.
        canvas_obj.setFillColor(INK)
        canvas_obj.rect(0, 0, width, height, stroke=0, fill=1)

        # Brand mark, top-left.
        ReportSkill._draw_brand_mark(canvas_obj, 1.1 * inch, height - 1.2 * inch, scale=1.5)

        # Wordmark next to the mark.
        canvas_obj.setFillColor(colors.white)
        canvas_obj.setFont("Helvetica-Bold", 14)
        canvas_obj.drawString(1.7 * inch, height - 1.25 * inch, "Universal Analyst")
        canvas_obj.setFillColor(colors.HexColor("#98A2B3"))
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawString(1.7 * inch, height - 1.45 * inch, "ANALYSIS REPORT")

        # Title block, vertically centered-ish.
        canvas_obj.setFillColor(colors.white)
        canvas_obj.setFont("Helvetica-Bold", 30)
        # Wrap the title to ~28 chars per line at this size.
        title_lines = ReportSkill._wrap_text(title, 28)
        ty = height * 0.62
        for i, line in enumerate(title_lines[:3]):
            canvas_obj.drawString(1.1 * inch, ty - i * 34, line)

        # Amber divider under the title.
        canvas_obj.setStrokeColor(ACCENT)
        canvas_obj.setLineWidth(2.4)
        last_y = ty - (min(len(title_lines), 3)) * 34 + 6
        canvas_obj.line(1.1 * inch, last_y, 1.1 * inch + 2.2 * inch, last_y)

        # Dataset + date metadata.
        canvas_obj.setFillColor(colors.HexColor("#C7CEDA"))
        canvas_obj.setFont("Helvetica", 11)
        canvas_obj.drawString(1.1 * inch, last_y - 30, f"Dataset:  {file_name}")
        canvas_obj.drawString(1.1 * inch, last_y - 50, f"Generated:  {generated_at}")

        # Footer line on the cover.
        canvas_obj.setStrokeColor(colors.HexColor("#2A3541"))
        canvas_obj.setLineWidth(0.6)
        canvas_obj.line(1.1 * inch, 0.9 * inch, width - 1.1 * inch, 0.9 * inch)
        canvas_obj.setFillColor(colors.HexColor("#6B7686"))
        canvas_obj.setFont("Helvetica-Oblique", 8)
        canvas_obj.drawString(1.1 * inch, 0.7 * inch, "Local LLM analysis — grounded in the dataset profile.")
        canvas_obj.restoreState()

    @staticmethod
    def _wrap_text(text: str, max_chars: int) -> list[str]:
        """Greedy word-wrap for the cover title."""
        words = (text or "").split()
        if not words:
            return [""]
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    @staticmethod
    def _figure_from_spec(spec: Any) -> Optional[go.Figure]:
        """Build a Plotly Figure from a stored chart spec or figure JSON."""
        import plotly.io as pio

        try:
            if isinstance(spec, go.Figure):
                return spec
            inner = _chart_inner(spec)
            if isinstance(inner, str):
                return pio.from_json(inner)
            if isinstance(inner, dict):
                return go.Figure(data=inner.get("data", []), layout=inner.get("layout", {}))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not parse chart spec for report: %s", exc)
        return None

    @staticmethod
    def _render_chart_image(spec: Any, df: Optional[Any] = None) -> Optional[bytes]:
        """Render a chart spec to PNG bytes via Plotly/Kaleido."""
        fig = None
        if df is not None:
            try:
                inner = _chart_inner(spec)
                if isinstance(inner, dict):
                    from app.visualization.chart_factory import ChartFactory
                    import plotly.io as pio
                    chart_json = ChartFactory.generate_chart(df, inner)
                    fig = pio.from_json(chart_json)
            except Exception as e:
                logger.warning("Could not compile chart spec using ChartFactory in report: %s", e)

        if fig is None:
            fig = ReportSkill._figure_from_spec(spec)

        if fig is None:
            return None
        try:
            fig.update_layout(
                template="plotly_white",
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(color="#17202A", family="Helvetica", size=13),
                title_font=dict(size=18, color="#17202A"),
                margin=dict(l=56, r=28, t=58, b=46),
                width=1100,
                height=620,
            )
            return fig.to_image(format="png", width=1100, height=620, scale=2)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Chart image render failed: %s", exc)
            return None

    @staticmethod
    def _chart_title(spec: Any, index: int) -> str:
        if isinstance(spec, dict):
            if spec.get("title"):
                return str(spec["title"])
            inner = _chart_inner(spec)
            layout = inner.get("layout", {}) if isinstance(inner, dict) else {}
            title = layout.get("title") if isinstance(layout, dict) else None
            if isinstance(title, dict) and title.get("text"):
                return str(title["text"])
            if isinstance(title, str) and title:
                return title
        return f"Figure {index + 1}"

    @staticmethod
    def _kpi_table(profile: Optional[dict], eda: Optional[dict], chart_count: int) -> Table:
        styles = ReportSkill._styles()
        summary = (eda or {}).get("summary") or {}
        rows = [
            ["Rows", _fmt(summary.get("row_count", (profile or {}).get("row_count")))],
            ["Columns", _fmt(summary.get("column_count", (profile or {}).get("column_count")))],
            ["Missing", _fmt(summary.get("missing_pct", (profile or {}).get("missing_pct")), "%")],
            ["Numeric", _fmt(summary.get("numeric_count", len((profile or {}).get("numeric_columns") or [])))],
            ["Categorical", _fmt(summary.get("categorical_count", len((profile or {}).get("categorical_columns") or [])))],
            ["Generated visuals", _fmt(chart_count)],
        ]
        cells = [
            Paragraph(
                f"<font color='#8A98A6'><b>{_safe_text(label)}</b></font><br/>"
                f"<font color='#17202A'><b>{_safe_text(value)}</b></font>",
                styles["body"],
            )
            for label, value in rows
        ]
        table = Table([cells[:3], cells[3:]], colWidths=[2.1 * inch, 2.1 * inch, 2.1 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), SURFACE),
                    ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return table

    @staticmethod
    def _column_rows(profile: Optional[dict], limit: int = MAX_COLUMNS_IN_REPORT) -> list[list[Any]]:
        if not profile:
            return []
        rows: list[list[Any]] = [["Column", "Role", "Missing", "Unique", "Profile signals"]]
        for name, info in list((profile.get("columns") or {}).items())[:limit]:
            summary_bits = []
            if info.get("mean_value") is not None:
                summary_bits.append(f"mean={_fmt(info.get('mean_value'))}")
            if info.get("median_value") is not None:
                summary_bits.append(f"median={_fmt(info.get('median_value'))}")
            if info.get("min_value") is not None:
                summary_bits.append(f"range={_fmt(info.get('min_value'))} to {_fmt(info.get('max_value'))}")
            top_values = _top_value_text(info.get("top_values"))
            if top_values != "-":
                summary_bits.append(f"top={top_values}")
            samples = info.get("sample_values") or []
            if samples:
                summary_bits.append("sample=" + ", ".join(str(v) for v in samples[:3]))
            rows.append(
                [
                    name,
                    info.get("semantic_type") or info.get("dtype") or "?",
                    _fmt(info.get("missing_pct"), "%"),
                    _fmt(info.get("unique_count")),
                    "; ".join(summary_bits) or "-",
                ]
            )
        return rows

    @staticmethod
    def _quality_rows(profile: Optional[dict]) -> list[list[Any]]:
        if not profile:
            return []
        columns = profile.get("columns") or {}
        signals: list[tuple[str, str, float]] = []
        for name, info in columns.items():
            missing = float(info.get("missing_pct") or 0.0)
            if missing > 0:
                signals.append(("Missing values", f"{name}: {_fmt(missing, '%')}", missing))
            unique = int(info.get("unique_count") or 0)
            rows = int(profile.get("row_count") or 0)
            if rows and unique / rows > 0.9:
                signals.append(("High cardinality", f"{name}: {_fmt(unique)} unique", unique / rows * 100))
        if not signals:
            return []
        signals.sort(key=lambda item: item[2], reverse=True)
        rows: list[list[Any]] = [["Signal", "Detail"]]
        for label, detail, _score in signals[:8]:
            rows.append([label, detail])
        return rows

    @staticmethod
    def _correlation_rows(profile: Optional[dict], limit: int = 8) -> list[list[Any]]:
        correlations = (profile or {}).get("correlations")
        if not isinstance(correlations, dict):
            return []
        seen: set[tuple[str, str]] = set()
        pairs: list[tuple[str, str, float]] = []
        for left, row in correlations.items():
            if not isinstance(row, dict):
                continue
            for right, value in row.items():
                if left == right:
                    continue
                key = tuple(sorted((str(left), str(right))))
                if key in seen:
                    continue
                seen.add(key)
                try:
                    val = float(value)
                except (TypeError, ValueError):
                    continue
                pairs.append((str(left), str(right), val))
        pairs.sort(key=lambda item: abs(item[2]), reverse=True)
        if not pairs:
            return []
        rows: list[list[Any]] = [["Columns", "Correlation"]]
        for left, right, value in pairs[:limit]:
            rows.append([f"{left} / {right}", f"{value:.3f}"])
        return rows

    @staticmethod
    def _assistant_snippets(chat_history: Iterable[dict], limit: int = 4) -> list[str]:
        snippets: list[str] = []
        for msg in reversed(list(chat_history or [])):
            if msg.get("role") != "assistant":
                continue
            content = CODE_BLOCK_RE.sub("", _plain(msg.get("content", ""))).strip()
            if not content:
                continue
            lines = [line.strip("# -*\t ") for line in content.splitlines() if line.strip()]
            joined = " ".join(lines)
            if joined:
                snippets.append(joined[:420].rstrip() + ("..." if len(joined) > 420 else ""))
            if len(snippets) >= limit:
                break
        return list(reversed(snippets))

    @staticmethod
    def _conversation_flowables(chat_history: Iterable[dict], styles: dict[str, ParagraphStyle]) -> list[Any]:
        flowables: list[Any] = []
        messages = list(chat_history or [])[-MAX_CONVERSATION_MESSAGES:]
        for msg in messages:
            role = str(msg.get("role", "unknown")).capitalize()
            content = CODE_BLOCK_RE.sub("", _plain(msg.get("content", ""), max_chars=1800)).strip()
            if not content:
                continue
            flowables.append(Paragraph(f"<b>{_safe_text(role)}:</b>", styles["h2"]))
            for raw_line in content.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("###"):
                    flowables.append(Paragraph(_inline_markdown(line.lstrip("# ")), styles["h2"]))
                elif line.startswith("##"):
                    flowables.append(Paragraph(_inline_markdown(line.lstrip("# ")), styles["h2"]))
                elif line.startswith("- "):
                    flowables.append(Paragraph(_inline_markdown(line[2:]), styles["bullet"], bulletText="-"))
                else:
                    flowables.append(Paragraph(_inline_markdown(line), styles["body"]))
            flowables.append(Spacer(1, 0.08 * inch))
        return flowables

    @staticmethod
    def generate_pdf(
        report_path: str,
        profile: Optional[dict] = None,
        eda: Optional[dict] = None,
        chat_history: Optional[List[dict]] = None,
        charts: Optional[List[Any]] = None,
        narrative: Optional[dict] = None,
        df: Optional[Any] = None,
    ) -> str:
        """Build a multi-section PDF report including profile, insights, and charts.

        When `narrative` is provided (an LLM-authored dict from
        report_narrative.generate_report_narrative), its prose is rendered in the
        executive summary, findings, per-chart readings, and recommendations.
        When it is None, the deterministic profile/transcript sections render on
        their own — nothing is fabricated.
        """
        charts = list(charts or [])
        chat_history = list(chat_history or [])
        narrative = narrative or {}
        doc = SimpleDocTemplate(
            report_path,
            pagesize=A4,
            rightMargin=0.55 * inch,
            leftMargin=0.55 * inch,
            topMargin=0.6 * inch,
            bottomMargin=0.7 * inch,
            title="Universal Analyst Report",
            author="Universal Analyst",
        )
        styles = ReportSkill._styles()
        story: List[Any] = []

        file_name = (profile or {}).get("file_name") or "Active dataset"
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        report_title = narrative.get("title") or "Analysis Report"

        # The cover is page 1, drawn by _cover_page (onFirstPage). The body
        # begins on page 2 — start with a PageBreak so the cover stands alone.
        story.append(PageBreak())

        # Contents — built from the sections that will actually appear below.
        contents_entries: list[str] = []
        if narrative.get("executive_summary"):
            contents_entries.append("Executive Summary")
        if narrative.get("key_findings") or ReportSkill._assistant_snippets(chat_history):
            contents_entries.append("Key Findings")
        if (eda or {}).get("suggestions"):
            contents_entries.append("Recommended Next Questions")
        if ReportSkill._quality_rows(profile):
            contents_entries.append("Data Quality & Anomalies")
        if ReportSkill._correlation_rows(profile):
            contents_entries.append("Strongest Profile Correlations")
        if ReportSkill._column_rows(profile):
            contents_entries.append("Column Dictionary")
        if charts:
            contents_entries.append("Executive Dashboard Overview")
            contents_entries.append("Model-Generated Visual Analysis")
        if narrative.get("recommendations"):
            contents_entries.append("Recommendations")
        if ReportSkill._conversation_flowables(chat_history, styles):
            contents_entries.append("Session Transcript")

        story.append(Paragraph("Contents", styles["h1"]))
        for idx, entry in enumerate(contents_entries, start=1):
            story.append(
                Paragraph(
                    f"<font color='#6366F1'>{idx:02d}</font>&nbsp;&nbsp;{_safe_text(entry)}",
                    styles["body"],
                )
            )
        story.append(Spacer(1, 0.22 * inch))

        # Dataset at-a-glance (KPI strip) right under the contents.
        story.append(ReportSkill._kpi_table(profile, eda, len(charts)))
        story.append(Spacer(1, 0.22 * inch))

        # LLM-authored narrative (executive summary + key findings) leads.
        exec_summary = narrative.get("executive_summary")
        if exec_summary:
            story.append(Paragraph("Executive Summary", styles["h1"]))
            story.append(Paragraph(_inline_markdown(exec_summary, max_chars=1200), styles["body"]))
            story.append(Spacer(1, 0.12 * inch))

        key_findings = narrative.get("key_findings") or []
        if key_findings:
            story.append(Paragraph("Key Findings", styles["h1"]))
            for item in key_findings:
                story.append(Paragraph(_inline_markdown(item, max_chars=440), styles["bullet"], bulletText="-"))
            story.append(Spacer(1, 0.12 * inch))

        snippets = ReportSkill._assistant_snippets(chat_history)
        if snippets and not key_findings:
            story.append(Paragraph("Latest Generated Insights", styles["h1"]))
            for item in snippets:
                story.append(Paragraph(_inline_markdown(item, max_chars=440), styles["bullet"], bulletText="-"))
            story.append(Spacer(1, 0.12 * inch))

        suggestions = (eda or {}).get("suggestions") or []
        if suggestions:
            story.append(Paragraph("Recommended Next Questions", styles["h1"]))
            for item in suggestions[:6]:
                story.append(Paragraph(_inline_markdown(str(item)), styles["bullet"], bulletText="-"))
            story.append(Spacer(1, 0.12 * inch))

        quality_rows = ReportSkill._quality_rows(profile)
        if quality_rows:
            story.append(Paragraph("Data Quality & Anomalies", styles["h1"]))
            quality_note = narrative.get("data_quality_note")
            if quality_note:
                story.append(Paragraph(_inline_markdown(quality_note, max_chars=700), styles["body"]))
            
            anomalies = narrative.get("anomalies") or []
            if anomalies:
                story.append(Paragraph("Detected Anomalies & Outliers", styles["h2"]))
                for item in anomalies:
                    story.append(Paragraph(_inline_markdown(item, max_chars=400), styles["bullet"], bulletText="-"))
                story.append(Spacer(1, 0.1 * inch))

            story.append(ReportSkill._table(quality_rows, widths=[1.55 * inch, 4.85 * inch]))
            story.append(Spacer(1, 0.16 * inch))

        correlation_rows = ReportSkill._correlation_rows(profile)
        if correlation_rows:
            story.append(Paragraph("Strongest Profile Correlations", styles["h1"]))
            story.append(ReportSkill._table(correlation_rows, widths=[4.65 * inch, 1.75 * inch]))
            story.append(Spacer(1, 0.16 * inch))

        rows = ReportSkill._column_rows(profile)
        if rows:
            story.append(Paragraph("Column Dictionary", styles["h1"]))
            story.append(
                ReportSkill._table(
                    rows,
                    widths=[1.35 * inch, 0.95 * inch, 0.78 * inch, 0.75 * inch, 2.55 * inch],
                )
            )
            total_cols = len((profile or {}).get("columns") or {})
            if total_cols > MAX_COLUMNS_IN_REPORT:
                story.append(Paragraph(f"Showing first {MAX_COLUMNS_IN_REPORT} of {total_cols} columns.", styles["small"]))
            story.append(Spacer(1, 0.18 * inch))

        if charts:
            # Executive Dashboard Overview Page
            story.append(PageBreak())
            story.append(Paragraph("Executive Dashboard Overview", styles["h1"]))
            
            dashboard_summary = narrative.get("dashboard_summary")
            if dashboard_summary:
                story.append(Paragraph(_inline_markdown(dashboard_summary, max_chars=500), styles["body"]))
                story.append(Spacer(1, 0.1 * inch))
                
            cells = []
            for i, chart in enumerate(charts[:4]):
                title_text = ReportSkill._chart_title(chart, i)
                cell_flowables = [
                    Paragraph(f"<b>{_safe_text(title_text)}</b>", styles["small"]),
                ]
                png = ReportSkill._render_chart_image(chart, df=df)
                if png:
                    cell_flowables.append(Image(io.BytesIO(png), width=3.35 * inch, height=1.9 * inch))
                else:
                    cell_flowables.append(Paragraph("Visual rendering unavailable.", styles["small"]))
                cells.append(cell_flowables)
                
            while len(cells) < 4:
                cells.append([Paragraph("", styles["small"])])
                
            grid_data = [
                [cells[0], cells[1]],
                [cells[2], cells[3]]
            ]
            grid_table = Table(grid_data, colWidths=[3.45 * inch, 3.45 * inch])
            grid_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("LEFTPADDING", (0, 0), (-1, -1), 2),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ]
                )
            )
            story.append(grid_table)
            story.append(Spacer(1, 0.12 * inch))

            # Individual Visual Analysis
            story.append(PageBreak())
            story.append(Paragraph("Model-Generated Visual Analysis", styles["h1"]))
            story.append(
                Paragraph(
                    "These charts were generated from the session's LLM visualization path and stored as Plotly artifacts.",
                    styles["muted"],
                )
            )
            story.append(Spacer(1, 0.08 * inch))
            chart_readings = narrative.get("chart_readings") or []
            for i, chart in enumerate(charts[:MAX_CHARTS_IN_REPORT]):
                title = ReportSkill._chart_title(chart, i)
                block: list[Any] = [Paragraph(_safe_text(title), styles["h2"])]
                png = ReportSkill._render_chart_image(chart, df=df)
                if png:
                    block.append(Image(io.BytesIO(png), width=6.75 * inch, height=3.8 * inch))
                else:
                    block.append(
                        Paragraph(
                            "Chart image export was unavailable in this runtime. The chart remains stored in the session as a Plotly artifact.",
                            styles["muted"],
                        )
                    )
                # Prefer the model's reading of this chart; fall back to its stored description.
                reading = chart_readings[i] if i < len(chart_readings) else None
                if not reading and isinstance(chart, dict):
                    reading = chart.get("description")
                if reading:
                    block.append(Paragraph(_inline_markdown(reading, max_chars=400), styles["muted"]))
                story.append(KeepTogether(block))
                story.append(Spacer(1, 0.18 * inch))

        recommendations = narrative.get("recommendations") or []
        if recommendations:
            story.append(Paragraph("Recommendations", styles["h1"]))
            for item in recommendations:
                story.append(Paragraph(_inline_markdown(item, max_chars=400), styles["bullet"], bulletText="-"))
            story.append(Spacer(1, 0.14 * inch))

        conversation = ReportSkill._conversation_flowables(chat_history, styles)
        if conversation:
            story.append(PageBreak())
            story.append(Paragraph("Session Transcript", styles["h1"]))
            story.append(
                Paragraph(
                    "Recent user and analyst turns are included for traceability. Internal chart-plan details are omitted from the PDF body.",
                    styles["muted"],
                )
            )
            story.append(Spacer(1, 0.08 * inch))
            story.extend(conversation)

        # Page 1 is the cover (full-bleed, no footer); pages 2+ get the footer.
        doc.build(
            story,
            onFirstPage=lambda c, d: ReportSkill._cover_page(
                c, d, report_title, file_name, generated_at
            ),
            onLaterPages=ReportSkill._footer,
        )
        logger.info("Report generated: %s", report_path)
        return report_path
