"""Cliente da API da Flora e Funga do Brasil (JBRJ)."""

from __future__ import annotations

import re
from typing import Any

import httpx

from ..models import FloraRecord
from ..regions import regions_from_states

_STATE_RE = re.compile(r"(?:BR-)?([A-Z]{2})$")


class FloraClient:
    """Cliente para https://servicos.jbrj.gov.br/v2/flora/taxon/<nome>.

    A API do JBRJ é pública e não exige autenticação. A resposta é uma lista de
    táxons — normalmente um ``NOME_ACEITO`` mais eventuais sinônimos.
    """

    BASE_URL = "https://servicos.jbrj.gov.br/v2/flora"

    def __init__(
        self,
        base_url: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = (base_url or self.BASE_URL).rstrip("/")
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._owns_client = client is None

    def __enter__(self) -> FloraClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def get_taxon(self, scientific_name: str) -> FloraRecord | None:
        """Retorna o táxon aceito para o nome científico, ou None se não houver."""
        url = f"{self._base_url}/taxon/{scientific_name}"
        response = self._client.get(url)
        response.raise_for_status()
        payload = response.json()

        if not isinstance(payload, list) or not payload:
            return None

        accepted = next(
            (
                item
                for item in payload
                if (item.get("taxon") or {}).get("taxonomicstatus") == "NOME_ACEITO"
            ),
            payload[0],
        )
        return self._parse(scientific_name, accepted)

    @staticmethod
    def _parse(queried_name: str, item: dict[str, Any]) -> FloraRecord:
        taxon = item.get("taxon") or {}
        profile = item.get("specie_profile") or {}
        distribution = item.get("distribuition") or []

        states: list[str] = []
        domains: set[str] = set()
        origin: str | None = None
        endemism: str | None = None

        for entry in distribution:
            code = _normalize_state(entry.get("locationid") or "")
            if code and code not in states:
                states.append(code)

            origin = origin or entry.get("establishmentmeans")
            remarks = entry.get("occurrenceremarks") or {}
            endemism = endemism or remarks.get("endemism")
            for d in remarks.get("phytogeographicDomain") or []:
                if d:
                    domains.add(str(d))

        return FloraRecord(
            scientific_name=taxon.get("scientificname") or queried_name,
            accepted_name=taxon.get("acceptednameusage") or taxon.get("scientificname"),
            taxonomic_status=taxon.get("taxonomicstatus"),
            family=taxon.get("family"),
            genus=taxon.get("genus"),
            origin=origin,
            endemism=endemism,
            life_form=_as_list(profile.get("lifeForm")),
            phytogeographic_domains=sorted(domains),
            vegetation_types=_as_list(profile.get("vegetationType")),
            occurrence_states=states,
            occurrence_regions=sorted(regions_from_states(states)),
        )


def _normalize_state(raw: str) -> str | None:
    if not isinstance(raw, str):
        return None
    match = _STATE_RE.search(raw.strip().upper())
    return match.group(1) if match else None


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return [str(value)]
