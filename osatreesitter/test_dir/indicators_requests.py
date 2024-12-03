import logging

from api.api import Api
from api.data_models import SummaryIndicators
from utils.measure_time import Timer


logger = logging.getLogger(__name__)


def get_indicators(
    indicators: list[str],
    name_id: str | int | None = None,
    territory_type: str | None = None,
    coordinates: dict | None = None,
) -> SummaryIndicators:
    # coordinates must be prepared and typed via api.utils.coords_typer.prepare_typed_coords
    if not indicators:
        msg = "Expected at least one indicator"
        raise ValueError(msg)
    if name_id or coordinates:
        json_data = {
            "indicators": indicators,
            "territory_name_id": name_id,
            "territory_type": territory_type,
            "selection_zone": coordinates,
        }
        with Timer() as t:
            response = Api.EndpointsUrban.get_indicators(json_data=json_data)
        logger.info(f"Getting context info time: {t.seconds_from_start} sec")
        return SummaryIndicators.from_dict(response)

    msg = "Expected name_id or coordinates"
    raise ValueError(msg)
