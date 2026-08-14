# -*- coding: utf-8 -*-
"""کلاینت Instagram Graph API (متا) — انتشار پست/استوری و دریافت اینسایت"""
import requests

GRAPH = "https://graph.facebook.com/v20.0"


class IGError(Exception):
    pass


def _friendly_network_error(e):
    import requests as _rq
    if isinstance(e, _rq.exceptions.SSLError) or "SSL" in str(e):
        return ("دسترسی به سرورهای متا (graph.facebook.com) برقرار نشد. "
                "اگر از ایران وصل هستی، VPN را روشن کن و دوباره امتحان کن.")
    return f"خطای شبکه: {e}"


class IGClient:
    def __init__(self, access_token, ig_user_id, base_url=""):
        self.token = access_token
        self.user_id = ig_user_id
        self.base_url = base_url.rstrip("/") if base_url else ""

    # ---------- کمکی ----------
    def _get(self, path, params=None):
        p = dict(params or {})
        p["access_token"] = self.token
        try:
            r = requests.get(f"{GRAPH}{path}", params=p, timeout=30)
        except requests.RequestException as e:
            raise IGError(_friendly_network_error(e))
        data = r.json()
        if r.status_code != 200 or "error" in data:
            msg = (data.get("error", {}) or {}).get("message") or data.get("error", "خطای نامشخص")
            code = (data.get("error", {}) or {}).get("code", r.status_code)
            raise IGError(f"[{code}] {msg}")
        return data

    def _post(self, path, params=None):
        p = dict(params or {})
        p["access_token"] = self.token
        try:
            r = requests.post(f"{GRAPH}{path}", data=p, timeout=60)
        except requests.RequestException as e:
            raise IGError(_friendly_network_error(e))
        data = r.json()
        if r.status_code != 200 or "error" in data:
            msg = (data.get("error", {}) or {}).get("message") or data.get("error", "خطای نامشخص")
            code = (data.get("error", {}) or {}).get("code", r.status_code)
            raise IGError(f"[{code}] {msg}")
        return data

    # ---------- اتصال ----------
    def test(self):
        data = self._get(f"/{self.user_id}", params={"fields": "id,username,name,followers_count,media_count"})
        return data

    @staticmethod
    def discover(access_token):
        """پیدا کردن اکانت‌های بیزینس اینستاگرام متصل به فیسبوک‌پیج‌های کاربر"""
        out = []
        try:
            r = requests.get(f"{GRAPH}/me/accounts",
                             params={"access_token": access_token,
                                     "fields": "id,name,instagram_business_account"},
                             timeout=30).json()
        except requests.RequestException as e:
            raise IGError(_friendly_network_error(e))
        for page in r.get("data", []):
            if page.get("instagram_business_account"):
                out.append({
                    "page_id": page["id"],
                    "page_name": page.get("name", ""),
                    "ig_id": page["instagram_business_account"]["id"],
                })
        if not out:
            raise IGError("هیچ اکانت اینستاگرام بیزینسی پیدا نشد. ابتدا اینستاگرام را به یک فیسبوک‌پیج وصل کن.")
        return out

    # ---------- انتشار ----------
    def publish(self, image_url, caption, is_story=False):
        """انتشار تصویر: مرحله ۱ ساخت media container، مرحله ۲ انتشار"""
        container = self._post(
            f"/{self.user_id}/media",
            params={
                "image_url": image_url,
                "caption": caption[:2200] if caption else "",
                **({"media_type": "STORIES"} if is_story else {}),
            },
        )
        cid = container.get("id")
        if not cid:
            raise IGError("ساخت container ناموفق بود")
        pub = self._post(f"/{self.user_id}/media_publish", params={"creation_id": cid})
        mid = pub.get("id")
        permalink = ""
        if mid:
            try:
                info = self._get(f"/{mid}", params={"fields": "permalink"})
                permalink = info.get("permalink", "")
            except IGError:
                pass
        return mid, permalink

    # ---------- اینسایت ----------
    def account_summary(self):
        data = self._get(f"/{self.user_id}",
                         params={"fields": "id,username,followers_count,follows_count,media_count"})
        return data

    def account_insights(self, days=30):
        """متریک‌های روزانه حساب"""
        metrics = "impressions,reach,profile_views,email_contacts,get_directions_clicks,phone_call_clicks,website_clicks,text_message_clicks,follower_count"
        data = self._get(f"/{self.user_id}/insights",
                         params={"metric": metrics, "period": "day",
                                 "since": _days_ago(days), "until": _days_ago(0)})
        return data.get("data", [])

    def online_followers(self):
        data = self._get(f"/{self.user_id}/insights",
                         params={"metric": "online_followers", "period": "lifetime"})
        return data.get("data", [])

    def audience(self):
        data = self._get(f"/{self.user_id}/insights",
                         params={"metric": "audience_gender_age,audience_country,audience_city",
                                 "period": "lifetime"})
        return data.get("data", [])

    def recent_media(self, limit=25):
        data = self._get(f"/{self.user_id}/media",
                         params={"fields": "id,caption,media_type,like_count,comments_count,timestamp,permalink,thumbnail_url",
                                 "limit": limit})
        return data.get("data", [])

    def media_insights(self, media_id):
        data = self._get(f"/{media_id}/insights",
                         params={"metric": "reach,impressions,saved,shares"})
        return data.get("data", [])


def _days_ago(n):
    from datetime import datetime, timedelta
    return (datetime.utcnow() - timedelta(days=n)).strftime("%Y-%m-%d")
