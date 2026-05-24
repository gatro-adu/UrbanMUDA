
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from agent_main.agent import make_graph
from scripts.stream_output import stream_output_graph
from langchain_core.runnables import RunnableConfig

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Init DB (optional)
    app.state.graph = await make_graph(RunnableConfig())
    print('\n', '='*100, '\n')
    yield

app = FastAPI(lifespan=lifespan)

# 示例路由
@app.get("/graph")
async def graph():
    return app.state.graph
