import unittest
from typing import get_args

from cloudcruise import EventType


class TestEventTypes(unittest.TestCase):
    def test_event_type_lists_the_decision_required_events_and_not_the_removed_execution_input_required(self):
        self.assertEqual(
            sorted(get_args(EventType)),
            [
                "agent.decision_answered",
                "agent.decision_requested",
                "agent.error_analysis",
                "execution.failed",
                "execution.paused",
                "execution.queued",
                "execution.requeued",
                "execution.start",
                "execution.step",
                "execution.stopped",
                "execution.success",
                "file.uploaded",
                "interaction.failed",
                "interaction.finished",
                "interaction.waiting",
                "screenshot.uploaded",
                "video.uploaded",
            ],
        )


if __name__ == "__main__":
    unittest.main()
