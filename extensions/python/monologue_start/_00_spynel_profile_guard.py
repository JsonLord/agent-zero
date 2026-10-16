"""Prevent persistent user/project instructions from silently shadowing Spynel."""

from helpers.errors import HandledException
from helpers.extension import Extension


class SpynelProfileGuard(Extension):
    async def execute(self, **kwargs):
        if not self.agent or self.agent.config.profile != "spynel":
            return
        from scripts.spynel_resolver import profile_override_conflicts

        if not profile_override_conflicts(self.agent):
            return
        message = (
            "Spynel routing is blocked because active profile overrides differ from the bundled routing contract. "
            "Run python scripts/spynel_resolver.py --check-profile, review and back up the listed files, "
            "then reconcile them explicitly. Existing user files have not been changed."
        )
        self.agent.context.log.log(type="error", content=message)
        raise HandledException(message)
