from unittest.mock import patch
from app.workers.tasks import process_job_task


def test_process_job_task():
    with patch("app.workers.tasks.process_job") as mock_process:
        process_job_task("test-job-uuid-1234")
        mock_process.assert_called_once()
        args, _ = mock_process.call_args
        assert args[1] == "test-job-uuid-1234"
