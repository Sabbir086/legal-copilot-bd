from fastapi import APIRouter
from app.schemas.legal import LegalSearchRequest
from app.services.legal_sources import search_sources

router = APIRouter(prefix="/api/v1/legal", tags=["legal research"])

@router.post("/search")
def legal_search(request: LegalSearchRequest):
    results = search_sources(request.query, request.jurisdiction)
    return {
        "results": results,
        "notice": "Search results are discovery leads only. All source text, amendments, commencement and current legal status require primary-source verification."
    }
