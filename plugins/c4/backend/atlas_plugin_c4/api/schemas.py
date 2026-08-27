"""Request schemas for the diagram endpoints — split out of
`server.apps.catalog.api.schemas`.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class DiagramPath(BaseModel):
    kind: str
    id: UUID


class DiagramQuery(BaseModel):
    view: str | None = None
    format: Literal["svg", "png"] = "svg"
    download: bool = False
    layout: Literal["LAYOUT_TOP_DOWN", "LAYOUT_LEFT_RIGHT", "LAYOUT_LANDSCAPE"] = (
        "LAYOUT_TOP_DOWN"
    )
    show_title: bool = True
    show_legend: bool = True
    show_selected_label: bool = True
    show_person_sprite: bool = True
    show_stereotypes: bool = True
