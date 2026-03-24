from fastapi import APIRouter, HTTPException, Request

from realtime_phone_agents.api.models import IngestRequest, SearchRequest


router = APIRouter(prefix="/knowledge", tags=["knowledge"])
compat_router = APIRouter(prefix="/superlinked", tags=["superlinked"])


async def _ingest_bundle(ingest_request: IngestRequest, request: Request) -> dict:
    try:
        result = request.app.state.knowledge_service.ingest_knowledge_bundle(
            ingest_request.bundle_path
        )
        return {
            "status": "success",
            "message": f"Knowledge bundle ingested successfully from {ingest_request.bundle_path}",
            **result,
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Knowledge bundle not found: {ingest_request.bundle_path}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error ingesting knowledge bundle: {str(exc)}",
        )


async def _search_knowledge(search_request: SearchRequest, request: Request) -> dict:
    try:
        response = await request.app.state.knowledge_service.search_knowledge(
            query=search_request.query,
            limit=search_request.limit,
            intent=search_request.intent,
            language=search_request.language,
        )
        count = response.get("result_count", len(response.get("results", [])))
        return {
            "status": "success",
            "query": search_request.query,
            "limit": search_request.limit,
            "count": count,
            **response,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching knowledge: {str(exc)}",
        )


@router.post("/ingest")
async def ingest_knowledge(ingest_request: IngestRequest, request: Request):
    return await _ingest_bundle(ingest_request, request)


@router.post("/search")
async def search_knowledge(search_request: SearchRequest, request: Request):
    return await _search_knowledge(search_request, request)


@compat_router.post("/ingest")
async def ingest_knowledge_compat(ingest_request: IngestRequest, request: Request):
    return await _ingest_bundle(ingest_request, request)


@compat_router.post("/search")
async def search_knowledge_compat(search_request: SearchRequest, request: Request):
    return await _search_knowledge(search_request, request)
