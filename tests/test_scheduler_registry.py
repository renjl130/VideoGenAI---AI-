import pytest
from diffusers import FlowMatchEulerDiscreteScheduler, UniPCMultistepScheduler

from utils.scheduler_registry import (
    SchedulerType,
    create_wan_scheduler,
    list_schedulers,
)


def test_registry_order_and_default_preserve_existing_unipc_behavior():
    schedulers = list_schedulers()

    assert [item.scheduler_type for item in schedulers] == [
        SchedulerType.UNIPC,
        SchedulerType.FLOW_MATCH_EULER,
    ]
    assert SchedulerType.parse(None) is SchedulerType.UNIPC


def test_unipc_factory_configures_wan_flow_prediction():
    scheduler = create_wan_scheduler(SchedulerType.UNIPC, flow_shift=3.0)

    assert isinstance(scheduler, UniPCMultistepScheduler)
    assert scheduler.config.prediction_type == "flow_prediction"
    assert scheduler.config.use_flow_sigmas is True
    assert scheduler.config.flow_shift == 3.0
    assert scheduler.config.num_train_timesteps == 1000


def test_flow_match_euler_factory_uses_model_flow_shift():
    scheduler = create_wan_scheduler("flow_match_euler", flow_shift=5.0)

    assert isinstance(scheduler, FlowMatchEulerDiscreteScheduler)
    assert scheduler.config.shift == 5.0
    assert scheduler.config.num_train_timesteps == 1000


def test_invalid_scheduler_and_flow_shift_are_rejected():
    with pytest.raises(ValueError, match="Unknown scheduler"):
        SchedulerType.parse("made_up")
    with pytest.raises(ValueError, match="flow_shift must be greater than zero"):
        create_wan_scheduler(SchedulerType.UNIPC, flow_shift=0)
