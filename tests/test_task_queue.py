import threading
import time
import unittest

from utils.inference_errors import (
    InferenceErrorKind,
    InferenceErrorReport,
    InferenceRuntimeError,
)
from utils.task_queue import GenerationTask, TaskQueue, TaskStatus


class TaskQueueCancellationTests(unittest.TestCase):
    def setUp(self):
        TaskQueue._instance = None
        self.queue = TaskQueue(max_concurrent=1)

    def tearDown(self):
        self.queue.clear_all()
        TaskQueue._instance = None

    def test_running_cancel_is_terminal_and_retains_slot_until_worker_exits(self):
        first_started = threading.Event()
        release_first = threading.Event()
        second_started = threading.Event()
        events = []

        def execute(task):
            if task.prompt == "first":
                first_started.set()
                release_first.wait(2)
                return {"output_path": "late.mp4"}
            second_started.set()
            return {"output_path": "second.mp4"}

        self.queue.set_execute_function(execute)
        self.queue.on_task_complete(lambda task: events.append(("complete", task.prompt)))
        self.queue.on_task_cancel(lambda task: events.append(("cancel", task.prompt)))

        first = GenerationTask(prompt="first")
        second = GenerationTask(prompt="second")
        self.queue.add_task(first)
        self.assertTrue(first_started.wait(1))
        self.queue.add_task(second)
        self.assertTrue(self.queue.cancel_task(first.task_id))

        time.sleep(0.05)
        self.assertEqual(self.queue.get_queue_status()["running"], 1)
        self.assertFalse(second_started.is_set())

        release_first.set()
        self.assertTrue(second_started.wait(1))
        deadline = time.time() + 1
        while second.status is not TaskStatus.COMPLETED and time.time() < deadline:
            time.sleep(0.01)

        self.assertIs(first.status, TaskStatus.CANCELLED)
        self.assertIsNone(first.output_path)
        self.assertIs(second.status, TaskStatus.COMPLETED)
        self.assertEqual(events.count(("cancel", "first")), 1)
        self.assertNotIn(("complete", "first"), events)

    def test_structured_inference_error_is_captured_on_failed_task(self):
        failed = threading.Event()
        report = InferenceErrorReport(
            kind=InferenceErrorKind.CUDA_OOM,
            phase="generation",
            user_message="GPU 显存不足",
            technical_message="CUDA out of memory",
            recoverable=True,
        )

        def execute(_task):
            raise InferenceRuntimeError(report)

        self.queue.set_execute_function(execute)
        self.queue.on_task_fail(lambda _task: failed.set())
        task = GenerationTask(prompt="oom")
        self.queue.add_task(task)
        self.assertTrue(failed.wait(1))

        self.assertIs(task.status, TaskStatus.FAILED)
        self.assertEqual(task.error_message, "GPU 显存不足")
        self.assertEqual(task.error_kind, "cuda_oom")
        self.assertEqual(task.error_details["phase"], "generation")


if __name__ == "__main__":
    unittest.main()
