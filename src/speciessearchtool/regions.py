"""Mapeamento das macrorregiões do Brasil para estados (UF)."""

from typing import Literal

Region = Literal["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]

REGION_TO_STATES: dict[Region, tuple[str, ...]] = {
    "Norte": ("AC", "AM", "AP", "PA", "RO", "RR", "TO"),
    "Nordeste": ("AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"),
    "Centro-Oeste": ("DF", "GO", "MS", "MT"),
    "Sudeste": ("ES", "MG", "RJ", "SP"),
    "Sul": ("PR", "RS", "SC"),
}

STATE_TO_REGION: dict[str, Region] = {
    state: region for region, states in REGION_TO_STATES.items() for state in states
}

STATE_NAMES: dict[str, str] = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
    "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina",
    "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}


def state_to_region(state_code: str) -> Region | None:
    return STATE_TO_REGION.get(state_code.upper())


def regions_from_states(state_codes: list[str]) -> set[Region]:
    return {r for s in state_codes if (r := state_to_region(s)) is not None}
