"""Etherscan API client — token transfers, gas oracle, ETH balances."""

from datetime import datetime, timezone

import httpx
import structlog

from fin_scraper.utils.rate_limiter import RateLimiter

logger = structlog.get_logger(__name__)

BASE_URL = "https://api.etherscan.io/api"


class EtherscanClient:
    """Thin httpx wrapper for Etherscan API.

    Rate limit: 5 calls/sec, 100K calls/day on free tier.
    Auth: API key as query param.
    """

    def __init__(self, api_key: str, rate_limiter: RateLimiter | None = None):
        self._api_key = api_key
        self._limiter = rate_limiter or RateLimiter(5, 1)
        self._client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    def _request(self, params: dict) -> dict:
        """Make a rate-limited request to Etherscan."""
        params["apikey"] = self._api_key
        self._limiter.acquire()
        resp = self._client.get("", params=params)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "0" and data.get("message") != "No transactions found":
            logger.warning("etherscan.api_error", message=data.get("message"), result=data.get("result"))
        return data

    def get_eth_balance(self, address: str) -> float:
        """Get ETH balance for an address (in ETH, not wei)."""
        data = self._request({
            "module": "account",
            "action": "balance",
            "address": address,
            "tag": "latest",
        })
        wei = int(data.get("result", 0))
        return wei / 1e18

    def get_token_transfers(
        self,
        address: str,
        start_block: int = 0,
        end_block: int = 99999999,
        page: int = 1,
        offset: int = 100,
    ) -> list[dict]:
        """Get ERC-20 token transfers for an address.

        Returns:
            List of normalized transfer dicts.
        """
        data = self._request({
            "module": "account",
            "action": "tokentx",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": offset,
            "sort": "desc",
        })

        transfers = data.get("result", [])
        if not isinstance(transfers, list):
            return []

        return [
            {
                "tx_hash": tx["hash"],
                "from_address": tx["from"],
                "to_address": tx["to"],
                "token_symbol": tx.get("tokenSymbol", ""),
                "amount": int(tx.get("value", 0)) / (10 ** int(tx.get("tokenDecimal", 18))),
                "block_number": int(tx.get("blockNumber", 0)),
                "timestamp": datetime.fromtimestamp(int(tx["timeStamp"]), tz=timezone.utc),
                "gas_used": int(tx.get("gasUsed", 0)),
                "gas_price": int(tx.get("gasPrice", 0)),
            }
            for tx in transfers
        ]

    def get_normal_transactions(
        self, address: str, page: int = 1, offset: int = 50
    ) -> list[dict]:
        """Get normal (ETH) transactions for an address."""
        data = self._request({
            "module": "account",
            "action": "txlist",
            "address": address,
            "page": page,
            "offset": offset,
            "sort": "desc",
        })

        txns = data.get("result", [])
        if not isinstance(txns, list):
            return []

        return [
            {
                "tx_hash": tx["hash"],
                "from_address": tx["from"],
                "to_address": tx["to"],
                "amount": int(tx.get("value", 0)) / 1e18,  # Wei to ETH
                "token_symbol": "ETH",
                "block_number": int(tx.get("blockNumber", 0)),
                "timestamp": datetime.fromtimestamp(int(tx["timeStamp"]), tz=timezone.utc),
                "gas_used": int(tx.get("gasUsed", 0)),
                "gas_price": int(tx.get("gasPrice", 0)),
            }
            for tx in txns
        ]

    def get_gas_oracle(self) -> dict:
        """Get current gas prices.

        Returns:
            {"low": ..., "average": ..., "high": ..., "base_fee": ...} in Gwei.
        """
        data = self._request({
            "module": "gastracker",
            "action": "gasoracle",
        })
        result = data.get("result", {})

        return {
            "low": float(result.get("SafeGasPrice", 0)),
            "average": float(result.get("ProposeGasPrice", 0)),
            "high": float(result.get("FastGasPrice", 0)),
            "base_fee": float(result.get("suggestBaseFee", 0)),
            "observed_at": datetime.now(timezone.utc),
        }

    def close(self) -> None:
        self._client.close()
