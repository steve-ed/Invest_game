from kivy.uix.boxlayout import BoxLayout
from kivy.properties import NumericProperty, StringProperty


class MacroSidebar(BoxLayout):
    tick = NumericProperty(0)
    total_ticks = NumericProperty(20)
    scenario = StringProperty("")
    price_index = NumericProperty(100.0)
    price_trend = StringProperty("flat")
    rate = NumericProperty(5.0)
    rate_trend = StringProperty("flat")
    rent_growth = NumericProperty(2.5)
    rent_trend = StringProperty("flat")
    rank = NumericProperty(1)
    score = NumericProperty(0)
    cash = NumericProperty(0)
    show_cash = NumericProperty(0)
