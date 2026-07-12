class PropertyModel:
    def update(self, state):
        events = []
        for prop in state.properties:
            prop.current_value = prop.base_value * (state.macro.price_index / 100.0) * prop.hpi_factor
            prop.rent *= (1 + state.macro.rent_growth / 2)
            events.append({
                "type": "property_valuation",
                "tick": state.tick,
                "property_id": prop.id,
                "current_value": prop.current_value,
                "rent": prop.rent,
                "detail": f"Property {prop.id}: value={prop.current_value:.2f}, rent={prop.rent:.2f}",
            })
        return events
