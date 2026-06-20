"""Pluggable fundamentals source. v1 ships NullProvider (no fundamentals).

A future FMP/yfinance provider implements get() returning, per symbol, any of:
pe, roe, roce, market_cap. Missing keys serialize as null downstream.
"""
from abc import ABC, abstractmethod

class FundamentalsProvider(ABC):
    @abstractmethod
    def get(self, symbols: list[str]) -> dict[str, dict]:
        ...

class NullProvider(FundamentalsProvider):
    def get(self, symbols: list[str]) -> dict[str, dict]:
        return {s: {} for s in symbols}
