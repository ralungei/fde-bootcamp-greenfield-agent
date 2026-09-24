"""Normalize how every agent chooses between OTP and PIN: ask first, one global rule."""
import pathlib, re, json

APP = pathlib.Path("/Users/rasalungei/Documents/2026/GECX Bootcamp/ras-fde-bootcamp-greenfield-agent/cxas_app/ras-_FDE-bootcamp_-greenfield-agent")
EVALS = APP.parent.parent / "evals/goldens/goldens.yaml"

# 1) Global rule 5: single method-choice rule for all agents
g = APP / "global_instruction.txt"
n=5
