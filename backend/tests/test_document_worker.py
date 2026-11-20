import unittest
from unittest.mock import patch

from app.workers import document_worker


class DocumentWorkerLifecycleTests(unittest.TestCase):
    def test_durable_job_moves_queued_to_processing_to_completed_once(self):
        state = {"status": "queued", "claim_count": 0}
        job = {
            "id": "job-1", "document_id": "00000000-0000-0000-0000-000000000001",
            "attachment_id": "00000000-0000-0000-0000-000000000002",
            "workspace_id": "00000000-0000-0000-0000-000000000003",
            "conversation_id": "00000000-0000-0000-0000-000000000004",
        }
        document = {"id": job["document_id"], "workspace_id": job["workspace_id"]}
        attachment = {
            "id": job["attachment_id"], "filename": "case.pdf",
            "mime_type": "application/pdf", "storage_path": "w/c/a.pdf",
        }
        result = {
            "status": "completed", "artifacts": [], "pages": [], "segments": [], "facts": [],
            "classification": {"document_type": "other"}, "uncertainty_notes": [],
        }

        def claim():
            if state["status"] != "queued":
                return None
            state["status"] = "processing"
            state["claim_count"] += 1
            return job

        def save(_document, _attachment, final_result, _artifacts):
            state["status"] = final_result["status"]

        with patch.object(document_worker.document_store, "claim_next_job", side_effect=claim), \
             patch.object(document_worker.document_store, "get_job_context", return_value=(document, attachment)), \
             patch.object(document_worker.document_store, "download_original", return_value=b"%PDF-1.7 test"), \
             patch.object(document_worker, "process_document_bytes", return_value=result), \
             patch.object(document_worker.document_store, "save_processing_result", side_effect=save) as saved:
            # Signature validation accepts PDF bytes; the pipeline is mocked so this stays synthetic.
            self.assertEqual(document_worker.process_one_job(), "completed")
            self.assertIsNone(document_worker.process_one_job())

        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["claim_count"], 1)
        self.assertEqual(saved.call_count, 1)

    def test_worker_failure_is_persisted_as_failed_state(self):
        job = {"id": "job-2", "document_id": "doc", "workspace_id": "workspace"}
        with patch.object(document_worker.document_store, "claim_next_job", return_value=job), \
             patch.object(document_worker.document_store, "get_job_context", side_effect=RuntimeError("missing attachment")), \
             patch.object(document_worker.document_store, "mark_job_failed") as failed:
            self.assertEqual(document_worker.process_one_job(), "failed")
        failed.assert_called_once()
        self.assertEqual(failed.call_args.args[0], job)


if __name__ == "__main__":
    unittest.main()
