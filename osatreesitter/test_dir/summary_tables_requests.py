from functools import partial

from api.api import Api
from api.api_tables import possible_tables
from api.data_models import SummaryTable


def get_summary_table(
    table: str,
    name_id: str | None = None,
    territory_type: str | None = None,
    coordinates: list = None,
) -> SummaryTable:
    if name_id:
        data = Api.EndpointsUrban.get_summary_table(
            table=table,
            territory_name_id=name_id,
            territory_type=territory_type,
            selection_zone=None,
        )
        return SummaryTable.from_dict(data)
    elif coordinates:
        data = Api.EndpointsUrban.get_summary_table(
            table=table,
            territory_name_id=None,
            territory_type=None,
            selection_zone=coordinates,
        )
        return SummaryTable.from_dict(data)
    else:
        raise ValueError("Expected name_id and type or coordinates or just name_id")


get_general_stats_city = partial(get_summary_table, table=possible_tables["city"])
get_general_stats_districts_mo = partial(get_summary_table, table=possible_tables["district"])
get_general_stats_block = partial(get_summary_table, table=possible_tables["block"])
get_general_stats_education = partial(get_summary_table, table=possible_tables["education"])
get_general_stats_healthcare = partial(get_summary_table, table=possible_tables["healthcare"])
get_general_stats_culture = partial(get_summary_table, table=possible_tables["culture"])
get_general_stats_sports = partial(get_summary_table, table=possible_tables["sport"])
get_general_stats_services = partial(get_summary_table, table=possible_tables["government_services"])
get_general_stats_demography = partial(get_summary_table, table=possible_tables["demography"])
get_general_stats_housing_and_communal_services = partial(get_summary_table, table=possible_tables["housing_services"])
get_general_stats_transport = partial(get_summary_table, table=possible_tables["transport"])
get_general_stats_object = partial(get_summary_table, table=possible_tables["object"])
get_general_stats_complaints = partial(get_summary_table, table=possible_tables["complaints"])
get_general_stats_provision = partial(get_summary_table, table=possible_tables["provision"])
get_general_stats_recreation = partial(get_summary_table, table=possible_tables["recreation"])
