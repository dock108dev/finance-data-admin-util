"""Social and news ingestion tasks.

Tasks:
    collect_social_sentiment  — Scrape Twitter/Reddit, map to assets, score sentiment
    ingest_news               — Fetch news articles from Finnhub
"""

import structlog
from celery import shared_task

from fin_scraper.db import get_db_session
from fin_scraper.services.run_manager import create_run, complete_run, fail_run

logger = structlog.get_logger(__name__)


@shared_task(name="fin_scraper.jobs.social_tasks.collect_social_sentiment")
def collect_social_sentiment(
    asset_class: str | None = None,
    hours_back: int = 1,
) -> dict:
    """Collect social media sentiment — Twitter cashtags, Reddit posts, Fear & Greed.

    Two-phase architecture:
    Phase 1 (COLLECT): Scrape posts matching cashtags
    Phase 2 (MAP): Map posts to assets, score sentiment
    """
    with get_db_session() as db:
        run = create_run(db, "social_collect", requested_by="celery_beat")
        try:
            logger.info(
                "social_collect.start",
                asset_class=asset_class,
                hours_back=hours_back,
            )

            results = {
                "twitter_posts_collected": 0,
                "reddit_posts_collected": 0,
                "posts_mapped": 0,
                "sentiment_snapshots_created": 0,
                "fear_greed_entries": 0,
            }

            all_posts = []

            # Phase 1: Collect from Reddit
            try:
                from fin_scraper.social.reddit_collector import RedditCollector
                reddit = RedditCollector(db)
                reddit_posts = reddit.collect(hours_back=hours_back)
                all_posts.extend(reddit_posts)
                results["reddit_posts_collected"] = len(reddit_posts)
            except Exception as e:
                logger.error("social_collect.reddit_error", error=str(e))

            # Phase 1: Collect from Twitter/X
            try:
                from fin_scraper.social.twitter_collector import TwitterCollector
                twitter = TwitterCollector(db)
                twitter_posts = twitter.collect(hours_back=hours_back)
                all_posts.extend(twitter_posts)
                results["twitter_posts_collected"] = len(twitter_posts)
            except Exception as e:
                logger.error("social_collect.twitter_error", error=str(e))

            # Phase 1: Collect Fear & Greed Index
            try:
                from fin_scraper.social.fear_greed import FearGreedCollector
                fg = FearGreedCollector(db)
                fg_result = fg.collect()
                results["fear_greed_entries"] = fg_result.get("entries_created", 0)
            except Exception as e:
                logger.error("social_collect.fear_greed_error", error=str(e))

            # Phase 2: Map posts to assets + aggregate sentiment
            if all_posts:
                try:
                    from fin_scraper.social.sentiment_mapper import SentimentMapper
                    mapper = SentimentMapper(db)
                    map_result = mapper.map_and_score(all_posts)
                    results["posts_mapped"] = map_result.get("posts_mapped", 0)
                    results["sentiment_snapshots_created"] = map_result.get(
                        "snapshots_created", 0
                    )
                except Exception as e:
                    logger.error("social_collect.mapper_error", error=str(e))

            complete_run(db, run, summary=str(results))
            logger.info("social_collect.complete", **results)
            return results

        except Exception as e:
            fail_run(db, run, error=str(e))
            raise


@shared_task(name="fin_scraper.jobs.social_tasks.ingest_news")
def ingest_news(hours_back: int = 1) -> dict:
    """Fetch and persist news articles from Finnhub.

    Fetches company news for all active stock tickers.
    """
    with get_db_session() as db:
        run = create_run(db, "news_ingest", requested_by="celery_beat")
        try:
            logger.info("news_ingest.start", hours_back=hours_back)

            from fin_scraper.config import get_settings
            from fin_scraper.clients.finnhub_client import FinnhubClient
            from sqlalchemy import text

            settings = get_settings()
            if not settings.finnhub_api_key:
                logger.warning("news_ingest.no_finnhub_key")
                complete_run(db, run, summary="no API key")
                return {"articles_fetched": 0, "articles_created": 0}

            client = FinnhubClient(api_key=settings.finnhub_api_key)
            results = {"articles_fetched": 0, "articles_created": 0, "tickers_matched": 0}

            # Get active stock tickers
            tickers_result = db.execute(
                text(
                    "SELECT id, ticker FROM fin_assets "
                    "WHERE asset_class_id = 1 AND is_active = true "
                    "ORDER BY ticker LIMIT 30"
                )
            )
            tickers = tickers_result.fetchall()

            for asset_id, ticker in tickers:
                try:
                    articles = client.get_company_news(ticker)
                    results["articles_fetched"] += len(articles)

                    for article in articles[:10]:  # Cap per ticker
                        result = db.execute(
                            text("""
                                INSERT INTO fin_news_articles
                                    (asset_id, title, url, source, published_at,
                                     description, category, tickers_mentioned, raw_payload)
                                VALUES
                                    (:asset_id, :title, :url, :source, :published_at,
                                     :description, :category, :tickers, :raw_payload)
                                ON CONFLICT (url) DO NOTHING
                                RETURNING id
                            """),
                            {
                                "asset_id": asset_id,
                                "title": article["title"][:500],
                                "url": article["url"],
                                "source": article["source"][:100],
                                "published_at": article["published_at"],
                                "description": article.get("description", "")[:2000],
                                "category": article.get("category", "general")[:50],
                                "tickers": str([ticker]),
                                "raw_payload": str(article.get("raw_payload", {})),
                            },
                        )
                        if result.fetchone() is not None:
                            results["articles_created"] += 1
                            results["tickers_matched"] += 1

                    db.commit()
                except Exception as e:
                    logger.error("news_ingest.ticker_error", ticker=ticker, error=str(e))

            client.close()
            complete_run(db, run, summary=str(results))
            logger.info("news_ingest.complete", **results)
            return results

        except Exception as e:
            fail_run(db, run, error=str(e))
            raise
