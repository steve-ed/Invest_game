from rich.console import Console

console = Console(highlight=False)


def trend_arrow(current: float, previous: float) -> str:
    if current - previous > 0.001:
        return "↑"
    if previous - current > 0.001:
        return "↓"
    return "→"


def compute_yield(rent: float, current_value: float) -> float:
    if current_value == 0:
        return 0.0
    return (rent * 12) / current_value * 100


def extract_news(events: list) -> list:
    relevant = [e for e in events if e.get("type") in ("scenario_event", "narrative_branch")]
    return list(reversed(relevant[-5:]))


def portfolio_value(portfolio: list, prop_map: dict) -> float:
    return sum(prop_map[pid].current_value for pid in portfolio if pid in prop_map)


def show_opening(state) -> None:
    from rich.table import Table
    from rich.rule import Rule

    prop_map = {p.id: p for p in state.properties}
    owned_all = {pid for a in state.actors.values() for pid in a.portfolio}

    console.clear()
    console.print(Rule("[bold cyan]REALESTGAME · 20 turns · 10 year simulation[/bold cyan]"))
    console.print()

    pos_table = Table(title="Starting Positions", show_header=True, header_style="bold yellow")
    pos_table.add_column("Actor")
    pos_table.add_column("Properties", justify="right")
    pos_table.add_column("Portfolio Value", justify="right")
    pos_table.add_column("Cash", justify="right")
    pos_table.add_column("Total", justify="right")
    for actor in state.actors.values():
        pv = portfolio_value(actor.portfolio, prop_map)
        pos_table.add_row(
            actor.name,
            str(len(actor.portfolio)),
            f"£{pv:,.0f}",
            f"£{actor.cash:,.0f}",
            f"£{pv + actor.cash:,.0f}",
        )
    console.print(pos_table)
    console.print()

    for actor in state.actors.values():
        if not actor.portfolio:
            continue
        p_table = Table(title=f"{actor.name} — Portfolio", show_header=True, header_style="bold")
        p_table.add_column("ID")
        p_table.add_column("Region")
        p_table.add_column("Value", justify="right")
        p_table.add_column("Rent/mo", justify="right")
        p_table.add_column("Yield", justify="right")
        for pid in actor.portfolio:
            p = prop_map.get(pid)
            if p:
                p_table.add_row(
                    p.id, p.region,
                    f"£{p.current_value:,.0f}",
                    f"£{p.rent:,.0f}",
                    f"{compute_yield(p.rent, p.current_value):.1f}%",
                )
        console.print(p_table)
        console.print()

    available = [p for p in state.properties if p.id not in owned_all]
    if available:
        mkt_table = Table(title="Market (unowned)", show_header=True, header_style="bold green")
        mkt_table.add_column("ID")
        mkt_table.add_column("Region")
        mkt_table.add_column("Value", justify="right")
        mkt_table.add_column("Rent/mo", justify="right")
        mkt_table.add_column("Gross Yield", justify="right")
        for p in available:
            mkt_table.add_row(
                p.id, p.region,
                f"£{p.current_value:,.0f}",
                f"£{p.rent:,.0f}",
                f"{compute_yield(p.rent, p.current_value):.1f}%",
            )
        console.print(mkt_table)
        console.print()

    console.print("[bold]Economic Conditions (start)[/bold]")
    console.print(
        f"  Price Index: {state.macro.price_index:.1f}   "
        f"Interest Rate: {state.macro.interest_rate * 100:.1f}%   "
        f"Rent Growth: {state.macro.rent_growth * 100:.1f}%"
    )
    console.print()
    console.print("[dim]Press ENTER to begin...[/dim]", end="")
    input()


def _render_macro_table(macro_history: list, current=None) -> None:
    from rich.table import Table

    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("Tick", justify="right", style="dim")
    table.add_column("Scenario")
    table.add_column("Price Idx", justify="right")
    table.add_column("Rate", justify="right")
    table.add_column("Rent Gr", justify="right")
    table.add_column("Events")

    # Current tick (live, not yet snapshotted)
    if current is not None:
        prev = macro_history[-1] if macro_history else None
        pi_arrow = trend_arrow(current.macro.price_index, prev.price_index) if prev else ""
        rate_arrow = trend_arrow(current.macro.interest_rate, prev.interest_rate) if prev else ""
        rent_arrow = trend_arrow(current.macro.rent_growth, prev.rent_growth) if prev else ""
        table.add_row(
            str(current.tick),
            current.current_scenario.upper(),
            f"{current.macro.price_index:.1f} {pi_arrow}",
            f"{current.macro.interest_rate * 100:.1f}% {rate_arrow}",
            f"{current.macro.rent_growth * 100:.1f}% {rent_arrow}",
            "",
        )

    # Historical snapshots, newest-first
    for i, snap in enumerate(reversed(macro_history)):
        prev_index = len(macro_history) - i - 2
        prev = macro_history[prev_index] if prev_index >= 0 else None
        pi_arrow = trend_arrow(snap.price_index, prev.price_index) if prev else ""
        rate_arrow = trend_arrow(snap.interest_rate, prev.interest_rate) if prev else ""
        rent_arrow = trend_arrow(snap.rent_growth, prev.rent_growth) if prev else ""
        event_strs = []
        for e in snap.events:
            detail = e.get("detail", "")
            if e.get("type") == "shock":
                event_strs.append(f"⚡ {detail}")
            elif e.get("type") == "scenario_transition":
                event_strs.append(f"↘ {detail}")
        table.add_row(
            str(snap.tick),
            snap.scenario.upper(),
            f"{snap.price_index:.1f} {pi_arrow}",
            f"{snap.interest_rate * 100:.1f}% {rate_arrow}",
            f"{snap.rent_growth * 100:.1f}% {rent_arrow}",
            "  ".join(event_strs),
        )

    console.print("[bold]ECONOMIC CONDITIONS[/bold]")
    console.print(table)


