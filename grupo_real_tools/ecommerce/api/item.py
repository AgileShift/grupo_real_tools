from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

import frappe
from erpnext.utilities.product import get_price
from frappe import _
from frappe.utils import cint, flt
from frappe.utils.caching import http_cache, redis_cache


MAX_PAGE_LENGTH = 50


def _comma_separated_to_list(value: str | None) -> list[str]:
	if not value:
		return []

	return [item.strip() for item in value.split(",") if item.strip()]


def _build_base_query():
	"""
	Query for Availability: projected_qty = actual_qty - reserved_qty | Planned | Requested | Ordered
	# actual_qty = All Items at Warehouse
	# reserved_qty = Sum of Items in Sales Orders(Not Draft) and Stock Reservation
	# projected_qty = actual_qty - reserved_qty
	# reserved_stock = Sum of Items in StockReservation

	# FIXME: Dont Show POS Reserved Stock! is like a Virtual Field?
	# TODO: Show BackOrder Products?(For future sales or pre-orders)
	"""
	return """
		SELECT
			item.item_code,
			item.item_name,
			item.image,
			item.item_group,
			item.variant_of,
			template.item_name as template_item_name,
			(bin.actual_qty - bin.reserved_stock) as actual_qty,
			COALESCE(
				(
					SELECT JSON_OBJECTAGG(va.attribute, JSON_OBJECT('value', va.attribute_value, 'abbr', av.abbr))
					FROM `tabItem Variant Attribute` AS va
					JOIN `tabItem Attribute Value` AS av
						ON av.parent = va.attribute AND av.attribute_value = va.attribute_value
					WHERE va.parent = item.name
				),
				JSON_OBJECT()
			) as attributes
		FROM `tabBin` AS bin
		JOIN `tabItem` AS item ON item.item_code = bin.item_code
		LEFT JOIN `tabItem` AS template ON template.name = item.variant_of
		WHERE (bin.actual_qty - bin.reserved_stock) > 0 AND bin.warehouse = %(warehouse)s
	"""


def _build_price_summary(variants: list[dict]) -> dict | None:
	prices = []
	first_price = None

	for variant in variants:
		price = variant.get("price") or {}
		price_list_rate = price.get("price_list_rate")

		if price_list_rate is None:
			continue

		if first_price is None:
			first_price = price

		prices.append(flt(price_list_rate))

	if not prices:
		return None

	min_price = min(prices)
	max_price = max(prices)

	return {
		"type": "single" if (min_price == max_price) else "range",
		"min_price": min_price,
		"max_price": max_price,
	}


def _get_catalog_warehouse() -> str | None:
	company = frappe.get_single_value("Global Defaults", "default_company")
	return frappe.get_value("Company", company, "default_warehouse") if company else None


def _group_items_by_template(items: list[dict]) -> list[dict]:
	products = {}

	for item in items:
		template_code = item.get("variant_of") or item.get("item_code")

		product = products.setdefault(template_code, {
			"item_code": template_code,
			"item_name": item.pop("template_item_name", None) or item.get("item_name"),
			"image": item.get("image"),
			"item_group": item.get("item_group"),
			"price_summary": None,
			"variants": [],
		})

		product["variants"].append(item)

	for product in products.values():
		product["price_summary"] = _build_price_summary(product["variants"])

	return list(products.values())


def _get_descendant_item_groups(item_groups: list[str]) -> list[str]:
	if not item_groups:
		return []

	descendant_groups = frappe.db.sql("""
		WITH RECURSIVE category_tree AS (
			SELECT name FROM `tabItem Group` WHERE name IN %(item_groups)s
			UNION ALL
			SELECT child.name FROM `tabItem Group` child
			INNER JOIN category_tree ON child.parent_item_group = category_tree.name
		)
		SELECT DISTINCT name FROM category_tree;
		""", {"item_groups": item_groups}, pluck='name')
	return descendant_groups


