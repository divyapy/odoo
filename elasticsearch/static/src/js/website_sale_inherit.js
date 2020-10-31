odoo.define('elasticsearch.productsearchbar', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var qweb = core.qweb;

    qweb.add_template('/elasticsearch/static/src/xml/templates.xml');

    publicWidget.registry.productsSearchBar.include({
        _render: function (res) {
            console.log("Render Method Called.")
            var $prevMenu = this.$menu;
            this.$el.toggleClass('dropdown show', !!res);
            if (res) {
                var products = res['products'];
                if('brands' in res){
                  this.$menu = $(qweb.render("elasticsearch.productsSearchBar_autocomplete", {
                      sequence: res['sequence'],
                      products: products,
                      brands: res['brands'],
                      categorys: res['category'],
                      hasMoreProducts: products.length < res['products_count'],
                      currency: res['currency'],
                      widget: this,
                  }));
                }
                else{
                  this.$menu = $(qweb.render("website_sale.productsSearchBar.autocomplete", {
                      products: products,
                      hasMoreProducts: products.length < res['products_count'],
                      currency: res['currency'],
                      widget: this,
                  }));
                }
                this.$menu.css('min-width', this.autocompleteMinWidth);
                this.$el.append(this.$menu);
            }
            if ($prevMenu) {
                $prevMenu.remove();
            }
        },
    });
});
