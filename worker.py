import asyncio
import signal
import sys
from typing import List
from temporalio.worker import Worker
from temporalio.client import Schedule, ScheduleActionStartWorkflow, ScheduleSpec

from app.utils.app_logging import logger
from app.config import config
from app.services.temporal_client import temporal_client_service
from app.workflows.workflow import PackagebotWorkflow, DependabotAlertsWorkflow, PACKAGEBOT_TASK_QUEUE
from app.workflows.agent_orchestrator import RemediationOrchestratorWorkflow
from app.activities.fetch_dependabot_alerts import fetch_dependabot_alerts_activity
from app.activities.build__alerts_object import build_alerts_object_activity
from app.activities.load_remediation_plan import load_remediation_plan_activity
from app.activities.execute_dependency_remediation_activity import execute_dependency_remediation_activity
from app.activities.execute_pull_request_activity import execute_pull_request_activity
from app.activities.execute_jira_ticket_activity import execute_jira_ticket_activity


class PackagebotTemporalWorker:
    """Temporal worker for running Packagebot workflows and activities."""

    def __init__(self):
        self.workers: List[Worker] = []
        self.running = False

    async def start_worker(
        self,
        task_queue: str,
        workflows: List[type],
        activities: List[type],
        max_concurrent_activities: int = 20,
    ) -> Worker:
        """
        Start a Temporal worker for specific task queue.

        Args:
            task_queue: Task queue name
            workflows: List of workflow classes
            activities: List of activity functions
            max_concurrent_activities: Maximum concurrent activities

        Returns:
            Started worker instance
        """
        try:
            client = await temporal_client_service.get_client()

            worker = Worker(
                client,
                task_queue=task_queue,
                workflows=workflows,
                activities=activities,
                max_concurrent_activities=max_concurrent_activities,
            )

            logger.info(f"Starting Packagebot worker for task queue: {task_queue}")
            logger.info(f"Registered workflows: {[w.__name__ for w in workflows]}")
            logger.info(f"Registered activities: {[a.__name__ for a in activities]}")

            self.workers.append(worker)
            return worker

        except Exception as e:
            logger.error(
                f"Failed to start Packagebot worker for task queue {task_queue}: {str(e)}"
            )
            raise

    async def start_all_workers(self) -> None:
        """Start all configured Packagebot workers."""
        logger.info("Starting all Packagebot Temporal workers")

        try:
            # Packagebot Worker
            await self.start_worker(
                task_queue=PACKAGEBOT_TASK_QUEUE,
                workflows=[
                    PackagebotWorkflow,
                    DependabotAlertsWorkflow,
                    RemediationOrchestratorWorkflow,
                ],
                activities=[
                    fetch_dependabot_alerts_activity,
                    build_alerts_object_activity,
                    load_remediation_plan_activity,
                    execute_dependency_remediation_activity,
                    execute_pull_request_activity,
                    execute_jira_ticket_activity,
                ],
                max_concurrent_activities=20,
            )

            self.running = True
            logger.info("All Packagebot workers started successfully")

        except Exception as e:
            logger.error(f"Failed to start Packagebot workers: {str(e)}")
            raise

    async def run(self) -> None:
        """Run all Packagebot workers."""
        if not self.workers:
            await self.start_all_workers()

        try:
            # Start all workers concurrently
            worker_tasks = [
                asyncio.create_task(worker.run()) for worker in self.workers
            ]

            logger.info("All Packagebot workers are running. Press Ctrl+C to stop.")

            # Wait for all workers to complete
            await asyncio.gather(*worker_tasks)

        except asyncio.CancelledError:
            logger.info("Packagebot workers cancelled by user")
        except Exception as e:
            logger.error(f"Error running Packagebot workers: {str(e)}")
            raise
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Shutdown all Packagebot workers gracefully."""
        if not self.running:
            return

        logger.info("Shutting down Packagebot workers...")

        try:
            # Cancel all worker tasks
            for worker in self.workers:
                if hasattr(worker, "shutdown"):
                    await worker.shutdown()

            # Close Temporal client
            await temporal_client_service.close_client()

            self.running = False
            logger.info("All Packagebot workers shut down successfully")

        except Exception as e:
            logger.error(f"Error during Packagebot workers shutdown: {str(e)}")

    async def get_schedule(self, client, schedule_id: str) -> bool:
        """
        Checks the Packagebot schedule state.

        Args:
            client: The client object to interact with schedules.
            schedule_id: The ID of the schedule to retrieve.

        Returns:
            True if the schedule is paused, False if it is running, None if it does not exist.
        """
        try:
            handle = client.get_schedule_handle(schedule_id)
            desc = await handle.describe()

            # Log detailed schedule state information
            logger.debug(
                "Packagebot schedule %s state: %s", schedule_id, desc.schedule.state.note
            )
            return desc.schedule.state.paused
        except Exception as e:
            if "not found" in str(e).lower():
                logger.info(f"Packagebot schedule '{schedule_id}' does not exist.")
                return None
            logger.error(
                "An unexpected error occurred while getting Packagebot schedule %s: %s",
                schedule_id,
                e,
            )
            raise

    async def create_or_update_schedule(
        self, schedule_id: str, cron: str, workflow: type, workflow_args: list
    ):
        """
        Create or update a Temporal schedule for Packagebot workflows.

        Args:
            schedule_id: Unique ID for the schedule
            cron: Cron expression for the schedule
            workflow: Workflow class to run
            workflow_args: Arguments to pass to the workflow
        """
        try:
            client = await temporal_client_service.get_client()
            handle = client.get_schedule_handle(schedule_id)

            try:
                # Check if the schedule exists
                desc = await handle.describe()
                logger.info(
                    f"Packagebot schedule '{schedule_id}' exists. Checking if update is needed..."
                )

                # Check if the cron expression or action has changed
                current_cron = (
                    desc.schedule.spec.cron_expressions[0]
                    if desc.schedule.spec.cron_expressions
                    else None
                )
                current_action = desc.schedule.action

                # Compare configurations
                config_changed = (
                    current_cron != cron or current_action.args != workflow_args
                )
                logger.info(f"Current cron: {current_cron}, New cron: {cron}")
                logger.info(
                    f"Current action args: {current_action.args}, New action args: {workflow_args}"
                )

                if not config_changed:
                    logger.info(
                        f"Packagebot schedule '{schedule_id}' configuration is already up-to-date."
                    )
                else:
                    logger.info(
                        f"Packagebot schedule '{schedule_id}' configuration changed. Updating..."
                    )

                    # Delete the existing schedule and create a new one
                    await handle.delete()
                    logger.info(f"Packagebot schedule '{schedule_id}' deleted.")

                    # Create a new schedule with updated configuration
                    schedule = Schedule(
                        action=ScheduleActionStartWorkflow(
                            workflow=workflow,
                            args=workflow_args,
                            id=f"{schedule_id}_workflow",
                            task_queue=PACKAGEBOT_TASK_QUEUE,
                        ),
                        spec=ScheduleSpec(
                            intervals=[],
                            cron_expressions=[cron],
                        ),
                    )
                    await client.create_schedule(schedule_id, schedule)
                    logger.info(
                        f"Packagebot schedule '{schedule_id}' recreated with new configuration."
                    )
            except Exception as e:
                if "not found" in str(e).lower():
                    # Schedule does not exist, create it
                    logger.info(
                        f"Packagebot schedule '{schedule_id}' does not exist. Creating..."
                    )
                    schedule = Schedule(
                        action=ScheduleActionStartWorkflow(
                            workflow=workflow,
                            args=workflow_args,
                            id=f"{schedule_id}_workflow",
                            task_queue=PACKAGEBOT_TASK_QUEUE,
                        ),
                        spec=ScheduleSpec(
                            intervals=[],
                            cron_expressions=[cron],
                        ),
                    )
                    await client.create_schedule(schedule_id, schedule)
                    logger.info(
                        f"Packagebot schedule '{schedule_id}' created with cron: {cron}"
                    )
                else:
                    raise

        except Exception as e:
            logger.error(
                f"Failed to create or update Packagebot schedule '{schedule_id}': {str(e)}"
            )
            raise


# Global Packagebot worker instance
packagebot_temporal_worker = PackagebotTemporalWorker()


async def main():
    """Main entry point for the Packagebot worker."""

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down Packagebot workers...")
        asyncio.create_task(packagebot_temporal_worker.shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Cron expression for every Sunday at 8 PM (20:00)
        packagebot_cron = "0 20 * * 0"

        # Create Packagebot schedule using PackagebotWorkflow as the entry point
        await packagebot_temporal_worker.create_or_update_schedule(
            schedule_id="packagebot_schedule",
            cron=packagebot_cron,
            workflow=PackagebotWorkflow,
            workflow_args=[
                {
                    "workflow_id": "packagebot-scheduled",
                    "org": config.get("GITHUB_ORG"),
                    "state": "open",
                    "enable_remediation": True,
                }
            ],
        )

        await packagebot_temporal_worker.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down Packagebot workers...")
    except Exception as e:
        logger.error(f"Packagebot worker failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())