from dataclasses import dataclass
from dataclasses import field

from dataclasses_json import CatchAll
from dataclasses_json import config
from dataclasses_json import dataclass_json
from dataclasses_json import Undefined


@dataclass_json
@dataclass
class Geometry:
    type: str
    coordinates: list


@dataclass_json
@dataclass
class Service:
    id: str
    type: str
    properties: str
    geometry: Geometry


@dataclass_json
@dataclass
class GeoJSON:
    type: str
    features: list[Service]


@dataclass_json
@dataclass
class DataByBudget:
    geojson: GeoJSON
    table: list
    summary_table: list


@dataclass_json
@dataclass
class NoContentMessage:
    message: str


@dataclass_json(undefined=Undefined.INCLUDE)
@dataclass
class ImpactEvaluation:
    geojson: GeoJSON
    explanation: CatchAll


@dataclass_json(undefined=Undefined.INCLUDE)
@dataclass
class SummaryTable:
    territorial_hierarchy: dict = field(metadata=config(field_name="Иерархия территории"))
    tables: CatchAll


@dataclass_json
@dataclass
class Indicator:
    name: str = field(metadata=config(field_name="Показатель"))
    value: str = field(metadata=config(field_name="Количество"))
    metric: str = field(metadata=config(field_name="Единицы измерения"))
    interpretation: str = field(metadata=config(field_name="Интерпретация"))
    blocks: list[dict]


@dataclass_json(undefined=Undefined.INCLUDE)
@dataclass
class SummaryIndicators:
    territorial_hierarchy: dict = field(metadata=config(field_name="Иерархия территории"))
    indicators: CatchAll  # list[Indicator] = field(metadata=config(field_name="Показатели"))
