# Polymarket Multi-Sport Bot

Автоматичен бот, който следи live резултати от няколко API и залага на Polymarket когато открие edge между implied вероятност (от score) и market odds.

## Инсталация

```bash
pip install -r requirements.txt
cp .env.example .env
# Попълни .env с твоите ключове
```

## Стартиране

```bash
python main.py
```

## Архитектура

```
adapters/
  pandascore.py  — LoL, CS2, Dota2, Valorant
  riot.py        — Live LoL gold/kills (Local Client или Spectator)
  sportdevs.py   — Football, Basketball, Tennis

prob_models/
  esports.py     — Binomial BO3/BO5 + gold correction
  football.py    — Poisson model (Dixon-Coles inspired)
  basketball.py  — Normal approximation (margin / sqrt(possessions))
  tennis.py      — Markov chain (game → set → match)

registry.py      — Свързва sport → adapter + model
strategy.py      — Edge detection + BUY/SELL/HOLD сигнали
polymarket_client.py — CLOB API wrapper
main.py          — Multi-threaded главен цикъл
config.py        — Конфигурация от .env
```

## Добавяне на нов спорт

1. Добави `Sport.NEWGAME` в `models.py`
2. Имплементирай `BaseAdapter` в `adapters/`
3. Имплементирай `BaseProbModel` в `prob_models/`
4. Регистрирай в `registry.py`
5. Добави мач в `WATCH_LIST` в `config.py`

## Probability модели

| Спорт      | Модел                                    |
|------------|------------------------------------------|
| LoL/CS2    | Binomial BO series + Riot gold lead      |
| Football   | Poisson (goals remaining)                |
| Basketball | Normal approx (margin / √possessions)    |
| Tennis     | Markov chain game → set → match          |
