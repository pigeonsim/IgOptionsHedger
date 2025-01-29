import math
from typing import Literal, Union

def std_norm_cdf(x: float) -> float:
    """
    Calculate the cumulative distribution function of the standard normal distribution.

    Args:
        x: The input value

    Returns:
        The probability that a standard normal random variable will be less than or equal to x
    """
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def std_norm_pdf(x: float) -> float:
    """
    Calculate the probability density function of the standard normal distribution.

    Args:
        x: The input value

    Returns:
        The height of the probability density function at x
    """
    return math.exp(-x*x/2.0) / math.sqrt(2*math.pi)

def get_w(s: float, k: float, t: float, v: float, r: float) -> float:
    """
    Calculate the W parameter used in the Black-Scholes formula.

    Args:
        s: Current price of the underlying
        k: Strike price
        t: Time to expiration in years
        v: Volatility as a decimal
        r: Annual risk-free interest rate as a decimal

    Returns:
        The W parameter for the Black-Scholes formula
    """
    try:
        return (math.log(s/k) + (r + (v*v)/2)*t) / (v * math.sqrt(t))
    except (ValueError, ZeroDivisionError):
        return float('inf') if s > k else float('-inf')

def _call_price(s: float, k: float, t: float, v: float, r: float) -> float:
    """
    Calculate the theoretical price of a call option using Black-Scholes.

    Args:
        s: Current price of the underlying
        k: Strike price
        t: Time to expiration in years
        v: Volatility as a decimal
        r: Annual risk-free interest rate as a decimal

    Returns:
        The theoretical price of the call option
    """
    if t <= 0:
        return max(0.0, s - k)

    w = get_w(s, k, t, v, r)
    if not math.isfinite(w):
        return max(0.0, s - k)

    d1 = w
    d2 = w - v * math.sqrt(t)

    return s * std_norm_cdf(d1) - k * math.exp(-r*t) * std_norm_cdf(d2)

def _put_price(s: float, k: float, t: float, v: float, r: float) -> float:
    """
    Calculate the theoretical price of a put option using put-call parity.

    Args:
        s: Current price of the underlying
        k: Strike price
        t: Time to expiration in years
        v: Volatility as a decimal
        r: Annual risk-free interest rate as a decimal

    Returns:
        The theoretical price of the put option
    """
    return _call_price(s, k, t, v, r) - s + k * math.exp(-r*t)

def _call_vega(s: float, k: float, t: float, v: float, r: float) -> float:
    """
    Calculate the vega of a call option (same as put vega).

    Args:
        s: Current price of the underlying
        k: Strike price
        t: Time to expiration in years
        v: Volatility as a decimal
        r: Annual risk-free interest rate as a decimal

    Returns:
        The option's vega (sensitivity to volatility changes)
    """
    if t <= 0:
        return 0.0

    w = get_w(s, k, t, v, r)
    if not math.isfinite(w):
        return 0.0

    return s * math.sqrt(t) * std_norm_pdf(w)

def _call_delta(s: float, k: float, t: float, v: float, r: float) -> float:
    """
    Calculate the delta of a call option.

    Args:
        s: Current price of the underlying
        k: Strike price
        t: Time to expiration in years
        v: Volatility as a decimal
        r: Annual risk-free interest rate as a decimal

    Returns:
        The delta of the call option
    """
    w = get_w(s, k, t, v, r)
    if not math.isfinite(w):
        return 1.0 if s > k else 0.0
    return std_norm_cdf(w)

def _put_delta(s: float, k: float, t: float, v: float, r: float) -> float:
    """
    Calculate the delta of a put option.

    Args:
        s: Current price of the underlying
        k: Strike price
        t: Time to expiration in years
        v: Volatility as a decimal
        r: Annual risk-free interest rate as a decimal

    Returns:
        The delta of the put option
    """
    delta = _call_delta(s, k, t, v, r) - 1
    return 0.0 if delta == -1 and k == s else delta

def get_delta(s: float, k: float, t: float, v: float, r: float, 
              call_put: Literal["call", "put"], direction: Literal["BUY", "SELL"]) -> float:
    """
    Calculate the delta of an option.

    Args:
        s: Current price of the underlying
        k: Strike price
        t: Time to expiration in years
        v: Volatility as a decimal
        r: Annual risk-free interest rate as a decimal
        call_put: The type of option - "call" or "put"
        direction: The direction of the trade - "BUY" or "SELL"

    Returns:
        The delta of the option, with sign adjusted for trade direction

    Examples:
        >>> get_delta(100, 100, 1, 0.2, 0.05, "call", "BUY")  # Long ATM call
        0.5398...
        >>> get_delta(100, 100, 1, 0.2, 0.05, "put", "BUY")   # Long ATM put
        -0.4602...
        >>> get_delta(100, 100, 1, 0.2, 0.05, "call", "SELL") # Short ATM call
        -0.5398...
    """
    if call_put == "call":
        delta = _call_delta(s, k, t, v, r)
    else:  # put
        delta = _put_delta(s, k, t, v, r)
        
    # Reverse sign for SELL positions
    return delta if direction == "BUY" else -delta

def calculate_implied_volatility(
    s: float, k: float, t: float, r: float, 
    market_price: float, call_put: Literal["call", "put"],
    initial_vol: float = 0.3,
    max_iterations: int = 100,
    precision: float = 1.0e-5
) -> float:
    """
    Calculate implied volatility using Newton-Raphson method.

    Args:
        s: Current price of the underlying
        k: Strike price
        t: Time to expiration in years
        r: Annual risk-free interest rate as a decimal
        market_price: Observed market price of the option
        call_put: Option type - "call" or "put"
        initial_vol: Starting guess for volatility
        max_iterations: Maximum number of iterations
        precision: Desired precision for the result

    Returns:
        float: The implied volatility that produces the market price

    Raises:
        ValueError: If the algorithm fails to converge

    Example:
        >>> # ATM call option
        >>> iv = calculate_implied_volatility(100, 100, 1/365, 0, 2.0, "call")
        >>> abs(_call_price(100, 100, 1/365, iv, 0) - 2.0) < 1e-4
        True
    """
    v = initial_vol
    price_func = _call_price if call_put == "call" else _put_price

    for i in range(max_iterations):
        price = price_func(s, k, t, v, r)
        diff = price - market_price

        if abs(diff) < precision:
            return v

        vega = _call_vega(s, k, t, v, r)
        if abs(vega) < 1e-10:  # Avoid division by zero
            break

        v = v - diff / vega  # Newton-Raphson update

        if v <= 0:  # Ensure volatility stays positive
            v = 0.0001

    raise ValueError(
        f"Implied volatility calculation did not converge. "
        f"Last estimate: {v:.4f}"
    )