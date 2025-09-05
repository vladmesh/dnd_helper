import logging

from fastapi import APIRouter

router = APIRouter(prefix="/spells", tags=["spells"])
logger = logging.getLogger(__name__)


from . import derived as _derived  # noqa: F401

# Register static GET routes before dynamic /{spell_id} routes to avoid 422 on '/spells/search-wrapped'
from . import (
    endpoints_list,  # noqa: F401  # static paths like '/list/*'
    endpoints_search,  # noqa: F401  # static paths like '/search/*'
    endpoints_detail,  # noqa: F401  # dynamic '/{spell_id}', '/{spell_id}/wrapped'
    endpoints_mutations,  # noqa: F401
)
from . import translations as _translations  # noqa: F401

__all__ = ["router"]


