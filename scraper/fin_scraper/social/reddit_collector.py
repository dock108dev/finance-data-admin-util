"""Reddit collector — PRAW-based scraping of r/wallstreetbets, r/cryptocurrency, r/stocks.

Extracts cashtags via regex, computes keyword-based sentiment scoring.
"""

import re
from datetime import datetime, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from fin_scraper.config import get_settings

logger = structlog.get_logger(__name__)

# Regex for cashtags: $AAPL, $BTC, etc.
CASHTAG_PATTERN = re.compile(r"\$([A-Z]{1,5})\b")

# Target subreddits
SUBREDDITS = ["wallstreetbets", "cryptocurrency", "stocks"]

# Simple keyword-based sentiment scoring
BULLISH_KEYWORDS = {
    "buy", "bull", "bullish", "moon", "rocket", "long", "calls", "breakout",
    "pump", "green", "ath", "dip", "undervalued", "hodl", "diamond hands",
    "tendies", "gains", "rally", "squeeze", "yolo",
}
BEARISH_KEYWORDS = {
    "sell", "bear", "bearish", "crash", "dump", "short", "puts", "overvalued",
    "red", "bag", "loss", "drop", "tank", "rug", "scam", "bubble",
    "paper hands", "correction", "decline",
}


def _score_sentiment(text_content: str) -> tuple[float, str]:
    """Simple keyword-based sentiment scoring.

    Returns:
        (score, label) where score is -1.0 to +1.0 and label is
        'bullish', 'bearish', or 'neutral'.
    """
    words = set(text_content.lower().split())
    bull_count = len(words & BULLISH_KEYWORDS)
    bear_count = len(words & BEARISH_KEYWORDS)
    total = bull_count + bear_count

    if total == 0:
        return 0.0, "neutral"

    score = (bull_count - bear_count) / total
    label = "bullish" if score > 0.1 else "bearish" if score < -0.1 else "neutral"
    return round(score, 3), label


class RedditCollector:
    """Collect posts from financial subreddits via PRAW."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self._reddit = None

    def _get_reddit(self):
        """Lazy-init PRAW Reddit instance."""
        if self._reddit is None:
            import praw
            settings = get_settings()
            self._reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                user_agent=settings.reddit_user_agent,
            )
        return self._reddit

    def collect(self, hours_back: int = 1, limit: int = 50) -> list[dict]:
        """Collect recent posts from target subreddits.

        Args:
            hours_back: How far back to look (hours).
            limit: Max posts per subreddit.

        Returns:
            List of collected post dicts.
        """
        settings = get_settings()
        if not settings.reddit_client_id:
            logger.warning("reddit_collector.no_credentials")
            return []

        all_posts = []
        reddit = self._get_reddit()
        cutoff = datetime.now(timezone.utc).timestamp() - (hours_back * 3600)

        for subreddit_name in SUBREDDITS:
            try:
                subreddit = reddit.subreddit(subreddit_name)
                for post in subreddit.new(limit=limit):
                    if post.created_utc < cutoff:
                        continue

                    text_content = f"{post.title} {post.selftext or ''}"
                    cashtags = CASHTAG_PATTERN.findall(text_content)
                    sentiment_score, sentiment_label = _score_sentiment(text_content)

                    post_data = {
                        "platform": "reddit",
                        "external_post_id": post.id,
                        "post_url": f"https://reddit.com{post.permalink}",
                        "author": str(post.author) if post.author else "[deleted]",
                        "text": text_content[:2000],
                        "cashtags": cashtags,
                        "sentiment_score": sentiment_score,
                        "sentiment_label": sentiment_label,
                        "score": post.score,
                        "replies_count": post.num_comments,
                        "posted_at": datetime.fromtimestamp(
                            post.created_utc, tz=timezone.utc
                        ),
                        "subreddit": subreddit_name,
                    }
                    all_posts.append(post_data)

                logger.info(
                    "reddit_collector.subreddit_done",
                    subreddit=subreddit_name,
                    posts=len([p for p in all_posts if p["subreddit"] == subreddit_name]),
                )
            except Exception as e:
                logger.error(
                    "reddit_collector.subreddit_error",
                    subreddit=subreddit_name,
                    error=str(e),
                )

        # Persist posts
        created = self._persist_posts(all_posts)
        logger.info("reddit_collector.complete", total=len(all_posts), created=created)
        return all_posts

    def _persist_posts(self, posts: list[dict]) -> int:
        """Persist posts to fin_social_posts."""
        created = 0
        for post in posts:
            result = self.db.execute(
                text("""
                    INSERT INTO fin_social_posts
                        (platform, external_post_id, post_url, author, text,
                         cashtags, sentiment_score, sentiment_label, score,
                         replies_count, posted_at, mapping_status)
                    VALUES
                        (:platform, :external_post_id, :post_url, :author, :text,
                         :cashtags, :sentiment_score, :sentiment_label, :score,
                         :replies_count, :posted_at, 'unmapped')
                    ON CONFLICT (platform, external_post_id) DO NOTHING
                    RETURNING id
                """),
                {
                    "platform": post["platform"],
                    "external_post_id": post["external_post_id"],
                    "post_url": post["post_url"],
                    "author": post["author"],
                    "text": post["text"],
                    "cashtags": str(post["cashtags"]),  # JSONB
                    "sentiment_score": post["sentiment_score"],
                    "sentiment_label": post["sentiment_label"],
                    "score": post.get("score", 0),
                    "replies_count": post.get("replies_count", 0),
                    "posted_at": post["posted_at"],
                },
            )
            if result.fetchone() is not None:
                created += 1

        self.db.commit()
        return created
