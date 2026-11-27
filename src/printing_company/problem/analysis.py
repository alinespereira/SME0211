r"""Pós-processamento da solução do modelo: tempo real com setup e consumo
de energia.

O modelo relaxado (`printing_company.problem.model`) dá as horas $t$ que
cada máquina fica produzindo, sem os setups. As funções deste módulo
calculam, a partir dessas horas, as grandezas do artigo:

- `operating_times`: o **tempo real** de cada máquina, com o setup. No
  artigo, a máquina $m$ gasta $A_{im}$ horas de setup para cada item $i$
  designado a ela ($x_{im} = 1$). O modelo relaxado agrega os itens por
  máquina e não diz quantos itens cada uma recebe, então contamos **um
  setup por máquina ligada**:

  $$
  \tau_m = t_m + A_m \, [t_m > 0].
  $$

  Toda máquina ligada recebe pelo menos um item, então esse é um limite
  inferior para o tempo do artigo. Os setups não entram na restrição de
  capacidade, então $\tau_m$ pode passar um pouco de $T$.
- `energy_consumption`: o **consumo de energia** de cada máquina, em kWh.
  Como na função objetivo (1) do artigo, o consumo $kw_m$ da Tabela 1 é a
  energia por hora de operação (a potência), e a máquina consome
  $kw_m$ durante todo o tempo real, setup incluído:

  $$
  E_m = kw_m \, \tau_m.
  $$

  O custo de energia do artigo é $c \sum_m E_m$, com a tarifa
  $c$ = `ENERGY_PRICE`, de 0,86 real por kWh (veja `energy_cost`).

As horas vêm de `Solution.x`, indexadas pelos nomes das variáveis (os
`Machine.id`): `dict(zip(problem.variable_names, solution.x))`.
"""

from collections.abc import Mapping, Sequence

from printing_company.problem.spec import Machine

__all__ = [
    "ENERGY_PRICE",
    "energy_consumption",
    "energy_cost",
    "operating_times",
]

ENERGY_PRICE = 0.86
r"""Tarifa de energia $c$ do artigo, em reais por kWh (horário fora de
ponta)."""

_TOLERANCE = 1e-9
"""Abaixo disso, a máquina é considerada desligada."""


def operating_times(
    *,
    hours: Mapping[str, float],
    machines: Sequence[Machine],
) -> dict[str, float]:
    r"""Tempo real $\tau_m = t_m + A_m [t_m > 0]$ de cada máquina, em horas.

    **Argumentos:**

    - `hours`: as horas de produção $t_m$ de cada máquina, pelo `id`
      (máquinas ausentes contam como desligadas);
    - `machines`: as máquinas, com os setups $A_m$ (`Machine.setup`).

    Devolve um dicionário com todas as `machines`, na ordem dada. Uma
    máquina desligada ($t_m = 0$) não tem setup.

    **Exemplo:** a `Print01` (setup de 0,25 h) imprime 20 h; a `Print02`
    fica desligada.

    >>> from printing_company.problem.spec import PrintingMachine
    >>> machines = [
    ...     PrintingMachine(id="Print01", speed=10_500, setup=0.25, consumption=40),
    ...     PrintingMachine(id="Print02", speed=3_000, setup=0.5, consumption=112),
    ... ]
    >>> operating_times(hours={"Print01": 20.0, "Print02": 0.0}, machines=machines)
    {'Print01': 20.25, 'Print02': 0.0}

    **Levanta:** `ValueError` se alguma hora for negativa.

    >>> operating_times(hours={"Print01": -1.0}, machines=machines)
    Traceback (most recent call last):
        ...
    ValueError: Horas negativas para Print01: -1.0.
    """
    times: dict[str, float] = {}
    for machine in machines:
        t = hours.get(machine.id, 0.0)
        if t < -_TOLERANCE:
            raise ValueError(f"Horas negativas para {machine.id}: {t}.")
        times[machine.id] = t + machine.setup if t > _TOLERANCE else 0.0
    return times


def energy_consumption(
    *,
    times: Mapping[str, float],
    machines: Sequence[Machine],
) -> dict[str, float]:
    r"""Consumo de energia $E_m = kw_m \, \tau_m$ de cada máquina, em kWh.

    **Argumentos:**

    - `times`: os tempos reais $\tau_m$, em horas, como os de
      `operating_times`;
    - `machines`: as máquinas, com os consumos $kw_m$
      (`Machine.consumption`).

    **Exemplo:** a `Print01` (40 kWh por hora) fica ligada 20,25 h.

    >>> from printing_company.problem.spec import PrintingMachine
    >>> machines = [
    ...     PrintingMachine(id="Print01", speed=10_500, setup=0.25, consumption=40),
    ...     PrintingMachine(id="Print02", speed=3_000, setup=0.5, consumption=112),
    ... ]
    >>> energy_consumption(times={"Print01": 20.25, "Print02": 0.0}, machines=machines)
    {'Print01': 810.0, 'Print02': 0.0}

    **Exemplo completo:** a carteira I do artigo com dois turnos.

    >>> from printing_company.problem import data
    >>> from printing_company.problem.model import SHIFT_HOURS, build_problem
    >>> machines = [*data.printers, *data.finishers]
    >>> problem = build_problem(
    ...     portfolio=data.portfolios[0],
    ...     printers=data.printers,
    ...     finishings=data.finishers,
    ...     capacity=2 * SHIFT_HOURS,
    ... )
    >>> hours = dict(zip(problem.variable_names, problem.solve().x.tolist()))
    >>> times = operating_times(hours=hours, machines=machines)
    >>> {name: round(tau, 2) for name, tau in times.items() if tau > 0}
    {'Print01': 20.25, 'Print04': 20.17, 'Print05': 9.25, 'Finish02': 19.5}
    >>> energy = energy_consumption(times=times, machines=machines)
    >>> {name: round(e, 2) for name, e in energy.items() if e > 0}
    {'Print01': 810.0, 'Print04': 484.08, 'Print05': 20.35, 'Finish02': 2184.0}
    >>> round(sum(energy.values()), 2), round(energy_cost(energy=energy), 2)
    (3498.43, 3008.65)
    """
    return {
        machine.id: machine.consumption * times.get(machine.id, 0.0)
        for machine in machines
    }


def energy_cost(
    *,
    energy: Mapping[str, float],
    price: float = ENERGY_PRICE,
) -> float:
    r"""Custo total de energia $c \sum_m E_m$, em reais.

    **Exemplo:** 810 kWh a 0,86 real por kWh.

    >>> round(energy_cost(energy={"Print01": 810.0}), 2)
    696.6
    """
    return price * sum(energy.values())
