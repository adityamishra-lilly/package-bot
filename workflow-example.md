```python
GENESYS_TASK_QUEUE = "genesys-task-queue"
DEFAULT_DOWNLOAD_CONCURRENCY = 5

# Retry policy constants for activities
AUTH_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=10),
    maximum_attempts=3,
)

CONVERSATIONS_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=5,
)

FILTER_CONVERSATIONS_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=10),
    maximum_attempts=3,
)

RECORDING_DETAILS_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=5,
)

DOWNLOAD_RECORDINGS_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=3,
)

SAVE_METADATA_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=3,
)

TRANSCRIPTION_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=3,
)

ORCHESTRATE_BUILD_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=10),
    maximum_attempts=3,
)

ORCHESTRATE_CALL_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=3,
)

INTERVAL_GENERATION_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=5),
    maximum_attempts=3,
)

# Type aliases for improved readability
WorkflowPayload = Dict[str, Any]
WorkflowResult = Dict[str, Any]


# ============================================================================
# Set A Child Workflow
# ============================================================================


@workflow.defn
class GenesysWorkflowSetA:
    """Child workflow for handling Set A Genesys tasks (activities 1-4)."""

    @workflow.run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Set A Genesys activities in sequence:
        1. Get authentication token
        2. Get conversations data
        3. Execute activities 1-4 with the conversations data

        Args:
            input_data: Input data containing:
                - interval: Time interval for conversations (required)
                - auth_config: Optional auth configuration
                - workflow_id: Workflow identifier

        Returns:
            Dictionary containing Set A workflow results with task_results array
        """

        workflow.logger.info(
            f"Starting Genesys Set A workflow with input: {input_data}"
        )

        workflow_id = input_data.get("workflow_id", "genesys-set-a")
        interval = input_data.get("interval")
        auth_config = input_data.get("auth_config", {})

        if not interval:
            raise ValueError("Missing required parameter: interval")

        results = {
            "workflow_id": workflow_id,
            "workflow_set": "set_a",
            "status": "success",
            "task_results": [],
            "auth_info": None,
            "conversations_info": None,
        }

        # Step 1: Get authentication token
        workflow.logger.info("Step 1: Getting Genesys authentication token")
        auth_result = await workflow.execute_activity(
            "genesys_auth_activity",
            auth_config,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
                maximum_attempts=3,
            ),
        )

        # Validate auth activity result
        if auth_result.get("status") not in {"success", "SUCCESS", "COMPLETED"}:
            raise exceptions.ApplicationError(
                f"genesys_auth_activity returned error status: {auth_result.get('status')}"
            )

        results["auth_info"] = {
            "generated_at": auth_result["generated_at"],
            "token_type": auth_result["token_type"],
            "status": auth_result["status"],
        }
        workflow.logger.info("Authentication completed successfully")

        # Step 2: Use token to get conversations
        workflow.logger.info(f"Step 2: Getting conversations for interval: {interval}")
        conversations_payload = {
            "access_token": auth_result["access_token"],
            "interval": interval,
        }

        conversations_result = await workflow.execute_activity(
            "get_conversations_activity",
            conversations_payload,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=2),
                maximum_interval=timedelta(seconds=30),
                maximum_attempts=5,
            ),
        )

        # Validate conversations activity result
        if conversations_result.get("status") not in {
            "success",
            "SUCCESS",
            "COMPLETED",
        }:
            raise exceptions.ApplicationError(
                f"get_conversations_activity returned error status: {conversations_result.get('status')}"
            )

        results["conversations_info"] = {
            "interval": conversations_result["interval"],
            "count": conversations_result["count"],
            "processed_at": conversations_result["processed_at"],
            "status": conversations_result["status"],
        }
        workflow.logger.info(
            f"Conversations retrieval completed with {conversations_result.get('count', 0)} conversations"
        )

        # Step 2.1: Filter completed conversations
        workflow.logger.info("Step 2.1: Filtering completed conversations")
        filter_payload = {"conversations": conversations_result["conversations"]}
        filtered_conversations = await workflow.execute_activity(
            "filter_completed_conversations_activity",
            filter_payload,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
                maximum_attempts=3,
            ),
        )
        workflow.logger.info(
            f"Filtered {len(filtered_conversations['conversation_ids'])} completed conversations"
        )

        if len(filtered_conversations["conversation_ids"]) == 0:
            workflow.logger.info(
                "No completed conversations found, skipping further processing"
            )
            results["status"] = "no_completed_conversations"
            return results

        # Step 2.2: Fetch conversation details in parallel
        workflow.logger.info("Step 2.2: Fetching conversation details in parallel")
        details_payload = {
            "conversation_ids": filtered_conversations["conversation_ids"],
            "access_token": auth_result["access_token"],
            "concurrency": 10,
        }
        conversation_details = await workflow.execute_activity(
            "get_multiple_conversation_recording_details_activity",
            details_payload,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=2),
                maximum_interval=timedelta(seconds=30),
                maximum_attempts=5,
            ),
        )
        workflow.logger.info(
            f"In activity Fetched details for {len(conversation_details['success'])} conversations, {len(conversation_details['failed'])} failed"
        )

        # Step 2.3: Download and save recordings to S3
        workflow.logger.info("Step 2.3: Downloading and saving recordings to S3")
        s3_bucket_name = config.get("GENESYS_RECORDINGS_S3_BUCKET")

        if s3_bucket_name and conversation_details.get("conversations"):
            download_payload = {
                "conversations": conversation_details["conversations"],
                "access_token": auth_result["access_token"],
                "s3_bucket_name": s3_bucket_name,
                "concurrency": input_data.get("download_concurrency", 5),
            }

            download_result = await workflow.execute_activity(
                "download_and_save_recordings_activity",
                download_payload,
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    maximum_interval=timedelta(seconds=60),
                    maximum_attempts=3,
                ),
            )

            results["recording_downloads"] = {
                "successful": download_result.get("success", []),
                "failed": download_result.get("failed", []),
                "status": "completed",
            }
            if download_result.get("success", []):
                save_data = await workflow.execute_activity(
                    "save_recording_metadata_activity",
                    download_result.get("success", []),
                    start_to_close_timeout=timedelta(minutes=10),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=2),
                        maximum_interval=timedelta(seconds=30),
                        maximum_attempts=3,
                    ),
                )
                workflow.logger.info(
                    f"Saved metadata for {save_data.get('saved_count', 0)} recordings"
                )
            workflow.logger.info(
                f"Downloaded and saved {len(download_result.get('success', []))} recordings, "
                f"{len(download_result.get('failed', []))} failed"
            )
        else:
            if not s3_bucket_name:
                workflow.logger.warning(
                    "S3 bucket name not provided, skipping recording downloads"
                )
            else:
                workflow.logger.warning("No conversations to download recordings for")
            results["recording_downloads"] = {
                "successful": 0,
                "failed": 0,
                "status": "skipped",
                "reason": (
                    "No S3 bucket configured"
                    if not s3_bucket_name
                    else "No conversations"
                ),
            }

        workflow.logger.info(
            f"Genesys Set A workflow completed with {len(results['task_results'])} results"
        )
        return results


@workflow.defn
class GenesysWorkflowSetB:
    """Child workflow for handling Set B Genesys tasks based on conversation items from set A"""

    @workflow.run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Set B Genesys activities in sequence for a specific SetA result item.

        Args:
            input_data: Input data containing:
                - workflow_id: Unique workflow identifier
                - set_a_result_item: Specific result item from SetA that this instance should process
                - item_index: Index of the item being processed

        Returns:
            Dictionary containing Set B workflow results
        """

        workflow.logger.info(
            f"Starting Genesys Set B workflow with input: {input_data}"
        )

        transaction_id = workflow.uuid4()

        workflow_id = input_data.get("workflow_id", "genesys-set-b")
        set_a_result_item = input_data.get("set_a_result_item", {})
        item_index = input_data.get("item_index", 0)

        results = {
            "workflow_id": workflow_id,
            "workflow_set": "set_b",
            "item_index": item_index,
            "set_a_result_item": set_a_result_item,
            "status": "success",
            "task_results": [],
        }

        transcription_data = []

        workflow.logger.info(f"Set B processing item {item_index}")
        conversation_id = set_a_result_item[0].get("conversation_id", "unknown")

        # Loop through each item in set_a_result_item array and call transcription activity
        for item in set_a_result_item:
            workflow.logger.info(
                f"Processing transcription for item: {item.get('recording_id', 'unknown')}"
            )
            transcription_input = {
                "configuration_item": "CI00000015932620",
                "source_system_reference_id": transaction_id,
                "audio_url": item.get("pre_signed_url", ""),
                "conversation_id": conversation_id,
                "recording_id": item.get("recording_id", ""),
            }

            transcription_result = await workflow.execute_activity(
                "transcription_activity",
                transcription_input,
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=2),
                    maximum_interval=timedelta(seconds=30),
                    maximum_attempts=3,
                ),
            )

            # Validate transcription result
            if transcription_result.get("status") not in {
                "COMPLETED",
                "success",
                "SUCCESS",
            }:
                workflow.logger.error(
                    f"Transcription failed for item {item.get('recording_id', 'unknown')}: "
                    f"status={transcription_result.get('status')}"
                )
                raise exceptions.ApplicationError(
                    f"transcription_activity returned error status: {transcription_result.get('status')}"
                )

            transcription_conv_result = transcription_result.get(
                "transcription_response", {}
            )

            results["task_results"].append(
                {
                    "activity": "transcription_activity",
                    "item": item,
                    "result": transcription_conv_result,
                    "status": "success",
                }
            )
            transcription_data.append(transcription_conv_result)

            workflow.logger.info(
                f"Transcription completed for recording: {item.get('recording_id', 'unknown')}"
            )

        # Use transcription_data to create a conversation and call the Orchestrate API activity

        build_request_payload = {
            "transcription_data": transcription_data,
            "conversation_id": conversation_id,
        }

        orchestrate_input = await workflow.execute_activity(
            "build_orchestrate_conversation_request_activity",
            build_request_payload,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
                maximum_attempts=3,
            ),
        )

        workflow.logger.info(
            f"Orchestrating conversation for transcription ID: {transaction_id}"
        )
        orchestrate_result = await workflow.execute_activity(
            "call_orchestrate_api_activity",
            orchestrate_input,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=2),
                maximum_interval=timedelta(seconds=30),
                maximum_attempts=3,
            ),
        )

        # Validate orchestrate result
        if not orchestrate_result.get("transaction_id"):
            workflow.logger.error(
                f"Orchestration failed for workflow transcription ID {transaction_id}: "
                f"status={orchestrate_result.get('status')}"
            )
            raise exceptions.ApplicationError(
                f"call_orchestrate_api_activity returned error status: {orchestrate_result.get('status')}"
            )

        results["task_results"].append(
            {
                "activity": "call_orchestrate_api_activity",
                "transcription_id": transaction_id,
                "result": orchestrate_result,
                "status": "success",
            }
        )
        workflow.logger.info(
            f"Orchestration completed for transcription ID: {transaction_id}"
        )

        workflow.logger.info(
            f"Genesys Set B workflow completed for item {item_index}: {results}"
        )
        return results


@workflow.defn
class GenesysWorkflow:
    """Parent workflow that executes SetA first, then spawns multiple SetB instances based on SetA results."""

    @workflow.run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the dynamic Genesys workflow:
        1. Execute GenesysWorkflowSetA and await completion
        2. Extract task_results from SetA response
        3. Spawn N GenesysWorkflowSetB instances (one per SetA result item)
        4. All SetB instances run in parallel (fire-and-forget)

        Args:
            input_data: Input data containing workflow configuration and parameters

        Returns:
            Dictionary containing SetA results and summary of spawned SetB instances
        """

        workflow.logger.info(
            f"Starting Genesys dynamic parent workflow with input: {input_data}"
        )

        workflow_id = input_data.get("workflow_id", "genesys-dynamic-workflow")

        parent_results = {
            "workflow_id": workflow_id,
            "status": "success",
            "set_a_result": None,
            "set_b_instances_spawned": 0,
            "set_b_workflow_ids": [],
            "execution_summary": {},
        }

        # STEP 1: Generate interval using activity and execute GenesysWorkflowSetA
        workflow.logger.info(
            "Generating interval and executing GenesysWorkflowSetA first..."
        )

        try:
            # Generate interval using deterministic activity
            interval_payload = input_data.get("interval_config", {})
            set_interval = await workflow.execute_activity(
                "generate_interval_activity",
                interval_payload,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=5),
                    maximum_attempts=3,
                ),
            )

            input_data["interval"] = set_interval  # Ensure interval is set
            set_a_input = {"workflow_id": f"{workflow_id}-set-a", **input_data}

            set_a_result = await workflow.execute_child_workflow(
                GenesysWorkflowSetA.run,
                set_a_input,
                id=f"genesys-set-a-{workflow.info().workflow_id}",
                task_queue="genesys-task-queue",
            )

            parent_results["set_a_result"] = set_a_result
            workflow.logger.info(
                f"GenesysWorkflowSetA completed successfully with {len(set_a_result.get('task_results', []))} results"
            )

        except Exception as e:
            workflow.logger.error(
                f"GenesysWorkflow failed during interval generation or SetA: {str(e)}"
            )
            raise

        # Validate SetA status - should only return "success" or "no_completed_conversations" after our changes
        set_a_status = set_a_result.get("status")
        if set_a_status not in {"success", "no_completed_conversations"}:
            workflow.logger.error(f"Unexpected SetA status: {set_a_status}")
            raise exceptions.ApplicationError(f"Unexpected SetA status: {set_a_status}")

        # Check if SetA completed successfully and has recordings to process
        if set_a_status != "success":
            workflow.logger.info(
                f"SetA returned status '{set_a_status}' - skipping SetB execution"
            )
            parent_results["execution_summary"] = {
                "set_a_status": set_a_status,
                "set_b_instances_spawned": 0,
                "message": "SetA did not complete with success status",
            }
            return parent_results

        recording_downloads = set_a_result.get("recording_downloads", {})
        if recording_downloads.get(
            "status"
        ) != "completed" or not recording_downloads.get("successful"):
            workflow.logger.warning(
                "No successful recording downloads from SetA - skipping SetB execution"
            )
            parent_results["execution_summary"] = {
                "set_a_status": "success",
                "set_b_instances_spawned": 0,
                "message": "No successful recording downloads to process",
            }
            return parent_results

        # Group successful uploads by conversation_id for SetB processing
        workflow.logger.info(
            "Spawning GenesysWorkflowSetB instances for recording processing"
        )
        successful_uploads = recording_downloads.get("successful", [])
        grouped_conversation_upload_details = {}
        for upload in successful_uploads:
            conv_id = upload.get("conversation_id")
            if conv_id:
                if conv_id not in grouped_conversation_upload_details:
                    grouped_conversation_upload_details[conv_id] = []
                grouped_conversation_upload_details[conv_id].append(upload)

        # Spawn SetB child workflows (fire-and-forget, so SetB failures don't fail parent)
        for index, conv_id in enumerate(grouped_conversation_upload_details.keys()):
            set_b_workflow_id = f"genesys-set-b-{index}-{workflow.info().workflow_id}"
            set_b_input = {
                "workflow_id": set_b_workflow_id,
                "set_a_result_item": grouped_conversation_upload_details[conv_id],
                "item_index": index,
            }

            # Fire-and-forget SetB child workflow (don't await)
            await workflow.execute_child_workflow(
                GenesysWorkflowSetB.run,
                set_b_input,
                id=set_b_workflow_id,
                task_queue="genesys-task-queue",
            )
            parent_results["set_b_workflow_ids"].append(set_b_workflow_id)
            workflow.logger.info(f"Spawned SetB workflow: {set_b_workflow_id}")

        parent_results["set_b_instances_spawned"] = len(
            parent_results["set_b_workflow_ids"]
        )

        parent_results["execution_summary"] = {
            "set_a_status": set_a_status,
            "set_b_instances_spawned": parent_results["set_b_instances_spawned"],
            "execution_pattern": "Sequential SetA → Fire-and-forget SetB",
            "message": f"Spawned {parent_results['set_b_instances_spawned']} SetB workflow instances",
        }

        workflow.logger.info(
            f"Genesys dynamic workflow completed: {parent_results['execution_summary']}"
        )
        return parent_results


@workflow.defn
class GenesysScheduledWorkflow:
    """Scheduled workflow for running Genesys tasks on a schedule."""

    @workflow.run
    async def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute scheduled Genesys tasks by calling the dynamic GenesysWorkflow.

        Args:
            config: Configuration for the scheduled workflow

        Returns:
            Dictionary containing workflow results from dynamic workflow
        """
        workflow.logger.info(
            f"Starting scheduled Genesys workflow with config: {config}"
        )

        # Create workflow input for the dynamic workflow
        workflow_input = {
            "workflow_id": f"scheduled-genesys-{workflow.info().workflow_id}",
            "source": "scheduled",
            "config": config,
        }

        workflow.logger.info("Calling dynamic GenesysWorkflow...")

        # Execute the dynamic Genesys workflow
        return await workflow.execute_child_workflow(
            GenesysWorkflow.run,
            workflow_input,
            id=f"genesys-dynamic-{workflow.info().workflow_id}",
            task_queue="genesys-task-queue",
        )
```
