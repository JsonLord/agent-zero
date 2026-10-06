from helpers.extension import Extension
from plugins._goal.tools import goal


class ReconcileGoals(Extension):
    """Conservatively reconcile durable goals after framework startup."""

    def execute(self, **kwargs):
        return goal.reconcile_persisted_goals()
