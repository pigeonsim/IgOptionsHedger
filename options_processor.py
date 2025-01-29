import math
from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime, date
import calendar
from epic_mapping import MARKET_TO_EPIC
from option_calculations import get_delta, calculate_implied_volatility

class OptionsProcessor:

    def __init__(self, ig_client):
        self.ig_client = ig_client

    def is_option(self, epic: str) -> bool:
        """Check if an instrument is an option based on its epic"""
        return epic.startswith("OP.") or epic.startswith("DO.")

    def get_third_friday(self, year: int, month: int) -> date:
        """Get the third Friday of a given month"""
        c = calendar.monthcalendar(year, month)
        # Get all Fridays (index 4) in the month
        fridays = [week[4] for week in c if week[4] != 0]
        # Return the third one (index 2)
        return date(year, month, fridays[2])

    def parse_expiry_date(self, expiry: str) -> date:
        """
        Parse expiry date string into a date object

        Args:
            expiry: Date string in format "DD-MMM-YY" or "MMM-YY"

        Returns:
            date: The expiry date
        """
        try:
            # Try full date format first (e.g., "29-JAN-25")
            try:
                return datetime.strptime(expiry, "%d-%b-%y").date()
            except ValueError:
                # Try month-year format (e.g., "MAR-25")
                month_str, year_str = expiry.split('-')
                year = 2000 + int(year_str)  # Convert "25" to 2025
                month = datetime.strptime(month_str, "%b").month
                return self.get_third_friday(year, month)
        except Exception as e:
            raise ValueError(f"Failed to parse expiry date {expiry}: {str(e)}")

    def calculate_time_to_expiry(self, expiry_str: str) -> float:
        """
        Calculate time to expiry in years

        Args:
            expiry_str: Expiry date string

        Returns:
            float: Time to expiry in years
        """
        expiry_date = self.parse_expiry_date(expiry_str)
        today = date.today()
        days_to_expiry = (expiry_date - today).days
        return max(max(days_to_expiry, 0) / 365.0, 0.001)  # Ensure non-negative, replace same-day option's 0 value with 0.001 to ensure IV computations later 

    def parse_option_epic(self, epic: str) -> Tuple[float, str]:
        """
        Parse strike price and option type from option EPIC code. NOT APPROPRIATE BECAUSE EPIC FORMAT IS UNPREDICTABLE.

        Args:
            epic: The option's EPIC code (e.g. "OP.D.SPX1.6000C.IP")

        Returns:
            Tuple containing (strike_price, option_type)

        Raises:
            ValueError: If EPIC format is invalid
        """
        try:
            # Split EPIC into components
            parts = epic.split('.')
            if len(parts) != 5:  # Should be: OP.D.MARKET.STRIKECP.IP
                raise ValueError(f"Invalid EPIC format: {epic}")

            # Get the strike and type part (e.g., "6000C")
            strike_type = parts[3]

            # Extract strike price (all digits) and type (last character)
            strike_str = ''.join(c for c in strike_type if c.isdigit())
            option_type = strike_type[-1].lower()

            # Validate option type
            if option_type not in ['c', 'p']:
                raise ValueError(f"Invalid option type (currently supporting only Call and Put): {option_type}")

            return float(strike_str), 'call' if option_type == 'c' else 'put'

        except Exception as e:
            raise ValueError(f"Failed to parse option EPIC {epic}: {str(e)}")

    def parse_option_info(self, name: str) -> Tuple[float, str]:
        """
        Parse strike price and option type from option name

        Args:
            name: The option's name
            Examples:
                - "US 500 6000 CALL"
                - "Daily US 500 6058.0 CALL" 
                - "Daily EURUSD 10410 CALL ($1)"
                - "Weekly Germany 40 (Wed)21500 CALL"

        Returns:
            Tuple containing (strike_price, option_type)

        Raises:
            ValueError: If name format is invalid
        """
        try:
            # Find CALL/PUT in the name
            for word in ['CALL', 'PUT']:
                if word in name.upper():
                    option_type = word.lower()
                    # Split the name at CALL/PUT
                    prefix = name.upper().split(word)[0].strip()
                    break
            else:
                raise ValueError(f"Could not find option type (CALL/PUT) in: {name}")
                
            # Find the last number in the prefix - this will be our strike
            # This handles cases where the number might be connected to other text like "(Wed)21500"
            strike_match = ''
            for char in reversed(prefix):
                if char.isdigit():
                    strike_match = char + strike_match
                elif strike_match:  # Stop once we hit non-digits after finding some digits
                    break
                    
            if not strike_match:
                raise ValueError(f"Could not find strike price in: {name}")
                
            strike = float(strike_match)
                
            return strike, option_type
            
        except Exception as e:
            raise ValueError(f"Failed to parse option name {name}: {str(e)}")

    def get_underlying_epic(self, market_id: str) -> Optional[str]:
        """
        Find the corresponding epic code for an underlying market ID

        Args:
            market_id: The market ID from the option's instrument details

        Returns:
            str: The epic code for the underlying instrument, or None if not found
        """
        # Try direct lookup first
        if market_id in MARKET_TO_EPIC:
            return MARKET_TO_EPIC[market_id]

        # Try alternate formats (with/without space)
        alternates = [
            market_id.replace(" ", ""),  # Remove spaces
            f"{market_id[:2]} {market_id[2:]}"  # Add space after 2 chars
        ]

        for alt in alternates:
            if alt in MARKET_TO_EPIC:
                return MARKET_TO_EPIC[alt]

        return None

    def adjust_fx_strike(self, raw_strike: float, underlying_price: float) -> float:
        """
        Adjust FX option strike based on underlying price decimal convention.
        If strike already matches underlying decimal magnitude, returns it as-is.
        
        Args:
            raw_strike: The raw strike from parse_option_info() (e.g., 8380, 15400, 0.8380)
            underlying_price: Current underlying price (e.g., 0.83752, 155.393)
            
        Returns:
            Adjusted strike price with correct decimal placement
        """
        # If the strike is already in the same magnitude as underlying, return as-is
        strike_magnitude = abs(math.floor(math.log10(raw_strike)))
        underlying_magnitude = abs(math.floor(math.log10(underlying_price)))
        
        if abs(strike_magnitude - underlying_magnitude) <= 1:  # Allow for 1 order of magnitude difference
            return raw_strike
            
        # Convert both numbers to strings to count digits before decimal
        underlying_str = f"{underlying_price:.6f}"
        underlying_whole_digits = len(underlying_str.split('.')[0])
        
        # Calculate how many digits to shift the strike
        raw_strike_digits = len(str(int(raw_strike)))
        decimal_shift = raw_strike_digits - underlying_whole_digits
        
        return raw_strike / (10 ** decimal_shift)
    
    def process_option_position(self, position: Dict) -> Dict:
        """
        Process a single option position to calculate its delta

        Args:
            position: The position data from the IG API

        Returns:
            dict: Position data enriched with delta calculations
        """
        try:
            # Get option details
            option_epic = position['market']['epic']
            option_details = self.ig_client.get_market_details(option_epic)

            # Parse strike price and option type from EPIC
            option_name = position['market']['instrumentName']
            strike_price, option_type = self.parse_option_info(option_name)

            # Extract underlying market ID and find corresponding epic
            underlying_market_id = option_details['instrument'].get('marketId')
            if not underlying_market_id:
                raise ValueError(
                    f"No underlying market ID found for option {option_epic}")

            #print("underlying_market_id", underlying_market_id)
            underlying_epic = self.get_underlying_epic(underlying_market_id)
            if not underlying_epic:
                raise ValueError(
                    f"No epic mapping found for underlying {underlying_market_id}"
                )

            # Get underlying market details
            underlying_details = self.ig_client.get_market_details(
                underlying_epic)
            
            #print("underlying_details")
            #print(underlying_details)

            # Extract required values for delta calculation
            current_price = (float(underlying_details['snapshot']['bid']) + float(underlying_details['snapshot']['offer'])) / 2.0
            #print(strike_price)
            #print(current_price)
            adjusted_strike = self.adjust_fx_strike(strike_price, current_price)
            time_to_expiry = self.calculate_time_to_expiry(
                position['market']['expiry'])
            interest_rate = 0  # Using 0% as default risk-free rate

            # Calculate implied volatility using mid price
            bid = float(position['market']['bid'])
            offer = float(position['market']['offer'])
            market_price = (bid + offer) / 2.0

            direction = position['position']['direction']

            try:
                volatility = calculate_implied_volatility(
                    s=current_price,
                    k=adjusted_strike,
                    t=time_to_expiry,
                    r=interest_rate,
                    market_price=market_price,
                    call_put=option_type
                )
            except ValueError as e:
                logging.warning(f"Failed to calculate IV: {str(e)}")
                volatility = 0.20  # Default to 20% if IV calculation fails

            # Calculate delta
            delta = get_delta(s=current_price,
                              k=adjusted_strike,
                              t=time_to_expiry,
                              v=volatility,
                              r=interest_rate,
                              call_put=option_type,
                              direction=direction)

            # Enrich position data with calculations
            return {
                **position, 'calculations': {
                    'delta': delta,
                    'underlying_price': current_price,
                    'strike_price': adjusted_strike,
                    'time_to_expiry': time_to_expiry,
                    'volatility': volatility,
                    'interest_rate': interest_rate
                }
            }

        except Exception as e:
            logging.error(f"Error processing option position: {str(e)}")
            return {**position, 'calculations': {'error': str(e)}}

    def process_positions(self, positions_data: Dict) -> Dict:
        """
        Process all positions, calculating delta for options

        Args:
            positions_data: The raw positions data from the IG API

        Returns:
            dict: Positions data enriched with calculations for options
        """
        if not positions_data or 'positions' not in positions_data:
            return {"message": "No positions found"}

        processed_positions = []

        for position in positions_data['positions']:
            epic = position['market']['epic']
            processed_position = self.process_option_position(position)
            '''
            if self.is_option(epic):
                processed_position = self.process_option_position(position)
            
            else:
                logging.info(f"{str(epic)} is not a vanilla Call or Put")
                processed_position = {
                    **position,
                    'calculations': {
                        'error': "Not a vanilla call or put options"
                    }
                }
            '''
            processed_positions.append(processed_position)               

        return {"positions": processed_positions}