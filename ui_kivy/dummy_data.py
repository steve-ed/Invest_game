START_STATE = {
    "tick": 0,
    "total_ticks": 20,
    "scenario": "Baseline",
    "macro": {
        "price_index": 100.0,
        "rate": 5.0,
        "rent_growth": 2.5,
        "prev": {"price_index": 100.0, "rate": 5.0, "rent_growth": 2.5},
    },
    # Starting portfolios reflect regional price levels at price_index=100
    # (national baseline £165k). All actors start at £1,200,000 total wealth.
    "actors": [
        {
            "name": "You", "cash": 345000, "props": 5, "portfolio_value": 855000,
            "portfolio": [
                {"id": "P-011", "region": "North",    "value": 130000, "rent": 650},   # 0.79x — high yield
                {"id": "P-012", "region": "East",     "value": 200000, "rent": 750},   # 1.21x — mid
                {"id": "P-013", "region": "Midlands", "value": 145000, "rent": 664},   # 0.88x — high yield
                {"id": "P-014", "region": "South",    "value": 255000, "rent": 850},   # 1.55x — growth
                {"id": "P-015", "region": "Wales",    "value": 125000, "rent": 678},   # 0.76x — highest yield
            ],
        },
        {
            "name": "Mr Hugh Price", "cash": 190000,
            # Capital growth focus: London/South heavy, lower yield
            "portfolio": [
                {"id": "P-H01", "region": "London",  "value": 330000, "rent": 963},
                {"id": "P-H02", "region": "South",   "value": 248000, "rent": 827},
                {"id": "P-H03", "region": "South",   "value": 200000, "rent": 667},
                {"id": "P-H04", "region": "East",    "value": 142000, "rent": 533},
                {"id": "P-H05", "region": "East",    "value":  90000, "rent": 338},
            ],
        },
        {
            "name": "Mr Max Lever", "cash": 190000,
            # Leverage/income focus: high-yield regions, more properties
            "portfolio": [
                {"id": "P-M01", "region": "North",    "value": 220000, "rent": 1100},
                {"id": "P-M02", "region": "Midlands", "value": 210000, "rent": 963},
                {"id": "P-M03", "region": "Wales",    "value": 195000, "rent": 1056},
                {"id": "P-M04", "region": "North",    "value": 195000, "rent":  975},
                {"id": "P-M05", "region": "Scotland", "value": 190000, "rent":  871},
            ],
        },
    ],
    # Opening market shows the full regional spread so the player can immediately
    # see the yield vs. growth trade-off.
    "market": [
        {"id": "P-001", "region": "London",   "value": 413000, "rent": 1205},  # 2.5x — low yield, high growth
        {"id": "P-002", "region": "South",    "value": 248000, "rent": 827},
        {"id": "P-003", "region": "East",     "value": 198000, "rent": 743},
        {"id": "P-004", "region": "West",     "value": 165000, "rent": 660},
        {"id": "P-005", "region": "Midlands", "value": 140000, "rent": 642},
        {"id": "P-006", "region": "North",    "value": 124000, "rent": 620},   # 0.75x — high yield, stable
        {"id": "P-007", "region": "Scotland", "value": 132000, "rent": 605},
        {"id": "P-008", "region": "Wales",    "value": 116000, "rent": 629},
        {"id": "P-009", "region": "London",   "value": 413000, "rent": 1205},
        {"id": "P-010", "region": "East",     "value": 198000, "rent": 743},
    ],
}

GAME_STATE = {
    "tick": 4,
    "total_ticks": 20,
    "scenario": "Recovery",
    "macro": {
        "price_index": 112.4,
        "rate": 4.5,
        "rent_growth": 3.2,
        "prev": {"price_index": 109.1, "rate": 5.0, "rent_growth": 2.8},
    },
    "player": {
        "cash": 42000,
        "portfolio": [
            {"id": "P-001", "region": "North", "value": 182000, "rent": 755},
            {"id": "P-004", "region": "South", "value": 158000, "rent": 630},
        ],
    },
    "ai": [
        {
            "name": "Mr Hugh Price",
            "cash": 30000,
            "portfolio_value": 410000,
            "props": 2,
            "last_action": "hold",
            "last_property": None,
            "rationale": "waiting for rate cut",
        },
        {
            "name": "Mr Max Lever",
            "cash": 15000,
            "portfolio_value": 520000,
            "props": 4,
            "last_action": "buy",
            "last_property": "P-003",
            "rationale": "chasing highest value asset",
        },
    ],
    "market": [
        {"id": "P-002", "region": "West",  "value": 210000, "rent": 820},
        {"id": "P-005", "region": "North", "value": 340000, "rent": 1100},
        {"id": "P-009", "region": "East",  "value": 195000, "rent": 780},
    ],
    "news": [
        "! Rate shock: +1% applied",
        "> Scenario: Baseline -> Recovery",
    ],
    "leaderboard": [
        {"name": "You",           "score": 485200},
        {"name": "Mr Max Lever",  "score": 520000},
        {"name": "Mr Hugh Price", "score": 410000},
    ],
    "end": {
        "player_breakdown": {"portfolio": 750000, "cash": 62000, "rent": 80000},
        "key_events": [
            {"tick": 3,  "text": "! Rate shock: +1%"},
            {"tick": 7,  "text": "> Downturn begins"},
            {"tick": 12, "text": "! Price crash -15%"},
            {"tick": 15, "text": "> Recovery"},
        ],
    },
}


def trend(current, previous):
    if current > previous:
        return "up"
    elif current < previous:
        return "down"
    return "flat"


def trend_arrow(direction):
    return {"up": "^", "down": "v", "flat": "-"}.get(direction, "-")


def portfolio_value(player):
    return sum(p["value"] for p in player["portfolio"])


def gross_yield(prop):
    return prop["rent"] * 12 / prop["value"] * 100
