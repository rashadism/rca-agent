import logging
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .core.config import settings
from .core.llm import get_model
from .core.opensearch import get_opensearch_client
from .logging_config import setup_logging

load_dotenv()
setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting up: Testing LLM connection...")
    try:
        model = get_model(settings.rca_agent_llm)
        test_response = await model.ainvoke("Hello")
        logger.info("LLM test successful: %s", test_response.content[:50])
    except Exception as e:
        logger.error("LLM initialization failed: %s", e, exc_info=True)
        sys.exit(1)

    logger.info("Testing OpenSearch connection...")
    try:
        opensearch_client = get_opensearch_client()
        if opensearch_client.check_connection():
            logger.info("OpenSearch connection successful")
        else:
            logger.error("OpenSearch connection check failed")
            sys.exit(1)
    except Exception as e:
        logger.error("OpenSearch initialization failed: %s", e, exc_info=True)
        sys.exit(1)

    yield

    logger.info("Shutting down...")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
