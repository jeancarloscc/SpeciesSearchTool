"""Modelos de resposta normalizados por fonte de dados."""

from pydantic import BaseModel, Field

from .regions import Region


class FloraRecord(BaseModel):
    """Resposta normalizada da Flora e Funga do Brasil (JBRJ)."""

    scientific_name: str
    accepted_name: str | None = None
    taxonomic_status: str | None = None
    family: str | None = None
    genus: str | None = None
    origin: str | None = None
    endemism: str | None = None
    life_form: list[str] = Field(default_factory=list)
    phytogeographic_domains: list[str] = Field(default_factory=list)
    vegetation_types: list[str] = Field(default_factory=list)
    occurrence_states: list[str] = Field(default_factory=list)
    occurrence_regions: list[Region] = Field(default_factory=list)


class IUCNAssessment(BaseModel):
    """Resposta normalizada da IUCN Red List."""

    scientific_name: str
    category: str | None = None
    category_label: str | None = None
    assessment_year: int | None = None
    assessment_id: int | None = None
    population_trend: str | None = None
    url: str | None = None


class GBIFOccurrenceSummary(BaseModel):
    """Resumo agregado de ocorrências do GBIF para o Brasil."""

    scientific_name: str
    taxon_key: int | None = None
    match_status: str | None = None
    total_br: int = 0
    counts_by_state: dict[str, int] = Field(default_factory=dict)
    counts_by_region: dict[str, int] = Field(default_factory=dict)
