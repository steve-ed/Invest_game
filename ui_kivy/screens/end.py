from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
import dummy_data as dd

_ACTOR_COLORS = {
    "You":          (0, 1, 0.533, 1),
    "Conservative": (0.984, 0.749, 0.141, 1),
    "Aggressive":   (0.973, 0.443, 0.443, 1),
}
_MUTED  = (0.580, 0.608, 0.660, 1)
_BODY   = (0.780, 0.800, 0.836, 1)
_BRIGHT = (0.976, 0.980, 0.984, 1)
_ACCENT = (0, 1, 0.533, 1)
_DIM    = (0.480, 0.510, 0.560, 1)


def _lbl(**kw):
    l = Label(**kw)
    l.bind(size=l.setter('text_size'))
    return l


class EndScreen(Screen):
    def on_enter(self):
        self._populate_leaderboard()
        self._populate_breakdown()
        self._populate_events()

    def _populate_leaderboard(self):
        box = self.ids.leaderboard_box
        box.clear_widgets()
        sorted_lb = sorted(dd.GAME_STATE["leaderboard"], key=lambda x: x["score"], reverse=True)
        for i, entry in enumerate(sorted_lb):
            winner = i == 0
            row = BoxLayout(size_hint_y=None, height='32dp', spacing='12dp')
            row.add_widget(_lbl(
                text=str(i + 1),
                color=_ACCENT if winner else _MUTED,
                font_size='14sp', size_hint_x=None, width='28dp',
                halign='left', valign='middle',
            ))
            row.add_widget(_lbl(
                text=entry["name"],
                color=_ACTOR_COLORS.get(entry["name"], _BODY),
                font_size='14sp', halign='left', valign='middle',
            ))
            row.add_widget(_lbl(
                text='\u00a3{:,.0f}'.format(entry["score"]),
                color=_BRIGHT if winner else _BODY,
                font_size='14sp', bold=winner, halign='right', valign='middle',
            ))
            box.add_widget(row)

    def _populate_breakdown(self):
        bd = dd.GAME_STATE["end"]["player_breakdown"]
        box = self.ids.breakdown_box
        box.clear_widgets()
        for label, value, color in [
            ("Portfolio value",  bd["portfolio"], _BODY),
            ("Cash",             bd["cash"],      _BODY),
            ("Cumulative rent",  bd["rent"],      _ACCENT),
        ]:
            row = BoxLayout(size_hint_y=None, height='28dp')
            row.add_widget(_lbl(text=label, color=_MUTED, font_size='14sp',
                                halign='left', valign='middle'))
            row.add_widget(_lbl(text='\u00a3{:,.0f}'.format(value), color=color,
                                font_size='14sp', halign='right', valign='middle'))
            box.add_widget(row)

    def _populate_events(self):
        box = self.ids.events_box
        box.clear_widgets()
        for ev in dd.GAME_STATE["end"]["key_events"]:
            box.add_widget(_lbl(
                text='T{}  {}'.format(ev["tick"], ev["text"]),
                color=_DIM, font_size='13sp',
                halign='left', valign='middle',
                size_hint_y=None, height='26dp',
            ))

    def play_again(self):
        dd.GAME_STATE["tick"] = 1
        self.manager.current = 'opening'
