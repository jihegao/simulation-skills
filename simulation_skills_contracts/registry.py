"""Closed Draft 2020-12 registry for Simulation Skills owned contracts."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

EXPORT_ROOT = Path(__file__).with_name("conformance") / "v0_1"
SCHEMA_DIR = EXPORT_ROOT / "schemas"


class ContractValidationError(ValueError):
    """A stable, fail-closed provider contract validation failure."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


class V01SimulationContractRegistry:
    """Validate provider-owned Version 0.1 objects and semantic invariants."""

    SCHEMA_FILES = (
        "common.schema.json",
        "model-spec.schema.json",
        "result-set.schema.json",
        "domain-pack.schema.json",
        "des-method-payload.schema.json",
        "abm-method-payload.schema.json",
        "conformance-case.schema.json",
        "conformance-export.schema.json",
    )
    CONTRACT_SCHEMAS = {
        "simulation.model_spec": "model-spec.schema.json",
        "simulation.result_set": "result-set.schema.json",
        "simulation.domain_pack": "domain-pack.schema.json",
        "simulation.des_method_payload": "des-method-payload.schema.json",
        "simulation.abm_method_payload": "abm-method-payload.schema.json",
    }

    def __init__(
        self,
        schema_dir: Path = SCHEMA_DIR,
        *,
        known_required_extensions: frozenset[str] = frozenset(),
    ) -> None:
        self.schema_dir = Path(schema_dir)
        self.known_required_extensions = known_required_extensions
        self.schemas = {
            name: json.loads((self.schema_dir / name).read_text(encoding="utf-8"))
            for name in self.SCHEMA_FILES
        }
        for schema in self.schemas.values():
            Draft202012Validator.check_schema(schema)
        registry = Registry().with_resources(
            [
                (schema["$id"], Resource.from_contents(schema))
                for schema in self.schemas.values()
            ]
        )
        checker = FormatChecker()
        self.validators = {
            name: Draft202012Validator(
                self.schemas[file_name], registry=registry, format_checker=checker
            )
            for name, file_name in self.CONTRACT_SCHEMAS.items()
        }
        self.case_validator = Draft202012Validator(
            self.schemas["conformance-case.schema.json"],
            registry=registry,
            format_checker=checker,
        )
        self.export_validator = Draft202012Validator(
            self.schemas["conformance-export.schema.json"],
            registry=registry,
            format_checker=checker,
        )

    def validate_object(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ContractValidationError("schema_contract_failed", "object must be a JSON object")
        contract = value.get("contract")
        validator = self.validators.get(contract)
        if validator is None:
            raise ContractValidationError(
                "schema_contract_failed", f"unsupported provider contract {contract!r}"
            )
        self._validate(validator, value, "object", "schema_contract_failed")
        self._validate_revision(value)
        self._validate_required_extensions(value)
        return deepcopy(value)

    def validate_case(self, value: Any) -> dict[str, Any]:
        self._validate(self.case_validator, value, "case", "schema_contract_failed")
        fragment = value["provider_fragment"]
        for item in (
            fragment["domain_pack"],
            fragment["model_spec"],
            fragment["method_payload"],
        ):
            self.validate_object(item)
        from .canonical_json import digest

        domain_pack = fragment["domain_pack"]
        descriptor = fragment["domain_pack_descriptor"]
        template = domain_pack["scenario_templates"][0]
        if descriptor != {
            "pack_id": domain_pack["pack_id"],
            "pack_version": domain_pack["pack_version"],
            "template_id": template["template_id"],
            "manifest_digest": digest(domain_pack),
        }:
            raise ContractValidationError(
                "domain_pack_manifest_digest_mismatch",
                "Domain Pack descriptor is stale or inconsistent",
            )
        method_payload = fragment["method_payload"]
        expected_method_ref = {
            "contract": method_payload["contract"],
            "schema_version": method_payload["schema_version"],
            "object_id": method_payload["object_id"],
            "revision": method_payload["revision"],
            "digest": digest(method_payload),
        }
        if fragment["model_spec"]["method_payload_ref"] != expected_method_ref:
            raise ContractValidationError(
                "stale_digest", "Model Spec method payload ref is stale"
            )
        roles = [item["role"] for item in fragment["required_connections"]]
        if sorted(roles) != ["experiment", "project", "scenario", "simulation_run"]:
            raise ContractValidationError(
                "input_contract_failed", "required connections must contain each role exactly once"
            )
        expected_contract = (
            "simulation.abm_method_payload"
            if value["mechanism"] == "agent_based_network"
            else "simulation.des_method_payload"
        )
        if method_payload["contract"] != expected_contract:
            raise ContractValidationError(
                "input_contract_failed", "case mechanism and method payload do not match"
            )
        expected_time_mode = (
            "discrete_step"
            if expected_contract == "simulation.abm_method_payload"
            else "discrete_event"
        )
        if fragment["model_spec"]["time_semantics"]["mode"] != expected_time_mode:
            raise ContractValidationError(
                "input_contract_failed", "Model Spec time semantics do not match the method"
            )
        method_line = f"{expected_contract}@0.1"
        if fragment["domain_pack"]["method_payload_contracts"] != [method_line]:
            raise ContractValidationError(
                "input_contract_failed", "Domain Pack method contract is inconsistent"
            )
        expected_family = (
            "agent_based"
            if expected_contract == "simulation.abm_method_payload"
            else "discrete_event"
        )
        if fragment["domain_pack"]["adapter_requirements"]["method_families"] != [
            expected_family
        ]:
            raise ContractValidationError(
                "input_contract_failed", "Domain Pack method family is inconsistent"
            )
        return deepcopy(value)

    def validate_export(self, value: Any) -> dict[str, Any]:
        self._validate(self.export_validator, value, "export", "schema_contract_failed")
        return deepcopy(value)

    @staticmethod
    def _validate(
        validator: Draft202012Validator,
        value: Any,
        label: str,
        code: str,
    ) -> None:
        errors = sorted(
            validator.iter_errors(value),
            key=lambda error: tuple(str(part) for part in error.absolute_path),
        )
        if errors:
            error = errors[0]
            location = "/" + "/".join(str(part) for part in error.absolute_path)
            raise ContractValidationError(
                code,
                f"{label} schema validation failed at {location or '/'}: {error.message}",
            )

    @staticmethod
    def _validate_revision(value: dict[str, Any]) -> None:
        revision = value["revision"]
        parent_revision = value["parent_revision"]
        if revision == 1 and parent_revision is not None:
            raise ContractValidationError(
                "invalid_revision", "revision 1 must have a null parent_revision"
            )
        if revision > 1 and parent_revision != revision - 1:
            raise ContractValidationError(
                "invalid_revision",
                "parent_revision must identify the immediately preceding revision",
            )

    def _validate_required_extensions(self, value: dict[str, Any]) -> None:
        for namespace, extension in value["extensions"].items():
            if (
                extension["required"] is True
                and namespace not in self.known_required_extensions
            ):
                raise ContractValidationError(
                    "unknown_required_extension",
                    f"required extension {namespace!r} is not supported",
                )
