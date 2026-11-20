import unittest

from app.services.document_intelligence import classify_document


class DocumentClassificationTests(unittest.TestCase):
    def test_khatian_is_routed_as_land_record_not_contract(self):
        pages = [{
            "page": 1,
            "text": "খতিয়ান নং ১৭৮৯ নামজারি মামলা নং ১৭৮৯ মৌজা উনশিয়া দাগ জমির শ্রেণী একর শতাংশ",
        }]
        result = classify_document(pages)
        self.assertEqual(result["document_type"], "land_record")
        self.assertEqual(result["document_workflow"], "land_record_review")

    def test_contract_keyword_group_is_detected(self):
        pages = [{
            "page": 1,
            "text": "This agreement contains an indemnify clause and termination obligations.",
        }]
        result = classify_document(pages)
        self.assertEqual(result["document_type"], "contract")


if __name__ == "__main__":
    unittest.main()
