"""Cliente da GBIF Occurrence API."""

from __future__ import annotations

from typing import Any

import httpx

from ..models import GBIFOccurrenceSummary
from ..regions import REGION_TO_STATES, STATE_NAMES, state_to_region

_STATE_BY_NAME = {name.lower(): code for code, name in STATE_NAMES.items()}


class GBIFClient:
    """Cliente para https://api.gbif.org/v1/.

    Não requer autenticação para leitura.
    """

    BASE_URL = "https://api.gbif.org/v1"

    def __init__(
        self,
        base_url: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = (base_url or self.BASE_URL).rstrip("/")
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def __enter__(self) -> GBIFClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def match_species(
        self, scientific_name: str, kingdom: str = "Plantae"
    ) -> dict[str, Any]:
        """Resolve o nome científico para um taxonKey canônico do GBIF."""
        response = self._client.get(
            f"{self._base_url}/species/match",
            params={"name": scientific_name, "kingdom": kingdom, "strict": "false"},
        )
        response.raise_for_status()
        return response.json()

    def occurrence_summary(
        self, scientific_name: str, kingdom: str = "Plantae"
    ) -> GBIFOccurrenceSummary:
        """Agrega ocorrências do táxon no Brasil por estado e macrorregião."""
        match = self.match_species(scientific_name, kingdom=kingdom)
        taxon_key = match.get("usageKey")
        match_status = match.get("matchType")

        if taxon_key is None:
            return GBIFOccurrenceSummary(
                scientific_name=scientific_name,
                taxon_key=None,
                match_status=match_status,
            )

        response = self._client.get(
            f"{self._base_url}/occurrence/search",
            params={
                "taxonKey": taxon_key,
                "country": "BR",
                "limit": 0,
                "facet": "stateProvince",
                "facetLimit": 50,
            },
        )
        response.raise_for_status()
        payload = response.json()

        counts_by_state: dict[str, int] = {}
        for facet in payload.get("facets") or []:
            if facet.get("field") != "STATE_PROVINCE":
                continue
            for bucket in facet.get("counts") or []:
                code = _STATE_BY_NAME.get((bucket.get("name") or "").strip().lower())
                if not code:
                    continue
                counts_by_state[code] = counts_by_state.get(code, 0) + int(
                    bucket.get("count", 0)
                )

        counts_by_region: dict[str, int] = {r: 0 for r in REGION_TO_STATES}
        for state, count in counts_by_state.items():
            region = state_to_region(state)
            if region:
                counts_by_region[region] += count

        return GBIFOccurrenceSummary(
            scientific_name=scientific_name,
            taxon_key=taxon_key,
            match_status=match_status,
            total_br=int(payload.get("count", 0)),
            counts_by_state=counts_by_state,
            counts_by_region=counts_by_region,
        )
