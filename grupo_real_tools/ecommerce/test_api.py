from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from grupo_real_tools.ecommerce.api import item, item_attribute, item_group


class TestEcommerceApi(TestCase):
	def test_public_methods_are_guest_get_endpoints(self):
		methods = (
			item.get_items,
			item.get_items_from_template,
			item_group.get_item_groups,
			item_attribute.get_item_attributes,
		)

		for method in methods:
			self.assertIn(method, frappe.whitelisted)
			self.assertIn(method, frappe.guest_methods)
			self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[method], ["GET"])

	@patch("grupo_real_tools.ecommerce.api.item.frappe.db.sql", return_value=[])
	@patch("grupo_real_tools.ecommerce.api.item._get_catalog_warehouse", return_value="Test Warehouse")
	def test_item_list_uses_bounded_stable_pagination(self, _warehouse, sql):
		self.assertEqual(item.get_items(start=20, limit=10), [])

		query, parameters = sql.call_args.args[:2]
		self.assertIn("ORDER BY item.creation DESC, item.name DESC", query)
		self.assertEqual(parameters["start"], 20)
		self.assertEqual(parameters["limit"], 10)
		self.assertEqual(parameters["warehouse"], "Test Warehouse")

	@patch("grupo_real_tools.ecommerce.api.item_attribute.frappe.get_all")
	def test_item_attributes_map_values(self, get_all):
		get_all.return_value = [frappe._dict(value="Red", abbr="R")]

		self.assertEqual(item_attribute.get_item_attributes("Color"), [{"value": "Red", "abbr": "R"}])
		self.assertEqual(get_all.call_args.kwargs["filters"]["parent"], "Color")

	def test_item_groups_build_nested_tree(self):
		query_builder = MagicMock()
		query = MagicMock()
		query_builder.from_.return_value = query
		query.select.return_value = query
		query.where.return_value = query
		query.orderby.return_value = query
		query.run.return_value = [
			{"name": "Clothing", "parent_item_group": None, "is_group": 1},
			{"name": "Shirts", "parent_item_group": "Clothing", "is_group": 0},
		]

		with patch("grupo_real_tools.ecommerce.api.item_group.frappe.qb", query_builder):
			result = item_group.get_item_groups()

		self.assertEqual(
			result,
			[
				{
					"name": "Clothing",
					"parent_item_group": None,
					"is_group": True,
					"children": [
						{
							"name": "Shirts",
							"parent_item_group": "Clothing",
							"is_group": False,
							"children": [],
						}
					],
				}
			],
		)
