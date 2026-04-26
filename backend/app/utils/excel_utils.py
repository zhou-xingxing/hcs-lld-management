from __future__ import annotations

import io
from typing import Any, Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

TEMPLATE_HEADERS = [
    "区域名称",
    "网络平面类型",
    "IP地址段(CIDR)",
    "VLAN ID",
    "网关",
    "子网掩码",
    "用途",
    "状态",
]

COLUMN_WIDTHS = [20, 16, 20, 12, 18, 18, 30, 12]


def generate_template() -> io.BytesIO:
    """生成 Excel 导入模板。

    Returns:
        BytesIO 对象，包含格式化后的 .xlsx 模板文件。
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "导入模板"

    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    for col_idx, header in enumerate(TEMPLATE_HEADERS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
        ws.column_dimensions[get_column_letter(col_idx)].width = COLUMN_WIDTHS[col_idx - 1]

    ws.freeze_panes = "A2"

    status_dv = DataValidation(
        type="list",
        formula1='"active,reserved,deprecated"',
        allow_blank=True,
    )
    status_dv.error = "请选择 active、reserved 或 deprecated"
    status_dv.errorTitle = "无效状态"
    ws.add_data_validation(status_dv)
    status_dv.add("H2:H1001")

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def parse_excel(file_bytes: bytes) -> list[dict[str, Any]]:
    """Parse an Excel file into a list of row dicts.

    Args:
        file_bytes: Excel 文件的二进制内容。

    Returns:
        解析后的行数据列表，每行包含 region_name、plane_type_name、
        ip_range、vlan_id、gateway、subnet_mask、purpose、status 等字段。
    """
    wb = load_workbook(io.BytesIO(file_bytes), read_only=True)
    ws = wb.active
    rows = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
        if all(v is None or (isinstance(v, str) and v.strip() == "") for v in row):
            continue
        rows.append(
            {
                "row_number": row_idx,
                "region_name": str(row[0] or "").strip(),
                "plane_type_name": str(row[1] or "").strip(),
                "ip_range": str(row[2] or "").strip(),
                "vlan_id": _parse_int(row[3]),
                "gateway": str(row[4] or "").strip() or None,
                "subnet_mask": str(row[5] or "").strip() or None,
                "purpose": str(row[6] or "").strip() or "",
                "status": str(row[7] or "active").strip().lower() or "active",
            }
        )
    wb.close()
    return rows


def _parse_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def build_export(data: list[dict[str, Any]]) -> io.BytesIO:
    """Build an Excel export workbook from allocation data.

    Args:
        data: 导出数据列表，每行应包含 region_name、plane_type_name、
              ip_range、vlan_id、gateway、subnet_mask、purpose、status。

    Returns:
        BytesIO 对象，包含格式化后的 .xlsx 导出文件。
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "IP分配导出"

    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    headers = ["区域", "网络平面类型", "IP地址段(CIDR)", "VLAN ID", "网关", "子网掩码", "用途", "状态"]
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
        ws.column_dimensions[get_column_letter(col_idx)].width = COLUMN_WIDTHS[col_idx - 1]

    for row_idx, item in enumerate(data, 2):
        values = [
            item.get("region_name", ""),
            item.get("plane_type_name", ""),
            item.get("ip_range", ""),
            item.get("vlan_id"),
            item.get("gateway", ""),
            item.get("subnet_mask", ""),
            item.get("purpose", ""),
            item.get("status", ""),
        ]
        for col_idx, val in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.border = thin_border

    ws.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
