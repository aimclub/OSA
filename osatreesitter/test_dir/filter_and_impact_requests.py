from api.api import Api
from api.data_models import DataByBudget
from api.data_models import ImpactEvaluation
from api.data_models import NoContentMessage


def parks_by_budget(budget: int | None = None, territory_name: str | None = None) -> DataByBudget | NoContentMessage:
    """Getting parks that fit the given parameters

    Args:
        budget: sum in rubles
        territory_name: name of territory where to find parks;
            can be city, municipality or district

    Returns:
        Either a class containing information about parks and their locations, or a
        class with a message that no data is available
    """
    data = Api.EndpointsUrban.get_parks(budget=budget, territory_name=territory_name)
    if len(data.keys()) > 1:
        return DataByBudget.from_dict(data)
    else:
        return NoContentMessage.from_dict(data)


def territory_by_budget(
    budget: int | None = None,
    service_type: str | None = None,
    territory_name: str | None = None,
) -> DataByBudget | NoContentMessage:
    """Getting territory that fit the given parameters

    Args:
        budget: sum in rubles
        service_type: name of service to place;
            can be school, polyclinic, kindergarten or park
        territory_name: name of territory where to find parks;
            can be city, municipality or district

    Returns:
        Either a class containing information about potential areas for the location of
        new services, or a class with a message that no data is available
    """
    if not all([service_type, territory_name]):
        raise ValueError("Type of service and territory name must be provided")

    data = Api.EndpointsUrban.get_territory_for_service(
        budget=budget, service_type=service_type, territory_name=territory_name
    )
    if len(data.keys()) > 1:
        return DataByBudget.from_dict(data)
    else:
        return NoContentMessage.from_dict(data)


def impact_by_construction(
    block_id: int | None = None,
    service_type: str | None = None,
    object_type: str | None = None,
    capacity: int | None = None,
) -> ImpactEvaluation:
    """Getting parks that fit the given parameters

    Args:
        block_id: identifier of the source block
        service_type: name of service to place;
            can be school, polyclinic, kindergarten
        object_type: selection of object for which the provision will be recalculated;
            can be service, house, apartment block, dwelling.
        capacity: new facility capacity

    Returns:
        A class containing information about changes from the construction of new
        services or a house
    """
    if not all([block_id, service_type, object_type, capacity]):
        raise ValueError("Block id, type of service, object type and capacity must be provided")
    data = Api.EndpointsUrban.get_impact(
        block_id=block_id,
        service_type=service_type,
        object_type=object_type,
        capacity=capacity,
    )
    return ImpactEvaluation.from_dict(data)
