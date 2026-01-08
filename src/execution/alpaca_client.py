from typing import Dict, List, Any
from src.execution.broker_interface import BrokerClient
import logging

logger = logging.getLogger(__name__)

class AlpacaBrokerClient(BrokerClient):
    """
    Real Alpaca Broker Client (Skeleton).
    Uses Alpaca Trading API.
    """
    def __init__(self, api_key: str, secret_key: str, base_url: str = "https://paper-api.alpaca.markets"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url
        # TODO: Initialize requests session or alpaca-trade-api

    def get_account(self) -> Dict[str, Any]:
        # TODO: Call GET /v2/account
        logger.warning("AlpacaBrokerClient.get_account not implemented yet.")
        return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        # TODO: Call GET /v2/positions
        logger.warning("AlpacaBrokerClient.get_positions not implemented yet.")
        return []

    def submit_order(self, symbol: str, qty: int, side: str, type: str = "market", time_in_force: str = "day") -> Dict[str, Any]:
        # TODO: Call POST /v2/orders
        logger.warning(f"AlpacaBrokerClient.submit_order({symbol}, {side}) not implemented yet.")
        return {}

    def close_all_positions(self) -> List[Dict[str, Any]]:
        # TODO: Call DELETE /v2/positions
        logger.warning("AlpacaBrokerClient.close_all_positions not implemented yet.")
        return []
