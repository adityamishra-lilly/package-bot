
```python
class GenesysTemporalWorker:
    """Temporal worker for running Genesys workflows and activities."""

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
            client = await temporal_client_service.get_client(
                "aepc-dev-orchestration-genesys"
            )

            worker = Worker(
                client,
                task_queue=task_queue,
                workflows=workflows,
                activities=activities,
                max_concurrent_activities=max_concurrent_activities,
            )

            logger.info(f"Starting Genesys worker for task queue: {task_queue}")
            logger.info(f"Registered workflows: {[w.__name__ for w in workflows]}")
            logger.info(f"Registered activities: {[a.__name__ for a in activities]}")

            self.workers.append(worker)
            return worker

        except Exception as e:
            logger.error(
                f"Failed to start Genesys worker for task queue {task_queue}: {str(e)}"
            )
            raise

    async def start_all_workers(self) -> None:
        """Start all configured Genesys workers."""
        logger.info("Starting all Genesys Temporal workers")

        try:
            # Genesys Worker
            await self.start_worker(
                task_queue="genesys-task-queue",
                workflows=[
                    GenesysWorkflow,
                    GenesysWorkflowSetA,
                    GenesysWorkflowSetB,
                    GenesysScheduledWorkflow,
                ],
                activities=[
                    # new activities
                    genesys_activities.generate_interval_activity,
                    get_conversations.genesys_auth_activity,
                    get_conversations.get_conversations_activity,
                    # New activities
                    get_conversation_recording_details.filter_completed_conversations_activity,
                    get_conversation_recording_details.get_conversation_recording_id_activity,
                    get_conversation_recording_details.get_multiple_conversation_recording_details_activity,
                    # Download and save recordings activity
                    download_recordings.download_and_save_recordings_activity,
                    # Save recording metadata activity
                    save_recording_metadata.save_recording_metadata_activity,
                    # New mock activities (5-8) for dynamic workflow testing
                    genesys_activities.transcription_activity,
                    genesys_activities.build_orchestrate_conversation_request_activity,
                    genesys_activities.call_orchestrate_api_activity,
                ],
                max_concurrent_activities=20,
            )

            self.running = True
            logger.info("All Genesys workers started successfully")

        except Exception as e:
            logger.error(f"Failed to start Genesys workers: {str(e)}")
            raise

    async def run(self) -> None:
        """Run all Genesys workers."""
        if not self.workers:
            await self.start_all_workers()

        try:
            # Start all workers concurrently
            worker_tasks = [
                asyncio.create_task(worker.run()) for worker in self.workers
            ]

            logger.info("All Genesys workers are running. Press Ctrl+C to stop.")

            # Wait for all workers to complete
            await asyncio.gather(*worker_tasks)

        except asyncio.CancelledError:
            logger.info("Genesys workers cancelled by user")
        except Exception as e:
            logger.error(f"Error running Genesys workers: {str(e)}")
            raise
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Shutdown all Genesys workers gracefully."""
        if not self.running:
            return

        logger.info("Shutting down Genesys workers...")

        try:
            # Cancel all worker tasks
            for worker in self.workers:
                if hasattr(worker, "shutdown"):
                    await worker.shutdown()

            # Close Temporal client
            await temporal_client_service.close_client()

            self.running = False
            logger.info("All Genesys workers shut down successfully")

        except Exception as e:
            logger.error(f"Error during Genesys workers shutdown: {str(e)}")

    async def create_schedule(
        self, schedule_id: str, cron: str, workflow: type, workflow_args: list
    ):
        """
        Create a Temporal schedule for Genesys workflows.

        Args:
            schedule_id: Unique ID for the schedule
            cron: Cron expression for the schedule
            workflow: Workflow class to run
            workflow_args: Arguments to pass to the workflow
        """
        try:
            client = await temporal_client_service.get_client(
                "aepc-dev-orchestration-genesys"
            )
            workflow_id = f"{schedule_id}_workflow"
            schedule = Schedule(
                action=ScheduleActionStartWorkflow(
                    workflow=workflow,
                    args=workflow_args,
                    id=workflow_id,
                    task_queue=temporal_client_service.get_task_queue("genesys"),
                ),
                spec=ScheduleSpec(
                    intervals=[],
                    cron_expressions=[cron],
                ),
            )

            # Check the schedule state
            schedule_state = await self.get_schedule(client, schedule_id)
            if schedule_state is None:
                # Schedule does not exist, create it
                await client.create_schedule(schedule_id, schedule)
                logger.info(
                    f"Genesys schedule '{schedule_id}' created with cron: {cron}"
                )
            elif schedule_state:
                # Schedule exists but is paused
                logger.info(f"Genesys schedule '{schedule_id}' exists but is paused.")
            else:
                # Schedule exists and is running
                logger.info(f"Genesys schedule '{schedule_id}' is already running.")

        except Exception as e:
            logger.error(f"Failed to create Genesys schedule '{schedule_id}': {str(e)}")
            raise

    async def get_schedule(self, client, schedule_id) -> bool:
        """
        Checks the Genesys schedule state.

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
                "Genesys schedule %s state: %s", schedule_id, desc.schedule.state.note
            )
            return desc.schedule.state.paused
        except Exception as e:
            if "not found" in str(e).lower():
                logger.info(f"Genesys schedule '{schedule_id}' does not exist.")
                return None
            logger.error(
                "An unexpected error occurred while getting Genesys schedule %s: %s",
                schedule_id,
                e,
            )
            raise

    async def create_or_update_schedule(
        self, schedule_id: str, cron: str, workflow: type, workflow_args: list
    ):
        """
        Create or update a Temporal schedule for Genesys workflows.

        Args:
            schedule_id: Unique ID for the schedule
            cron: Cron expression for the schedule
            workflow: Workflow class to run
            workflow_args: Arguments to pass to the workflow
        """
        try:
            client = await temporal_client_service.get_client(
                "aepc-dev-orchestration-genesys"
            )
            handle = client.get_schedule_handle(schedule_id)

            try:
                # Check if the schedule exists
                desc = await handle.describe()
                logger.info(
                    f"Genesys schedule '{schedule_id}' exists. Checking if update is needed..."
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
                        f"Genesys schedule '{schedule_id}' configuration is already up-to-date."
                    )
                else:
                    logger.info(
                        f"Genesys schedule '{schedule_id}' configuration changed. Updating..."
                    )

                    # Delete the existing schedule and create a new one
                    await handle.delete()
                    logger.info(f"Genesys schedule '{schedule_id}' deleted.")

                    # Create a new schedule with updated configuration
                    schedule = Schedule(
                        action=ScheduleActionStartWorkflow(
                            workflow=workflow,
                            args=workflow_args,
                            id=f"{schedule_id}_workflow",
                            task_queue=temporal_client_service.get_task_queue(
                                "genesys"
                            ),
                        ),
                        spec=ScheduleSpec(
                            intervals=[],
                            cron_expressions=[cron],
                        ),
                    )
                    await client.create_schedule(schedule_id, schedule)
                    logger.info(
                        f"Genesys schedule '{schedule_id}' recreated with new configuration."
                    )
            except Exception as e:
                if "not found" in str(e).lower():
                    # Schedule does not exist, create it
                    logger.info(
                        f"Genesys schedule '{schedule_id}' does not exist. Creating..."
                    )
                    schedule = Schedule(
                        action=ScheduleActionStartWorkflow(
                            workflow=workflow,
                            args=workflow_args,
                            id=f"{schedule_id}_workflow",
                            task_queue=temporal_client_service.get_task_queue(
                                "genesys"
                            ),
                        ),
                        spec=ScheduleSpec(
                            intervals=[],
                            cron_expressions=[cron],
                        ),
                    )
                    await client.create_schedule(schedule_id, schedule)
                    logger.info(
                        f"Genesys schedule '{schedule_id}' created with cron: {cron}"
                    )
                else:
                    raise

        except Exception as e:
            logger.error(
                f"Failed to create or update Genesys schedule '{schedule_id}': {str(e)}"
            )
            raise


# Global Genesys worker instance
genesys_temporal_worker = GenesysTemporalWorker()


async def main():
    """Main entry point for the Genesys worker."""

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down Genesys workers...")
        asyncio.create_task(genesys_temporal_worker.shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Fetch cron timings from the config for Genesys
        genesys_cron = config.get(
            "GENESYS_CRON", "0 */2 * * *"
        )  # Default: Every 2 hours

        # Create Genesys schedule using GenesysScheduledWorkflow as the entry point
        await genesys_temporal_worker.create_or_update_schedule(
            schedule_id="genesys_schedule",
            cron=genesys_cron,
            workflow=GenesysScheduledWorkflow,
            workflow_args=[
                {
                    "temporal_address": config.get("TEMPORAL_HOST"),
                    "namespace": config.get("TEMPORAL_NAMESPACE"),
                    "workflow_type": "GenesysScheduledWorkflow",
                    "lookback_minutes": int(
                        config.get("GENESYS_LOOKBACK_MINUTES", 360)
                    ),
                    "workflow_sets": config.get(
                        "GENESYS_WORKFLOW_SETS", ["set_a", "set_b"]
                    ),
                    "batch_size": int(config.get("GENESYS_BATCH_SIZE", 100)),
                    "api_endpoint": config.get("GENESYS_API_ENDPOINT", "/default"),
                }
            ],
        )

        await genesys_temporal_worker.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down Genesys workers...")
    except Exception as e:
        logger.error(f"Genesys worker failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
```
