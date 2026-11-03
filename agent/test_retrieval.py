"""Live retrieval check for T5: five hand-picked questions must return the right DOC-ID first.

Needs the GEEKOM box (OLLAMA_HOST, D49) and data/docs.duckdb (`make index`). Embedding is free;
nothing here calls a paid model. The off-topic questions are the ones the threshold was set on (D56).
Run with: python -m unittest agent.test_retrieval
"""
import unittest

from agent import tools

QUERIES = [
    ("Can a distributor change the quantity on a PO after we confirm it?", "POL-01-v1"),
    ("Which SKUs get priority when stock is short?", "POL-02-v1"),
    ("How much caffeine is in a 16 oz can of Frost Kiwi?", "PRD-TRV-KIW-v1"),
    ("How is on-time-in-full calculated?", "MET-01-v1"),
    ("What happens when a promo's authorization was never recorded?", "POL-03-v1"),
]
OFF_TOPIC = [
    "What is the capital of France?", "Give me a recipe for banana bread.", "Who won the football game last night?",
    "How do I reset my laptop password?", "Explain how photosynthesis works.", "What is the weather tomorrow in Chicago?",
]


class Retrieval(unittest.TestCase):
    def test_hand_picked_queries_return_the_right_doc_first(self):
        for question, doc_id in QUERIES:
            with self.subTest(question):
                out = tools.search_docs(question)
                self.assertTrue(out["ok"], out.get("error"))
                self.assertTrue(out["passages"], "nothing above the threshold")
                self.assertEqual(out["passages"][0]["doc_id"], doc_id,
                                 [(p["id"], p["score"]) for p in out["passages"]])

    def test_off_topic_questions_return_nothing(self):
        for question in OFF_TOPIC:
            with self.subTest(question):
                out = tools.search_docs(question)
                self.assertEqual(out["passages"], [], [(p["id"], p["score"]) for p in out["passages"]])


if __name__ == "__main__":
    unittest.main()
