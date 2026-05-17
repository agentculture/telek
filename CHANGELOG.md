# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-05-18

### Added

- Initial sibling-scaffold per [agentculture/telek#1](https://github.com/agentculture/telek/issues/1):
  Python package layout with universal agent-affordance verbs (`telek learn`,
  `telek explain`, `telek whoami`); structured `TelekError` + `--json` output;
  vendored baseline skills (`cicd`, `communicate`, `run-tests`, `sonarclaude`,
  `version-bump`) from `agentculture/steward`; CI (`tests.yml` with
  pytest+coverage+lint+SonarCloud-gated scan+`version-check`, `publish.yml`
  with Trusted Publishing to TestPyPI/PyPI); `sonar-project.properties` and
  `culture.yaml` declaring `telek` as the agent nick.
