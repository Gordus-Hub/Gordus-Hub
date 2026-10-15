"""Governed Argos Translate adapter. No language package is downloaded at runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .adapters import AdapterGateError
from .contracts import AdapterReadiness, WorkRequest


class ArgosTranslateAdapter:
    """Offline Argos adapter requiring an approved, installed direct language pair."""

    component_id = "argostranslate"

    def __init__(self, pair_registry_path: str | Path | None = None) -> None:
        self.pair_registry_path = (
            Path(pair_registry_path).resolve()
            if pair_registry_path is not None
            else Path(__file__).resolve().parents[2] / "translation" / "pairs.json"
        )

    def _load_registry(self) -> Mapping[str, Any]:
        try:
            value = json.loads(self.pair_registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AdapterGateError("ARGOS_PAIR_REGISTRY_MISSING_OR_INVALID") from exc
        if not isinstance(value, dict):
            raise AdapterGateError("ARGOS_PAIR_REGISTRY_INVALID")
        policy = value.get("policy")
        pairs = value.get("approved_language_pairs")
        if (
            not isinstance(policy, dict)
            or policy.get("fail_closed") is not True
            or policy.get("model_package_downloads_enabled") is not False
            or value.get("state") != "APPROVED_FOR_CONTROLLED_ACQUISITION"
            or not isinstance(pairs, list)
            or not pairs
        ):
            raise AdapterGateError("LANGUAGE_PAIR_MATRIX_NOT_APPROVED")
        return value

    @staticmethod
    def _translation_object(source_code: str, target_code: str):
        try:
            from argostranslate import translate
        except ImportError as exc:
            raise AdapterGateError("ARGOS_RUNTIME_DEPENDENCY_MISSING") from exc

        installed = translate.get_installed_languages()
        source = next((language for language in installed if language.code == source_code), None)
        if source is None or not any(language.code == target_code for language in installed):
            raise AdapterGateError("ARGOS_LANGUAGE_PACKS_NOT_INSTALLED")
        direct = next(
            (item for item in source.translations_from if item.to_lang.code == target_code),
            None,
        )
        if direct is None:
            raise AdapterGateError("ARGOS_DIRECT_LANGUAGE_PAIR_NOT_INSTALLED")
        return direct

    def preflight(self) -> AdapterReadiness:
        try:
            pairs = self._load_registry()["approved_language_pairs"]
            for pair in pairs:
                if not isinstance(pair, dict):
                    continue
                source = pair.get("source_language")
                target = pair.get("target_language")
                if isinstance(source, str) and isinstance(target, str):
                    try:
                        self._translation_object(source, target)
                        return AdapterReadiness(True, ())
                    except AdapterGateError:
                        continue
            return AdapterReadiness(False, ("ARGOS_LANGUAGE_PACKS_NOT_INSTALLED",))
        except AdapterGateError as exc:
            return AdapterReadiness(False, (exc.gate_code,))

    def invoke(self, request: WorkRequest, input_text: str) -> str:
        registry = self._load_registry()
        source_code = request.parameters.get("source_language")
        target_code = request.parameters.get("target_language")
        if not isinstance(source_code, str) or not isinstance(target_code, str):
            raise AdapterGateError("SOURCE_AND_TARGET_LANGUAGE_REQUIRED")
        approved = registry["approved_language_pairs"]
        if not any(
            isinstance(pair, dict)
            and pair.get("source_language") == source_code
            and pair.get("target_language") == target_code
            for pair in approved
        ):
            raise AdapterGateError("LANGUAGE_PAIR_NOT_APPROVED")
        return self._translation_object(source_code, target_code).translate(input_text)
