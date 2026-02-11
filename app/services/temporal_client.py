from app.utils.app_logging import logger
from app.utils.singleton_meta import SingletonMeta
from temporalio.client import Client
from app.config import config
from typing import Optional

class TemporalClientService(metaclass=SingletonMeta):
    def __init__(self):
        self._client: Optional[Client] = None
        logger.info("Initializing TemporalClientService")
        self._temporal_host = config.TEMPORAL_HOST
        self._temporal_namespace = config.TEMPORAL_NAMESPACE
        logger.info(f"TEMPORAL_HOST: {self._temporal_host}")
        logger.info(f"TEMPORAL_NAMESPACE: {self._temporal_namespace}")

    async def get_client(self, namespace: Optional[str] = None) -> Client:
        """
        Get or create a Temporal client instance.

        Returns:
            Temporal client instance
        """
        if self._client is None:
            try:
                logger.info("Creating new Temporal client instance")
                self._client = await Client.connect(
                    self._temporal_host,
                    namespace=namespace or self._temporal_namespace
                )
                logger.info(f"Temporal client connected successfully at: {self._temporal_host}")
            except Exception as e:
                logger.error(f"Failed to connect to Temporal server: {e}")
                raise

        return self._client
    async def close_client(self) -> None:
        """Close the Temporal client connection."""
        if self._client:
            # In newer versions of temporalio, the client doesn't have a close method
            # The connection is managed automatically
            self._client = None
            logger.info("Temporal client connection closed")

    def get_task_queue(self, language: str) -> str:
        """
        Get the task queue name for a specific language.

        Args:
            language: Name of the language (e.g., 'Golang', 'Python')

        Returns:
            Task queue name
        """
        return f"{language}-task-queue"

    def get_workflow_id(self, repository_name: str, workflow_type: str) -> str:
        """
        Generate a unique workflow ID.

        Args:
            repository_name: Repository name
            workflow_type: Type of workflow

        Returns:
            Unique workflow ID
        """
        return f"{workflow_type}-{repository_name}"

temporal_client_service = TemporalClientService()
