"""Enterprise-value source inputs exposed through the native OpenBB query lifecycle."""

from openbb_core.app.model.command_context import CommandContext
from openbb_core.app.model.example import APIEx
from openbb_core.app.model.obbject import OBBject
from openbb_core.app.provider_interface import (
    ExtraParams,
    ProviderChoices,
    StandardParams,
)
from openbb_core.app.query import Query
from openbb_core.app.router import Router

router = Router()


@router.command(model="EnterpriseValues", examples=[APIEx(parameters={"symbol": "AAPL", "provider": "fmp"})])
async def enterprise_values(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """Get provider-reported enterprise-value inputs without analyst adjustments."""
    return await OBBject.from_query(Query(**locals()))
