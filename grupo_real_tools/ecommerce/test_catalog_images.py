from unittest import TestCase
from unittest.mock import patch

import frappe

from grupo_real_tools.ecommerce.api.item import _get_item_images, get_items_from_template


class TestCatalogImages(TestCase):
	@patch("grupo_real_tools.ecommerce.api.item.frappe.get_all")
	def test_images_are_scoped_ordered_and_filtered(self, get_all):
		get_all.return_value = [
			frappe._dict(attached_to_name="PARENT", file_url="/files/front.JPG"),
			frappe._dict(attached_to_name="PARENT", file_url="/files/notes.pdf"),
			frappe._dict(attached_to_name="PARENT", file_url="/private/files/secret.png"),
			frappe._dict(attached_to_name="PARENT", file_url="https://example.com/image.jpg"),
			frappe._dict(attached_to_name="PARENT", file_url="/files/%2e%2e/secret.jpg"),
			frappe._dict(attached_to_name="VARIANT", file_url="/files/back.jpeg"),
		]
		self.assertEqual(
			_get_item_images(["PARENT", "VARIANT"]),
			{"PARENT": [{"url": "/files/front.JPG"}], "VARIANT": [{"url": "/files/back.jpeg"}]},
		)
		filters = get_all.call_args.kwargs["filters"]
		self.assertEqual(filters["is_private"], 0)
		self.assertEqual(filters["is_folder"], 0)
		self.assertEqual(filters["attached_to_doctype"], "Item")
		self.assertEqual(filters["attached_to_name"], ["in", ["PARENT", "VARIANT"]])

	@patch("grupo_real_tools.ecommerce.api.item.frappe.get_all")
	def test_empty_items_do_not_query(self, get_all):
		self.assertEqual(_get_item_images([]), {})
		get_all.assert_not_called()

	@patch("grupo_real_tools.ecommerce.api.item._get_item_price", return_value={"price_list_rate": 10})
	@patch("grupo_real_tools.ecommerce.api.item._get_item_images")
	@patch("grupo_real_tools.ecommerce.api.item.frappe.db.sql")
	@patch("grupo_real_tools.ecommerce.api.item._get_catalog_warehouse", return_value="Test warehouse")
	def test_detail_keeps_parent_and_variant_images_separate(self, _warehouse, sql, get_images, _price):
		sql.return_value = [
			frappe._dict(item_code="V1", template_item_name="Product", image="/files/main.jpg",
				item_group="Test", attributes="{}"),
			frappe._dict(item_code="V2", template_item_name="Product", image="/files/v2.jpg",
				item_group="Test", attributes="{}"),
		]
		get_images.return_value = {
			"PARENT": [{"url": "/files/parent.jpg"}],
			"V1": [{"url": "/files/v1.png"}],
			"V2": [],
		}
		result = get_items_from_template("PARENT")
		self.assertEqual(result["image"], "/files/main.jpg")
		self.assertEqual(result["images"], [{"url": "/files/parent.jpg"}])
		self.assertEqual(result["variants"][0].images, [{"url": "/files/v1.png"}])
		self.assertEqual(result["variants"][1].images, [])
