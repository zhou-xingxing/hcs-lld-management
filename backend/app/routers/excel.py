from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ip_allocation import IPAllocation
from app.schemas.excel import ImportConfirmRequest, ImportResultResponse
from app.services import excel as excel_service
from app.utils.excel_utils import build_export, generate_template

router = APIRouter(prefix="/api/excel", tags=["Excel"])


def get_operator(x_operator: str = Header("system")) -> str:
    return x_operator


@router.get("/template")
def download_template():
    """下载 Excel 导入模板。"""
    buf = generate_template()
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=hcs_lld_import_template.xlsx"},
    )


@router.post("/import/preview")
async def preview_import(
    file: UploadFile,
    db: Session = Depends(get_db),
):
    """上传 Excel 文件并预览导入结果。"""
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx / .xls 文件")

    contents = await file.read()
    result = excel_service.preview_import(contents, db)
    return result


@router.post("/import/confirm", response_model=ImportResultResponse)
def confirm_import(
    data: ImportConfirmRequest,
    db: Session = Depends(get_db),
):
    """确认执行导入预览数据。"""
    result = excel_service.confirm_import(data.preview_id, data.operator, db)
    return result


@router.get("/export")
def export_excel(
    region_id: Optional[str] = Query(None),
    plane_type_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """导出 IP 分配数据到 Excel。"""
    query = db.query(IPAllocation)
    if region_id:
        query = query.filter(IPAllocation.region_id == region_id)
    if plane_type_id:
        query = query.filter(IPAllocation.plane_type_id == plane_type_id)

    allocations = query.order_by(IPAllocation.created_at.desc()).all()

    data = []
    for a in allocations:
        data.append(
            {
                "region_name": a.region.name if a.region else "",
                "plane_type_name": a.plane_type.name if a.plane_type else "",
                "ip_range": a.ip_range,
                "vlan_id": a.vlan_id,
                "gateway": a.gateway or "",
                "subnet_mask": a.subnet_mask or "",
                "purpose": a.purpose or "",
                "status": a.status,
            }
        )

    buf = build_export(data)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=hcs_lld_export.xlsx"},
    )
