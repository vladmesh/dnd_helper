import logging
from fastapi import APIRouter


router = APIRouter(prefix="/monsters", tags=["monsters"])
logger = logging.getLogger(__name__)


# Import submodules to register routes on the shared router
from . import translations as _translations  # noqa: F401
from . import derived as _derived  # noqa: F401
# Register static GET routes before dynamic /{monster_id} routes to avoid 422 on '/monsters/search-wrapped'
from . import endpoints_list  # noqa: F401
from . import endpoints_search  # noqa: F401
from . import endpoints_detail  # noqa: F401
from . import endpoints_mutations  # noqa: F401

__all__ = ["router"]


