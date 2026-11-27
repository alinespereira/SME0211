from abc import ABC

from pydantic import BaseModel, ConfigDict, PositiveFloat, computed_field


class Machine(BaseModel, ABC):
    model_config = ConfigDict(frozen=True)

    id: str
    speed: PositiveFloat
    setup: PositiveFloat
    consumption: PositiveFloat

    def __init__(self, **data) -> None:
        if type(self) is Machine:
            raise TypeError("Base é abstrata")
        super().__init__(**data)


class Printer(Machine):
    model_config = ConfigDict(frozen=True)
    pass


class Finishing(Machine):
    model_config = ConfigDict(frozen=True)
    pass


class Demand(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    quantity: PositiveFloat
    requires_finishing: bool = False


class Portfolio(BaseModel):
    model_config = ConfigDict(frozen=True)

    demands: list[Demand]

    @computed_field
    def with_finishing(self) -> float:
        return sum(
            demand.quantity
            for demand in self.demands
            if demand.requires_finishing
        )

    @computed_field
    def without_finishing(self) -> float:
        return sum(
            demand.quantity
            for demand in self.demands
            if not demand.requires_finishing
        )
