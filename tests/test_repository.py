import tempfile
import unittest
from pathlib import Path

from web.repository import Repository


class RepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "app.db")
        self.repo = Repository(self.db_path)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_create_and_list(self) -> None:
        created = self.repo.create_post(
            title="Title",
            platform="telegram",
            channel_name="@my_channel",
            publish_at="2026-01-10 12:30",
            status="planned",
            description="desc",
            hashtags="#one",
            media_url="",
        )
        self.assertGreater(created.id, 0)
        posts = self.repo.list_posts()
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].platform, "telegram")

    def test_update_status_and_delete(self) -> None:
        created = self.repo.create_post(
            title="Title",
            platform="youtube",
            channel_name="YT Main",
            publish_at="2026-01-10 12:30",
            status="draft",
            description="desc",
            hashtags="",
            media_url="",
        )
        updated = self.repo.update_status(created.id, "published")
        self.assertEqual(updated.status, "published")
        self.repo.delete_post(created.id)
        self.assertEqual(self.repo.list_posts(), [])


if __name__ == "__main__":
    unittest.main()
