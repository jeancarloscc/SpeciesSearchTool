"""Cliente da IUCN Red List API (v4)."""

from __future__ import annotations

import os
from typing import Any

import httpx

from ..models import IUCNAssessment

_CATEGORY_LABELS = {
    "LC": "Least Concern",
    "NT": "Near Threatened",
    "VU": "Vulnerable",
    "EN": "Endangered",
    "CR": "Critically Endangered",
    "EW": "Extinct in the Wild",
    "EX": "Extinct",
    "DD": "Data Deficient",
    "NE": "Not Evaluated",
}


class IUCNClient:
    """Cliente para https://api.iucnredlist.org/api/v4/.

    Requer token de acesso (https://api.iucnredlist.org/). Pode ser passado via
    argumento ``api_key`` ou pela variável de ambiente ``IUCN_API_KEY``.
    """

    BASE_URL = "https://api.iucnredlist.org/api/v4"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
    ) -> None:
        key = api_key or os.getenv("IUCN_API_KEY")
        if not key:
            raise ValueError(
                "IUCN API key ausente. Defina IUCN_API_KEY ou passe api_key=..."
            )
        self._api_key = key
        self._base_url = (base_url or self.BASE_URL).rstrip("/")
        self._client = client or httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
        )
        self._owns_client = client is None

    def __enter__(self) -> IUCNClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def get_assessment(self, scientific_name: str) -> IUCNAssessment | None:
        """Busca a avaliação mais recente para o nome científico informado."""
        genus, species = _split_binomial(scientific_name)
        if not species:
            return None

        url = f"{self._base_url}/taxa/scientific_name"
        response = self._client.get(
            url, params={"genus_name": genus, "species_name": species}
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()

        return self._parse(scientific_name, payload)

    @staticmethod
    def _parse(queried_name: str, data: dict[str, Any]) -> IUCNAssessment | None:
        assessments = data.get("assessments") or []
        if not assessments:
            return None

        latest = max(
            assessments,
            key=lambda a: (a.get("latest", False), a.get("year_published") or 0),
        )

        code = latest.get("red_list_category_code") or latest.get("category")
        year = latest.get("year_published") or latest.get("assessment_year")

        return IUCNAssessment(
            scientific_name=data.get("scientific_name") or queried_name,
            category=code,
            category_label=_CATEGORY_LABELS.get(code) if code else None,
            assessment_year=int(year) if year else None,
            assessment_id=latest.get("assessment_id"),
            population_trend=latest.get("population_trend"),
            url=latest.get("url"),
        )


def _split_binomial(scientific_name: str) -> tuple[str, str]:
    parts = scientific_name.strip().split()
    if len(parts) < 2:
        return (parts[0] if parts else "", "")
    return parts[0], parts[1]
