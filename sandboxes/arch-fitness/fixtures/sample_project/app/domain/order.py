# sample_project domain — the stable core: abstract (Na>0) + zero outgoing deps (Ce=0, I=0, maximally stable).
from abc import ABC, abstractmethod


class OrderSpec(ABC):           # abstract → contributes to Na (abstractness numerator)
    @abstractmethod
    def total(self):
        ...


class Money:                    # concrete value object
    pass
