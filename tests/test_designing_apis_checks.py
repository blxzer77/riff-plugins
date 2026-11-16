"""Validates the designing-apis eval checks on known contracts: the untouched fixture,
good solutions written in different ways, and near misses."""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS = REPO / "evals" / "designing-apis"
FIXTURE = EVALS / "files" / "shop-api"
PROBLEM = {"$ref": "#/components/responses/Problem"}
LIMIT = {"$ref": "#/components/parameters/Limit"}
CURSOR = {"$ref": "#/components/parameters/Cursor"}


def json_body(schema):
    return {"content": {"application/json": {"schema": schema}}}


def export_operation(status_values):
    return {"type": "object", "required": ["id", "status"],
            "properties": {"id": {"type": "string"},
                           "status": {"type": "string", "enum": status_values},
                           "progress": {"type": "integer", "minimum": 0, "maximum": 100},
                           "download_url": {"type": ["string", "null"], "format": "uri"}}}


def export_good_post(spec):
    spec["components"]["schemas"]["ExportOperation"] = export_operation(
        ["queued", "running", "succeeded", "failed"])
    ref = {"$ref": "#/components/schemas/ExportOperation"}
    spec["paths"]["/customer-exports"] = {"post": {
        "operationId": "startCustomerExport", "summary": "Start a customer export",
        "parameters": [{"name": "Idempotency-Key", "in": "header", "required": True,
                        "schema": {"type": "string"}}],
        "responses": {"202": {"description": "Accepted.", **json_body(ref)}, "401": PROBLEM}}}
    spec["paths"]["/customer-exports/{export_id}"] = {"get": {
        "operationId": "getCustomerExport", "summary": "Get an export",
        "parameters": [{"name": "export_id", "in": "path", "required": True,
                        "schema": {"type": "string"}}],
        "responses": {"200": {"description": "The export.", **json_body(ref)},
                      "401": PROBLEM, "404": PROBLEM}}}


def export_good_put(spec):
    state = {"type": "object", "properties": {
        "export_id": {"type": "string"},
        "state": {"oneOf": [{"const": "pending"}, {"const": "done"}, {"const": "error"}]}}}
    param = [{"name": "export_id", "in": "path", "required": True, "schema": {"type": "string"}}]
    spec["paths"]["/customers/exports/{export_id}"] = {
        "parameters": param,
        "put": {"operationId": "putExport", "summary": "Create the export with this client-chosen id",
                "responses": {"201": {"description": "Created.", **json_body(state)},
                              "200": {"description": "Already exists.", **json_body(state)},
                              "401": PROBLEM}},
        "get": {"operationId": "getExport", "summary": "Export state",
                "responses": {"200": {"description": "State.", **json_body(state)}, "401": PROBLEM}}}
    spec["paths"]["/customers/exports/{export_id}/file"] = {"parameters": param, "get": {
        "operationId": "downloadExport", "summary": "Download the finished export",
        "responses": {"200": {"description": "CSV.", "content": {"text/csv": {"schema": {"type": "string"}}}},
                      "401": PROBLEM, "404": PROBLEM}}}


def export_202_without_status(spec):
    spec["paths"]["/exports"] = {"post": {
        "operationId": "startExport", "summary": "Start an export",
        "responses": {"202": {"description": "Accepted."}, "401": PROBLEM}}}


def export_synchronous(spec):
    spec["paths"]["/exports"] = {"post": {
        "operationId": "exportCustomers", "summary": "Export customers",
        "parameters": [{"name": "Idempotency-Key", "in": "header", "schema": {"type": "string"}}],
        "responses": {"200": {"description": "The CSV.",
                              "content": {"text/csv": {"schema": {"type": "string"}}}},
                      "401": PROBLEM}}}


def export_status_without_states(spec):
    body = {"type": "object", "properties": {"id": {"type": "string"}, "status": {"type": "string"},
                                             "download_url": {"type": "string"}}}
    spec["paths"]["/exports"] = {"post": {
        "operationId": "startExport", "summary": "Start an export",
        "responses": {"202": {"description": "Accepted.", **json_body(body)}, "401": PROBLEM}}}
    spec["paths"]["/exports/{id}"] = {"get": {
        "operationId": "getExport", "summary": "Export",
        "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
        "responses": {"200": {"description": "Export.", **json_body(body)}, "401": PROBLEM}}}


def items_params(*extra):
    def apply(spec):
        spec["paths"]["/items"]["get"]["parameters"] = [
            {"name": "owner_id", "in": "query", "schema": {"type": "string"}},
            {"name": "sort", "in": "query", "schema": {"type": "string", "enum": ["updated_at", "-updated_at"]}},
            *extra]
    return apply


