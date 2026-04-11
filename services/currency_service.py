"""
currency_service.py
────────────────────────────────────────────────────────
Uses the free open.er-api.com API (no key required for v6/latest).
Rates are cached in-memory with a configurable TTL.
"""
import time
import logging
import requests
from flask import current_app

log = logging.getLogger(__name__)

# In-memory cache: { base_currency: { 'rates': {...}, 'fetched_at': float } }
_cache: dict = {}

# Fallback rates relative to USD (used when the API is unreachable)
_FALLBACK_USD_RATES = {
    'USD': 1.0,    'INR': 83.5,  'EUR': 0.92,  'GBP': 0.79,
    'AUD': 1.53,   'CAD': 1.36,  'SGD': 1.34,  'JPY': 151.0,
    'CNY': 7.24,   'AED': 3.67,  'CHF': 0.90,  'MYR': 4.72,
    'THB': 35.1,   'NZD': 1.63,
}


class CurrencyService:

    @staticmethod
    def get_rates(base: str = 'INR') -> dict:
        """
        Return exchange rates dict { 'USD': 0.012, 'EUR': 0.011, ... }
        relative to `base`.  Results are cached per base currency.
        """
        base = base.upper()
        ttl  = current_app.config.get('EXCHANGE_CACHE_TTL_SECONDS', 3600)
        now  = time.time()

        cached = _cache.get(base)
        if cached and (now - cached['fetched_at']) < ttl:
            return cached['rates']

        try:
            api_base = current_app.config.get('EXCHANGE_API_BASE', 'https://open.er-api.com/v6/latest')
            resp = requests.get(f'{api_base}/{base}', timeout=5)
            resp.raise_for_status()
            data  = resp.json()
            rates = data.get('rates', {})
            if rates:
                _cache[base] = {'rates': rates, 'fetched_at': now}
                log.info('Currency rates refreshed for base=%s', base)
                return rates
        except Exception as exc:
            log.warning('Currency API unavailable (%s). Using fallback rates.', exc)

        # Derive fallback rates relative to requested base
        return CurrencyService._fallback_rates(base)

    @staticmethod
    def convert(amount: float, from_currency: str, to_currency: str) -> float:
        """Convert `amount` from one currency to another."""
        from_currency = from_currency.upper()
        to_currency   = to_currency.upper()
        if from_currency == to_currency:
            return round(amount, 2)

        rates = CurrencyService.get_rates(from_currency)
        rate  = rates.get(to_currency)
        if rate is None:
            log.warning('No rate found for %s→%s', from_currency, to_currency)
            return round(amount, 2)
        return round(amount * rate, 2)

    @staticmethod
    def _fallback_rates(base: str) -> dict:
        """Build approximate rates relative to `base` from hardcoded USD pivot."""
        usd_base = _FALLBACK_USD_RATES.get(base, 1.0)
        return {
            code: round(rate / usd_base, 6)
            for code, rate in _FALLBACK_USD_RATES.items()
        }
