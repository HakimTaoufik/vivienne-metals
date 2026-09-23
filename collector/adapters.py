"""Audited mappings. A changed selector fails closed rather than guessing."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit
from .dom import Tree


class ParseError(ValueError):
    pass


def money(value):
    """French/decimal EUR -> integer cents; zero/dashes are unavailable."""
    s = str(value).strip().replace("EUR", "").replace("€", "").strip()
    s = re.sub(r"\s", "", s)
    if s in ("", "—", "--", "-", "N/A"):
        return None
    if not re.fullmatch(r"\d+(?:[.,]\d+)?", s):
        raise ParseError(f"Ambiguous money: {value!r}")
    try:
        amount = Decimal(s.replace(",", "."))
        if not amount.is_finite() or amount < 0 or amount > 10_000_000:
            raise ParseError("Price outside supported range")
        return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)) or None
    except InvalidOperation as e:
        raise ParseError("Invalid money") from e


def norm(s):
    return re.sub(r"\s+", " ", "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))).strip()


NAMES = {
    "20 francs marianne coq": "coq20", "20 francs coq or": "coq20",
    "20 francs napoleon ou genie": "napoleon20", "20 francs napoleon or": "napoleon20",
    "10 francs napoleon marianne coq": "coq10", "10 francs coq": "coq10",
    "50 francs hercule": "hercule50", "10 francs hercule": "hercule10",
    "5 francs semeuse": "semeuse5", "lingotin 1 oz or": "goldoz", "lingotin or 1 once": "goldoz",
    "lingot 1 kg or": "gold1000", "lingot or 1 kilo": "gold1000",
    "lingot 1 kilo fiji": "silverfiji1000", "lingot 500g fiji": "silverfiji500", "lingot 250g fiji": "silverfiji250",
}
for g in [1, 5, 10, 20, 50, 100, 250, 500]:
    for name in [f"lingot {g} g or", f"lingotin {g} g or", f"lingotin or {g} g", f"lingotin or {g}g"]:
        NAMES[name] = f"gold{g}"

JOUBERT = {"11028": "napoleon20", "10980": "gold1000", "10991": "gold500", "10992": "gold250", "10993": "gold100", "10996": "gold50", "10997": "goldoz", "10999": "gold20", "11003": "gold10", "11004": "gold5"}


def clean_url(url):
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        raise ParseError("Non-HTTPS product URL")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def first(node, cls):
    found = node.find(cls=cls)
    if len(found) != 1:
        raise ParseError(f"Expected one {cls}, got {len(found)}")
    return found[0]


def direct_price(node):
    # Nested text may contain quantity tiers; only the primary text is a price.
    return money(" ".join(c for c in node.children if isinstance(c, str)))


def positive_int(v):
    if not re.fullmatch(r"[1-9]\d{0,5}", str(v)):
        raise ParseError("Invalid minimum quantity")
    return int(v)


def base(source, product, url, observed):
    return dict(dealer=source["dealer"], product=product, source=source["id"], url=clean_url(url),
                observedAt=observed, bid=None, ask=None, minBuy=None, minSell=None,
                availability="unknown", currency="EUR")


def parse(html, source, observed):
    root = Tree(html).root
    quotes, spots = [], []
    adapter = source["adapter"]
    if adapter in ("cv_home", "cv_table"):
        for n in root.find(cls="cours-text"):
            m = re.fullmatch(r"(Or|Argent):\s*([\d.,\s]+)\s*€/kg", n.text())
            if m:
                cents_kg = money(m[2])
                if cents_kg:
                    spots.append(dict(metal="gold" if m[1] == "Or" else "silver", eurPerGram=cents_kg / 100000,
                                      observedAt=observed, source=source["id"], url=source["url"], label="Change Vivienne · spot indicatif"))
        rows = root.find(cls="product-item" if adapter == "cv_home" else "cv-table-row")
        if not rows:
            raise ParseError("Change Vivienne product structure missing")
        for row in rows:
            name = first(row, "product-name" if adapter == "cv_home" else "cv-product-name")
            product = NAMES.get(norm(name.text()))
            if not product:
                continue
            q = base(source, product, row.find("a")[0].attrs["href"], observed)
            if adapter == "cv_home":
                buttons = row.find("button", cls="btn-price")
                for btn in buttons:
                    action = btn.attrs.get("data-action")
                    if action not in ("buy", "sell"):
                        raise ParseError("Unknown home price direction")
                    # Home data-action is the DEALER action; verified on product page.
                    side, minimum = ("bid", "minSell") if action == "buy" else ("ask", "minBuy")
                    if q[side] is not None:
                        raise ParseError("Duplicate price side")
                    q[side] = money(btn.attrs.get("data-price", ""))
                    q[minimum] = positive_int(btn.attrs.get("data-min-qty", ""))
                if len(buttons) != 2:
                    raise ParseError("Expected both labeled home prices")
            else:
                # Category labels are from the CUSTOMER perspective.
                q["bid"] = money(first(row, "cv-price-sell").text())
                q["ask"] = money(first(row, "cv-price-buy").text())
                q["minSell"] = positive_int(row.attrs.get("data-min-qty", ""))
                q["minBuy"] = q["minSell"]
                stock = first(row, "cv-badge-stock").text().strip()
                q["availability"] = "in_stock" if stock == "En stock" else "unavailable"
                if q["availability"] != "in_stock":
                    q["ask"] = None
            quotes.append(q)
    elif adapter == "joubert":
        rows = root.find("tr", cls="product-row")
        if not rows:
            raise ParseError("Joubert table structure missing")
        for row in rows:
            product = JOUBERT.get(row.attrs.get("data-product-id"))
            if not product:
                continue
            q = base(source, product, row.find("a")[0].attrs["href"], observed)
            q["bid"] = direct_price(first(row, "joubert-achat-net"))
            q["ask"] = direct_price(first(row, "joubert-vend-net"))
            inputs = row.find("input", cls="qty-input")
            unavailable = any(n.text() == "Rupture de stock" for n in row.find("span"))
            if source.get("side") == "ask" and unavailable and not inputs:
                # The catalog replaces the quantity control with an explicit
                # stock label. Keep the row, but never offer its displayed ask.
                q["availability"] = "unavailable"
                q["ask"] = None
            elif len(inputs) != 1 or unavailable:
                raise ParseError("Joubert minimum quantity missing")
            else:
                q["minBuy"] = positive_int(inputs[0].attrs.get("min", ""))
            # Buy-page bid has no documented minimum; don't infer a sell minimum.
            if source.get("side") == "bid":
                q["minSell"] = q["minBuy"]
                q["ask"] = None
                q["minBuy"] = None
            elif source.get("side") == "ask":
                q["bid"] = None
            quotes.append(q)
    elif adapter == "oc":
        side = source.get("side")
        if side not in ("ask", "bid"):
            raise ParseError("Or & Change needs explicit side")
        rows = root.find("article", cls="product-miniature")
        if not rows:
            raise ParseError("Or & Change product structure missing")
        for row in rows:
            name = first(row, "product-name")
            product = NAMES.get(norm(name.text()))
            if not product:
                continue
            links = name.find("a")
            if len(links) != 1:
                raise ParseError("Product link missing")
            q = base(source, product, links[0].attrs["href"], observed)
            price = first(row, "product-price")
            q[side] = money(price.text())
            # Category pages don't establish minimum quantities or stock.
            quotes.append(q)
    else:
        raise ParseError("Unknown adapter")
    if not quotes:
        raise ParseError("No recognized products; mapping or layout changed")
    for q in quotes:
        if q["ask"] and q["bid"] and q["bid"] > q["ask"]:
            raise ParseError("Inverted dealer spread")
    keys = [(q["dealer"], q["product"]) for q in quotes]
    if len(keys) != len(set(keys)):
        raise ParseError("Duplicate products in source")
    return quotes, spots