def render_turn(state) -> None:
    from rich.table import Table
    from rich.rule import Rule

    prop_map = {p.id: p for p in state.properties}
    owned_all = {pid for a in state.actors.values() for pid in a.portfolio}
    available = [p for p in state.properties if p.id not in owned_all]
    player = state.actors.get("player")

    console.clear()

    months = state.tick * 6
    console.print(Rule(
        f"[bold cyan]TICK {state.tick}  ·  {state.current_scenario.upper()}  ·  {months} months elapsed[/bold cyan]"
    ))
    console.print()

    _render_macro_table(state.macro_history, current=state)
    console.print()

    news = extract_news(state.event_log)
    if news:
        console.print("[bold]MARKET NEWS[/bold]  (latest 5)")
        for item in news:
            console.print(f"  › {item.get('detail', '')}")
        console.print()

    if player:
        console.print(f"[bold]YOUR POSITION[/bold]                         Cash: [green]£{player.cash:,.0f}[/green]")
        console.rule(style="dim")
        if player.portfolio:
            p_table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
            p_table.add_column("ID")
            p_table.add_column("Region")
            p_table.add_column("Value", justify="right")
            p_table.add_column("Rent/mo", justify="right")
            p_table.add_column("Yield", justify="right")
            for pid in player.portfolio:
                p = prop_map.get(pid)
                if p:
                    p_table.add_row(
                        p.id, p.region,
                        f"£{p.current_value:,.0f}",
                        f"£{p.rent:,.0f}/mo",
                        f"{compute_yield(p.rent, p.current_value):.1f}%",
                    )
            console.print(p_table)
        else:
            console.print("  (no properties)")
    console.print()

    console.print("[bold]AI DASHBOARD[/bold]")
    console.rule(style="dim")
    for actor_id, actor in state.actors.items():
        if actor_id == "player":
            continue
        pv = portfolio_value(actor.portfolio, prop_map)
        last = state.last_ai_actions.get(actor_id, "—")
        console.print(
            f"  [bold]{actor.name}[/bold]   "
            f"Score: £{pv + actor.cash:,.0f}   "
            f"Cash: £{actor.cash:,.0f}   "
            f"Last: {last}"
        )
        for pid in actor.portfolio:
            p = prop_map.get(pid)
            if p:
                console.print(
                    f"   {p.id}  {p.region:<22}  "
                    f"£{p.current_value:,.0f}   "
                    f"£{p.rent:,.0f}/mo   "
                    f"{compute_yield(p.rent, p.current_value):.1f}%"
                )
        console.print()

    if available:
        console.print("[bold]MARKET (unowned)[/bold]")
        console.rule(style="dim")
        player_cash = player.cash if player else 0
        for p in available:
            yld = compute_yield(p.rent, p.current_value)
            if player_cash >= p.current_value:
                afford = "[green]✓ affordable[/green]"
            else:
                need = p.current_value - player_cash
                afford = f"(need £{need:,.0f})"
            console.print(
                f"  {p.id}  {p.region:<24}  "
                f"£{p.current_value:,.0f}  "
                f"£{p.rent:,.0f}/mo  "
                f"{yld:.1f}%   {afford}"
            )


def show_end(state, leaderboard: list) -> None:
    from rich.table import Table
    from rich.rule import Rule

    prop_map = {p.id: p for p in state.properties}

    console.clear()
    console.print(Rule("[bold red]GAME OVER  ·  20 turns  ·  10 years elapsed[/bold red]"))
    console.print()

    lb_table = Table(title="Final Leaderboard", show_header=True, header_style="bold yellow")
    lb_table.add_column("Rank", justify="right")
    lb_table.add_column("Actor")
    lb_table.add_column("Score", justify="right")
    lb_table.add_column("Portfolio", justify="right")
    lb_table.add_column("Cash", justify="right")
    for rank, entry in enumerate(leaderboard, 1):
        lb_table.add_row(
            str(rank),
            entry["name"],
            f"£{entry['final_score']:,.0f}",
            f"£{entry['portfolio_value']:,.0f}",
            f"£{entry['cash']:,.0f}",
        )
    console.print(lb_table)
    console.print()

    console.print("[bold]PORTFOLIO BREAKDOWN[/bold]")
    for actor in state.actors.values():
        pv = portfolio_value(actor.portfolio, prop_map)
        console.print(f"  [bold]{actor.name}[/bold]   Portfolio: £{pv:,.0f}   Cash: £{actor.cash:,.0f}")
        for pid in actor.portfolio:
            p = prop_map.get(pid)
            if p:
                console.print(
                    f"    {p.id}  {p.region:<22}  "
                    f"£{p.current_value:,.0f}  "
                    f"£{p.rent:,.0f}/mo  "
                    f"{compute_yield(p.rent, p.current_value):.1f}%"
                )
    console.print()

    key_events = [snap for snap in state.macro_history if snap.events]
    if key_events:
        console.print("[bold]KEY EVENTS[/bold]")
        for snap in key_events:
            for e in snap.events:
                detail = e.get("detail", "")
                if e.get("type") == "shock":
                    console.print(f"  Tick {snap.tick:>2}  ⚡ {detail}")
                elif e.get("type") == "scenario_transition":
                    console.print(f"  Tick {snap.tick:>2}  ↘ {detail}")