def items_new_endpoint(spec):
    spec["components"]["schemas"]["ItemPage"] = {
        "type": "object", "required": ["data", "next_cursor"],
        "properties": {"data": {"type": "array", "items": {"$ref": "#/components/schemas/Item"}},
                       "next_cursor": {"type": ["string", "null"]}}}
    spec["paths"]["/items/search"] = {"get": {
        "operationId": "searchItems", "summary": "Filter, sort, and page items",
        "parameters": [LIMIT, CURSOR, {"name": "owner_id", "in": "query", "schema": {"type": "string"}}],
        "responses": {"200": {"description": "A page.",
                              **json_body({"$ref": "#/components/schemas/ItemPage"})},
                      "401": PROBLEM}}}


def items_envelope_in_place(spec):
    items_new_endpoint(spec)
    spec["paths"]["/items"]["get"] = spec["paths"].pop("/items/search")["get"]
    spec["paths"]["/items"]["get"]["operationId"] = "listItems"


def customers_email_required(spec):
    spec["paths"]["/customers"]["get"]["parameters"][2]["required"] = True


def export_put_to_another_resource(spec):
    body = export_operation(["queued", "running", "succeeded", "failed"])
    spec["paths"]["/orders/{order_id}/export"] = {"put": {
        "operationId": "exportOrder", "summary": "Start an export of an order",
        "parameters": [{"name": "order_id", "in": "path", "required": True, "schema": {"type": "string"}}],
        "responses": {"202": {"description": "Accepted.", **json_body(body)}, "401": PROBLEM}}}


def export_status_without_result_link(spec):
    status = {"type": "object", "properties": {
        "id": {"type": "string"}, "profile_id": {"type": "string"},
        "status": {"type": "string", "enum": ["running", "succeeded", "failed"]}}}
    spec["paths"]["/exports"] = {"post": {
        "operationId": "startExport", "summary": "Start an export",
        "parameters": [{"name": "Idempotency-Key", "in": "header", "schema": {"type": "string"}}],
        "responses": {"202": {"description": "Accepted.", **json_body(status)}, "401": PROBLEM}}}
    spec["paths"]["/exports/{id}"] = {"get": {
        "operationId": "getExport", "summary": "Export",
        "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
        "responses": {"200": {"description": "Export.", **json_body(status)}, "401": PROBLEM}}}


def export_key_in_one_of_body(spec):
    export_good_post(spec)
    start = spec["paths"]["/customer-exports"]["post"]
    start["parameters"] = []
    start["requestBody"] = {"required": True, **json_body({"oneOf": [
        {"type": "object", "properties": {"request_id": {"type": "string"}, "format": {"const": "csv"}}},
        {"type": "object", "properties": {"request_id": {"type": "string"}, "format": {"const": "xlsx"}}}]})}


def export_self_referencing_schema(spec):
    spec["components"]["schemas"]["Loop"] = {"allOf": [{"$ref": "#/components/schemas/Loop"}]}
    spec["paths"]["/exports"] = {"post": {
        "operationId": "startExport", "summary": "Start an export",
        "responses": {"201": {"description": "Created.",
                              **json_body({"$ref": "#/components/schemas/Loop"})}, "401": PROBLEM}}}


def items_list_under_another_name(spec):
    items_new_endpoint(spec)
    spec["paths"]["/catalogue/entries"] = spec["paths"].pop("/items/search")


def broken_ref(spec):
    spec["paths"]["/items"]["get"]["responses"]["200"] = {"$ref": "#/components/responses/Missing"}


class DesigningApisChecksTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="riff-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def run_check(self, script: str, *changes) -> int:
        fixture, workdir = self.tmp / "fixture", self.tmp / "workdir"
        for target in (fixture, workdir):
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(FIXTURE, target)
        spec = json.loads((workdir / "openapi.json").read_text(encoding="utf-8"))
        spec = copy.deepcopy(spec)
        for change in changes:
            change(spec)
        (workdir / "openapi.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
        response = self.tmp / "response.md"
        response.write_text("", encoding="utf-8")
        env = dict(os.environ, EVAL_FIXTURE=str(fixture), EVAL_WORKDIR=str(workdir),
                   EVAL_RESPONSE=str(response))
        proc = subprocess.run([sys.executable, str(EVALS / "checks" / script)], env=env,
                              capture_output=True, text=True, cwd=self.tmp)
        self.last_output = proc.stdout + proc.stderr
        return proc.returncode

    def run_check_output(self, script: str, *changes) -> str:
        self.run_check(script, *changes)
        return self.last_output

    def test_put_to_another_resource_is_not_retry_safe(self):
        self.assertEqual(self.run_check("export_create_is_idempotent.py",
                                        export_put_to_another_resource), 1)

    def test_a_status_without_a_result_link_or_download_fails(self):
        self.assertEqual(self.run_check("export_is_operation_resource.py",
                                        export_status_without_result_link), 1)

    def test_an_idempotency_key_inside_a_one_of_body_passes(self):
        self.assertEqual(self.run_check("export_create_is_idempotent.py",
                                        export_key_in_one_of_body), 0)

    def test_a_self_referencing_schema_fails_cleanly(self):
        output = self.run_check_output("export_is_operation_resource.py",
                                       export_self_referencing_schema)
        self.assertIn("FAIL:", output)
        self.assertNotIn("Traceback", output)

    def test_an_items_list_under_another_path_passes(self):
        self.assertEqual(self.run_check("items_list_paginated.py", items_list_under_another_name), 0)

    def test_untouched_fixture(self):
        self.assertEqual(self.run_check("contract_valid.py"), 0)
        self.assertEqual(self.run_check("existing_operations_compatible.py"), 0)
        self.assertEqual(self.run_check("export_is_operation_resource.py"), 1)
        self.assertEqual(self.run_check("export_create_is_idempotent.py"), 1)
        self.assertEqual(self.run_check("items_list_paginated.py"), 1)

    def test_export_with_idempotency_key_and_status_resource_passes(self):
        for script in ("contract_valid.py", "existing_operations_compatible.py",
                       "export_is_operation_resource.py", "export_create_is_idempotent.py"):
            self.assertEqual(self.run_check(script, export_good_post), 0, script)

    def test_export_as_put_to_client_chosen_id_passes(self):
        for script in ("contract_valid.py", "existing_operations_compatible.py",
                       "export_is_operation_resource.py", "export_create_is_idempotent.py"):
            self.assertEqual(self.run_check(script, export_good_put), 0, script)

    def test_export_returning_202_without_a_status_resource_fails(self):
        self.assertEqual(self.run_check("export_is_operation_resource.py", export_202_without_status), 1)
        self.assertEqual(self.run_check("export_create_is_idempotent.py", export_202_without_status), 1)

    def test_synchronous_export_fails_the_async_check(self):
        self.assertEqual(self.run_check("export_is_operation_resource.py", export_synchronous), 1)
        self.assertEqual(self.run_check("export_create_is_idempotent.py", export_synchronous), 0)

    def test_export_status_without_defined_states_fails(self):
        self.assertEqual(self.run_check("export_is_operation_resource.py",
                                        export_status_without_states), 1)

    def test_items_paged_in_place_with_cursor_and_bounded_limit_passes(self):
        change = items_params(LIMIT, CURSOR)
        for script in ("contract_valid.py", "existing_operations_compatible.py",
                       "items_list_paginated.py"):
            self.assertEqual(self.run_check(script, change), 0, script)

    def test_items_on_a_new_endpoint_passes(self):
        for script in ("contract_valid.py", "existing_operations_compatible.py",
                       "items_list_paginated.py"):
            self.assertEqual(self.run_check(script, items_new_endpoint), 0, script)

    def test_items_wrapped_in_a_page_object_in_place_breaks_old_clients(self):
        self.assertEqual(self.run_check("existing_operations_compatible.py",
                                        items_envelope_in_place), 1)
        self.assertEqual(self.run_check("items_list_paginated.py", items_envelope_in_place), 0)

    def test_items_paged_by_offset_fails(self):
        offset = items_params(LIMIT, {"name": "offset", "in": "query",
                                      "schema": {"type": "integer", "minimum": 0}})
        self.assertEqual(self.run_check("items_list_paginated.py", offset), 1)

    def test_items_cursor_with_unbounded_limit_fails(self):
        unbounded = items_params({"name": "limit", "in": "query", "schema": {"type": "integer"}}, CURSOR)
        self.assertEqual(self.run_check("items_list_paginated.py", unbounded), 1)

    def test_making_an_optional_parameter_required_breaks_old_clients(self):
        self.assertEqual(self.run_check("existing_operations_compatible.py",
                                        customers_email_required), 1)

    def test_a_dangling_reference_fails_the_contract_check(self):
        self.assertEqual(self.run_check("contract_valid.py", broken_ref), 1)


if __name__ == "__main__":
    unittest.main()
