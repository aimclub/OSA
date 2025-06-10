import json
import os
import tempfile
import time
import uuid

from osa_tool.utils import logger


class WebPlanEditor:
    """
    Utility class for converting task plans for web interface and applying updates.
    """

    def __init__(self, plan: dict):
        self.plan = plan
        self.file_path = os.path.join(tempfile.gettempdir(), f"osa_plan_{uuid.uuid4().hex}.json")
        os.environ["OSA_PLAN_PATH"] = self.file_path
        self.save_plan()

    def save_plan(self) -> None:
        """
        Save the current plan dictionary to the JSON file.
        """
        with open(self.file_path, "w") as f:
            json.dump(self.plan, f, indent=4)

    def get_updated_plan(self) -> dict:
        """
        Load the plan dictionary from the JSON file.

        Returns:
            dict: The updated plan loaded from the file.
        """
        self._wait_for_update()

        with open(self.file_path, "r") as f:
            self.plan = json.load(f)
        os.remove(self.file_path)

        return self.plan

    def get_plan_path(self) -> str:
        """
        Get the file path of the temporary plan JSON file.

        Returns:
            str: Full path to the plan file.
        """
        return self.file_path

    def _wait_for_update(self, timeout=600):
        """
        Wait for the plan file to be updated by monitoring its modification time.
        Raises a TimeoutError if the file is not modified within the timeout period.

        Args:
            timeout (optional): Number of seconds to wait before timing out. Defaults to 600.

        Raises:
            TimeoutError: If no update detected within the timeout period.
        """
        logger.info("Waiting for web interface to update the plan...")
        last_mtime = os.path.getmtime(self.file_path)
        start_time = time.time()

        while time.time() - start_time < timeout:
            current_mtime = os.path.getmtime(self.file_path)
            if current_mtime != last_mtime:
                logger.info("Plan updated by web interface.")
                return
            time.sleep(1)

        raise TimeoutError("Timeout waiting for web interface to update the plan.")
