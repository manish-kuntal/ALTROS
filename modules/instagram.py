# ============================================================
#  ALTROS Module: Instagram Integration
#  Post, Delete, DM, Search, Like, Follow — real time
# ============================================================

import os
import json
from modules.base import BaseModule

CREDS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "memory", "instagram_session.json")

IG_TRIGGERS = [
    "instagram", "insta", "post kar", "photo dal", "reel dal",
    "story dal", "dm kar", "message kar instagram", "like kar",
    "follow kar", "unfollow", "comment kar", "search kar insta",
    "delete post", "post delete", "insta pe", "ig pe",
]


class InstagramModule(BaseModule):
    name = "instagram"
    description = "Instagram — post, DM, like, follow, search — real time"

    def __init__(self):
        self._ready = False
        self._client = None

    def on_enable(self):
        try:
            from instagrapi import Client
            self._client = Client()

            # Load saved session
            if os.path.exists(CREDS_FILE):
                try:
                    self._client.load_settings(CREDS_FILE)
                    self._client.get_timeline_feed()  # Test session
                    self._ready = True
                    print("     ✅ Instagram module ready (session loaded)")
                    return
                except Exception:
                    print("     ⚠️  Session expired — login karo: 'instagram login'")

            print("     ⚠️  Instagram login nahi hua. Bolo: 'instagram login'")

        except ImportError:
            print("     ⚠️  Run: pip install instagrapi")

    def login(self, username: str, password: str) -> str:
        """Login aur session save karo."""
        try:
            from instagrapi import Client
            self._client = Client()
            self._client.login(username, password)
            os.makedirs(os.path.dirname(CREDS_FILE), exist_ok=True)
            self._client.dump_settings(CREDS_FILE)
            self._ready = True
            return f"Instagram: ✅ {username} se login ho gaya!"
        except Exception as e:
            return f"Instagram: ❌ Login fail — {e}"

    def can_handle(self, query: str, context: dict) -> bool:
        if not self._ready:
            q = query.lower()
            return "instagram login" in q or "insta login" in q
        q = query.lower()
        return any(t in q for t in IG_TRIGGERS)

    def handle(self, query: str, context: dict) -> str:
        q = query.lower()

        # Login command
        if "instagram login" in q or "insta login" in q:
            import shlex

            try:
                parts = shlex.split(query)
            except ValueError:
                return 'Instagram: Format use karo: instagram login username "password"'

            if len(parts) < 4:
                return 'Instagram: Format use karo: instagram login username "password"'

            username, password = parts[2], parts[3]
            return self.login(username, password)

        if not self._ready:
            return "Instagram: Pehle login karo — 'instagram login username password'"

        # ── POST PHOTO ────────────────────────────────────────
        if any(w in q for w in ["post kar", "photo dal", "upload kar", "post karo"]):
            import re
            path_match = re.search(r'[A-Za-z]:\\[^\s"]+\.(jpg|jpeg|png|mp4)', query, re.I)
            caption_match = re.search(r'"([^"]+)"', query)

            if not path_match:
                return "Instagram: Photo ka path batao — example: 'post karo C:\\Users\\manish\\pic.jpg caption \"Meri photo\"'"

            filepath = path_match.group()
            caption = caption_match.group(1) if caption_match else ""

            try:
                if filepath.lower().endswith('.mp4'):
                    media = self._client.video_upload(filepath, caption=caption)
                else:
                    media = self._client.photo_upload(filepath, caption=caption)
                return f"Instagram: ✅ Post ho gaya! Media ID: {media.pk}"
            except Exception as e:
                return f"Instagram: ❌ Post error — {e}"

        # ── DELETE POST ───────────────────────────────────────
        if any(w in q for w in ["delete post", "post delete", "hata do post"]):
            import re
            # Get recent posts and delete latest
            try:
                user_id = self._client.user_id
                medias = self._client.user_medias(user_id, 5)
                if not medias:
                    return "Instagram: Koi post nahi mili."

                # Delete latest by default
                latest = medias[0]
                self._client.media_delete(latest.pk)
                return f"Instagram: ✅ Latest post delete ho gayi."
            except Exception as e:
                return f"Instagram: ❌ Delete error — {e}"

        # ── SEND DM ───────────────────────────────────────────
        if any(w in q for w in ["dm kar", "message kar", "dm bhej"]):
            import re
            # Extract username and message
            user_match = re.search(r'(?:dm kar|message kar|bhej)\s+@?(\w+)', q)
            msg_match = re.search(r'"([^"]+)"', query)

            if not user_match:
                return "Instagram: Kisko DM karna hai? Format: 'dm kar @username \"message\"'"
            if not msg_match:
                return "Instagram: Message quotes mein likho — 'dm kar @username \"Hello yaar!\"'"

            username = user_match.group(1)
            message = msg_match.group(1)

            try:
                user_id = self._client.user_id_from_username(username)
                self._client.direct_send(message, [user_id])
                return f"Instagram: ✅ DM bhej diya @{username} ko — '{message}'"
            except Exception as e:
                return f"Instagram: ❌ DM error — {e}"

        # ── READ DMs ──────────────────────────────────────────
        if any(w in q for w in ["inbox dekho", "messages dekho", "dms dekho", "new messages"]):
            try:
                threads = self._client.direct_threads(amount=5)
                if not threads:
                    return "Instagram: Koi DM nahi hai."
                lines = ["Instagram: Recent DMs:"]
                for t in threads[:5]:
                    user = t.users[0].username if t.users else "Unknown"
                    last_msg = t.messages[0].text if t.messages and hasattr(t.messages[0], 'text') else "[media]"
                    lines.append(f"  @{user}: {str(last_msg)[:50]}")
                return "\n".join(lines)
            except Exception as e:
                return f"Instagram: ❌ DM read error — {e}"

        # ── LIKE POST ─────────────────────────────────────────
        if any(w in q for w in ["like kar", "like karo"]):
            import re
            url_match = re.search(r'instagram\.com/p/([A-Za-z0-9_-]+)', query)
            if not url_match:
                return "Instagram: Post URL batao — 'like karo instagram.com/p/POST_ID'"
            try:
                media_pk = self._client.media_pk_from_url(f"https://www.instagram.com/p/{url_match.group(1)}/")
                self._client.media_like(media_pk)
                return "Instagram: ✅ Post like ho gayi!"
            except Exception as e:
                return f"Instagram: ❌ Like error — {e}"

        # ── FOLLOW ───────────────────────────────────────────
        if "follow kar" in q or "follow karo" in q:
            import re
            user_match = re.search(r'follow\s+kar(?:o)?\s+@?(\w+)', q)
            if not user_match:
                return "Instagram: Kisko follow karna hai? 'follow karo @username'"
            try:
                username = user_match.group(1)
                user_id = self._client.user_id_from_username(username)
                self._client.user_follow(user_id)
                return f"Instagram: ✅ @{username} ko follow kar liya!"
            except Exception as e:
                return f"Instagram: ❌ Follow error — {e}"

        # ── UNFOLLOW ─────────────────────────────────────────
        if "unfollow" in q:
            import re
            user_match = re.search(r'unfollow\s+@?(\w+)', q)
            if not user_match:
                return "Instagram: Kisko unfollow karna hai? 'unfollow @username'"
            try:
                username = user_match.group(1)
                user_id = self._client.user_id_from_username(username)
                self._client.user_unfollow(user_id)
                return f"Instagram: ✅ @{username} ko unfollow kar diya!"
            except Exception as e:
                return f"Instagram: ❌ Unfollow error — {e}"

        # ── SEARCH USER ───────────────────────────────────────
        if any(w in q for w in ["search kar", "dhundo", "profile dekho"]):
            import re
            user_match = re.search(r'(?:search kar|dhundo|profile dekho)\s+@?(\w+)', q)
            if not user_match:
                return "Instagram: Kise search karna hai? 'search kar @username'"
            try:
                username = user_match.group(1)
                user_info = self._client.user_info_by_username(username)
                return (
                    f"Instagram: @{username} ka profile:\n"
                    f"  Naam: {user_info.full_name}\n"
                    f"  Followers: {user_info.follower_count:,}\n"
                    f"  Following: {user_info.following_count:,}\n"
                    f"  Posts: {user_info.media_count}\n"
                    f"  Bio: {user_info.biography[:100] if user_info.biography else 'Empty'}"
                )
            except Exception as e:
                return f"Instagram: ❌ Search error — {e}"

        # ── MY PROFILE ────────────────────────────────────────
        if any(w in q for w in ["mera profile", "my profile", "mere followers"]):
            try:
                user_id = self._client.user_id
                info = self._client.user_info(user_id)
                return (
                    f"Instagram: Tera profile:\n"
                    f"  Username: @{info.username}\n"
                    f"  Followers: {info.follower_count:,}\n"
                    f"  Following: {info.following_count:,}\n"
                    f"  Posts: {info.media_count}\n"
                    f"  Bio: {info.biography[:100] if info.biography else 'Empty'}"
                )
            except Exception as e:
                return f"Instagram: ❌ Profile error — {e}"

        return ""
