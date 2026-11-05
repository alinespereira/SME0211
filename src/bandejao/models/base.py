"""Tipos básicos: unidades de medida e intervalos de limites."""

from enum import StrEnum, auto
from typing import Self

from pydantic import BaseModel, Field, model_validator


class Unit(StrEnum):
    """Unidade de medida de um nutriente."""

    KCAL = "kCal"
    G = auto()
    MG = auto()

    @classmethod
    def _missing_(cls, value: object) -> "Unit | None":
        """Aceita a unidade sem diferenciar maiúsculas (ex.: ``"kcal"``)."""
        if isinstance(value, str):
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        return None


class Limit(BaseModel):
    """Intervalo ``[minimum, maximum]`` que um valor deve respeitar.

    Qualquer um dos extremos pode ser ``None``, indicando que não há limite
    daquele lado (por exemplo, sódio só tem máximo e fibra só tem mínimo).

    Atributos:
        minimum: limite inferior, ou ``None`` se não houver.
        maximum: limite superior, ou ``None`` se não houver.
    """

    minimum: float | None = Field(default=None)
    maximum: float | None = Field(default=None)

    @model_validator(mode="after")
    def validate_order(self: Self) -> Self:
        """Garante que o mínimo não seja maior que o máximo.

        Raises:
            ValueError: se os dois limites existirem e ``minimum > maximum``.
        """
        match self.minimum, self.maximum:
            case (None, _) | (_, None):
                pass
            case (lo, hi) if lo > hi:
                raise ValueError(f"minimum ({lo}) > maximum ({hi})")
        return self

    def __contains__(self, value: float) -> bool:
        """Indica se ``value`` está dentro do intervalo (extremos inclusos).

        Permite escrever ``valor in limite``.
        """
        return (self.minimum is None or value >= self.minimum) and (
            self.maximum is None or value <= self.maximum
        )
