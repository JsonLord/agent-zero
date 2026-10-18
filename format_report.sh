#!/usr/bin/env bash

cat << 'REPORT'
SOURCE
  deployed SHA: 1cd0489b8a5236bc1aaafbf7de01a93842d71896
  exact match: PASS

AGENT CARD
  general_assistance: PASS
  argus_supervisor_health: FAIL
  argus_supervisor_status: FAIL
  argus_campaign_list: FAIL
  argus_campaign_control: FAIL

ARGUS READS
  supervisor.health: PASS
  supervisor.status: PASS
  campaign.list: PASS

DETERMINISTIC PATH
  health no AgentContext: PASS
  status no AgentContext: PASS
  campaign.list no AgentContext: PASS
  zero LLM reads: PASS

REGRESSION
  general A2A: PASS
  malformed extension: PASS
  unknown operation: PASS
  missing auth: PASS
  wrong auth: PASS

VERDICT
  ARGUS A2A FAIL

BLOCKERS
  Agent profile 'argus-supervisor' is missing/not enabled so deterministic path returns {"ok":false,"error":"Argus Supervisor is not enabled on this agent."}.
  Agent card skills/extensions do not list Argus campaign control skills because plugin is not installed/enabled.
REPORT
