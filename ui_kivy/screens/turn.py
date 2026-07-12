from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
import dummy_data as dd
from dummy_data import trend

_AI_COLORS = {
    "Conservative": (0.984, 0.749, 0.141, 1),
    "Aggressive":   (0.973, 0.443, 0.443, 1),
}
_MUTED  = (0.580, 0.608, 0.660, 1)
_BODY   = (0.780, 0.800, 0.836, 1)
_ACCENT = (0, 1, 0.533, 1)
_DIM    = (0.480, 0.510, 0.560, 1)
_BUY    = _ACCENT
_SELL   = (0.973, 0.443, 0.443, 1)


def _lbl(**kw):
    l = Label(**kw)
    l.bind(size=l.setter('text_size'))
    return l


class TurnScreen(Screen):
    def on_enter(self):
        self._update_sidebar()
        self._populate_portfolio()
        self._populate_ai()
        self._populate_news()

    def _update_sidebar(self):
        gs = dd.GAME_STATE
        m = gs["macro"]
        sb = self.ids.sidebar
        sb.tick = gs["tick"]
        sb.total_ticks = gs["total_ticks"]
        sb.scenario = gs["scenario"]
        sb.price_index = m["price_index"]
        sb.price_trend = trend(m["price_index"], m["prev"]["price_index"])
        sb.rate = m["rate"]
        sb.rate_trend = trend(m["rate"], m["prev"]["rate"])
        sb.rent_growth = m["rent_growth"]
        sb.rent_trend = trend(m["rent_growth"], m["prev"]["rent_growth"])
        player = gs["player"]
        player_score = sum(p["value"] for p in player["portfolio"]) + player["cash"]
        for entry in gs["leaderboard"]:
            if entry["name"] == "You":
                entry["score"] = player_score
                break
        sorted_lb = sorted(gs["leaderboard"], key=lambda x: x["score"], reverse=True)
        sb.rank = next((i + 1 for i, e in enumerate(sorted_lb) if e["name"] == "You"), 1)
        sb.score = player_score

    def _populate_portfolio(self):
        gs = dd.GAME_STATE
        player = gs["player"]
        total = sum(p["value"] for p in player["portfolio"])
        self.ids.portfolio_value_label.text = '\u00a3{:,.0f}'.format(total)
        self.ids.cash_label.text = 'cash \u00a3{:,.0f}'.format(player["cash"])
        grid = self.ids.portfolio_grid
        grid.clear_widgets()
        for prop in player["portfolio"]:
            yld = prop["rent"] * 12 / prop["value"] * 100
            for text, color, align in [
                (prop["id"],                              _BODY,   'left'),
                (prop["region"],                          _BODY,   'left'),
                ('\u00a3{:,.0f}'.format(prop["value"]),  _BODY,   'right'),
                ('\u00a3{:,.0f}/mo'.format(prop["rent"]),_BODY,   'right'),
                ('{:.1f}%'.format(yld),                  _ACCENT, 'right'),
            ]:
                grid.add_widget(_lbl(text=text, color=color, font_size='14sp',
                                     halign=align, valign='middle'))

    def _populate_ai(self):
        box = self.ids.ai_box
        box.clear_widgets()
        for ai in dd.GAME_STATE["ai"]:
            name_color = _AI_COLORS.get(ai["name"], _BODY)
            action = ai["last_action"]
            prop = ai.get("last_property")
            rationale = ai.get("rationale", "")

            if action == "buy" and prop:
                action_text = "bought {}".format(prop)
                action_color = _BUY
            elif action == "sell" and prop:
                action_text = "sold {}".format(prop)
                action_color = _SELL
            else:
                action_text = "held"
                action_color = _MUTED

            block = BoxLayout(orientation='vertical', size_hint_y=None, height='52dp')

            # Line 1: name (strategy color) + portfolio summary (muted)
            line1 = BoxLayout(orientation='horizontal')
            line1.add_widget(_lbl(
                text=ai["name"], color=name_color, font_size='14sp',
                halign='left', valign='middle', size_hint_x=0.35,
            ))
            line1.add_widget(_lbl(
                text="\u00a3{:,.0f}   {} props".format(ai["portfolio_value"], ai["props"]),
                color=_BODY, font_size='14sp',
                halign='left', valign='middle', size_hint_x=0.65,
            ))
            block.add_widget(line1)

            # Line 2: action verb (colored) + rationale (dim)
            line2 = BoxLayout(orientation='horizontal')
            verb = "> {}".format(action_text)
            line2.add_widget(_lbl(
                text=verb, color=action_color, font_size='13sp',
                halign='left', valign='middle', size_hint_x=0.4,
            ))
            if rationale:
                line2.add_widget(_lbl(
                    text="--  {}".format(rationale), color=_DIM, font_size='13sp',
                    halign='left', valign='middle', size_hint_x=0.6,
                ))
            block.add_widget(line2)
            box.add_widget(block)

    def _populate_news(self):
        box = self.ids.news_box
        box.clear_widgets()
        for item in dd.GAME_STATE["news"][-2:]:
            box.add_widget(_lbl(text=item, color=_DIM, font_size='14sp',
                                halign='left', valign='middle',
                                size_hint_y=None, height='26dp'))
