import copy
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
import dummy_data as dd

_ACTOR_COLORS = {
    "You":          (0, 1, 0.533, 1),
    "Conservative": (0.984, 0.749, 0.141, 1),
    "Aggressive":   (0.973, 0.443, 0.443, 1),
}
_MUTED  = (0.580, 0.608, 0.660, 1)
_BODY   = (0.780, 0.800, 0.836, 1)
_ACCENT = (0, 1, 0.533, 1)


def _lbl(**kw):
    l = Label(**kw)
    l.bind(size=l.setter('text_size'))
    return l


class OpeningScreen(Screen):
    def on_enter(self):
        self._populate_actors()
        self._populate_market()
        self._populate_macro()

    def _populate_actors(self):
        grid = self.ids.actors_grid
        grid.clear_widgets()
        for h in ("Actor", "Props", "Portfolio", "Cash"):
            grid.add_widget(_lbl(text=h, color=_MUTED, font_size='13sp',
                                 halign='left', valign='middle'))
        for actor in dd.START_STATE["actors"]:
            nc = _ACTOR_COLORS.get(actor["name"], _BODY)
            grid.add_widget(_lbl(text=actor["name"], color=nc, font_size='14sp',
                                 halign='left', valign='middle'))
            grid.add_widget(_lbl(text=str(actor["props"]), color=_BODY, font_size='14sp',
                                 halign='right', valign='middle'))
            grid.add_widget(_lbl(text='\u00a3{:,.0f}'.format(actor["portfolio_value"]),
                                 color=_BODY, font_size='14sp', halign='right', valign='middle'))
            grid.add_widget(_lbl(text='\u00a3{:,.0f}'.format(actor["cash"]),
                                 color=nc, font_size='14sp', halign='right', valign='middle'))

    def _populate_market(self):
        grid = self.ids.market_grid
        grid.clear_widgets()
        for h in ("ID", "Region", "Value", "Rent/mo", "Yield"):
            grid.add_widget(_lbl(text=h, color=_MUTED, font_size='13sp',
                                 halign='left', valign='middle'))
        for prop in dd.START_STATE["market"]:
            yld = prop["rent"] * 12 / prop["value"] * 100
            grid.add_widget(_lbl(text=prop["id"], color=_BODY, font_size='14sp',
                                 halign='left', valign='middle'))
            grid.add_widget(_lbl(text=prop["region"], color=_BODY, font_size='14sp',
                                 halign='left', valign='middle'))
            grid.add_widget(_lbl(text='\u00a3{:,.0f}'.format(prop["value"]),
                                 color=_BODY, font_size='14sp', halign='right', valign='middle'))
            grid.add_widget(_lbl(text='\u00a3{:,.0f}'.format(prop["rent"]),
                                 color=_BODY, font_size='14sp', halign='right', valign='middle'))
            grid.add_widget(_lbl(text='{:.1f}%'.format(yld), color=_ACCENT, font_size='14sp',
                                 halign='right', valign='middle'))

    def _populate_macro(self):
        m = dd.START_STATE["macro"]
        self.ids.macro_price.text = '{:.1f}'.format(m["price_index"])
        self.ids.macro_rate.text = '{:.1f}%'.format(m["rate"])
        self.ids.macro_rent.text = '{:.1f}%'.format(m["rent_growth"])

    def start_game(self):
        ss = dd.START_STATE
        player = next(a for a in ss["actors"] if a["name"] == "You")
        ai_actors = [a for a in ss["actors"] if a["name"] != "You"]
        dd.GAME_STATE.update({
            "tick": 1,
            "total_ticks": ss["total_ticks"],
            "scenario": ss["scenario"],
            "macro": copy.deepcopy(ss["macro"]),
            "player": {
                "cash": player["cash"],
                "portfolio": copy.deepcopy(player.get("portfolio", [])),
            },
            "ai": [
                {
                    "name": a["name"],
                    "cash": a["cash"],
                    "portfolio_value": a["portfolio_value"],
                    "props": a["props"],
                    "last_action": "hold",
                    "last_property": None,
                    "rationale": "",
                }
                for a in ai_actors
            ],
            "market": copy.deepcopy(ss["market"]),
            "news": [],
            "leaderboard": [
                {"name": a["name"], "score": a["cash"] + a["portfolio_value"]}
                for a in ss["actors"]
            ],
        })
        self.manager.current = 'turn'
