from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.label import Label
import dummy_data as dd
from dummy_data import trend

_MUTED      = (0.580, 0.608, 0.660, 1)
_BODY       = (0.780, 0.800, 0.836, 1)
_ACCENT     = (0, 1, 0.533, 1)
_DIM        = (0.480, 0.510, 0.560, 1)
_HL_BG      = (0.0, 0.45, 0.25, 1)
_BTN_ACTIVE = (0.0, 0.45, 0.25, 1)
_SELL_BG    = (0.45, 0.10, 0.10, 1)   # red tint for portfolio (sell) selection


class DecisionScreen(Screen):
    selected_prop      = None   # market property chosen to BUY
    selected_sell_prop = None   # portfolio property chosen to SELL
    selected_action    = None
    _actor_index       = 0

    def on_enter(self):
        self._actor_index = 0
        self._setup_for_actor()

    # ------------------------------------------------------------------ actors

    def _actor_list(self):
        return [None] + dd.GAME_STATE["ai"]

    def _is_player_turn(self):
        return self._actor_index == 0

    def _current_ai(self):
        return dd.GAME_STATE["ai"][self._actor_index - 1]

    def _current_cash(self):
        if self._is_player_turn():
            return dd.GAME_STATE["player"]["cash"]
        return self._current_ai()["cash"]

    # ----------------------------------------------------------- screen setup

    def _setup_for_actor(self):
        self.selected_prop      = None
        self.selected_sell_prop = None
        self.selected_action    = None

        actors    = self._actor_list()
        is_player = self._is_player_turn()
        is_last   = self._actor_index == len(actors) - 1

        self._update_sidebar()
        self._populate_properties(self._current_cash())

        inactive = (0.122, 0.161, 0.216, 1)
        if is_player:
            self.ids.turn_header.text  = "YOUR DECISION"
            self.ids.btn_confirm.text  = "CONFIRM  >>"
            for name in ('btn_buy', 'btn_hold', 'btn_sell'):
                self.ids[name].disabled        = False
                self.ids[name].background_color = inactive
            self._refresh_action_buttons()
            self.ids.btn_confirm.disabled = True
        else:
            ai = self._current_ai()
            self.ids.turn_header.text = "{}'S DECISION".format(ai["name"].upper())
            self.ids.btn_confirm.text = "CONTINUE  >>" if not is_last else "END TURN  >>"
            self._ai_decide(ai)
            self._highlight_ai_decision(ai)

    def _update_sidebar(self):
        gs = dd.GAME_STATE
        m  = gs["macro"]
        sb = self.ids.sidebar
        sb.tick        = gs["tick"]
        sb.total_ticks = gs["total_ticks"]
        sb.scenario    = gs["scenario"]
        sb.price_index = m["price_index"]
        sb.price_trend = trend(m["price_index"], m["prev"]["price_index"])
        sb.rate        = m["rate"]
        sb.rate_trend  = trend(m["rate"], m["prev"]["rate"])
        sb.rent_growth = m["rent_growth"]
        sb.rent_trend  = trend(m["rent_growth"], m["prev"]["rent_growth"])
        sb.cash        = self._current_cash()
        sb.show_cash   = 1
        player       = gs["player"]
        player_score = sum(p["value"] for p in player["portfolio"]) + player["cash"]
        for entry in gs["leaderboard"]:
            if entry["name"] == "You":
                entry["score"] = player_score
                break
        sorted_lb = sorted(gs["leaderboard"], key=lambda x: x["score"], reverse=True)
        sb.rank  = next((i + 1 for i, e in enumerate(sorted_lb) if e["name"] == "You"), 1)
        sb.score = player_score

    # ----------------------------------------------------- property panel

    def _section_lbl(self, text):
        lbl = Label(text=text, color=_MUTED, font_size='12sp',
                    halign='left', valign='middle',
                    size_hint_y=None, height='22dp')
        lbl.bind(size=lbl.setter('text_size'))
        return lbl

    def _prop_btn(self, prop, color, affordable):
        yld = prop["rent"] * 12 / prop["value"] * 100
        text = "{id}  {region}  \u00a3{value:,.0f}  \u00a3{rent:,.0f}/mo  {yld:.1f}%".format(
            id=prop["id"], region=prop["region"],
            value=prop["value"], rent=prop["rent"], yld=yld,
        )
        if affordable is not None:
            text += "  " + ("affordable" if affordable else "too expensive")
        btn = Button(text=text, color=color, font_size='14sp',
                     halign='left', valign='middle',
                     size_hint_y=None, height='42dp',
                     background_normal='', background_color=(0, 0, 0, 0))
        btn._prop_id    = prop["id"]
        btn._orig_color = color
        return btn

    def _populate_properties(self, actor_cash):
        gs  = dd.GAME_STATE
        box = self.ids.market_box
        box.clear_widgets()
        is_player = self._is_player_turn()

        # --- market section ---
        box.add_widget(self._section_lbl("MARKET"))
        for prop in gs["market"]:
            affordable = prop["value"] <= actor_cash
            color = _BODY if affordable else _DIM
            btn = self._prop_btn(prop, color, affordable)
            if affordable and is_player:
                btn.bind(on_press=lambda b, p=prop: self._select_buy_prop(p, b))
            box.add_widget(btn)

        # --- portfolio section (player turn only) ---
        if is_player:
            portfolio = gs["player"]["portfolio"]
            if portfolio:
                box.add_widget(self._section_lbl("YOUR PORTFOLIO  (click to sell)"))
                for prop in portfolio:
                    btn = self._prop_btn(prop, _BODY, None)
                    btn.bind(on_press=lambda b, p=prop: self._select_sell_prop_btn(p, b))
                    box.add_widget(btn)

    # ------------------------------------------------------------- player UI

    def _clear_prop_highlights(self):
        for child in self.ids.market_box.children:
            if hasattr(child, '_orig_color'):
                child.background_color = (0, 0, 0, 0)
                child.color = child._orig_color

    def _select_buy_prop(self, prop, btn):
        self.selected_prop      = prop
        self.selected_sell_prop = None
        self._clear_prop_highlights()
        btn.background_color = _HL_BG
        btn.color            = _ACCENT
        self._refresh_action_buttons()
        self.select_action('buy')   # also calls _refresh_confirm_button

    def _select_sell_prop_btn(self, prop, btn):
        self.selected_sell_prop = prop
        self.selected_prop      = None
        self._clear_prop_highlights()
        btn.background_color = _SELL_BG
        btn.color            = (1, 0.6, 0.6, 1)
        self._refresh_action_buttons()
        self.select_action('sell')  # also calls _refresh_confirm_button

    def _refresh_action_buttons(self):
        gs = dd.GAME_STATE
        self.ids.btn_buy.disabled  = self.selected_prop is None
        self.ids.btn_hold.disabled = False
        self.ids.btn_sell.disabled = len(gs["player"]["portfolio"]) == 0

    def select_action(self, action):
        self.selected_action = action
        inactive = (0.122, 0.161, 0.216, 1)
        for name in ('btn_buy', 'btn_hold', 'btn_sell'):
            self.ids[name].background_color = _BTN_ACTIVE if name == 'btn_' + action else inactive
        self._refresh_confirm_button()

    def _refresh_confirm_button(self):
        if not self._is_player_turn():
            self.ids.btn_confirm.disabled = False
            return
        gs = dd.GAME_STATE
        can_confirm = (
            self.selected_action == 'hold'
            or (self.selected_action == 'buy'  and self.selected_prop is not None)
            or (self.selected_action == 'sell' and len(gs["player"]["portfolio"]) > 0)
        )
        self.ids.btn_confirm.disabled = not can_confirm

    # -------------------------------------------------------------- AI logic

    def _ai_decide(self, ai):
        gs = dd.GAME_STATE
        affordable = [p for p in gs["market"] if p["value"] <= ai["cash"]]
        if affordable:
            if ai["name"] == "Aggressive":
                chosen = max(affordable, key=lambda p: p["value"])
                ai["rationale"] = "maximum exposure"
            else:
                good = [p for p in affordable if p["rent"] * 12 / p["value"] * 100 > 4.0]
                chosen = min(good or affordable, key=lambda p: p["value"])
                ai["rationale"] = "defensive yield"
            ai["last_action"]   = "buy"
            ai["last_property"] = chosen["id"]
        else:
            ai["last_action"]   = "hold"
            ai["last_property"] = None
            ai["rationale"]     = "insufficient cash"

    def _highlight_ai_decision(self, ai):
        if ai["last_property"]:
            for child in self.ids.market_box.children:
                if getattr(child, '_prop_id', None) == ai["last_property"]:
                    child.background_color = _HL_BG
                    child.color = _ACCENT
        self.select_action(ai["last_action"])
        for name in ('btn_buy', 'btn_hold', 'btn_sell'):
            self.ids[name].disabled = True

    # ---------------------------------------------------------------- confirm

    def confirm(self):
        gs = dd.GAME_STATE
        if self._is_player_turn():
            self._apply_player_action(gs)
        else:
            self._apply_ai_action(gs, self._current_ai())

        self._actor_index += 1
        if self._actor_index < len(self._actor_list()):
            self._setup_for_actor()
        else:
            self._advance_tick(gs)
            gs["tick"] += 1
            self.manager.current = 'end' if gs["tick"] >= gs["total_ticks"] else 'turn'

    def _apply_player_action(self, gs):
        player = gs["player"]
        if self.selected_action == "buy" and self.selected_prop:
            prop = next((p for p in gs["market"] if p["id"] == self.selected_prop["id"]), None)
            if prop and player["cash"] >= prop["value"]:
                player["cash"] -= prop["value"]
                player["portfolio"].append(prop)
                gs["market"].remove(prop)
        elif self.selected_action == "sell" and player["portfolio"]:
            prop = (
                next((p for p in player["portfolio"] if p["id"] == self.selected_sell_prop["id"]), None)
                if self.selected_sell_prop else None
            ) or player["portfolio"][0]
            player["portfolio"].remove(prop)
            player["cash"] += prop["value"]
            gs["market"].append(prop)

    def _apply_ai_action(self, gs, ai):
        if ai["last_action"] == "buy" and ai["last_property"]:
            prop = next((p for p in gs["market"] if p["id"] == ai["last_property"]), None)
            if prop:
                ai["cash"]           -= prop["value"]
                ai["portfolio_value"] += prop["value"]
                ai["props"]           += 1
                gs["market"].remove(prop)

    def _advance_tick(self, gs):
        player = gs["player"]
        m      = gs["macro"]
        growth = (m["price_index"] - m["prev"]["price_index"]) / m["prev"]["price_index"] / 2
        player["cash"] += sum(p["rent"] for p in player["portfolio"]) * 6
        for p in player["portfolio"]:
            p["value"] = int(p["value"] * (1 + growth))
        for ai in gs["ai"]:
            ai["cash"]            += int(ai["portfolio_value"] * 0.05 / 2)
            ai["portfolio_value"]  = int(ai["portfolio_value"] * (1 + growth))
