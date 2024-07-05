
# SpeciesInfoAPI

SpeciesInfoAPI é uma ferramenta em Python que permite buscar informações detalhadas sobre várias espécies utilizando a API do GBIF (Global Biodiversity Information Facility). Este projeto facilita a obtenção de dados como nome científico, família, ordem e reino das espécies a partir de seus nomes científicos.
## Funcionalidades

- Busca de informações de espécies pelo nome científico.
- Geração de um DataFrame Pandas com os dados coletados.
- Suporte para pesquisa de múltiplas espécies simultaneamente.


## Requisitos

- Python 3.7 ou superior.
- Pandas.
- Requests
## Instalação

```bash
  git clone https://github.com/SeuUsuario/SpeciesInfoAPI.git
  cd SpeciesInfoAPI
  pip install -r requirements.txt

```
    
## Uso

```python
import pandas as pd
from species_info import create_species_dataframe

# Lista de nomes científicos das espécies a serem pesquisadas
scientific_names = ["Macroditassa", "Helianthus annuus", "Panthera leo"]

# Cria um DataFrame com as informações das espécies
species_df = create_species_dataframe(scientific_names)

# Exibe o DataFrame resultante
print(species_df)

```


## Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests com melhorias.

Faça um fork do projeto
Crie uma branch para sua feature (git checkout -b minha-feature)
Commite suas alterações (git commit -am 'Adiciona minha feature')
Faça um push para a branch (git push origin minha-feature)
Abra um Pull Request

<ol>
  <li>Faça um fork do projeto</li>
  <li>Crie uma branch para sua feature (git checkout -b minha-feature)</li>
  <li>Commite suas alterações (git commit -am 'Adiciona minha feature')</li>
  <li>Faça um push para a branch (git push origin minha-feature)</li>
  <li>Abra um Pull Request</li>
</ol>

## Licença

Licença
Este projeto está licenciado sob a [Licença](https://choosealicense.com/licenses/mit/) MIT - veja o arquivo LICENSE para mais detalhes.


## Suporte

Se você tiver alguma dúvida ou sugestão, sinta-se à vontade para abrir uma issue no repositório ou entrar em contato através de jeancc.costa@gmail.com.

