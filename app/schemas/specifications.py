from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SpecSource(str, Enum):
    USER_DEFINED = "user_defined"
    AGENT_ESTIMATE = "agent_estimate"
    TYPICAL_ASSUMPTION = "typical_assumption"


class WorkItem(BaseModel):
    order: int = Field(description="Порядковый номер работы")
    name: str = Field(description="Название работы")
    description: str | None = Field(default=None, description="Уточнение")


class VolumeItem(BaseModel):
    name: str = Field(description="Работа или материал")
    unit: str = Field(description="Единица измерения")
    value: float | None = Field(default=None, description="Значение, если известно")
    basis: SpecSource = Field(description="Основание значения")
    basis_note: str | None = Field(default=None, description="Пояснение основания")


class NormativeReference(BaseModel):
    code: str = Field(description="Обозначение (ГОСТ, СП, СНиП)")
    title: str = Field(description="Название документа")
    source: str = Field(description="Источник, откуда взята ссылка")
    verified: bool = Field(default=False, description="Проверена ли ссылка")


class AcceptanceCriterion(BaseModel):
    text: str = Field(description="Формулировка критерия")
    measurable: bool = Field(default=True, description="Измерим ли критерий")


class GeneralInfo(BaseModel):
    customer: str | None = None
    object_name: str | None = None
    address: str | None = None
    goal: str | None = None


class ObjectDescription(BaseModel):
    defect: str | None = None
    cause: str | None = None
    photos_attached: bool = False


class MaterialsRequirements(BaseModel):
    entries: list[str] = Field(default_factory=list)
    notes: str | None = None


class QualityRequirements(BaseModel):
    entries: list[str] = Field(default_factory=list)
    notes: str | None = None


class Deadlines(BaseModel):
    start: str | None = None
    end: str | None = None
    milestones: list[str] = Field(default_factory=list)


class Conditions(BaseModel):
    access: str | None = None
    work_hours: str | None = None
    safety: str | None = None
    cleaning: str | None = None


class ContractorRequirements(BaseModel):
    experience: str | None = None
    permits: str | None = None
    sro_membership: bool | None = None


class Acceptance(BaseModel):
    procedure: str | None = None
    criteria: list[AcceptanceCriterion] = Field(default_factory=list)


class Warranty(BaseModel):
    period: str | None = None
    conditions: str | None = None


class Assumption(BaseModel):
    text: str
    source: SpecSource
    requires_check: bool = True


class TechnicalSpecification(BaseModel):
    """13 разделов из Приложения А ТЗ."""

    general_info: GeneralInfo
    object_description: ObjectDescription
    work_items: list[WorkItem] = Field(default_factory=list)
    volumes: list[VolumeItem] = Field(default_factory=list)
    materials: MaterialsRequirements
    quality: QualityRequirements
    normative_references: list[NormativeReference] = Field(default_factory=list)
    deadlines: Deadlines
    conditions: Conditions
    contractor_requirements: ContractorRequirements
    acceptance: Acceptance
    warranty: Warranty
    assumptions: list[Assumption] = Field(default_factory=list)


class SpecificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    purchase_id: UUID
    version: int
    content: TechnicalSpecification
    is_current: bool
    created_at: datetime
    assumptions: list["SpecAssumptionRead"] = Field(default_factory=list)


class SpecAssumptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    text: str
    source: str
    requires_check: bool


class SpecificationListItem(BaseModel):
    """Метаданные версии без content — чтобы список не раздувался"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version: int
    is_current: bool
    created_at: datetime
