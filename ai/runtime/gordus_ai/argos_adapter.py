"""Governed Argos Translate adapter. No language package is downloaded at runtime.

Direct pairs come from ``approved_language_pairs``. A two-hop route (source -> via -> target)
is used only when it is listed explicitly in ``approved_two_hop_routes`` and both hops are
themselves approved direct pairs; routes are never inferred automatically. An approved pair
must carry its artifact SHA-256; ``candidate_*`` lists written by scripts/ai/sync_argos_pairs.py
are never read here, so candidates stay not approved.
"""

from __future__ import annotations

import json
from itertools import pairwise
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

    @staticmethod
    def _is_direct_approved(registry: Mapping[str, Any], source: str, target: str) -> bool:
        return any(
            isinstance(pair, dict)
            and pair.get("source_language") == source
            and pair.get("target_language") == target
            and isinstance(pair.get("artifact_sha256"), str)
            and len(pair["artifact_sha256"]) == 64
            for pair in registry["approved_language_pairs"]
        )

    def resolve_route(self, source_code: str, target_code: str) -> tuple[str, ...]:
        """Return the approved language chain, e.g. ("pt", "es") or ("fr", "en", "es")."""
        registry = self._load_registry()
        if self._is_direct_approved(registry, source_code, target_code):
            return (source_code, target_code)
        if registry.get("policy", {}).get("explicit_two_hop_routes_allowed_when_registered") is True:
            routes = registry.get("approved_two_hop_routes", [])
            for route in routes if isinstance(routes, list) else []:
                if (
                    isinstance(route, dict)
                    and route.get("explicit_two_hop_approved") is True
                    and route.get("source_language") == source_code
                    and route.get("target_language") == target_code
                    and isinstance(route.get("via_language"), str)
                ):
                    via = route["via_language"]
                    if self._is_direct_approved(registry, source_code, via) and self._is_direct_approved(
                        registry, via, target_code
                    ):
                        return (source_code, via, target_code)
                    raise AdapterGateError("TWO_HOP_ROUTE_HOP_NOT_APPROVED")
        raise AdapterGateError("LANGUAGE_PAIR_NOT_APPROVED")

    def pair_readiness(self, source_code: str, target_code: str) -> AdapterReadiness:
        """Preflight for one specific request: approved route and every hop installed."""
        try:
            chain = self.resolve_route(source_code, target_code)
            for hop_source, hop_target in pairwise(chain):
                self._translation_object(hop_source, hop_target)
            return AdapterReadiness(True, ())
        except AdapterGateError as exc:
            return AdapterReadiness(False, (exc.gate_code,))

    def invoke(self, request: WorkRequest, input_text: str) -> str:
        source_code = request.parameters.get("source_language")
        target_code = request.parameters.get("target_language")
        if not isinstance(source_code, str) or not isinstance(target_code, str):
            self._load_registry()
            raise AdapterGateError("SOURCE_AND_TARGET_LANGUAGE_REQUIRED")
        chain = self.resolve_route(source_code, target_code)
        text = input_text
        for hop_source, hop_target in pairwise(chain):
            text = self._translation_object(hop_source, hop_target).translate(text)
        return text
