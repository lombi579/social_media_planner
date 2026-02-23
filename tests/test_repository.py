import tempfile
import unittest
from pathlib import Path

from web.repository import Repository


class RepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "app.db")
        self.repo = Repository(self.db_path)
        self.user = self.repo.create_user("alice", "secret12")
        self.ws = self.repo.list_workspaces(self.user.id)[0]["id"]

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_create_and_list(self) -> None:
        created = self.repo.create_post(
            self.user.id,
            self.ws,
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
        posts = self.repo.list_posts(self.user.id, self.ws)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].platform, "telegram")

    def test_update_status_and_delete(self) -> None:
        created = self.repo.create_post(
            self.user.id,
            self.ws,
            title="Title",
            platform="youtube",
            channel_name="YT Main",
            publish_at="2026-01-10 12:30",
            status="draft",
            description="desc",
            hashtags="",
            media_url="",
        )
        updated = self.repo.update_status(self.user.id, self.ws, created.id, "published")
        self.assertEqual(updated.status, "published")
        self.repo.delete_post(self.user.id, self.ws, created.id)
        self.assertEqual(self.repo.list_posts(self.user.id, self.ws), [])

    def test_edit_filters_and_auth(self) -> None:
        created = self.repo.create_post(
            self.user.id,
            self.ws,
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
            self.user.id,
            self.ws,
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
        filtered = self.repo.list_posts(self.user.id, self.ws, platform="tiktok", q="updated")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].id, created.id)
        self.assertIsNotNone(self.repo.authenticate("alice", "secret12"))
        self.assertIsNone(self.repo.authenticate("alice", "bad"))

    def test_workspace_oauth_jobs_audit_notifications(self) -> None:
        bob = self.repo.create_user("bob", "secret34")
        self.repo.add_member(self.user.id, self.ws, "bob", "editor")
        self.repo.set_subscription_plan(self.user.id, self.ws, "pro")
        account = self.repo.add_social_account(
            self.user.id,
            self.ws,
            platform="youtube",
            account_label="Main",
            access_token="a",
            refresh_token="r",
            expires_at="2026-01-01 10:00",
        )
        self.assertEqual(account.platform, "youtube")
        post = self.repo.create_post(
            self.user.id,
            self.ws,
            title="Job Post",
            platform="youtube",
            channel_name="Main",
            publish_at="2000-01-01 00:00",
            status="planned",
            description="desc",
            hashtags="",
            media_url="",
        )
        result = self.repo.process_due_jobs(limit=50)
        self.assertGreaterEqual(result["processed"], 1)
        audits = self.repo.list_audit_events(self.user.id, self.ws)
        self.assertGreaterEqual(len(audits), 1)
        notes = self.repo.list_notifications(1)
        self.assertGreaterEqual(len(notes), 1)
        hooks_before = self.repo.list_webhooks(self.user.id, self.ws)
        self.repo.create_webhook(self.user.id, self.ws, "post.published", "https://example.com/h", "sec")
        hooks_after = self.repo.list_webhooks(self.user.id, self.ws)
        self.assertEqual(len(hooks_after), len(hooks_before) + 1)
        # bob should have workspace access now
        self.assertTrue(any(int(w["id"]) == int(self.ws) for w in self.repo.list_workspaces(bob.id)))


if __name__ == "__main__":
    unittest.main()
