"""
Startup валидация — проверява всички connections преди старт.
Работи в paper и live режим.
"""
import logging
import requests
import config

log = logging.getLogger(__name__)

CLOB = "https://clob.polymarket.com"


def _check_polymarket_connectivity() -> bool:
    try:
        r = requests.get(f"{CLOB}/markets", params={"limit": 1}, timeout=5)
        r.raise_for_status()
        log.info("  ✅ Polymarket CLOB API — достъпен")
        return True
    except Exception as e:
        log.error(f"  ❌ Polymarket CLOB API — грешка: {e}")
        return False


def _check_wallet() -> bool:
    if not config.PRIVATE_KEY or config.PRIVATE_KEY.startswith("0xYOUR"):
        log.warning("  ⚠️  POLYMARKET_PRIVATE_KEY не е конфигуриран")
        return not config.PAPER_TRADING   # критично само в live режим
    try:
        from py_clob_client.client import ClobClient
        from py_clob_client.constants import POLYGON
        client = ClobClient(host=CLOB, key=config.PRIVATE_KEY, chain_id=POLYGON)
        creds  = client.create_or_derive_api_creds()
        log.info(f"  ✅ Wallet валиден — API key: {creds.api_key[:12]}…")
        return True
    except Exception as e:
        log.error(f"  ❌ Wallet грешка: {e}")
        return False


def _check_pandascore() -> bool:
    if not config.PANDASCORE_KEY:
        log.info("  ⏭️  Pandascore — не е конфигуриран (пропускам)")
        return True
    try:
        r = requests.get(
            "https://api.pandascore.co/matches/running",
            headers={"Authorization": f"Bearer {config.PANDASCORE_KEY}"},
            timeout=5,
        )
        r.raise_for_status()
        log.info(f"  ✅ Pandascore — OK ({len(r.json())} live мача)")
        return True
    except Exception as e:
        log.error(f"  ❌ Pandascore: {e}")
        return False


def _check_sportdevs() -> bool:
    if not config.SPORTDEVS_KEY:
        log.info("  ⏭️  SportDevs — не е конфигуриран (пропускам)")
        return True
    try:
        r = requests.get(
            "https://api.sportdevs.com/football/matches/live",
            headers={"x-api-key": config.SPORTDEVS_KEY},
            timeout=5,
        )
        r.raise_for_status()
        log.info("  ✅ SportDevs — OK")
        return True
    except Exception as e:
        log.error(f"  ❌ SportDevs: {e}")
        return False


def _check_tokens() -> bool:
    """Провери дали token_id-тата в WATCH_LIST са валидни на Polymarket."""
    all_ok = True
    for watch in config.WATCH_LIST:
        for key in ["token_a", "token_b"]:
            token = watch.get(key, "")
            if not token or token.startswith("0xTOKEN"):
                log.warning(f"  ⚠️  {watch['team_a']} vs {watch['team_b']} — {key} не е попълнен")
                all_ok = False
    return all_ok


def run_checks() -> bool:
    """Изпълни всички проверки. Върни True ако е безопасно да се стартира."""
    mode = "PAPER 🧪" if config.PAPER_TRADING else "⚠️  LIVE — РЕАЛНИ ПАРИ ⚠️"
    log.info(f"╔══ Startup валидация │ Режим: {mode}")

    results = {
        "Polymarket connectivity": _check_polymarket_connectivity(),
        "Wallet":                  _check_wallet(),
        "Pandascore":              _check_pandascore(),
        "SportDevs":               _check_sportdevs(),
        "Token IDs":               _check_tokens(),
    }

    ok = all(results.values())

    log.info("╠══ Резултат:")
    for name, passed in results.items():
        icon = "✅" if passed else "❌"
        log.info(f"║   {icon} {name}")

    if ok:
        log.info("╚══ Всички проверки минаха — стартирам бота.")
    else:
        log.error("╚══ Има грешки — поправи конфигурацията преди да продължиш.")

    return ok
