# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**SpeciesSearchTool** — ferramenta Python para preencher um dataframe de espécies de plantas com dados de **Flora e Funga do Brasil (JBRJ)**, **IUCN Red List** e **GBIF**, agregando ocorrências pelas macrorregiões do Brasil (Norte, Nordeste, Centro-Oeste, Sudeste, Sul). A busca é feita por nome científico.

## Commands

```bash
poetry install                          # instala o pacote + deps
poetry run pytest                       # roda testes
poetry run pytest tests/test_x.py       # arquivo específico
poetry run pytest -k "nome_do_teste"    # teste específico
poetry add <pacote>                     # nova dep de produção
poetry add --group dev <pacote>         # nova dep de dev
```

Variáveis de ambiente:
- `IUCN_API_KEY` — obrigatória para o `IUCNClient` (token de https://api.iucnredlist.org/).

## Architecture

Src layout: pacote em `src/speciessearchtool/`.

```
src/speciessearchtool/
├── regions.py          # mapeamento macrorregião <-> UF (Region = Literal[...])
├── models.py           # Pydantic: FloraRecord, IUCNAssessment, GBIFOccurrenceSummary
└── apis/
    ├── flora.py        # FloraClient  -> https://servicos.jbrj.gov.br/v2/flora
    ├── iucn.py         # IUCNClient   -> https://api.iucnredlist.org/api/v4 (Bearer token)
    └── gbif.py         # GBIFClient   -> https://api.gbif.org/v1
```

**Padrões:**

- Cada cliente encapsula um `httpx.Client` e expõe context manager (`with ... as c:`). Aceita `client=` injetável — útil para testes com `httpx.MockTransport` / `pytest-httpx`.
- Toda resposta externa é normalizada para um modelo Pydantic antes de sair do cliente. O consumidor (dataframe) nunca vê JSON bruto.
- Estados da Flora vêm como `BR-XX`; o parser extrai a UF via `_STATE_RE` e deriva a macrorregião via `regions.regions_from_states`.
- GBIF usa um **único** `occurrence/search` com `facet=stateProvince` (não 27 queries por espécie); nomes de estado em PT vêm de `STATE_NAMES` e são mapeados de volta para siglas.
- IUCN v4: endpoint `/taxa/scientific_name` com `genus_name` + `species_name` separados. O parser escolhe a avaliação mais recente (flag `latest` + `year_published`).

**Quando adicionar uma nova fonte:** criar cliente em `apis/`, adicionar modelo em `models.py`, exportar em `apis/__init__.py` e `__init__.py`.
