"""Validated scheduler registry for Wan inference pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SchedulerType(Enum):
    """Schedulers supported by the current Wan engine."""

    UNIPC = "unipc"
    FLOW_MATCH_EULER = "flow_match_euler"

    @classmethod
    def parse(cls, value: str | None) -> SchedulerType:
        """Parse a persisted/user value and report valid choices on failure."""
        try:
            return cls(value or cls.UNIPC.value)
        except ValueError as error:
            choices = ", ".join(item.value for item in cls)
            raise ValueError(f"Unknown scheduler: {value}. Choose: {choices}") from error


@dataclass(frozen=True)
class SchedulerInfo:
    """Stable metadata exposed to configuration and UI layers."""

    scheduler_type: SchedulerType
    display_name: str
    description: str


SCHEDULER_REGISTRY: dict[SchedulerType, SchedulerInfo] = {
    SchedulerType.UNIPC: SchedulerInfo(
        scheduler_type=SchedulerType.UNIPC,
        display_name="UniPC Multistep",
        description="Existing VideoGenAI default; a fast multistep flow-prediction solver.",
    ),
    SchedulerType.FLOW_MATCH_EULER: SchedulerInfo(
        scheduler_type=SchedulerType.FLOW_MATCH_EULER,
        display_name="FlowMatch Euler",
        description="Diffusers Wan pipeline default; conservative Euler flow matching.",
    ),
}


def list_schedulers() -> tuple[SchedulerInfo, ...]:
    """Return scheduler metadata in deterministic UI order."""
    return tuple(SCHEDULER_REGISTRY[item] for item in SchedulerType)


def create_wan_scheduler(scheduler: SchedulerType | str, flow_shift: float) -> Any:
    """Create a scheduler configured for the current Wan flow-prediction model."""
    scheduler_type = (
        scheduler if isinstance(scheduler, SchedulerType) else SchedulerType.parse(scheduler)
    )
    if flow_shift <= 0:
        raise ValueError("flow_shift must be greater than zero")

    if scheduler_type is SchedulerType.UNIPC:
        from diffusers import UniPCMultistepScheduler

        return UniPCMultistepScheduler(
            prediction_type="flow_prediction",
            use_flow_sigmas=True,
            num_train_timesteps=1000,
            flow_shift=flow_shift,
        )

    if scheduler_type is SchedulerType.FLOW_MATCH_EULER:
        from diffusers import FlowMatchEulerDiscreteScheduler

        return FlowMatchEulerDiscreteScheduler(
            num_train_timesteps=1000,
            shift=flow_shift,
        )

    # Enum exhaustiveness guard for future registry additions.
    raise ValueError(f"Unsupported scheduler: {scheduler_type.value}")
