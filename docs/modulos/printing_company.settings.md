Ficam aqui os **parâmetros do cenário** do artigo, que descrevem a
operação da gráfica e que faz sentido trocar sem mexer no código: as horas
de um turno (`Settings.shift_hours`) e a tarifa de energia
(`Settings.energy_price`), ambas positivas. Os detalhes numéricos não
ficam aqui: a tolerância e o limite de iterações do simplex são do pacote
`simplex` (`simplex.defaults`), que não depende de `printing_company`, e a
escala das restrições de demanda (`printing_company.problem.model.SCALE`)
é parte da formulação do modelo.

O objeto `settings` é carregado na importação e usado em todo o pacote.
Cada campo pode ser trocado, nesta ordem de prioridade, por

1. uma variável de ambiente com o nome do campo (em maiúsculas ou
   minúsculas): `SHIFT_HOURS=8 uv run printing-company`;
2. uma linha no arquivo `.env` da raiz do projeto (`ENV_FILE`), que não
   vai para o git. O `.env.example`, versionado, tem os valores do
   artigo: copie-o para `.env` e mude o que quiser;
3. o valor padrão do campo (o do artigo).

Variáveis do `.env` que não são campos de `Settings` são ignoradas. Para
ler outro arquivo, use `Settings(_env_file=caminho)`.
