def format_positions(positions_data):
    """Format the positions data for better readability"""
    if not positions_data or 'positions' not in positions_data:
        return {"message": "No positions found"}

    formatted_positions = []
    for position in positions_data['positions']:
        formatted_position = {
            # Market information
            "instrument": position['market']['instrumentName'],
            "expiry": position['market']['expiry'],
            "bid": position['market']['bid'],
            "offer": position['market']['offer'],
            "high": position['market']['high'],
            "low": position['market']['low'],
            "change": f"{position['market']['percentageChange']}%",

            # Position details
            "deal_id": position['position']['dealId'],
            "direction": position['position']['direction'],
            "deal_size": position['position']['dealSize'],
            "contract_size": position['position']['contractSize'],
            "open_level": position['position']['openLevel'],
            "currency": position['position']['currency'],
            "controlled_risk": position['position']['controlledRisk'],
            "created_date": position['position']['createdDate']
        }

        # Add calculations if present (for options)
        if 'calculations' in position:
            if 'error' in position['calculations']:
                formatted_position['calculations'] = {
                    'error': position['calculations']['error']
                }
            else:
                formatted_position['calculations'] = {
                    'delta': round(position['calculations']['delta'], 4),
                    'underlying_price': position['calculations']['underlying_price'],
                    'strike_price': position['calculations']['strike_price'],
                    'time_to_expiry': round(position['calculations']['time_to_expiry'] * 365),  # Convert back to days
                    'volatility': f"{round(position['calculations']['volatility'] * 100, 2)}%",
                    'interest_rate': f"{round(position['calculations']['interest_rate'] * 100, 2)}%"
                }

        formatted_positions.append(formatted_position)

    return {"positions": formatted_positions}