@frappe.whitelist(allow_guest=True, methods=["GET"])
@http_cache(public=True, max_age=300, stale_while_revalidate=900)
@redis_cache(ttl=90, user=None, shared=False)
def get_items(sale: bool = False, item_group: str = '', attributes: str = '', start: int = 0, limit: int = 19, sort: str = 'desc'):
	"""
	Get a list of available items, includes filtering by category and its descendants.

	Parameters:
		sale (bool): Fetches only items with discounts.
		item_group (str): Fetches items from the specified Item Groups and their descendants.
		start (int): Pagination start index.
		limit (int): Number of items to fetch.
		sort (str): Sort direction by creation date: asc or desc.
		attributes (str): JSON object mapping attribute names to selected values.

	Returns:
		List of items or a single item.
	"""
	start, limit = max(0, cint(start)), min(MAX_PAGE_LENGTH, max(1, cint(limit)))
	sort = (sort or '').lower()
	if sort not in {'asc', 'desc'}:
		frappe.throw(_('Sort order must be ASC or DESC.'))

	item_groups = _comma_separated_to_list(item_group)
	attribute_filters = frappe.parse_json(attributes) if attributes else {}

	warehouse = _get_catalog_warehouse()
	if not warehouse:
		return []

	query = _build_base_query()
	params = {"start": start, "limit": limit, "warehouse": warehouse}

	for index, (attribute, values) in enumerate(attribute_filters.items()):
		if not values:
			continue

		attribute_key = f"attribute_{index}"
		values_key = f"attribute_values_{index}"
		params[attribute_key] = attribute
		params[values_key] = tuple(values)

		match = f"""
			EXISTS (
				SELECT 1
				FROM `tabItem Variant Attribute` AS va
				WHERE va.parent = item.name
					AND va.attribute = %({attribute_key})s
					AND va.attribute_value IN %({values_key})s
			)
		"""

		if attribute == "Color":
			name_conditions = []
			for color_index, color_name in enumerate(values):
				key = f"color_like_{color_index}"
				params[key] = f"%{color_name.lower()}%"
				name_conditions.append(
					f"(LOWER(item.item_name) LIKE %({key})s OR LOWER(template.item_name) LIKE %({key})s)"
				)

			name_filter = " OR ".join(name_conditions)
			match += f"""
				OR (
					NOT EXISTS (
						SELECT 1
						FROM `tabItem Variant Attribute` AS va
						WHERE va.parent = item.name
							AND va.attribute = %({attribute_key})s
					)
					AND ({name_filter})
				)
			"""

		query += f" AND ({match})"

	if sale:
		items_on_sale = frappe.db.sql("""
			SELECT
				pri.item_code
			FROM `tabPricing Rule Item Code` pri
			JOIN `tabPricing Rule` pr ON pr.name = pri.parent
			WHERE
				pr.disable = 0 and pr.apply_on = 'Item Code'
			AND
				(pr.valid_from <= CURDATE() AND pr.valid_upto >= CURDATE()) -- TODO: Validate the valid_from and valid_upto dates.
		""", as_dict=True, pluck='item_code')

		if not items_on_sale:
			return []

		query += " AND item.item_code IN %(items_on_sale)s"
		params["items_on_sale"] = items_on_sale

	if item_groups:
		if descendant_groups := _get_descendant_item_groups(item_groups):
			params["item_groups"] = descendant_groups
			query += " AND item.item_group IN %(item_groups)s"
		else:
			return []  # Bad Item Group

	# Add Pagination
	items = frappe.db.sql(
		query + f" ORDER BY item.creation {sort}, item.name {sort} LIMIT %(start)s, %(limit)s;",
		params,
		as_dict=True,
	)

	for item in items:
		item.price = _get_item_price(item.item_code)
		item.attributes = frappe.parse_json(item.attributes)

	return _group_items_by_template(items)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_items_from_template(item_code: str):
	"""
	Get the template for a variant item and all available variants.

	Parameters:
		item_code (str): Variant item code used to resolve the template.

	Returns:
		Template item with available variants.
	"""
	warehouse = _get_catalog_warehouse()
	if not warehouse:
		return []

	items = frappe.db.sql("""
		SELECT
			item.item_code,
			item.item_name,
			item.image,
			item.item_group,
			item.variant_of,
			template.item_name as template_item_name,
			(bin.actual_qty - bin.reserved_stock) as actual_qty,
			COALESCE(
				(
					SELECT JSON_OBJECTAGG(va.attribute, JSON_OBJECT('value', va.attribute_value, 'abbr', av.abbr))
					FROM `tabItem Variant Attribute` AS va
					JOIN `tabItem Attribute Value` AS av
						ON av.parent = va.attribute AND av.attribute_value = va.attribute_value
					WHERE va.parent = item.name
				),
				JSON_OBJECT()
			) as attributes
		FROM `tabBin` AS bin
		JOIN `tabItem` AS item ON item.item_code = bin.item_code
		LEFT JOIN `tabItem` AS template ON template.name = item.variant_of
		WHERE
			(item.item_code = %(item_code)s OR item.variant_of = %(item_code)s)
			AND (bin.actual_qty - bin.reserved_stock) > 0
			AND bin.warehouse = %(warehouse)s
		ORDER BY item.creation ASC, item.name ASC
	""", {"item_code": item_code, "warehouse": warehouse}, as_dict=True)

	if not items:
		return []

	images = _get_item_images(list({item_code, *(item.item_code for item in items)}))
	prices = []
	product = {
		"item_code": item_code,
		"item_name": items[0].pop("template_item_name", None),
		"image": items[0].pop("image", None),
		"images": images[item_code],
		"item_group": items[0].pop("item_group", None),
		"price_summary": None,
		"variants": [],
	}

	for item in items:
		item.images = images[item.item_code]
		item.price = _get_item_price(item.item_code)
		item.attributes = frappe.parse_json(item.attributes)

		if item.price.get("price_list_rate") is not None:
			prices.append(flt(item.price.get("price_list_rate")))

		product["variants"].append(item)

	if prices:
		min_price = min(prices)
		max_price = max(prices)
		product["price_summary"] = {
			"type": "single" if min_price == max_price else "range",
			"min_price": min_price,
			"max_price": max_price,
		}

	return product


