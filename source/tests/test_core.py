import os
import sys
import tempfile
import unittest

TMP = tempfile.mkdtemp(prefix="tensei_test_")
os.environ["TENSEI_HOME"] = TMP
os.environ["TENSEI_OFFLINE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tensei import config, util, seed_data  # noqa: E402
from tensei.embed import Embedder  # noqa: E402
from tensei.nn import MLP  # noqa: E402
from tensei.memory import Memory  # noqa: E402
from tensei.brain import Brain  # noqa: E402
from tensei.thinker import Thinker, safe_math  # noqa: E402


class TestUtil(unittest.TestCase):
    def test_words_sentences(self):
        self.assertEqual(util.content_words("What is the black hole?"), ["black", "hole"])
        s = util.sentences("First sentence here. Second one is longer than thirty chars!")
        self.assertEqual(len(s), 2)

    def test_math(self):
        self.assertIn("100", safe_math("what is 12 * 8 + 4"))
        self.assertIn("30", safe_math("15% of 200"))
        self.assertIsNone(safe_math("__import__('os')"))

    def test_categories(self):
        self.assertEqual(seed_data.classify_category("what is quantum computing"), "tech")
        self.assertEqual(seed_data.classify_category("vitamin d study"), "health")


class TestEmbed(unittest.TestCase):
    def test_determinism_and_similarity(self):
        e = Embedder()
        self.assertEqual(e.encode("hello world"), e.encode("hello world"))
        a = e.encode("black holes have extreme gravity")
        b = e.encode("a black hole has very strong gravity")
        c = e.encode("sourdough bread recipe with flour")
        self.assertGreater(util.dot(a, b), util.dot(a, c))

    def test_numpy_python_projection_match(self):
        e = Embedder()
        f = e.featurize("quantum entanglement correlations")
        d = max(abs(x - y) for x, y in zip(e._project_np(f), e._project_py(f)))
        self.assertLess(d, 1e-9)


class TestNN(unittest.TestCase):
    def test_learns_blobs(self):
        import random
        rnd = random.Random(0)
        X, y = [], []
        for i in range(200):
            c = i % 2
            X.append([rnd.gauss(0, .5), rnd.gauss(3 if c else 0, .5)])
            y.append(c)
        m = MLP([2, 12, 2], seed=1)
        r = m.train(X, y, epochs=25)
        self.assertGreater(r["train_acc"], 0.9)

    def test_save_load(self):
        m = MLP([4, 6, 2], seed=2)
        p = os.path.join(TMP, "m.json")
        m.save(p)
        m2 = MLP.load(p)
        x = [0.1, 0.2, 0.3, 0.4]
        self.assertAlmostEqual(m.predict_proba(x)[0], m2.predict_proba(x)[0], places=4)


class TestMemoryBrain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mem = Memory()
        cls.brain = Brain(cls.mem)
        cls.brain.train_all()
        cls.think = Thinker(cls.mem, cls.brain)
        cls.mem.add_passages(
            "http://example.org/photo", "Photosynthesis facts",
            "Photosynthesis is the process used by green plants to convert light energy "
            "into chemical energy. It produces glucose and oxygen from carbon dioxide "
            "and water using sunlight. Chlorophyll inside chloroplasts absorbs light.",
            topic="photosynthesis")
        cls.mem.add_qa("what is photosynthesis", "It is how plants make food from light.",
                       [{"url": "http://example.org/photo", "title": "Photosynthesis facts"}],
                       cls.brain.embedder.encode("what is photosynthesis"))

    def test_cold_training_quality(self):
        met = self.brain.meta["metrics"]
        self.assertGreater(met["intent"]["val_acc"], 0.75)

    def test_dedupe(self):
        n = self.mem.stats()["passages"]
        text = ("Photosynthesis is the process used by green plants to convert light energy "
                "into chemical energy. It produces glucose and oxygen from carbon dioxide "
                "and water using sunlight. Chlorophyll inside chloroplasts absorbs light.")
        self.mem.add_passages("http://example.org/photo", "Photosynthesis facts", text)
        self.assertEqual(self.mem.stats()["passages"], n)

    def test_retrieval(self):
        q = self.brain.embedder.encode("how do plants make food from sunlight")
        hits = self.mem.search_emb("docs", q, k=3, keywords=["plants", "sunlight"])
        self.assertTrue(hits)
        self.assertIn("Photosynthesis", hits[0]["title"])

    def test_thinker_offline_memory_answer(self):
        res = self.think.ask("What is photosynthesis?")
        self.assertIn("photosynthesis", res["answer"].lower())
        self.assertGreater(res["confidence"], 0.2)
        self.assertIn(res["mode"], ("memory", "fact"))
        self.assertTrue(res["steps"])

    def test_thinker_specials(self):
        self.assertIn("12 * 8", self.think.ask("what is 12 * 8 + 4")["answer"])
        self.assertIn("TenSeiAi", self.think.ask("who are you")["answer"])
        self.assertIn("TenSeiAi", self.think.ask("hello")["answer"])

    def test_lm_trains_and_generates(self):
        lm = self.brain.lm
        self.assertTrue(lm.trained, "language model should train on origin facts")
        self.assertGreater(lm.V, 50)
        g1 = lm.generate("hello tenseiai", seed=1)
        g2 = lm.generate("hello tenseiai", seed=2)
        self.assertIsInstance(g1, str)
        self.assertTrue(len(g1) > 0 or len(g2) > 0)

    def test_generated_reply_not_canned(self):
        a1 = self.think.ask("hi", )["answer"]
        a2 = self.think.ask("hey there")["answer"]
        self.assertTrue(a1.startswith("**TenSeiAi:**")
                        or a1.startswith("**Answer"), a1[:80])
        self.assertNotEqual(a1, a2)

    def test_model_file_roundtrip(self):
        from tensei import model_file
        self.brain.train_all()
        f = os.path.join(TMP, "TenSeiAi.tsei")
        info = model_file.save_model(f, TMP)
        self.assertLess(info["size_mb"], 45)
        d = model_file.describe(f)
        self.assertIn("brains/lm_vocab.json", d["meta"]["blobs"])
        home2 = os.path.join(TMP, "runtime2")
        r = model_file.install_model(f, home2)
        self.assertTrue(r["installed"])
        self.assertTrue(os.path.exists(os.path.join(home2, "brains", "meta.json")))
        self.assertTrue(os.path.exists(os.path.join(home2, "data", "tensei.db")))
        brain2 = Brain(Memory(os.path.join(home2, "data", "tensei.db")))
        self.assertTrue(brain2.embedder.learned())
        self.assertTrue(brain2.lm.trained)

    def test_learning_loop(self):
        qa_before = self.mem.stats()["qa_pairs"]
        self.think.ask("what is chlorophyll")
        self.assertEqual(self.mem.stats()["qa_pairs"], qa_before + 1)
        topics = [t["name"] for t in self.mem.all_topics()]
        self.assertTrue(any("chlorophyll" in t for t in topics))

    def test_brain_size_cap(self):
        sz = sum(os.path.getsize(os.path.join(config.BRAINS, f))
                 for f in os.listdir(config.BRAINS))
        self.assertLess(sz, 45 * 1024 * 1024)


class TestUpgrades(unittest.TestCase):
    """Regression tests for the 2.0 engine upgrades."""

    @classmethod
    def setUpClass(cls):
        cls.mem = Memory()
        cls.brain = Brain(cls.mem)
        cls.brain.train_all()
        cls.think = Thinker(cls.mem, cls.brain)

    def test_algebra_solver(self):
        from tensei import reasoner
        self.assertIn("5", reasoner.try_answer("solve 3x + 6 = 21")["answer"])
        self.assertIn("4", reasoner.try_answer("2x = 8")["answer"])
        self.assertIn("15", reasoner.try_answer("x/3 = 5")["answer"])
        self.assertIn("14", reasoner.try_answer("x - 4 = 10")["answer"])

    def test_arithmetic_still_works(self):
        self.assertIn("391", safe_math("17*23"))
        self.assertIn("100", safe_math("what is 12 * 8 + 4"))
        # algebra must NOT be mangled into a truncated arithmetic expression
        self.assertIsNone(safe_math("solve 3x + 6 = 21"))

    def test_time_unit_solver(self):
        from tensei import reasoner
        r = reasoner.try_answer("how many seconds are in a week")
        self.assertIn("604800", r["answer"])
        r = reasoner.try_answer("how many minutes in a day")
        self.assertIn("1440", r["answer"])

    def test_temporal_guard(self):
        from tensei.thinker import _is_temporal
        self.assertFalse(_is_temporal("what year did world war 2 end"))
        self.assertFalse(_is_temporal("what year was the telephone invented"))
        self.assertTrue(_is_temporal("what time is it"))
        self.assertTrue(_is_temporal("what is the date today"))
        self.assertTrue(_is_temporal("what day is it today"))

    def test_greeting_guard(self):
        a = self.think.ask("explain blockchain like I am five")["analysis"]
        self.assertNotEqual(a["intent"], "greeting")
        a2 = self.think.ask("hi there")["analysis"]
        self.assertEqual(a2["intent"], "greeting")

    def test_poisoned_qa_not_replayed(self):
        emb = self.brain.embedder.encode("why do we dream?")
        self.mem.add_qa("why do we dream?",
                        "Blue light is scattered in all directions by the atmosphere.",
                        [{"url": "http://example.org/sky", "title": "sky"}],
                        emb,
                        emb0=self.brain.embedder.base_encode("why do we dream?"),
                        mode="memory")
        res = self.think.ask("why do we dream?")
        self.assertNotIn("scattered in all directions", res["answer"].lower())

    def test_smalltalk_stays_greeting(self):
        # "how are you ..." starts with "how are" which the knowledge-word
        # guard would otherwise treat as a research question.
        r = self.think.ask("how are you doing today?")
        self.assertEqual(r["mode"], "chat")
        self.assertIn("TenSeiAi", r["answer"])
        r = self.think.ask("hello there")
        self.assertEqual(r["mode"], "chat")

    def test_entity_extraction(self):
        self.assertEqual(
            self.think.analyze("How does electricity work?")["entity"].lower(),
            "electricity")
        self.assertEqual(
            self.think.analyze("Explain blockchain like I am five")["entity"].lower(),
            "blockchain")
        self.assertEqual(
            self.think.analyze("Explain quantum computing in simple terms")["entity"].lower(),
            "quantum computing")
        self.assertEqual(
            self.think.analyze("What is the capital of Japan?")["entity"].lower(),
            "capital of japan")

    def test_knowledge_never_smalltalk(self):
        for q in ("Explain blockchain like I am five",
                  "explain photosynthesis to me",
                  "How does the internet work?",
                  "Describe how rainbows form"):
            a = self.think.analyze(q)
            self.assertNotIn(a["intent"], ("greeting", "chitchat"), q)

    def test_qa_mode_stored(self):
        emb = self.brain.embedder.encode("what is a test subject?")
        rid = self.mem.add_qa("what is a test subject?",
                              "A test subject is an entity used for experiments.",
                              [{"url": "http://example.org/t", "title": "t"}],
                              emb,
                              emb0=self.brain.embedder.base_encode("what is a test subject?"),
                              mode="web")
        row = self.mem.conn.execute("SELECT mode FROM qa WHERE id=?", (rid,)).fetchone()
        self.assertEqual(row[0], "web")


if __name__ == "__main__":
    unittest.main(verbosity=2)
