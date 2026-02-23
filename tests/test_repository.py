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

    def test_edit_and_filters(self) -> None:
        created = self.repo.create_post(
            title="Campaign A",
            platform="instagram",
            channel_name="Brand",
            publish_at="2026-01-11 09:00",
            status="planned",
            description="launch content",
            hashtags="#launch",
            media_url="",
        )
        edited = self.repo.update_post(
            created.id,
            title="Campaign B",
            platform="tiktok",
            channel_name="BrandTT",
            publish_at="2026-01-12 10:30",
            description="updated copy",
            hashtags="#updated",
            media_url="https://example.com/video.mp4",
        )
        self.assertEqual(edited.title, "Campaign B")
        filtered = self.repo.list_posts(platform="tiktok", q="updated")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].id, created.id)


if __name__ == "__main__":
    unittest.main()
