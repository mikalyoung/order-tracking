import pickle
import os.path
from lib.objects_to_drive import ObjectsToDrive
from typing import Any, List

OUTPUT_FOLDER = "output"
CLUSTERS_FILENAME = "clusters.pickle"
CLUSTERS_FILE = OUTPUT_FOLDER + "/" + CLUSTERS_FILENAME


class Cluster:

  def __init__(self, group) -> None:
    self._initiate(set(), set(), group, 0, 0, '0', set(), 0.0)

  def _initiate(self,
                orders,
                trackings,
                group,
                expected_cost,
                tracked_cost,
                last_ship_date='0',
                purchase_orders=set(),
                adjustment=0.0,
                to_email='',
                notes='',
                manual_override=False,
                non_reimbursed_trackings=set()) -> None:
    self.orders = orders
    self.trackings = trackings
    self.group = group
    self.expected_cost = expected_cost
    self.tracked_cost = tracked_cost
    self.last_ship_date = last_ship_date
    self.purchase_orders = purchase_orders
    self.adjustment = adjustment
    self.to_email = to_email
    self.notes = notes
    self.manual_override = manual_override
    self.non_reimbursed_trackings = non_reimbursed_trackings

  def __setstate__(self, state) -> None:
    self._initiate(**state)

  def __str__(self) -> str:
    return "orders: %s, trackings: %s, group: %s, expected cost: %s, tracked cost: %s, last_ship_date: %s, purchase_orders: %s, adjustment: %s" % (
        str(self.orders), str(self.trackings), self.group,
        str(self.expected_cost), str(self.tracked_cost), self.last_ship_date,
        str(self.purchase_orders), str(self.adjustment))

  def get_header(self) -> List[str]:
    return [
        "Orders", "Trackings", "Amount Billed", "Amount Reimbursed",
        "Non-Reimbursed Trackings", "Last Ship Date", "POs", "Group",
        "Manual Cost Adjustment", "Manual Override", "Total Diff", "Notes"
    ]

  def to_row(self) -> list:
    return [
        ",".join(self.orders), ",".join(self.trackings), self.expected_cost,
        self.tracked_cost, ",".join(self.non_reimbursed_trackings),
        self.last_ship_date, "'" + ",".join(self.purchase_orders), self.group,
        self.adjustment, self.manual_override,
        '=INDIRECT(CONCAT("C", ROW())) - INDIRECT(CONCAT("D", ROW())) - INDIRECT(CONCAT("I", ROW()))',
        self.notes
    ]

  def merge_with(self, other) -> None:
    self.orders.update(other.orders)
    self.trackings.update(other.trackings)
    self.expected_cost += other.expected_cost
    self.tracked_cost += other.tracked_cost
    self.last_ship_date = max(self.last_ship_date, other.last_ship_date)
    self.purchase_orders.update(other.purchase_orders)
    self.adjustment += other.adjustment
    if self.notes and other.notes:
      self.notes += ", " + other.notes
    elif other.notes:
      self.notes = other.notes
    self.manual_override = self.manual_override and other.manual_override
    self.non_reimbursed_trackings.update(other.non_reimbursed_trackings)


def dedupe_clusters(clusters) -> list:
  result = []
  seen_tracking_ids = set()
  for cluster in clusters:
    if not cluster.group:
      continue
    if not cluster.trackings.intersection(seen_tracking_ids):
      seen_tracking_ids.update(cluster.trackings)
      result.append(cluster)
  return result


def write_clusters(config, clusters) -> None:
  clusters = dedupe_clusters(clusters)
  if not os.path.exists(OUTPUT_FOLDER):
    os.mkdir(OUTPUT_FOLDER)

  with open(CLUSTERS_FILE, 'wb') as output:
    pickle.dump(clusters, output)

  objects_to_drive = ObjectsToDrive()
  objects_to_drive.save(config, CLUSTERS_FILENAME, CLUSTERS_FILE)


def get_existing_clusters(config) -> list:
  objects_to_drive = ObjectsToDrive()
  from_drive = objects_to_drive.load(config, CLUSTERS_FILENAME)
  if from_drive:
    return from_drive

  print(
      "Drive folder ID not present or we couldn't load from drive. Loading from local"
  )
  if not os.path.exists(CLUSTERS_FILE):
    return []

  with open(CLUSTERS_FILE, 'rb') as clusters_file_stream:
    clusters = pickle.load(clusters_file_stream)
  return dedupe_clusters(clusters)


def find_cluster(all_clusters, tracking) -> Any:
  for cluster in all_clusters:
    if cluster.group == tracking.group and cluster.orders.intersection(
        set(tracking.order_ids)):
      return cluster
  return None


def update_clusters(all_clusters, trackings) -> None:
  for tracking in trackings:
    cluster = find_cluster(all_clusters, tracking)
    if cluster is None:
      cluster = Cluster(tracking.group)
      all_clusters.append(cluster)

    cluster.orders.update(tracking.order_ids)
    cluster.trackings.add(tracking.tracking_number)
    cluster.last_ship_date = max(cluster.last_ship_date, tracking.ship_date)
    cluster.to_email = tracking.to_email


def merge_by_purchase_orders(clusters) -> list:
  while True:
    prev_length = len(clusters)
    clusters = run_merge_iteration(clusters)
    if len(clusters) == prev_length:
      break
  return clusters


def run_merge_iteration(clusters) -> list:
  result = []
  for cluster in clusters:
    to_merge = find_by_purchase_orders(cluster, result)
    if to_merge:
      to_merge.merge_with(cluster)
    else:
      result.append(cluster)
  return result


def find_by_purchase_orders(cluster, all_clusters) -> Any:
  if not cluster.purchase_orders:
    return None

  for candidate in all_clusters:
    if candidate.group == cluster.group and candidate.purchase_orders.intersection(
        cluster.purchase_orders):
      return candidate

  return None


def from_row(header, row) -> Cluster:
  orders = set(str(
      row[header.index('Orders')]).split(',')) if 'Orders' in header else set()
  trackings = set(str(row[header.index('Trackings')]).split(
      ',')) if 'Trackings' in header else set()
  expected_cost = float(
      row[header.index('Amount Billed')]) if 'Amount Billed' in header else 0.0
  tracked_cost_str = row[header.index(
      "Amount Reimbursed")] if "Amount Reimbursed" in header else ''
  tracked_cost = float(tracked_cost_str) if tracked_cost_str else 0.0
  non_reimbursed_str = str(row[header.index("Non-Reimbursed Trackings")]
                          ) if "Non-Reimbursed Trackings" in header else ""
  non_reimbursed_trackings = set(
      non_reimbursed_str.split(',')) if non_reimbursed_str else set()
  last_ship_date = row[header.index(
      'Last Ship Date')] if 'Last Ship Date' in header else '0'
  pos_string = str(row[header.index('POs')]) if 'POs' in header else ''
  pos = set(pos_string.split(',')) if pos_string else set()
  group = row[header.index('Group')] if 'Group' in header else ''
  adj_string = row[header.index(
      "Manual Cost Adjustment")] if "Manual Cost Adjustment" in header else ''
  adjustment = float(adj_string) if adj_string else 0.0
  manual_override = row[header.index(
      'Manual Override')] if 'Manual Override' in header else False
  to_email = row[header.index('To Email')] if 'To Email' in header else ''
  notes = str(row[header.index('Notes')]) if 'Notes' in header else ''
  cluster = Cluster(group)
  cluster._initiate(orders, trackings, group, expected_cost, tracked_cost,
                    last_ship_date, pos, adjustment, to_email, notes,
                    manual_override, non_reimbursed_trackings)
  return cluster
