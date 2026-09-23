"""Exports the four operational tables within the current user's RBAC scope."""
import csv
from datetime import date, datetime
from io import BytesIO, StringIO
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.dependencies import CurrentUser
from app.dbapi.base import get_async_session
from app.dbapi.models import Assignment, AssignmentItem, Channel, Event, Forecast, Object, User
from app.dbapi.models.access import District
from app.rbac import accessible_events, accessible_objects


router = APIRouter(prefix="/reports", tags=["reports"])
Db = Annotated[AsyncSession, Depends(get_async_session)]


def _query(
    dataset: str, user: User, date_from: datetime | None, date_to: datetime | None,
    search: str | None, district_id: str | None, object_id: int | None,
    sensor_type: str | None, risk_order: str,
):
    object_ids = accessible_objects(user.id).with_only_columns(Object.id)
    if dataset == "objects":
        query = select(
            Object.id.label("ID"), Object.dispatch_name.label("Объект"),
            Object.object_type.label("Тип"), District.name.label("Район"),
        ).outerjoin(District, District.id == Object.district_id).where(Object.id.in_(object_ids))
        if search:
            query = query.where(Object.dispatch_name.ilike(f"%{search}%"))
        if district_id:
            query = query.where(Object.district_id == district_id)
        return query.order_by(Object.id)
    if dataset == "events":
        event_ids = accessible_events(user.id).with_only_columns(Event.id)
        query = select(
            Event.event_at.label("Дата"), Object.dispatch_name.label("Объект"),
            Channel.sensor_name.label("Датчик"), Channel.sensor_type.label("Тип датчика"),
            Event.sensor_value.label("Значение"), Event.is_alarm.label("Тревога"),
        ).join(Channel, Channel.id == Event.channel_id).join(Object, Object.id == Channel.object_id).where(Event.id.in_(event_ids))
        field = Event.event_at
    elif dataset == "assignments":
        technician, dispatcher = aliased(User), aliased(User)
        query = select(
            Assignment.scheduled_date.label("Дата"), Object.dispatch_name.label("Объект"),
            Channel.sensor_name.label("Датчик"), Channel.sensor_type.label("Тип датчика"),
            technician.name.label("Техник"), dispatcher.name.label("Диспетчер"),
            AssignmentItem.status.label("Статус проверки"), AssignmentItem.completed_at.label("Выполнено"),
        ).join(Object, Object.id == Assignment.object_id).join(AssignmentItem, AssignmentItem.assignment_id == Assignment.id).join(Channel, Channel.id == AssignmentItem.channel_id).join(technician, technician.id == Assignment.technician_id).join(dispatcher, dispatcher.id == Assignment.dispatcher_id).where(Assignment.object_id.in_(object_ids))
        if user.has_permission("assignment.complete") and not user.has_permission("assignment.create") and not user.is_admin():
            query = query.where(Assignment.technician_id == user.id)
        field = Assignment.scheduled_date
    elif dataset == "forecasts":
        query = select(
            Forecast.forecast_at.label("Дата прогноза"), Object.dispatch_name.label("Объект"),
            Channel.sensor_name.label("Датчик"), Channel.sensor_type.label("Тип датчика"),
            Forecast.risk_score.label("Риск"), Forecast.warning.label("Предупреждение"),
            Forecast.status.label("Статус"),
        ).join(Object, Object.id == Forecast.object_id).join(Channel, Channel.id == Forecast.channel_id).where(Forecast.object_id.in_(object_ids))
        field = Forecast.forecast_at
    else:
        raise HTTPException(404, "Неизвестный вид отчёта")
    if date_from is not None:
        query = query.where(field >= date_from)
    if date_to is not None:
        query = query.where(field <= date_to)
    if object_id is not None and dataset == "events":
        query = query.where(Channel.object_id == object_id)
    if sensor_type and dataset == "events":
        query = query.where(Channel.sensor_type == sensor_type)
    if dataset == "forecasts":
        risk_sort = Forecast.risk_score.asc().nullslast() if risk_order == "asc" else Forecast.risk_score.desc().nullslast()
        return query.order_by(risk_sort, field.desc())
    return query.order_by(field.desc())


def _value(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Да" if value else "Нет"
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    return value


def _pdf_font():
    paths = (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    )
    for path in paths:
        if path.exists():
            pdfmetrics.registerFont(TTFont("ReportFont", str(path)))
            return "ReportFont"
    return "Helvetica"


@router.get("/{dataset}/{file_format}")
async def export_report(
    dataset: str,
    file_format: str,
    db: Db,
    user: CurrentUser,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = Query(None, max_length=1000),
    district_id: str | None = None,
    object_id: int | None = None,
    sensor_type: str | None = Query(None, max_length=255),
    risk_order: str = Query("desc", pattern="^(asc|desc)$"),
):
    if file_format not in {"csv", "xlsx", "pdf"}:
        raise HTTPException(404, "Поддерживаются форматы CSV, XLSX и PDF")
    query = _query(
        dataset, user, date_from, date_to, search, district_id,
        object_id, sensor_type, risk_order,
    )
    filename = f"{dataset}-{datetime.now().date().isoformat()}.{file_format}"
    disposition = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if file_format == "csv":
        result = await db.stream(query.execution_options(yield_per=1000))
        headers = list(result.keys())

        def csv_line(values):
            output = StringIO()
            csv.writer(output, delimiter=";").writerow(values)
            return output.getvalue().encode("utf-8")

        async def content():
            yield b"\xef\xbb\xbf" + csv_line(headers)
            async for row in result:
                yield csv_line([_value(value) for value in row])

        return StreamingResponse(content(), media_type="text/csv; charset=utf-8", headers=disposition)

    total = await db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    if file_format == "pdf" and total > 100:
        raise HTTPException(422, "PDF доступен только для отчётов до 100 строк")
    if file_format == "xlsx" and total > 1_000_000:
        raise HTTPException(422, "XLSX доступен только для отчётов до 1 000 000 строк")
    result = await db.execute(query)
    headers = list(result.keys())
    rows = [[_value(value) for value in row] for row in result]
    if file_format == "xlsx":
        output = BytesIO()
        workbook = Workbook(write_only=True)
        sheet = workbook.create_sheet("Отчёт")
        sheet.append(headers)
        for row in rows:
            sheet.append(row)
        workbook.save(output)
        output.seek(0)
        return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=disposition)

    output = BytesIO()
    font = _pdf_font()
    document = SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
    table = Table([headers, *[[str(value) for value in row] for row in rows]], repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    document.build([table])
    output.seek(0)
    return StreamingResponse(output, media_type="application/pdf", headers=disposition)
