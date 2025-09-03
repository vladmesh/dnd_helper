import logging
from typing import Dict, Optional

from dnd_helper_api.db import get_session
from fastapi import APIRouter, Depends, Response
from sqlmodel import Session, select

from shared_models.enums import Language
from shared_models.ui_translation import UiTranslation

router = APIRouter(prefix="/i18n", tags=["i18n"])
logger = logging.getLogger(__name__)


def _select_language(lang: Optional[str]) -> Language:
    try:
        if isinstance(lang, str):
            v = lang.strip().lower()
            if v in {"ru", "en"}:
                return Language(v)
    except Exception:
        pass
    return Language.RU


@router.get("/ui", response_model=Dict[str, str])
def get_ui_translations(
    ns: str,
    lang: Optional[str] = None,
    session: Session = Depends(get_session),  # noqa: B008
    response: Response = None,
) -> Dict[str, str]:
    requested = _select_language(lang)
    if response is not None:
        response.headers["Content-Language"] = requested.value

    rows = session.exec(
        select(UiTranslation).where(
            UiTranslation.namespace == ns,
            UiTranslation.lang == requested,
        )
    ).all()
    result: Dict[str, str] = {r.key: r.text for r in rows}

    # Fallback for missing keys from the opposite language
    fallback_lang = Language.EN if requested == Language.RU else Language.RU
    if rows:
        fallback_rows = session.exec(
            select(UiTranslation).where(
                UiTranslation.namespace == ns,
                UiTranslation.lang == fallback_lang,
            )
        ).all()
        for r in fallback_rows:
            if r.key not in result:
                result[r.key] = r.text

    logger.info("UI translations fetched", extra={"namespace": ns, "lang": requested.value, "count": len(result)})
    return result


