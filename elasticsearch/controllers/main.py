# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime
from werkzeug.exceptions import Forbidden, NotFound
from collections import defaultdict

from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.http import request
from odoo.addons.base.models.ir_qweb_fields import nl2br
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.exceptions import ValidationError
from odoo.addons.website.controllers.main import Website
from odoo.addons.website_form.controllers.main import WebsiteForm
from odoo.osv import expression
from odoo.addons.website_sale.controllers.main import WebsiteSale, TableCompute

_logger = logging.getLogger(__name__)


class WebsiteSaleElasticSearch(WebsiteSale):

    def _get_ec_search_order(self, post):
        order = post.get('order')
        return '%s' % order

    @http.route([
        '''/shop''',
        '''/shop/page/<int:page>''',
        '''/shop/category/<model("product.public.category"):category>''',
        '''/shop/category/<model("product.public.category"):category>/page/<int:page>'''
    ], type='http', auth="public", website=True, sitemap=WebsiteSale.sitemap_shop)
    def shop(self, page=0, category=None, search='', ppg=False, **post):
        add_qty = int(post.get('add_qty', 1))
        Category = request.env['product.public.category']
        Brand = request.env['product.brand.ept']
        if category:
            category = Category.search([('id', '=', int(category))], limit=1)
            if not category or not category.can_access_from_current_website():
                raise NotFound()
        else:
            category = Category

        if ppg:
            try:
                ppg = int(ppg)
                post['ppg'] = ppg
            except ValueError:
                ppg = False
        if not ppg:
            ppg = request.env['website'].get_current_website().shop_ppg or 20

        ppr = request.env['website'].get_current_website().shop_ppr or 4

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
        attributes_ids = {v[0] for v in attrib_values}
        attrib_set = {v[1] for v in attrib_values}

        domain = self._get_search_domain(search, category, attrib_values)
        ec_domain = self._get_search_domain(False, category, attrib_values)
        keep = QueryURL('/shop', category=category and int(category), search=search, attrib=attrib_list, order=post.get('order'))
        pricelist_context, pricelist = self._get_pricelist_context()

        request.context = dict(request.context, pricelist=pricelist.id, partner=request.env.user.partner_id)

        url = "/shop"
        if search:
            post["search"] = search
        if attrib_list:
            post['attrib'] = attrib_list

        Product = request.env['product.template'].with_context(bin_size=True)
        ElasticServer = request.env['elastic.server.configuration']
        es_obj =  ElasticServer.search([('active', '=', True)], limit=1)
        IndexObj = request.env['elastic.index.configuration']

        _logger.info('START======shop=method=======%s=====' %(datetime.now()))

        search_product = []
        ei_pt_obj =  IndexObj.search([('ec_name', '=', 'product-template')])
        ec_products = []
        brands = []
        categorys = []
        if ei_pt_obj and search and es_obj:
            ec_result = IndexObj.website_product_search(search, ei_pt_obj)
            ec_products = ec_result['products']
            ec_products = map(int, ec_products)
            search_product = request.env['product.template'].browse(ec_products)
            if self._get_ec_search_order(post).strip():
                search_product = request.env['product.template'].search([('id', 'in', search_product.ids)], order=self._get_ec_search_order(post))
            ## Brands

            if 'brands' in ec_result and  ec_result['brands']:
                for line in ec_result['brands']:
                    if line:
                        brand = Brand.search([('id', '=', int(line))], limit=1)
                        url = "/brand/%s" % slug(brand)
                        brand_data = {
                            'url': url,
                            'name': brand.name,
                            'id': brand.id
                        }
                        brands.append(brand_data)

            ## Brands

            ## Category

            if 'category' in ec_result and ec_result['category']:
                for line in ec_result['category']:
                    if line:
                        categorie = Category.search([('id', '=', int(line))], limit=1)
                        url = "/shop/category/%s" % slug(categorie)
                        cat_data = {
                            'url': url,
                            'name': categorie.name,
                            'id': categorie.id
                        }
                        categorys.append(cat_data)

            ## Category

        else:
            search_product = Product.search(domain, order=self._get_search_order(post))

        website_domain = request.website.website_domain()
        categs_domain = [('parent_id', '=', False)] + website_domain

        # ei_pc_obj =  IndexObj.search([('ec_name', '=', 'product-public-category')])
        # if ei_pc_obj and es_obj:
        #     if search:
        #         ec_search_categories = IndexObj.website_categories_search(ei_pc_obj, search_product.ids)
        #         search_categories = Category.search([('id', 'in', ec_search_categories)] + website_domain).parents_and_self
        #         categs_domain.append(('id', 'in', search_categories.ids))
        #     else:
        #         search_categories = Category
        #     categs = Category.search(categs_domain)
        # else:
        if search:
            search_categories = Category.search([('product_tmpl_ids', 'in', search_product.ids)] + website_domain).parents_and_self
            categs_domain.append(('id', 'in', search_categories.ids))
        else:
            search_categories = Category
        categs = Category.search(categs_domain)

        if category:
            url = "/shop/category/%s" % slug(category)

        product_count = len(search_product)
        pager = request.website.pager(url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)
        offset = pager['offset']
        products = search_product[offset: offset + ppg]

        ProductAttribute = request.env['product.attribute']
        # ei_pa_obj =  IndexObj.search([('ec_name', '=', 'product-attribute')])
        # if ei_pa_obj and ec_products and products and es_obj:
        #     ec_attributes = IndexObj.website_attribute_search(ei_pa_obj, ec_products)
        #     attributes = ProductAttribute.search([('id', 'in', ec_attributes)])
        # el
        if products:
            # get all products without limit
            attributes = ProductAttribute.search([('product_tmpl_ids', 'in', search_product.ids)])
        else:
            attributes = ProductAttribute.browse(attributes_ids)

        _logger.info('END======shop=method========%s=====' %(datetime.now()))

        layout_mode = request.session.get('website_sale_shop_layout_mode')
        if not layout_mode:
            if request.website.viewref('website_sale.products_list_view').active:
                layout_mode = 'list'
            else:
                layout_mode = 'grid'
        values = {
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'add_qty': add_qty,
            'products': products,
            'search_count': product_count,  # common for all searchbox
            'bins': TableCompute().process(products, ppg, ppr),
            'ppg': ppg,
            'ppr': ppr,
            'categories': categs,
            'attributes': attributes,
            'keep': keep,
            'search_categories_ids': search_categories.ids,
            'layout_mode': layout_mode,
            **({'ec_brands': [brands[i:i + ppr] for i in range(0, len(brands), ppr)]} if brands else {}),
            **({'ec_categorys': [categorys[i:i + ppr] for i in range(0, len(categorys), ppr)]} if categorys else {}),
        }
        if category:
            values['main_object'] = category
        return request.render("website_sale.products", values)


    @http.route('/shop/products/autocomplete', type='json', auth='public', website=True)
    def products_autocomplete(self, term, options={}, **kwargs):
        """
        Returns list of products according to the term and product options

        Params:
            term (str): search term written by the user
            options (dict)
                - 'limit' (int), default to 5: number of products to consider
                - 'display_description' (bool), default to True
                - 'display_price' (bool), default to True
                - 'order' (str)
                - 'max_nb_chars' (int): max number of characters for the
                                        description if returned

        Returns:
            dict (or False if no result)
                - 'products' (list): products (only their needed field values)
                        note: the prices will be strings properly formatted and
                        already containing the currency
                - 'products_count' (int): the number of products in the database
                        that matched the search query
        """
        ProductTemplate = request.env['product.template']
        Category = request.env['product.public.category']
        Brand = request.env['product.brand.ept']

        display_description = options.get('display_description', True)
        display_price = options.get('display_price', True)
        order = self._get_search_order(options)
        max_nb_chars = options.get('max_nb_chars', 999)
        category = options.get('category')
        attrib_values = options.get('attrib_values')

        domain = self._get_search_domain(term, category, attrib_values, display_description)
        # _logger.info('domain======products_autocomplete========%s=====' %(domain))

        ElasticServer = request.env['elastic.server.configuration']
        es_obj =  ElasticServer.search([('active', '=', True)], limit=1)
        IndexObj = request.env['elastic.index.configuration']
        ei_pt_obj =  IndexObj.search([('ec_name', '=', 'product-template')])
        ei_pp_obj =  IndexObj.search([('ec_name', '=', 'product-product')])
        ei_ppc_obj =  IndexObj.search([('ec_name', '=', 'product-public-category')])
        ei_pbe_obj =  IndexObj.search([('ec_name', '=', 'product-brand-ept')])
        products = []
        brands = []
        categorys = []
        # _logger.info('START======products_autocomplete========%s=====' %(datetime.now()))
        if ei_pt_obj and ei_pp_obj and ei_ppc_obj and ei_pbe_obj and es_obj:
            res = IndexObj.website_autocomplete_product_search(term, ei_pt_obj, min(20, options.get('limit', 5)))
            ## Brands

            if 'brands' in res and res['brands']:
                for line in res['brands']:
                    # for key,value in line.items():
                    if line:
                        brand = Brand.search([('id', '=', int(line))], limit=1)
                        url = "/brand/%s" % slug(brand)
                        brand_data = {
                            'url': url,
                            'name': brand.name,
                            'id': brand.id
                        }
                        brands.append(brand_data)
            res['brands'] = brands

            ## Brands

            ## Category

            if 'category' in res and res['category']:
                for line in res['category']:
                    # for key,value in line.items():
                    if line:
                        category = Category.search([('id', '=', int(line))], limit=1)
                        url = "/shop/category/%s" % slug(category)
                        cat_data = {
                            'url': url,
                            'name': category.name,
                            'id': category.id
                        }
                        categorys.append(cat_data)
            res['category'] = categorys

            ## Category

            ## Product Variants

            variant_res = {}
            if 'variant' in res and res['variant']:
                p_ids = []
                for line in res['variant']:
                    tmp = list(line.values())
                    p_ids.append(tmp[0])
                domain = [('id', 'in', p_ids)]
                variant_products = ProductTemplate.search(
                    domain,
                    limit=min(20, options.get('limit', 5)),
                    order=order
                )
                fields = ['id', 'name', 'website_url']
                if display_description:
                    fields.append('description_sale')

                variant_res = {
                    'products': variant_products.read(fields),
                    'products_count': ProductTemplate.search_count(domain),
                }
                if display_description:
                    for res_product in variant_res['products']:
                        desc = res_product['description_sale']
                        if desc and len(desc) > max_nb_chars:
                            res_product['description_sale'] = "%s..." % desc[:(max_nb_chars - 3)]

                if display_price:
                    FieldMonetary = request.env['ir.qweb.field.monetary']
                    monetary_options = {
                        'display_currency': request.website.get_current_pricelist().currency_id,
                    }
                    for res_product, product in zip(variant_res['products'], variant_products):
                        combination_info = product._get_combination_info(only_template=True)
                        res_product.update(combination_info)
                        res_product['list_price'] = FieldMonetary.value_to_html(res_product['list_price'], monetary_options)
                        res_product['price'] = FieldMonetary.value_to_html(res_product['price'], monetary_options)

                _logger.info('========products_autocomplete=======variant_res======== %s' %(variant_res))

            ## Product Variants

            if display_description:
                for res_product in res['products']:
                    desc = res_product['description_sale']
                    if desc and len(desc) > max_nb_chars:
                        res_product['description_sale'] = "%s..." % desc[:(max_nb_chars - 3)]

            if display_price:
                FieldMonetary = request.env['ir.qweb.field.monetary']
                monetary_options = {
                    'display_currency': request.website.get_current_pricelist().currency_id,
                }
                for res_product in res['products']:
                    res_product['list_price'] = FieldMonetary.value_to_html(res_product['list_price'], monetary_options)
                    res_product['price'] = FieldMonetary.value_to_html(res_product['price'], monetary_options)
            # _logger.info('END====IF======products_autocomplete========%s=====' %(datetime.now()))

            if 'products' in variant_res and variant_res['products']:
                res['products'] = res['products'] + variant_res['products']

            _logger.info('=======products_autocomplete========res======== %s' %(res))
            return res
        else:
            products = ProductTemplate.search(
                domain,
                limit=min(20, options.get('limit', 5)),
                order=order
            )

            fields = ['id', 'name', 'website_url']
            if display_description:
                fields.append('description_sale')

            res = {
                'products': products.read(fields),
                'products_count': ProductTemplate.search_count(domain),
            }

            if display_description:
                for res_product in res['products']:
                    desc = res_product['description_sale']
                    if desc and len(desc) > max_nb_chars:
                        res_product['description_sale'] = "%s..." % desc[:(max_nb_chars - 3)]

            if display_price:
                FieldMonetary = request.env['ir.qweb.field.monetary']
                monetary_options = {
                    'display_currency': request.website.get_current_pricelist().currency_id,
                }
                for res_product, product in zip(res['products'], products):
                    combination_info = product._get_combination_info(only_template=True)
                    res_product.update(combination_info)
                    res_product['list_price'] = FieldMonetary.value_to_html(res_product['list_price'], monetary_options)
                    res_product['price'] = FieldMonetary.value_to_html(res_product['price'], monetary_options)
            # _logger.info('END====ELSE======products_autocomplete========%s=====' %(datetime.now()))
            return res
