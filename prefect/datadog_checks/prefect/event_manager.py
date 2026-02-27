class EventManager:
    def __init__(self, event: dict):
        from .utils import _parse_time

        self.event = event

        self.id = event.get('id', '')
        self.follows = event.get('follows', '')  # the id of the event that this event follows
        self.occurred = _parse_time(self.event.get('occurred', ''), None)  # the timestamp of the event
        self.event_type = self.event.get('event', '')  # e.g. "prefect.task-run.Completed"
        self.event_state_type = self.event_type.split('.')[-1]  # e.g. "Completed"

        self.resource = event.get('resource') or {}
        self.resource_id_parts = self.resource.get('prefect.resource.id', '').split(
            '.'
        )  # e.g. "prefect.task-run.019bc69e-7438-7f35-a011-26ce615b1e7d"
        self.resource_type = (
            '.'.join(self.resource_id_parts[1:-1]) if self.resource_id_parts else ''
        )  # e.g. "task-run", "docker.container"
        self.resource_id = (
            self.resource_id_parts[-1] if self.resource_id_parts else ''
        )  # e.g. "019bc69e-7438-7f35-a011-26ce615b1e7d"
        self.state_name = self.resource.get('prefect.state-name', '')  # e.g. "AwaitingRetry"
        self.state_type = self.resource.get('prefect.state-type', '')  # e.g. "SCHEDULED"
        self.resource_name = self.resource.get('prefect.resource.name', '')  # e.g. "task-run-1234"
        self.resource_message = self.resource.get('prefect.state-message', '')  # e.g. "Error 123"

        self.payload = event.get('payload') or {}
        self.intended_state_type = (self.payload.get('intended') or {}).get('to', '')  # e.g. "RUNNING"
        self.initial_state = self.payload.get('initial_state') or {}
        self.initial_state_message = self.initial_state.get('message', '')  # e.g. "Error 123"
        self.initial_state_name = self.initial_state.get('name', '')  # e.g. "AwaitingRetry"
        self.initial_state_type = self.initial_state.get('type', '')  # e.g. "SCHEDULED"

    @property
    def event_related(self) -> dict:
        related_raw = self.event.get('related', [])
        related = {}
        for r in related_raw:
            role = r.get('prefect.resource.role')
            if role:
                related[role] = {
                    'id': r.get('prefect.resource.id', '').split('.')[-1],
                    'name': r.get('prefect.resource.name', ''),
                }
        return related

    @property
    def tags(self) -> list[str]:
        tags = [
            f"resource_name:{self.resource_name}",
            f"resource_id:{self.resource_id}",
            f"state_type:{self.state_type}",
            f"initial_state_type:{self.initial_state_type}",
            f"intended_state_type:{self.intended_state_type}",
        ]
        for role, val in self.event_related.items():
            tags.append(f"{role}_id:{val.get('id', '')}")
            tags.append(f"{role}_name:{val.get('name', '')}")
        return tags

    @property
    def flow_tags(self) -> list[str]:
        if self.event_type.startswith('prefect.flow-run') or self.event_type.startswith('prefect.task-run'):
            return [
                f"work_pool_id:{self.event_related.get('work-pool', {}).get('id')}",
                f"work_pool_name:{self.event_related.get('work-pool', {}).get('name')}",
                f"work_queue_id:{self.event_related.get('work-queue', {}).get('id')}",
                f"work_queue_name:{self.event_related.get('work-queue', {}).get('name')}",
                f"deployment_id:{self.event_related.get('deployment', {}).get('id')}",
                f"deployment_name:{self.event_related.get('deployment', {}).get('name')}",
                f"flow_id:{self.event_related.get('flow', {}).get('id')}",
            ]
        else:
            return []

    @property
    def task_tags(self) -> list[str]:
        if self.event_type.startswith('prefect.task-run'):
            return self.flow_tags + [
                f"task_key:{self.payload.get('task_run', {}).get('task_key')}",
            ]
        else:
            return []

    @property
    def task_run_dependencies(self) -> list[str]:
        if not self.event_type.startswith("prefect.task-run"):
            return []
        task_inputs = self.payload.get("task_run", {}).get("task_inputs", {})
        dependencies: list[str] = []
        for arguments in task_inputs.values():
            if isinstance(arguments, list):
                dependencies.extend(
                    arg.get("id") for arg in arguments if arg.get("id") and arg.get("input_type") == "task_run"
                )
            elif isinstance(arguments, dict) and "data" in arguments:
                dependencies.extend(
                    arg.get("id")
                    for arg in arguments.get("data", [])
                    if arg.get("id") and arg.get("input_type") == "task_run"
                )
        return dependencies

    @property
    def message(self) -> str:
        if self.event_type.startswith('prefect.flow-run') or self.event_type.startswith('prefect.task-run'):
            run_count = self.resource.get('prefect.run-count') or self.payload.get('task_run', {}).get('run_count')
            message = (
                f"{self.resource_type} went from {self.initial_state_name} to {self.state_name}\n"
                f"Resource ID: {self.resource_id}\n"
                f"Resource Name: {self.resource_name}\n"
            )

            if run_count:
                message += f"Run count: {run_count}\n"

            if self.initial_state_message:
                message += f"Initial message: {self.initial_state_message}\n"

            if self.resource_message:
                message += f"Message: {self.resource_message}\n"

        else:
            message = f"{self.resource_type} {self.resource_name} with id {self.resource_id} {self.event_state_type}\n"
        return message

    @property
    def msg_title(self) -> str:
        return f"[{self.resource_type}] {self.resource_name} -> {self.event_state_type}"

    @property
    def alert_type(self) -> str:
        if (
            "Failed" in self.event_state_type
            or "Crashed" in self.event_state_type
            or "not-ready" in self.event_state_type
            or "AwaitingRetry" in self.event_state_type
        ):
            return "error"
        else:
            return "info"
