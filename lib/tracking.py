import datetime
import re
from typing import Any, List


class Tracking:

  def __init__(self,
               tracking_number,
               group,
               order_ids,
               price,
               to_email,
               url='',
               ship_date='0',
               tracked_cost=0.0,
               items='',
               merchant='',
               reconcile: bool = True,
               delivery_date="") -> None:
    self.tracking_number = tracking_number
    self.group = group
    self.order_ids = order_ids
    self.price = price
    self.to_email = to_email
    self.ship_date = ship_date
    self.tracked_cost = tracked_cost
    self.items = items
    self.merchant = merchant
    self.reconcile = reconcile
    self.delivery_date = delivery_date

  def __setstate__(self, state) -> None:
    self.__init__(**state)

  def __str__(self) -> str:
    return (f"number: {self.tracking_number}, group: {self.group}, "
            f"order(s): {self.order_ids}, price: {self.price}, "
            f"to_email: {self.to_email}, "
            f"ship_date: {self.ship_date}, items: {self.items}, "
            f"merchant: {self.merchant}, reconcile: {self.reconcile}, "
            f"delivery_date: {self.delivery_date}")

  def to_row(self) -> list:
    hyperlink = self._create_hyperlink()
    return [
        hyperlink, ", ".join(self.order_ids), self.to_email, self.ship_date, self.delivery_date,
        self.group, self.tracked_cost, self.merchant, self.items
    ]

  def get_header(self) -> List[str]:
    return [
        "Tracking Number", "Order Number(s)", "To Email", "Ship Date", "Est. Delivery Date",
        "Group", "Amount Reimbursed", "Merchant", "Items"
    ]

  def _create_hyperlink(self) -> Any:
    link = self._get_tracking_url()
    if link == None:
      return self.tracking_number
    return '=HYPERLINK("%s", "%s")' % (link, self.tracking_number)

  def _get_tracking_url(self) -> Any:
    if self.tracking_number.startswith("TBA"):  # Amazon
      return None
    elif self.tracking_number.startswith("1Z"):  # UPS
      return "https://www.ups.com/track?loc=en_US&tracknum=%s" % self.tracking_number
    elif len(self.tracking_number) == 12 or len(self.tracking_number) == 15:  # FedEx
      return "https://www.fedex.com/apps/fedextrack/?tracknumbers=%s" % self.tracking_number
    elif len(self.tracking_number) == 22:  # USPS
      return "https://tools.usps.com/go/TrackConfirmAction?qtc_tLabels1=%s" % self.tracking_number
    else:
      return None


def convert_int_to_date(i):
  return (datetime.date(1900, 1, 1) + datetime.timedelta(int(i) - 2)).strftime("%Y-%m-%d")


def from_row(header, row) -> Tracking:
  tracking = row[header.index('Tracking Number')]
  orders = set([s.strip() for s in str(row[header.index('Order Number(s)')]).split(',')])
  price_str = str(row[header.index('Price')]).replace(',', '').replace(
      '$', '') if 'Price' in header else ''
  price = float(price_str) if price_str else 0.0
  to_email = row[header.index("To Email")]
  ship_date = row[header.index("Ship Date")]

  if isinstance(ship_date, int):
    ship_date = convert_int_to_date(ship_date)

  delivery_date = row[header.index("Est. Delivery Date")] if "Est. Delivery Date" in header else ""
  if isinstance(delivery_date, int):
    delivery_date = convert_int_to_date(delivery_date)

  group = row[header.index("Group")]
  tracked_cost_str = row[header.index("Amount Reimbursed")] if "Amount Reimbursed" in header else ""
  tracked_cost = float(tracked_cost_str) if tracked_cost_str else 0.0
  items = row[header.index("Items")] if 'Items' in header else ""
  merchant = row[header.index("Merchant")] if 'Merchant' in header else ""
  return Tracking(
      tracking,
      group,
      orders,
      price,
      to_email,
      ship_date=ship_date,
      tracked_cost=tracked_cost,
      items=items,
      merchant=merchant,
      reconcile=True,
      delivery_date=delivery_date)
