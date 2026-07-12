import os
os.environ.setdefault('KIVY_NO_CONSOLELOG', '1')

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, SlideTransition

Builder.load_file('widgets/macro_sidebar.kv')
Builder.load_file('screens/opening.kv')
Builder.load_file('screens/turn.kv')
Builder.load_file('screens/decision.kv')
Builder.load_file('screens/end.kv')

from screens.opening import OpeningScreen
from screens.turn import TurnScreen
from screens.decision import DecisionScreen
from screens.end import EndScreen


class RealEstApp(App):
    def build(self):
        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(OpeningScreen(name='opening'))
        sm.add_widget(TurnScreen(name='turn'))
        sm.add_widget(DecisionScreen(name='decision'))
        sm.add_widget(EndScreen(name='end'))
        return sm


if __name__ == '__main__':
    RealEstApp().run()
