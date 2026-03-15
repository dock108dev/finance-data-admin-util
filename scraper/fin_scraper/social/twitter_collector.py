"""Twitter/X collector — Playwright-based scraping of cashtag mentions.

Same pattern as sports-data-admin's Twitter collector.
Searches for cashtag mentions ($AAPL, $BTC, etc.) via X advanced search.
"""

import re
from datetime import datetime, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from fin_scraper.config import get_settings

logger = structlog.get_logger(__name__)

CASHTAG_PATTERN = re.compile(r"\$([A-Z]{1,5})\b")

# Top cashtags to search for
DEFAULT_CASHTAGS = [
    "$AAPL", "$MSFT", "$GOOGL", "$AMZN", "$NVDA", "$META", "$TSLA",
    "$BTC", "$ETH", "$SOL", "$XRP", "$DOGE",
]


class TwitterCollector:
    """Collect tweets with financial cashtags via Playwright scraping.

    Requires X_AUTH_TOKEN and X_CT0 cookies to be set.
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    def collect(self, hours_back: int = 1, cashtags: list[str] | None = None) -> list[dict]:
        """Scrape tweets containing cashtags.

        Args:
            hours_back: How far back to search.
            cashtags: List of cashtags to search (e.g. ["$AAPL", "$BTC"]).

        Returns:
            List of collected tweet dicts.
        """
        settings = get_settings()
        if not settings.x_auth_token or not settings.x_ct0:
            logger.warning("twitter_collector.no_credentials")
            return []

        if cashtags is None:
            cashtags = DEFAULT_CASHTAGS

        all_tweets = []

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("twitter_collector.playwright_not_installed")
            return []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()

            # Set auth cookies
            context.add_cookies([
                {
                    "name": "auth_token",
                    "value": settings.x_auth_token,
                    "domain": ".x.com",
                    "path": "/",
                },
                {
                    "name": "ct0",
                    "value": settings.x_ct0,
                    "domain": ".x.com",
                    "path": "/",
                },
            ])

            page = context.new_page()

            for cashtag in cashtags:
                try:
                    tweets = self._search_cashtag(page, cashtag, hours_back)
                    all_tweets.extend(tweets)
                    logger.info(
                        "twitter_collector.cashtag_done",
                        cashtag=cashtag,
                        tweets=len(tweets),
                    )
                except Exception as e:
                    logger.error(
                        "twitter_collector.cashtag_error",
                        cashtag=cashtag,
                        error=str(e),
                    )

            browser.close()

        # Persist tweets
        created = self._persist_tweets(all_tweets)
        logger.info("twitter_collector.complete", total=len(all_tweets), created=created)
        return all_tweets

    def _search_cashtag(self, page, cashtag: str, hours_back: int) -> list[dict]:
        """Search X for a specific cashtag and extract tweets."""
        query = f"{cashtag} min_faves:5"
        search_url = f"https://x.com/search?q={query}&src=typed_query&f=live"

        page.goto(search_url, wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(2000)

        tweets = []
        articles = page.query_selector_all('article[data-testid="tweet"]')

        for article in articles[:20]:  # Cap at 20 per cashtag
            try:
                tweet = self._extract_tweet(article, cashtag)
                if tweet:
                    tweets.append(tweet)
            except Exception:
                continue

        return tweets

    def _extract_tweet(self, article, cashtag: str) -> dict | None:
        """Extract tweet data from a tweet article element."""
        text_el = article.query_selector('[data-testid="tweetText"]')
        if not text_el:
            return None

        text_content = text_el.inner_text()

        # Extract author
        author_el = article.query_selector('a[role="link"] span')
        author = author_el.inner_text() if author_el else "unknown"

        # Extract engagement metrics
        likes = self._extract_metric(article, "like")
        retweets = self._extract_metric(article, "retweet")
        replies = self._extract_metric(article, "reply")

        # Extract all cashtags from the tweet
        cashtags = CASHTAG_PATTERN.findall(text_content)

        # Simple sentiment from the collector
        from fin_scraper.social.reddit_collector import _score_sentiment
        sentiment_score, sentiment_label = _score_sentiment(text_content)

        return {
            "platform": "twitter",
            "external_post_id": f"tw_{hash(text_content[:100])}",
            "author": author,
            "text": text_content[:2000],
            "cashtags": cashtags,
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "likes_count": likes,
            "retweets_count": retweets,
            "replies_count": replies,
            "posted_at": datetime.now(timezone.utc),  # Approximate
        }

    def _extract_metric(self, article, metric_type: str) -> int:
        """Extract engagement metric count from tweet."""
        try:
            el = article.query_selector(f'[data-testid="{metric_type}"]')
            if el:
                text = el.inner_text().strip()
                if text and text[0].isdigit():
                    text = text.replace(",", "").replace("K", "000").replace("M", "000000")
                    return int(float(text))
        except Exception:
            pass
        return 0

    def _persist_tweets(self, tweets: list[dict]) -> int:
        """Persist tweets to fin_social_posts."""
        created = 0
        for tweet in tweets:
            result = self.db.execute(
                text("""
                    INSERT INTO fin_social_posts
                        (platform, external_post_id, author, text,
                         cashtags, sentiment_score, sentiment_label,
                         likes_count, retweets_count, replies_count,
                         posted_at, mapping_status)
                    VALUES
                        (:platform, :external_post_id, :author, :text,
                         :cashtags, :sentiment_score, :sentiment_label,
                         :likes_count, :retweets_count, :replies_count,
                         :posted_at, 'unmapped')
                    ON CONFLICT (platform, external_post_id) DO NOTHING
                    RETURNING id
                """),
                {
                    "platform": tweet["platform"],
                    "external_post_id": tweet["external_post_id"],
                    "author": tweet["author"],
                    "text": tweet["text"],
                    "cashtags": str(tweet["cashtags"]),
                    "sentiment_score": tweet["sentiment_score"],
                    "sentiment_label": tweet["sentiment_label"],
                    "likes_count": tweet.get("likes_count", 0),
                    "retweets_count": tweet.get("retweets_count", 0),
                    "replies_count": tweet.get("replies_count", 0),
                    "posted_at": tweet["posted_at"],
                },
            )
            if result.fetchone() is not None:
                created += 1

        self.db.commit()
        return created
