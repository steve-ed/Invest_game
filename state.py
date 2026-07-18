from dataclasses import dataclass, field


@dataclass
class MacroState:
    price_index: float = 100.0
    interest_rate: float = 0.05
    rent_growth: float = 0.03


@dataclass
class MacroSnapshot:
    tick: int
    scenario: str
    price_index: float
    interest_rate: float
    rent_growth: float
    events: list


@dataclass
class Property:
    id: str
    region: str
    base_value: float
    current_value: float
    rent: float                        # monthly rent (£)
    archetype: str = "btl"            # btl | hmo | short_let | new_build | value_add
    epc_band: int = 4                 # 1=A (best) … 7=G (worst)
    age: int = 40                     # years
    mortgage_balance: float = 0.0
    mortgage_rate: float = 0.0        # fixed at purchase if is_fixed_rate
    is_fixed_rate: bool = False
    fixed_ticks_remaining: int = 0
    void_ticks_remaining: int = 0     # ticks of zero rent after acquisition
    epc_void: bool = False            # permanently void until EPC upgraded to C or better
    renovated: bool = False           # tracks whether property has been renovated (once only)
    is_auction: bool = False          # marks property as auction listing (removed after 1 tick if unsold)
    bedrooms: int = 3
    hpi_factor: float = 1.0          # regional HPI sensitivity multiplier


@dataclass
class ActorState:
    id: str
    name: str
    cash: float
    risk_appetite: float
    portfolio: list = field(default_factory=list)
    strategy: str = "balanced"        # yield | capital | value_add | brrr | leverage | demographic | balanced
    total_rent_received: float = 0.0
    total_mortgage_paid: float = 0.0
    total_transaction_costs: float = 0.0
    total_void_losses: float = 0.0
    total_maintenance_costs: float = 0.0
    total_insurance_paid: float = 0.0
    initial_wealth: float = 0.0


@dataclass
class SimulationState:
    tick: int = 0
    current_scenario: str = "baseline"
    macro: MacroState = field(default_factory=MacroState)
    properties: list = field(default_factory=list)
    actors: dict = field(default_factory=dict)
    macro_history: list = field(default_factory=list)      # list[MacroSnapshot]
    last_ai_actions: dict = field(default_factory=dict)    # actor_id -> "hold"/"bought m1"/"sold p09"
    event_log: list = field(default_factory=list)          # all events across the game
    start_year: int = 0
    start_half: int = 1
    era_label: str = ""
    epc_mandate_announced: bool = False

    def advance_tick(self):
        self.tick += 1
