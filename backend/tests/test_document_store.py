import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services import document_store
from app.services.document_pipeline import process_document_bytes


class DummyQuery:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self.action = None
        self.payload = None
        self.filters = []

    def upsert(self, data, on_conflict=None):
        self.action, self.payload = "upsert", data
        self.client.writes.append((self.table, self.action, data, on_conflict))
        return self

    def update(self, data):
        self.action, self.payload = "update", data
        self.client.writes.append((self.table, self.action, data, None))
        return self

    def select(self, *args, **kwargs):
        if self.action is None:
            self.action = "select"
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        self.client.filters.append((self.table, key, value))
        return self

    def in_(self, key, values):
        self.filters.append((key, values))
        return self

    def order(self, *args, **kwargs):
        return self

    def range(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        data = [{"id": "job-1", "status": "queued"}] if self.table == "document_processing_jobs" and self.action == "update" else []
        return SimpleNamespace(data=data, count=len(data))


class DummyStorageBucket:
    def __init__(self, client, bucket):
        self.client = client
        self.bucket = bucket

    def upload(self, path, file, file_options):
        self.client.objects[path] = (file, file_options)
        return {"path": path}

    def download(self, path):
        return self.client.objects[path][0]


class DummyStorage:
    def __init__(self, client):
        self.client = client

    def from_(self, bucket):
        return DummyStorageBucket(self.client, bucket)


class DummyClient:
    def __init__(self):
        self.writes = []
        self.filters = []
        self.objects = {}
        self.storage = DummyStorage(self)

    def table(self, table):
        return DummyQuery(self, table)


class DocumentStoreAdapterTests(unittest.TestCase):
    def test_processing_result_upserts_are_stable_across_retry(self):
        client = DummyClient()
        result = process_document_bytes("document.pdf", _pdf_bytes(), segment_chars=700, segment_overlap_chars=100)
        document = {"id": "00000000-0000-0000-0000-000000000001", "workspace_id": "00000000-0000-0000-0000-000000000002", "conversation_id": "00000000-0000-0000-0000-000000000003"}
        attachment = {"id": document["id"]}
        with patch.object(document_store, "_client", return_value=client):
            document_store.save_processing_result(document, attachment, result, {})
            first = [write for write in client.writes if write[1] == "upsert"]
            first_ids = {table: [row["id"] for row in payload] for table, _, payload, _ in first}
            document_store.save_processing_result(document, attachment, result, {})
            second = [write for write in client.writes if write[1] == "upsert"][len(first):]
            second_ids = {table: [row["id"] for row in payload] for table, _, payload, _ in second}
        self.assertEqual(first_ids, second_ids)
        self.assertIn("document_pages", first_ids)
        self.assertIn("document_segments", first_ids)
        self.assertIn("document_facts", first_ids)

    def test_private_derived_storage_adapter_upload_and_download(self):
        client = DummyClient()
        path = "workspace/conversation/document/derived/page-0001.png"
        with patch.object(document_store, "_client", return_value=client):
            document_store.upload_derived(path, b"png-content", "image/png")
            downloaded = document_store.download_original(path)
        self.assertEqual(downloaded, b"png-content")
        self.assertIn(path, client.objects)
        self.assertEqual(client.objects[path][1]["upsert"], "true")

    def test_retry_is_workspace_scoped_and_resets_attempts(self):
        client = DummyClient()
        with patch.object(document_store, "_client", return_value=client):
            result = document_store.retry_document_job("document-1", "workspace-1")
        self.assertEqual(result["status"], "queued")
        self.assertIn(("document_processing_jobs", "workspace_id", "workspace-1"), client.filters)
        job_write = next(write for write in client.writes if write[0] == "document_processing_jobs")
        self.assertEqual(job_write[2]["attempts"], 0)
        self.assertEqual(job_write[2]["status"], "queued")


def _pdf_bytes():
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Agreement between Alice and Bob, with payment amount BDT 25000 and termination.")
    value = doc.tobytes()
    doc.close()
    return value


if __name__ == "__main__":
    unittest.main()
