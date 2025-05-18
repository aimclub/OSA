from osa_tool.utils import logger


class ModeScheduler:
    def __init__(self, args):
        self.mode = args.mode
        self.args = args
        self.plan = self._select_plan()

    def _collect_active_args(self):
        return {key: value for key, value in vars(self.args).items() if value not in [None, False]}

    @staticmethod
    def _basic_plan():
        plan = {
            "generate_report": True,
            "community_docs": True,
            "generate_readme": True,
            "organize": True
        }
        return plan

    def _select_plan(self):
        active_args = self._collect_active_args()
        if self.mode == "basic":
            logger.info("Basic mode selected for task scheduler.")
            plan = self._basic_plan()

            for key, value in active_args.items():
                if key not in plan:
                    plan[key] = value
            return plan

        elif self.mode == "advanced":
            logger.info("Advanced mode selected for task scheduler.")
            return active_args

        elif self.mode == "auto":
            logger.info("Auto mode selected for task scheduler.")
            pass

        raise ValueError(f"Unsupported mode: {self.mode}")
