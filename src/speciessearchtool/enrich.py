"""Orquestrador que consulta Flora, IUCN e GBIF para preencher um dataframe."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
import pandas as pd

from .apis import FloraClient, GBIFClient, IUCNClient
from .models import FloraRecord, IUCNAssessment

# Colunas do dataframe de entrada
COL_SPECIES = "ESPÉCIE"
COL_KINGDOM = "REINO"
COL_PHYLUM = "FILO"
COL_CLASS = "CLASSE"
COL_ORDER = "ORDEM"
COL_FAMILY = "FAMÍLIA"
COL_GENUS = "GÊNERO"
COL_THREAT = "GRAU DE AMEAÇA"
COL_ENDEMISM = "ENDEMISMO"
COL_BIOMES = "BIOMAS"
COL_AMAZON_ENDEMIC = "ENDEMICA_AMAZONIA"

AMAZON_BIOME = "Amazônia"

TAXONOMY_COLS = (COL_KINGDOM, COL_PHYLUM, COL_CLASS, COL_ORDER, COL_FAMILY, COL_GENUS)


@dataclass
class SpeciesEnrichment:
    """Consolidado das 3 fontes para uma espécie."""

    queried_name: str
    rank: str = "SPECIES"  # SPECIES ou GENUS (quando entrada só tem 1 palavra)
    gbif_match: dict[str, Any] | None = None
    flora: FloraRecord | None = None
    iucn: IUCNAssessment | None = None
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def kingdom(self) -> str | None:
        if self.gbif_match:
            return self.gbif_match.get("kingdom")
        return None

    def taxonomy(self) -> dict[str, str | None]:
        m = self.gbif_match or {}
        return {
            COL_KINGDOM: m.get("kingdom"),
            COL_PHYLUM: m.get("phylum"),
            COL_CLASS: m.get("class"),
            COL_ORDER: m.get("order"),
            COL_FAMILY: m.get("family"),
            COL_GENUS: m.get("genus"),
        }

    def threat_code(self) -> str | None:
        return self.iucn.category if self.iucn else None

    def endemism_flag(self) -> str | None:
        """Retorna 'S'/'N' conforme Flora. Só aplicável a plantas."""
        if not self.flora or not self.flora.endemism:
            return None
        value = self.flora.endemism.strip().lower()
        if "não" in value or "nao" in value:
            return "N"
        if "endêmica" in value or "endemica" in value:
            return "S"
        return None

    def biomes(self) -> list[str]:
        """Lista de biomas onde a espécie ocorre (só plantas, via Flora)."""
        if self.flora:
            return list(self.flora.phytogeographic_domains)
        return []

    def amazon_endemic_flag(self) -> str | None:
        """Retorna 'S' se a espécie ocorre APENAS na Amazônia; 'N' se ocorre em
        outros biomas; None se não há dados (não-plantas ou não encontrada na Flora).
        """
        biomes = self.biomes()
        if not biomes:
            return None
        biomes_set = set(biomes)
        if biomes_set == {AMAZON_BIOME}:
            return "S"
        return "N"


def _is_binomial(name: str) -> bool:
    return len(name.strip().split()) >= 2


def enrich_species(
    name: str,
    gbif: GBIFClient,
    flora: FloraClient | None = None,
    iucn: IUCNClient | None = None,
) -> SpeciesEnrichment:
    """Consulta as 3 APIs para um nome científico (ou gênero)."""
    result = SpeciesEnrichment(
        queried_name=name, rank="SPECIES" if _is_binomial(name) else "GENUS"
    )

    # 1. GBIF match (fornece taxonomia + reino para decidir Flora)
    try:
        match = gbif.match_species(name, kingdom="")
        # match retorna matchType='NONE' se não achou
        if match.get("matchType") == "NONE":
            result.errors["gbif"] = "no match"
        else:
            result.gbif_match = match
    except (httpx.HTTPError, ValueError) as exc:
        result.errors["gbif"] = f"{type(exc).__name__}: {exc}"

    kingdom = result.kingdom

    # 2. Flora — só para Plantae e se tivermos nome binomial
    if flora is not None and kingdom == "Plantae" and result.rank == "SPECIES":
        try:
            result.flora = flora.get_taxon(name)
            if result.flora is None:
                result.errors["flora"] = "not found"
        except httpx.HTTPError as exc:
            result.errors["flora"] = f"{type(exc).__name__}: {exc}"
    elif flora is not None and kingdom not in (None, "Plantae"):
        result.errors["flora"] = f"skipped: kingdom={kingdom}"
    elif flora is not None and result.rank != "SPECIES":
        result.errors["flora"] = "skipped: genus-level query"

    # 3. IUCN — qualquer reino, mas precisa de binomial
    if iucn is not None and result.rank == "SPECIES":
        try:
            result.iucn = iucn.get_assessment(name)
            if result.iucn is None:
                result.errors["iucn"] = "not found"
        except httpx.HTTPError as exc:
            result.errors["iucn"] = f"{type(exc).__name__}: {exc}"
    elif iucn is None:
        result.errors["iucn"] = "skipped: no API key"
    elif result.rank != "SPECIES":
        result.errors["iucn"] = "skipped: genus-level query"

    return result


def enrich_dataframe(
    df: pd.DataFrame,
    iucn_api_key: str | None = None,
    on_progress: callable | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Enriquece o dataframe in-place (retorna uma cópia) e devolve o relatório.

    - Só preenche células atualmente vazias (NaN). Não sobrescreve.
    - Deduplica por ESPÉCIE: consulta cada nome único 1x só.
    - Retorna (df_enriquecido, df_missing).
    """
    enriched = df.copy()
    for col in (COL_BIOMES, COL_AMAZON_ENDEMIC):
        if col not in enriched.columns:
            enriched[col] = pd.NA

    species_series = enriched[COL_SPECIES].dropna().astype(str).str.strip()
    unique_names = sorted(set(species_series) - {""})

    cache: dict[str, SpeciesEnrichment] = {}

    with GBIFClient() as gbif, FloraClient() as flora:
        iucn: IUCNClient | None = None
        try:
            iucn = IUCNClient(api_key=iucn_api_key) if iucn_api_key is not None else IUCNClient()
        except ValueError:
            iucn = None

        try:
            for i, name in enumerate(unique_names):
                cache[name] = enrich_species(name, gbif=gbif, flora=flora, iucn=iucn)
                if on_progress:
                    on_progress(i + 1, len(unique_names), name)
        finally:
            if iucn is not None:
                iucn.close()

    # Propaga resultados para todas as linhas
    missing_rows: list[dict[str, Any]] = []

    for idx, row in enriched.iterrows():
        raw_name = row.get(COL_SPECIES)
        if not isinstance(raw_name, str) or not raw_name.strip():
            continue
        name = raw_name.strip()
        result = cache.get(name)
        if result is None:
            continue

        # Taxonomia — só preenche o que está vazio
        taxonomy = result.taxonomy()
        for col, value in taxonomy.items():
            if value and _is_empty(enriched.at[idx, col]):
                enriched.at[idx, col] = value

        # Grau de ameaça
        threat = result.threat_code()
        if threat and _is_empty(enriched.at[idx, COL_THREAT]):
            enriched.at[idx, COL_THREAT] = threat

        # Endemismo (só para plantas)
        endemism = result.endemism_flag()
        if endemism and _is_empty(enriched.at[idx, COL_ENDEMISM]):
            enriched.at[idx, COL_ENDEMISM] = endemism

        # Biomas + endemismo Amazônia (só plantas via Flora)
        biomes = result.biomes()
        if biomes:
            enriched.at[idx, COL_BIOMES] = "; ".join(biomes)
        amazon = result.amazon_endemic_flag()
        if amazon:
            enriched.at[idx, COL_AMAZON_ENDEMIC] = amazon

        # Coleta faltantes para o relatório
        for api, msg in result.errors.items():
            if msg.startswith("skipped:"):
                continue  # ignora skips esperados no relatório
            missing_rows.append(
                {
                    "ESPÉCIE": name,
                    "PONTO": row.get("PONTO"),
                    "FAMÍLIA": row.get(COL_FAMILY) or result.taxonomy()[COL_FAMILY],
                    "REINO": row.get(COL_KINGDOM) or result.kingdom,
                    "API": api,
                    "MOTIVO": msg,
                }
            )

    missing = pd.DataFrame(missing_rows).drop_duplicates(
        subset=["ESPÉCIE", "API"], keep="first"
    ) if missing_rows else pd.DataFrame(
        columns=["ESPÉCIE", "PONTO", "FAMÍLIA", "REINO", "API", "MOTIVO"]
    )

    # Convenção IUCN: espécies sem avaliação recebem o código 'NE' (Not Evaluated).
    # Aplica-se também a consultas a nível de gênero, onde a IUCN não avalia.
    enriched[COL_THREAT] = enriched[COL_THREAT].fillna("NE")

    return enriched, missing


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False
