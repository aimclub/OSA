"""Snapshot manager for creating and managing Git snapshots."""

import subprocess
from pathlib import Path
from datetime import datetime

from osa_tool.utils.logger import logger


class SnapshotManager:
    """
    Manages repository snapshots using a temporary Git branch.

    Creates a temporary branch to capture the current state (including uncommitted changes)
    before reorganization. After reorganization, it can transfer the changes back to the
    original branch without automatically committing them, allowing the user to review.
    """

    def __init__(self, base_path: Path):
        """
        Initialize the snapshot manager.

        Args:
            base_path: Root directory path of the Git repository
        """
        self.base_path = base_path
        self.original_branch = None
        self.temp_branch = f"osa-temp-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.temp_branch_head = None
        self.original_stash_ref = None

    def create_snapshot(self) -> bool:
        """
        Create a snapshot of the current repository state in a temporary branch.

        Creates a new branch, stages all changes (including uncommitted work),
        and commits them to create a snapshot point.

        Returns:
            bool: True if snapshot created successfully, False otherwise
        """
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"], cwd=self.base_path, capture_output=True, text=True, check=True
            )
            self.original_branch = result.stdout.strip()

            status = subprocess.run(
                ["git", "status", "--porcelain"], cwd=self.base_path, capture_output=True, text=True, check=True
            )
            has_local_changes = bool(status.stdout.strip())
            if has_local_changes:
                subprocess.run(
                    ["git", "stash", "push", "--include-untracked", "-m", "OSA Tool: preserved local changes"],
                    cwd=self.base_path,
                    check=True,
                    capture_output=True,
                )
                stash_ref = subprocess.run(
                    ["git", "stash", "list", "--format=%gd", "-n", "1"],
                    cwd=self.base_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.original_stash_ref = stash_ref.stdout.strip() or None

            subprocess.run(
                ["git", "checkout", "-b", self.temp_branch], cwd=self.base_path, check=True, capture_output=True
            )

            if self.original_stash_ref:
                subprocess.run(
                    ["git", "stash", "apply", self.original_stash_ref],
                    cwd=self.base_path,
                    check=True,
                    capture_output=True,
                )

            if has_local_changes:
                subprocess.run(["git", "add", "-A"], cwd=self.base_path, check=True, capture_output=True)
                subprocess.run(
                    ["git", "commit", "-m", "OSA Tool: pre-reorganization snapshot"],
                    cwd=self.base_path,
                    check=True,
                    capture_output=True,
                )

            head = subprocess.run(
                ["git", "rev-parse", "--verify", "HEAD"],
                cwd=self.base_path,
                capture_output=True,
                text=True,
                check=True,
            )
            self.temp_branch_head = head.stdout.strip()

            logger.info("Snapshot created in temporary branch: %s", self.temp_branch)
            return True

        except subprocess.CalledProcessError as e:
            if self.original_stash_ref:
                try:
                    subprocess.run(
                        ["git", "stash", "pop", self.original_stash_ref],
                        cwd=self.base_path,
                        check=True,
                        capture_output=True,
                    )
                    self.original_stash_ref = None
                except subprocess.CalledProcessError as restore_error:
                    logger.error("Failed to restore stashed local changes after snapshot failure: %s", restore_error.stderr)
            logger.error("Git snapshot creation failed: %s", e.stderr)
            return False

    def transfer_changes(self) -> bool:
        """
        Transfer changes from the temporary branch back to the original branch.

        Performs a squash merge of the temporary branch into the original branch,
        staging all changes but not committing them, allowing user review.

        Returns:
            bool: True if transfer succeeded, False otherwise
        """
        if not self.original_branch:
            logger.error("No original branch to return to")
            return False

        try:
            logger.info("Merging changes from %s into %s (squashed)", self.temp_branch, self.original_branch)

            temp_ref = subprocess.run(
                ["git", "rev-parse", "--verify", f"refs/heads/{self.temp_branch}"],
                cwd=self.base_path,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            self.temp_branch_head = temp_ref or self.temp_branch_head

            subprocess.run(
                ["git", "checkout", self.original_branch], cwd=self.base_path, check=True, capture_output=True
            )

            subprocess.run(
                ["git", "merge", "--squash", self.temp_branch_head],
                cwd=self.base_path,
                check=True,
                capture_output=True,
            )

            subprocess.run(
                ["git", "branch", "-D", self.temp_branch], cwd=self.base_path, check=True, capture_output=True
            )

            if self.original_stash_ref:
                subprocess.run(
                    ["git", "stash", "drop", self.original_stash_ref],
                    cwd=self.base_path,
                    check=True,
                    capture_output=True,
                )
                self.original_stash_ref = None

            logger.info("Changes staged in %s.", self.original_branch)
            return True

        except subprocess.CalledProcessError as e:
            logger.error("Git operation failed: %s", e.stderr)
            return False

    def rollback(self) -> bool:
        """
        Rollback to the original branch and delete the temporary branch.

        Returns to the original branch without applying any changes from
        the temporary branch.

        Returns:
            bool: True if rollback succeeded, False otherwise
        """
        if not self.original_branch:
            logger.error("No original branch to return to")
            return False

        try:
            subprocess.run(
                ["git", "checkout", self.original_branch], cwd=self.base_path, check=True, capture_output=True
            )

            subprocess.run(
                ["git", "branch", "-D", self.temp_branch], cwd=self.base_path, check=True, capture_output=True
            )

            if self.original_stash_ref:
                subprocess.run(
                    ["git", "stash", "pop", self.original_stash_ref],
                    cwd=self.base_path,
                    check=True,
                    capture_output=True,
                )
                self.original_stash_ref = None

            logger.info("Rollback successful - returned to branch %s", self.original_branch)
            return True

        except subprocess.CalledProcessError as e:
            logger.error("Git rollback failed: %s", e.stderr)
            return False