@redis_cache(ttl=120)
def _get_item_price(item_code):
	price = get_price(
		item_code=item_code,
		price_list=frappe.get_single_value('Selling Settings', 'selling_price_list'),
		customer_group='',
		company=frappe.get_single_value('Global Defaults', 'default_company')
	) or {}

	if price.get('formatted_discount_rate'):
		# When 'Formatted Discount Rate' is Set, other fields are empty so auto-calculated here!
		price.mrp = float(price.formatted_mrp.replace('$', '').strip())
		price.discount_rate = float(price.formatted_discount_rate.replace('$', '').strip())
		price.discount_percent = round((price.discount_rate / price.mrp) * 100, 2)

	if price.get('discount_percent'):  # If there is any discount. FIXME: As Fallback?
		price.formatted_discount_percent = f"{price.discount_percent:.0f}%"

	return price


def _get_item_images(item_codes: list[str]) -> dict[str, list[dict[str, str]]]:
	"""Return local public image attachments grouped by their exact Item."""
	images = {item_code: [] for item_code in item_codes}
	if not images:
		return images

	files = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "Item",
			"attached_to_name": ["in", list(images)],
			"is_private": 0,
			"is_folder": 0,
		},
		fields=["attached_to_name", "file_url"],
		order_by="creation asc, name asc",
		limit_page_length=0,
	)
	for file in files:
		url = file.file_url or ""
		parts = urlsplit(url)
		path = unquote(parts.path)
		if (
			parts.scheme or parts.netloc or parts.query or parts.fragment
			or not path.startswith("/files/")
			or ".." in PurePosixPath(path).parts
			or "\\" in path
			or PurePosixPath(path).suffix.lower() not in {".jpg", ".jpeg", ".png"}
		):
			continue
		images[file.attached_to_name].append({"url": url})

	return images
