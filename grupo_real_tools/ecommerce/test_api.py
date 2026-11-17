from unittest import TestCase
from unittest.mock import patch

from grupo_real_tools.ecommerce.api import item, item_attribute, item_group


class TestEcommerceApi(TestCase):
	@patch("grupo_real_tools.ecommerce.api.item.catalog.get_items")
	def test_item_list_delegates_parameters(self, get_items):
		get_items.return_value = [{"item_code": "ITEM-1"}]

		result = item.get_items(sale=True, category="Clothing", size="M", color="Red", start=20, limit=10)

		self.assertEqual(result, [{"item_code": "ITEM-1"}])
		get_items.assert_called_once_with(
			sale=True,
			category="Clothing",
			size="M",
			color="Red",
			start=20,
			limit=10,
		)

	@patch("grupo_real_tools.ecommerce.api.item.catalog.get_items_from_template")
	def test_item_detail_delegates_item_code(self, get_items_from_template):
		item.get_items_from_template("ITEM-TEMPLATE")

		get_items_from_template.assert_called_once_with("ITEM-TEMPLATE")

	@patch("grupo_real_tools.ecommerce.api.item_group.catalog.get_item_groups")
	def test_item_group_delegates(self, get_item_groups):
		item_group.get_item_groups()

		get_item_groups.assert_called_once_with()

	@patch("grupo_real_tools.ecommerce.api.item_attribute.catalog.get_item_attributes")
	def test_item_attribute_delegates(self, get_item_attributes):
		item_attribute.get_item_attributes("Color")

		get_item_attributes.assert_called_once_with("Color")
