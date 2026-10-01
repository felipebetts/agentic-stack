from fastapi import APIRouter, Query, status

from agent.api.deps import GraphDep, PoolDep, PrincipalDep, ThreadDep
from agent.api.schemas import CreateThreadIn, ThreadOut, ThreadStateOut
from agent.api.serializers import load_thread_state
from agent.persistence import threads as repo

router = APIRouter(prefix="/threads", tags=["threads"])


@router.post("", response_model=ThreadOut, status_code=status.HTTP_201_CREATED)
async def create_thread(body: CreateThreadIn, principal: PrincipalDep, pool: PoolDep):
    return await repo.create_thread(pool, principal.user_id, body.title)


@router.get("", response_model=list[ThreadOut])
async def list_threads(
    principal: PrincipalDep, pool: PoolDep, limit: int = Query(50, ge=1, le=200)
):
    return await repo.list_threads(pool, principal.user_id, limit)


@router.get("/{thread_id}", response_model=ThreadStateOut)
async def get_thread_state(thread: ThreadDep, graph: GraphDep):
    return await load_thread_state(graph, thread["id"])


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(thread: ThreadDep, pool: PoolDep, graph: GraphDep):
    await graph.checkpointer.adelete_thread(str(thread["id"]))  # type: ignore[union-attr]
    await repo.delete_thread(pool, thread["id"])
