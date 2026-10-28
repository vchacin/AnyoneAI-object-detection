from app.backend.routers.inspections import _public


def test_inspection_export_payload_contains_contract_fields():
    class Inspection:
        id = "inspection-1"
        store_id = "store-1"
        camera_id = None
        shelf_id = None
        image_key = "stores/store-1/inspections/image.png"
        image_width = 100
        image_height = 80
        image_bytes = 10
        source = "manual"
        model_version = "model-v1"
        n_objects = 1
        n_missing = 0
        latency_ms = 2.5
        created_by = "user-1"
        employee_id = None
        created_at = None

    class Query:
        def filter(self, _):
            return self

        def all(self):
            return []

    class Session:
        def query(self, _):
            return Query()

    payload = _public(Inspection(), Session())
    assert payload["id"] == "inspection-1"
    assert payload["model_version"] == "model-v1"
    assert payload["detections"] == []
