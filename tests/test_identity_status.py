from __future__ import annotations

from http import HTTPStatus
import unittest

import python.identity_status as identity_status


class IdentityStatusTests(unittest.TestCase):
    def test_reference_status_code_mapping_preserves_existing_cases(self) -> None:
        self.assertEqual(
            identity_status.resolve_identity_reference_status_code(
                error_type="invalid_request",
                blocker=None,
                service_unavailable_blockers=frozenset({"comfy_unreachable"}),
            ),
            HTTPStatus.BAD_REQUEST,
        )
        self.assertEqual(
            identity_status.resolve_identity_reference_status_code(
                error_type="timeout",
                blocker=None,
                service_unavailable_blockers=frozenset(),
            ),
            HTTPStatus.GATEWAY_TIMEOUT,
        )
        self.assertEqual(
            identity_status.resolve_identity_reference_status_code(
                error_type=None,
                blocker="comfy_unreachable",
                service_unavailable_blockers=frozenset({"comfy_unreachable"}),
            ),
            HTTPStatus.SERVICE_UNAVAILABLE,
        )

    def test_transfer_status_code_mapping_preserves_existing_cases(self) -> None:
        self.assertEqual(
            identity_status.resolve_identity_transfer_status_code(
                error_type=None,
                blocker="missing_identity_head_reference",
            ),
            HTTPStatus.BAD_REQUEST,
        )
        self.assertEqual(
            identity_status.resolve_identity_transfer_status_code(
                error_type="invalid_request",
                blocker=None,
            ),
            HTTPStatus.BAD_REQUEST,
        )
        self.assertEqual(
            identity_status.resolve_identity_transfer_generate_status_code(
                error_type="api_error",
                blocker="comfy_unreachable",
                reference_status_resolver=lambda **kwargs: HTTPStatus.SERVICE_UNAVAILABLE,
            ),
            HTTPStatus.SERVICE_UNAVAILABLE,
        )

    def test_readiness_http_status_returns_ok_or_delegates(self) -> None:
        self.assertEqual(
            identity_status.resolve_identity_readiness_http_status(
                {"ok": True},
                status_code_resolver=lambda **kwargs: HTTPStatus.BAD_REQUEST,
            ),
            HTTPStatus.OK,
        )
        self.assertEqual(
            identity_status.resolve_identity_readiness_http_status(
                {"ok": False, "error_type": "invalid_request", "blocker": "missing_x"},
                status_code_resolver=lambda **kwargs: HTTPStatus.BAD_REQUEST,
            ),
            HTTPStatus.BAD_REQUEST,
        )

    def test_build_identity_transfer_status_payload_builds_roles_and_blockers(self) -> None:
        dir_states = {
            "identity_head_reference": (True, None),
            "target_body_image": (False, "target_body_image_dir_not_accessible"),
            "style_reference": (True, None),
        }
        images = {
            "identity_head_reference": {"image_id": "head-1"},
            "target_body_image": None,
            "style_reference": None,
        }
        payload = identity_status.build_identity_transfer_status_payload(
            roles=["identity_head_reference", "target_body_image", "style_reference"],
            required_roles=["identity_head_reference", "target_body_image"],
            role_dir_state_resolver=lambda role: dir_states[role],
            role_image_state_resolver=lambda role: images[role],
        )

        self.assertEqual(payload["status"], "ok")
        self.assertFalse(payload["v6_3_transfer_ready"])
        self.assertEqual(payload["required_roles"], ["identity_head_reference", "target_body_image"])
        self.assertEqual(payload["optional_roles"], ["style_reference"])
        self.assertEqual(payload["occupied_role_count"], 1)
        self.assertEqual(payload["blockers"], ["target_body_image_dir_not_accessible", "missing_target_body_image"])
        self.assertTrue(payload["roles"][0]["occupied"])
        self.assertFalse(payload["roles"][1]["occupied"])

    def test_build_identity_transfer_status_payload_defaults_optional_roles(self) -> None:
        payload = identity_status.build_identity_transfer_status_payload(
            roles=["identity_head_reference"],
            required_roles=["identity_head_reference"],
            role_dir_state_resolver=lambda role: (True, None),
            role_image_state_resolver=lambda role: {"image_id": "x"},
        )

        self.assertTrue(payload["v6_3_transfer_ready"])
        self.assertEqual(payload["optional_roles"], [])
        self.assertEqual(payload["blockers"], [])


if __name__ == "__main__":
    unittest.main()
