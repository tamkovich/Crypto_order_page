import time, urllib, hmac, hashlib

# https://github.com/BitMEX/api-connectors/tree/master/official-ws/python


def find_by_keys(keys, rows, match):
    for r in rows:
        if all(r[k] == match[k] for k in keys):
            return r


def generate_nonce():
    return int(round(time.time() + 3600))


def generate_signature(secret, verb, url, nonce, data):
    """Generate a request signature compatible with BitMEX."""
    # Parse the url so we can remove the base and extract just the path.
    parsedURL = urllib.parse.urlparse(url)
    path = parsedURL.path
    if parsedURL.query:
        path = path + "?" + parsedURL.query

    # print "Computing HMAC: %s" % verb + path + str(nonce) + data
    message = (verb + path + str(nonce) + data).encode("utf-8")

    signature = hmac.new(
        secret.encode("utf-8"), message, digestmod=hashlib.sha256
    ).hexdigest()
    return signature


NO_AUTH = {
    "announcement",  # Site announcements
    "chat",  # Trollbox chat
    "connected",  # Statistics of connected users/bots
    "funding",  # Updates of swap funding rates. Sent every funding interval (usually 8hrs)
    "instrument",  # Instrument updates including turnover and bid/ask
    "insurance",  # Daily Insurance Fund updates
    "liquidation",  # Liquidation orders as they're entered into the book
    "orderBookL2_25",  # Top 25 levels of level 2 order book
    "orderBookL2",  # Full level 2 order book
    "orderBook10",  # Top 10 levels using traditional full book push
    "publicNotifications",  # System-wide notifications (used for short-lived messages)
    "quote",  # Top level of the book
    "quoteBin1m",  # 1-minute quote bins
    "quoteBin5m",  # 5-minute quote bins
    "quoteBin1h",  # 1-hour quote bins
    "quoteBin1d",  # 1-day quote bins
    "settlement",  # Settlements
    "trade",  # Live trades
    "tradeBin1m",  # 1-minute trade bins
    "tradeBin5m",  # 5-minute trade bins
    "tradeBin1h",  # 1-hour trade bins
    "tradeBin1d",  # 1-day trade bins
}

AUTH = {
    "affiliate",  # Affiliate status, such as total referred users & payout %
    "execution",  # Individual executions; can be multiple per order
    "order",  # Live updates on your orders
    "margin",  # Updates on your current account balance and margin requirements
    "position",  # Updates on your positions
    "privateNotifications",  # Individual notifications - currently not used
    "transact",  # Deposit/Withdrawal updates
    "wallet",  # Bitcoin address balance data, including total deposits & withdrawals
}
