from inspect import ismethod
import os

from attr import dataclass
from dataclasses_json import dataclass_json
from dotenv import load_dotenv

from api.endpoint import GetEndpoint
from api.endpoint import PostEndpoint
from modules.variables.definitions import ROOT


load_dotenv(ROOT / "config.env")


class Api:
    class EndpointsUrban:
        _base_url = os.environ.get("ENDPOINT_TABLES_URL")
        get_summary_table = PostEndpoint(
            url="/api_llm/tables_context/",
            param_names=(
                "table",
                "territory_name_id",
                "territory_type",
                "selection_zone",
            ),
        )
        get_indicators = PostEndpoint(
            url="/api_llm/indicators_context/",
        )
        get_parks = GetEndpoint(
            url="/api_llm/filter_parks",
            param_names=("budget", "territory_name"),
        )
        get_territory_for_service = GetEndpoint(
            url="/api_llm/filter_services",
            param_names=("budget", "service_type", "territory_name"),
        )
        get_impact = GetEndpoint(
            url="/api_llm/impact_evaluation",
            param_names=("block_id", "service_type", "object_type", "capacity"),
        )

    class EndpointsChats:
        _base_url = os.environ.get("ENDPOINT_CHAT_URL")
        get_history = PostEndpoint(
            url="/history/all",
            param_names=(
                "user_id",
                "context",
            ),
        )
        post_message = PostEndpoint(
            url="/history",
        )


@dataclass_json
@dataclass
class ApiGeometry:
    type: str
    coordinates: list


@dataclass_json
@dataclass
class ApiMessage:
    msg: str
    from_: str
    to_: str
    context: str | None
    context_id: str | None
    geometry: ApiGeometry | None


# Process all endpoint groups to set base url
for endpoint_group_name in dir(Api):
    if not endpoint_group_name.startswith("Endpoints"):
        continue
    endpoint_group = getattr(Api, endpoint_group_name)

    for endpoint_name in dir(endpoint_group):
        if ismethod(getattr(endpoint_group, endpoint_name)) or endpoint_name.startswith(
            "_",
        ):
            continue
        endpoint = getattr(endpoint_group, endpoint_name)
        if endpoint_group._base_url:
            endpoint.url = endpoint_group._base_url + endpoint.url
        else:
            msg = f"Base url for endpoint {endpoint_group.__name__}.{endpoint_name} is not set in config.env"
            raise KeyError(msg)
