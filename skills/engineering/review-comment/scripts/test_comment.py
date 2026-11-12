import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import comment  # noqa: E402

INLINE = "https://github.com/acme/shop/pull/12#discussion_r345"
GENERAL = "https://github.com/acme/shop/pull/12#issuecomment-678"


class FakeGh:
    def __init__(self, in_reply_to_id=None):
        self.calls = []
        self.in_reply_to_id = in_reply_to_id

    def __call__(self, *args, raw=False):
        self.calls.append(args)
        if "-X" in args:
            return {"html_url": "https://github.com/acme/shop/pull/12#reply"}
        return {"in_reply_to_id": self.in_reply_to_id}


class Comment(unittest.TestCase):
    def setUp(self):
        self.body = Path(tempfile.mkdtemp()) / "body.md"
        self.body.write_text("> [!NOTE]\n> 🤖 **Model responding on behalf of Name**\n\nFixed in abc\n")
        self.real_gh = comment.gh

    def tearDown(self):
        comment.gh = self.real_gh

    def test_parses_both_url_forms(self):
        self.assertEqual(comment.parse_url(INLINE),
                         {"kind": "inline", "owner": "acme", "repo": "shop", "pr": 12, "id": 345})
        self.assertEqual(comment.parse_url(GENERAL + "?foo=1")["kind"], "general")
        self.assertEqual(comment.parse_url("https://github.com/acme/shop/pull/12/files#discussion_r9")["id"], 9)
        with self.assertRaises(ValueError):
            comment.parse_url("https://github.com/acme/shop/pull/12")

    def test_inline_reply_goes_to_the_threads_top_comment(self):
        comment.gh = fake = FakeGh(in_reply_to_id=111)
        comment.reply(INLINE, self.body)
        self.assertEqual(fake.calls[-1][1], "repos/acme/shop/pulls/12/comments/111/replies")
        comment.gh = fake = FakeGh()
        comment.reply(INLINE, self.body)
        self.assertEqual(fake.calls[-1][1], "repos/acme/shop/pulls/12/comments/345/replies")
        self.assertIn(f"body=@{self.body}", fake.calls[-1])

    def test_general_reply_is_a_new_pr_comment(self):
        comment.gh = fake = FakeGh()
        comment.reply(GENERAL, self.body)
        self.assertEqual(fake.calls, [("api", "repos/acme/shop/issues/12/comments", "-X", "POST", "-F",
                                       f"body=@{self.body}")])

    def test_refuses_a_body_without_the_byline(self):
        comment.gh = fake = FakeGh()
        self.body.write_text("Fixed in abc\n")
        with self.assertRaises(ValueError):
            comment.reply(INLINE, self.body)
        self.assertEqual(fake.calls, [])

    def test_fetch_escapes_the_path_in_the_contents_request(self):
        calls = []

        def fake(*args, raw=False):
            calls.append(args)
            if raw:
                return "line\n"
            if args[0] == "pr":
                return {"baseRefName": "main", "headRefName": "f", "headRefOid": "abc"}
            return {"user": {"login": "r"}, "body": "b", "path": "examples/C#/a b.cs", "line": 1}

        comment.gh = fake
        comment.fetch(INLINE)
        self.assertEqual(calls[-1][1], "repos/acme/shop/contents/examples/C%23/a%20b.cs?ref=abc")

    def test_numbered_context_marks_the_line(self):
        text = "\n".join(f"l{n}" for n in range(1, 51))
        out = comment.numbered(text, 25, radius=2).splitlines()
        self.assertEqual(out, ["   23  l23", "   24  l24", "   25> l25", "   26  l26", "   27  l27"])


if __name__ == "__main__":
    unittest.main()
