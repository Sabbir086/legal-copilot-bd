from __future__ import annotations

import argparse
import logging
import threading
import time

from app.config.settings import settings
from app.services import document_store
from app.services.document_pipeline import process_document_bytes
from app.services.upload_validation import validate_attachment_upload

logger = logging.getLogger("mylegal.document_worker")


def _heartbeat_loop(job: dict, stop: threading.Event) -> None:
    # Refresh the durable lease while OCR processes multi-page files.
    while not stop.wait(120):
        try:
            if not document_store.heartbeat_job(job["id"], job["workspace_id"]):
                logger.warning("Document job %s no longer owns its processing lease", job["id"])
                return
        except Exception:
            logger.exception("Could not refresh processing lease for job %s", job["id"])


def process_one_job() -> str | None:
    job = document_store.claim_next_job()
    if not job:
        return None
    stop_heartbeat = threading.Event()
    heartbeat = threading.Thread(target=_heartbeat_loop, args=(job, stop_heartbeat), daemon=True)
    heartbeat.start()
    try:
        document, attachment = document_store.get_job_context(job)
        content = document_store.download_original(attachment["storage_path"])
        filename, mime_type, _kind = validate_attachment_upload(
            attachment["filename"], content, settings.max_upload_mb * 1024 * 1024,
            max_image_pixels=settings.max_image_pixels,
            max_image_bytes=settings.max_image_upload_mb * 1024 * 1024,
        )
        if mime_type != attachment["mime_type"]:
            raise ValueError("Stored MIME type does not match the verified file signature.")
        result = process_document_bytes(filename, content)
        artifact_paths: dict[tuple[str, int | None], str] = {}
        for artifact in result.get("artifacts", []):
            artifact_type = artifact["artifact_type"]
            page_number = artifact.get("page_number")
            suffix = f"page-{int(page_number):04d}" if page_number is not None else "normalized"
            storage_path = (
                f"{job['workspace_id']}/{job['conversation_id']}/{job['document_id']}"
                f"/derived/{artifact_type}/{suffix}.png"
            )
            document_store.upload_derived(storage_path, artifact["content"], artifact["mime_type"])
            artifact_paths[(artifact_type, page_number)] = storage_path
        document_store.save_processing_result(document, attachment, result, artifact_paths)
        logger.info("Processed document %s with status %s", job["document_id"], result["status"])
        return str(result["status"])
    except Exception as exc:
        logger.exception("Document job %s failed", job.get("id"))
        try:
            document_store.mark_job_failed(job, type(exc).__name__, str(exc))
        except Exception:
            logger.exception("Failed to persist terminal state for job %s", job.get("id"))
        return "failed"
    finally:
        stop_heartbeat.set()
        heartbeat.join(timeout=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="MyLegal AI durable document processing worker")
    parser.add_argument("--once", action="store_true", help="Claim and process at most one queued job")
    parser.add_argument("--poll-seconds", type=int, default=settings.document_worker_poll_seconds)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    while True:
        status = process_one_job()
        if args.once:
            return
        if status is None:
            time.sleep(max(1, args.poll_seconds))


if __name__ == "__main__":
    main()
