import unittest
from typing import get_args

from cloudcruise import EventType


class TestEventTypes(unittest.TestCase):
    def test_event_type_lists_every_event_the_api_sends_including_recovery_and_decision_required(self):
        self.assertEqual(
            sorted(get_args(EventType)),
            [
                "agent.decision_answered",
                "agent.decision_requested",
                "agent.error_analysis",
                "agent.recovery",
                "agent.tfa_setup_recovery",
                "execution.failed",
                "execution.password_recovery",
                "execution.password_updated",
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
