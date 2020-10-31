odoo.define('pos_repair_order.pos_repair_order', function (require) {
    "use strict"
    var screens = require('point_of_sale.screens');
    var gui = require('point_of_sale.gui');
    var models = require('point_of_sale.models');
    var core = require('web.core');
    var _t = core._t;
    var popup_widget = require('point_of_sale.popups');
    var QWeb = core.qweb;
    var rpc = require('web.rpc');
    var SuperOrder = models.Order;
    var PosBaseWidget = require('point_of_sale.BaseWidget');
    var SuperClientListScreenWidget = screens.ClientListScreenWidget;
    var session = require('web.session');


    models.Order = models.Order.extend({
		initialize: function(attributes, options) {
            self = this;
            // self.repair_order_created = false;
            self.repair_id = null;
            self.repair_name = '';
            self.repair_type = false;
            self.operation_type = false;
            self.note = false;
            self.odometer_reading = false;
            self.v_model = false;
            self.v_brand = false;
            self.v_fuel_type = false;
            self.v_l_num =  false;
            self.vehicle_id = false;
            self.year = false;
            self.delivery_date = false;
            self.adv_pymt_done = false;
            self.pos_order_id = false;
            self.adv_pymt_data = false;
            self.repair_state = false;
            self.created_for = false;
			SuperOrder.prototype.initialize.call(this, attributes, options);
        },
        export_as_JSON: function() {
            var self = this;
            var loaded = SuperOrder.prototype.export_as_JSON.call(this);
            var current_order = self.pos.get_order();
            if (self.pos.get_order() != null) {
                loaded.repair_id = current_order.repair_id;
                loaded.repair_name = current_order.repair_name;
                loaded.repair_type = current_order.repair_type;
                loaded.operation_type = current_order.operation_type;
                loaded.note = current_order.note;
                loaded.odometer_reading = current_order.odometer_reading;
                loaded.v_model = current_order.v_model;
                loaded.v_brand = current_order.v_brand;
                loaded.v_fuel_type = current_order.v_fuel_type;
                loaded.v_l_num =  current_order.v_l_num;
                loaded.vehicle_id = current_order.vehicle_id;
                loaded.year = current_order.year;
                loaded.delivery_date = current_order.delivery_date;
                loaded.pos_order_id = current_order.pos_order_id;
                loaded.adv_pymt_data = current_order.adv_pymt_data;
                loaded.repair_state = current_order.repair_state;
                loaded.created_for = current_order.created_for;
            }
            return loaded;
        },

        cal_string: function(string){
            var res = string.split("\n");
            return res
        },
    });

    models.load_fields('product.product', 'type');    
    
    models.load_models([{
		model:'repair.order',
		fields:['partner_id','state','amount_total','date_order','name','pos_order_id', 'repair_type', 'final_pos_order_id', 'adv_pymt_amt'],
		loaded:function(self,quotations) {
            self.db.r_orders=[];
			self.db.all_repair_ids=[];
			self.db.all_quotations = quotations;
			self.db.repair_by_id = {};
			quotations = quotations.sort(function(a,b){
				return b.id - a.id;
			});
			quotations.forEach(function(quotation){
                if(quotation.name != false){
                    self.db.r_orders.push(quotation)
                    self.db.all_repair_ids.push(quotation.name);
                    self.db.repair_by_id[quotation.name] = quotation;
                }
			})
		}
	}]);

    models.load_models([
    {
        model: 'customer.vehicle',
        fields: ['license_number', 'model_id', 'brand_id', 'fuel_type_id', 'year'],
        loaded(self, vehicles) {
            self.vehicles = vehicles;
        },
    },
    {
        model: 'customer.vehicle.brand',
        fields: ['brand_name'],
        loaded(self, vehiclebrands) {
            self.vehiclebrands = vehiclebrands;
        },
    },
    {
        model: 'customer.vehicle.model',
        fields: ['model_name', 'brand_id'],
        loaded(self, vehiclemodels) {
            self.vehiclemodels = vehiclemodels;
        },
    },
    {
        model: 'fuel.type',
        fields: ['fuel_type'],
        loaded(self, fueltypes) {
            self.fueltypes = fueltypes;
        },
    }], {
            after: 'product.product',
        });

    var VehicleInformationWidget = PosBaseWidget.extend({
        template: 'VehicleInformationWidget',

        init: function(parent, options) {
            this._super(parent,options);
        },
    });

    var PrErrorNotifyPopopWidget = popup_widget.extend({
        template: 'PrErrorNotifyPopopWidget',
        events: {
            'click .button.cancel': 'click_cancel'
        },
        show: function (options) {
            var self = this;
            self._super(options);
            this.options = options;
        }
    });
    gui.define_popup({
        name: 'pr_error_notify',
        widget: PrErrorNotifyPopopWidget
    });

    var RepairOrderSavedPopopWidget = popup_widget.extend({
        template: 'RepairOrderSavedPopopWidget',
        events: {
            'click .button.cancel': 'click_cancel'
        },
        show: function (options) {
            var self = this;
            self._super(options)
            this.options = options;
            this.$('.order_status').show();
            $('#order_sent_status').hide();
            this.$('.order_status').removeClass('order_done');
            this.$('.show_tick').hide();
            setTimeout(function () {
                $('.order_status').addClass('order_done');
                $('.show_tick').show();
                $('#order_sent_status').show();
                $('.order_status').css({ 'border-color': '#5cb85c' })
            }, 500)
            if (!(self.options && self.options.quotation_status)) {
                setTimeout(function () {
                    self.pos.get_order().destroy({
                        'reason': 'abandon'
                    });
                }, 1500)
            }
            else {
                setTimeout(function () {
                    self.click_cancel();
                }, 1500)
            }
        },

        click_cancel: function () {
            this.pos.gui.close_popup();
        }
    });
    gui.define_popup({
        name: 'repair_order_saved',
        widget: RepairOrderSavedPopopWidget
    });

    var QuotationSavedPopopWidget = popup_widget.extend({
		template: 'QuotationSavedPopopWidget',
		events:{
			'click .button.cancel': 'click_cancel'
		},
		show: function(options){
			var self = this;
			self._super(options)
			this.options = options;
			this.$('.order_status').show();
			$('#order_sent_status').hide();
            this.$('.order_status').removeClass('order_done');
			this.$('.show_tick').hide();
			setTimeout(function(){
				$('.order_status').addClass('order_done');
  				$('.show_tick').show();
				$('#order_sent_status').show();
				$('.order_status').css({'border-color':'#5cb85c'})
			},500)
			if(!(self.options && self.options.quotation_status)){
				setTimeout(function(){
					self.pos.get_order().destroy({
						'reason': 'abandon'
					});
				},1500)
			}
			else{
				setTimeout(function(){
					self.click_cancel();
				},1500)
			}
		},

		click_cancel: function(){
			this.pos.gui.close_popup();
		}
	});
	gui.define_popup({
		name: 'quotation_saved',
		widget: QuotationSavedPopopWidget
	});

    screens.PaymentScreenWidget.include({
        template: 'PaymentScreenWidget',
        events: {
            'click #adv_pymt_validate': 'validate_adv_pymt',
            'click .button.adv_pymt_back': 'back_from_adv_pymt',
        },
        adv_order_is_valid: function(){
            var self = this;    
            var order = this.pos.get_order();
            if (Math.abs(order.get_total_paid()) < 0) {
                var cash = false;
                for (var i = 0; i < this.pos.payment_methods.length; i++) {
                    cash = cash || (this.pos.payment_methods[i].is_cash_count);
                }
                if (!cash) {
                    this.gui.show_popup('error',{
                        title: _t('Cannot return change without a cash payment method'),
                        body:  _t('There is no cash payment method available in this point of sale to handle the change.\n\n Please pay the exact amount or add a cash payment method in the point of sale configuration'),
                    });
                }
            }
            // if the change is too large, it's probably an input error, make the user confirm.
            if (order.get_total_with_tax() > 0 && (order.get_total_with_tax() * 1000 < order.get_total_paid())) {
                this.gui.show_popup('confirm',{
                    title: _t('Please Confirm Large Amount'),
                    body:  _t('Are you sure that the customer wants to  pay') + 
                           ' ' + 
                           this.format_currency(order.get_total_paid()) +
                           ' ' +
                           _t('for an order of') +
                           ' ' +
                           this.format_currency(order.get_total_with_tax()) +
                           ' ' +
                           _t('? Clicking "Confirm" will validate the payment.'),
                    confirm: function() {
                        self.validate_order('confirm');
                    },
                });
                return false;
            }
    
            return true;
        },
        finalize_adv_validation: function() {
            var self = this;
            var order = self.pos.get_order();
            var json = order.export_as_JSON();
            if(self.pos.get_order().repair_name){
                var order = self.pos.get_order();
                var order_vals = {
                    'repair_type': $("input[name='order_types']:checked").val(),
                    'note': $("#note").val(),
                    'operation_type': $("input[name='operation_type']:checked").val(),
                    'odometer_reading': parseFloat($("#odoo_meter").val()),
                    'delivery_date': $("#delivery_date").val(),
                    'vehicle_id': $("#client-vehicle").val(),
                    'partner_id': (order.get_client() != null) ? (order.get_client().id) : undefined
                }
                rpc.query({
                    model: 'repair.order',
                    method: 'update_repair_order',
                    args: [{"json": json, "order_vals": order_vals}]
                })
                .then(function(data){
                    var order = self.pos.get_order();
                    var json = order.export_as_JSON();
                    console.log(json, '=========json============qqq')
                    var order_amt;
                    if(order.get_total_paid() <= order.get_total_with_tax())
                        order_amt = order.get_total_paid();
                    else
                        order_amt = order.get_total_with_tax();
                    json['amount_total'] = order_amt
                    json['lines'] = [[0, 0, {
                        'qty': 1,
                        'price_unit': order_amt,
                        'price_subtotal': order_amt,
                        'price_subtotal_incl': order_amt,
                        'discount': 0,
                        'product_id': self.pos.config.adv_pymt_product_id[0],
                    }]]
                    json['to_invoice'] = false
                    json['product_data'] = []
                    json['created_for'] = 'ad_pymt';
                    var arr = []
                    var data = {
                        'id': json['uid'],
                        'data': json
                    }
                    arr.push(data);
                    rpc.query({
                        model: 'pos.order',
                        method: 'create_from_ui',
                        args: arr,
                        kwargs: {context: session.user_context}, 
                    })
                    .then(function (server_ids) {
                        console.log('======server_ids====', server_ids)
                    }).catch(function (reason){
                        console.log(reason, '++++++++++++++++')
                        var error = reason.message;
                        console.log(error, '++++++++++++++++')
                    });
                    self.gui.show_screen('receipt');
                })
                .catch(function(error){
                    console.log(error, '++++++++++error')
                    self.gui.show_popup('pr_error_notify', {
                        title: _t('Failed To update Quotation Details.'),
                        body: _t('Please make sure you are connected to the network.'),
                    });
                });
            }
            else{
                var order_vals = {};
                var oo_count = 0;
                order_vals.product_id = self.pos.config.product_id[0];
                order_vals.product_uom = self.pos.config.pr_uom_id[0];
                order_vals.date_order = order.creation_date;
                order_vals.user_id = self.pos.user.id;
                order_vals.session_id = self.pos.pos_session.id;
                order_vals.employee_id = self.pos.get_cashier().id;
                order_vals.pricelist_id = order.pricelist.id;
                order_vals.repair_type = $("input[name='order_types']:checked").val();
                order.odoometer_reading = parseFloat($("#odoo_meter").val());           
                order_vals.vehicle_id = $("#client-vehicle").val();
                order_vals.warehouse_id = self.pos.config.warehouse_id[0];
                order_vals.odoometer_reading = parseFloat($("#odoo_meter").val());
                if($("#delivery_date").val())
                    order_vals.expected_delivery_date = $("#delivery_date").val();
                order_vals.internal_notes = $("#note").val();
                order_vals.operation_type = $("input[name='operation_type']:checked").val();
                var vehicle;
                var dictionary = self.pos.vehicles;
                for(var i in dictionary){
                    if(dictionary[i].id == parseInt($("#client-vehicle").val())){
                        vehicle = dictionary[i];
                        break; 
                    }
                }
                order.delivery_date = $("#delivery_date").val();
                if(vehicle){
                    order.v_brand = vehicle.brand_id[1]
                    order.v_model = vehicle.model_id[1]
                    order.v_fuel_type = vehicle.fuel_type_id[1]
                    order.v_l_num = vehicle.license_number
                    order.year = vehicle.year
                }
                if (order.fiscal_position)
                    order_vals.fiscal_position_id = order.fiscal_position.id
                if (order.get_client() != null)
                    order_vals.partner_id = order.get_client().id;
                rpc.query({
                    model: 'repair.order',
                    method: 'create',
                    args: [order_vals],
                })
                    .then(function (new_quotation_id) {
                        var order = self.pos.get_order();
                        console.log(order, '===============order========1111')
                        order.repair_id = new_quotation_id;
                        rpc.query({
                            model: 'repair.order',
                            method: 'get_quotation_name',
                            args: [new_quotation_id],
                        })
                        .then(function (quote) {
                            console.log(quote, '==============quote11111')
                            console.log(order, '===============order========11112')
                            var order = self.pos.get_order();
                            order.repair_name = quote;
                            self.pos.db.all_repair_ids.unshift(quote);
                            var orderlines = order.get_orderlines();
                            var line_length = orderlines.length;
                            orderlines.forEach(function (orderline) {
                                var order_line_vals = {};
                                order_line_vals.repair_id = new_quotation_id;
                                if(orderline.stock_location_id){
                                    order_line_vals.stock_loc_id = orderline.stock_location_id;
                                }
                                order_line_vals.product_id = orderline.product.id;
                                order_line_vals.price_unit = orderline.get_unit_display_price();
                                order_line_vals.product_uom_qty = orderline.quantity;
                                order_line_vals.product_uom = orderline.product.uom_id[0];
                                
                                var tax_ids = [];
                                orderline.product.taxes_id.forEach(function (tax_id) {
                                    tax_ids.push(tax_id);
                                    order_line_vals.tax_id = [[6, false, tax_ids]];
                                });
                                if (orderline.product.type !== 'service') {
                                    // order_line_vals.location_id = self.pos.config.location_id[0];
                                    // order_line_vals.location_dest_id = self.pos.config.location_dest_id[0];
                                    order_line_vals.discount = orderline.discount;
                                    order_line_vals.type = 'add'; 
                                    order_line_vals.created_from = 'pos';
                                    rpc.query({
                                        model: 'repair.line',
                                        method: 'create',
                                        args: [order_line_vals],
                                    })
                                        .then(function (quotation_line_id) {
                                            oo_count+=1;
                                            if(oo_count === line_length){
                                                self.confirm_adv_order(new_quotation_id);
                                            }
                                        })
                                        .catch(function (error)  {
                                            self.gui.show_popup('pr_error_notify', {
                                                title: _t('Failed To Save Quotation Details.'),
                                                body: _t('Please make sure you are connected to the network.'),
                                            });
                                        });
                                }
                                else {
                                    order_line_vals.name = orderline.product.display_name;
                                    order_line_vals.created_from = 'pos';
                                    rpc.query({
                                        model: 'repair.fee',
                                        method: 'create',
                                        args: [order_line_vals],
                                    })
                                        .then(function (quotation_line_id) {
                                            oo_count+=1;
                                            if(oo_count === line_length){
                                                self.confirm_adv_order(new_quotation_id);
                                            }
                                        })
                                        .catch(function (error) {
                                            self.gui.show_popup('pr_error_notify', {
                                                title: _t('Failed To Save Quotation Details.'),
                                                body: _t('Please make sure you are connected to the network.'),
                                            });
                                        });
                                }

                            });

                            var order = self.pos.get_order();
                            var json = order.export_as_JSON();
                            console.log(json, '=========json============')
                            console.log(order.get_total_paid(), '================Paid')
                            console.log(order.get_total_with_tax(),'==========subtotal')
                            var order_amt;
                            if(order.get_total_paid() <= order.get_total_with_tax())
                                order_amt = order.get_total_paid();
                            else
                                order_amt = order.get_total_with_tax();
                            json['amount_total'] = order_amt
                            json['lines'] = [[0, 0, {
                                'qty': 1,
                                'price_unit': order_amt,
                                'price_subtotal': order_amt,
                                'price_subtotal_incl': order_amt,
                                'discount': 0,
                                'product_id': self.pos.config.adv_pymt_product_id[0],
                            }]]
                            json['to_invoice'] = false
                            json['product_data'] = []
                            json['created_for'] = 'ad_pymt';
                            var arr = []
                            var data = {
                                'id': json['uid'],
                                'data': json
                            }
                            arr.push(data);
                            rpc.query({
                                model: 'pos.order',
                                method: 'create_from_ui',
                                args: arr,
                                kwargs: {context: session.user_context}, 
                            })
                            .then(function (server_ids) {
                                console.log('========server_ids======', server_ids)
                            }).catch(function (reason){
                                console.log(reason, '++++++++++++++++')
                                var error = reason.message;
                                console.log(error, '++++++++++++++++')
                            });
                            self.gui.show_screen('receipt');
                        })
                        .catch(function(error){
                            console.log(error, '++++++++++error')
                            self.gui.show_popup('pr_error_notify', {
                                title: _t('Failed To Create Quotation.'),
                                body: _t('Please make sure you are connected to the network.'),
                            });
                        })
                    })
                    .catch(function (error)  {
                        console.log(error, '++++++++++error')
                        self.gui.show_popup('pr_error_notify', {
                            title: _t('Failed To Create Quotation.'),
                            body: _t('Please make sure you are connected to the network.'),
                        });
                    });
                // order.finalized = true;    
            }
        },
        confirm_adv_order: function(new_quotation_id){
            rpc.query({
                model: 'repair.order',
                method: 'confirm_repair_order',
                args: [new_quotation_id],
            })
            .then(function(){
                console.log('done');
            })
            .catch(function(error){
                console.log('error', error);
            })
        },
        check_paid_amount: function(){
            var self = this;
            var order = self.pos.get_order();
            console.log(order.get_subtotal(), '========get_subtotal=========')
            if(order.get_total_paid() > 0) {
                return true;
            }       
            return false;
        },
        validate_adv_pymt: function(){
            var self=this;
            if(self.adv_order_is_valid() && self.check_paid_amount()) {
                self.finalize_adv_validation();
            }
        },
        validate_order: function(force_validation) {
            if (this.order_is_valid(force_validation)) {
                this.validate_and_crate_picking_order();
            }
        },
        validate_and_crate_picking_order: function(){
            var self = this;
            // console.log(this.pos.get_order(), '=================');
            // console.log(this.pos.get_order().repair_id, '===============')
            if(self.pos.get_order().repair_id){
                var repair_id = self.pos.get_order().repair_id;
                var data = {
                    'repair_id': repair_id
                }
                self._rpc({
                    model: 'repair.order',
                    method: 'stock_picking_check',
                    args: [data],
                })
                .then(function(r_data){
                    console.log(r_data, 'then========data====stock_picking_check')
                    if(r_data.status){
                        self.pos.gui.show_popup('stock_picking_status_in_pos',{
                            'repair_name': r_data.repair_name,
                            'picking_info': r_data.data
                        }); 
                    }
                    else{
                        if(!self.pos.config.auto_repair_order_transfer){
                            console.log(data, '==========normal_data======')
                            self._rpc({
                                model: 'repair.order',
                                method: 'reverse_move_for_ro',
                                args: [data],
                            })
                            .then(function(data_i){
                                console.log('==========reverse_move_for_ro==data====', data_i);
                            })
                            .catch(function(error_i){
                                console.log('==========reverse_move_for_ro==error====', error_i);
                            });
                        }
                        else if(self.pos.config.auto_repair_order_transfer && self.pos.config.repair_order_op_type){
                            console.log(data, '===============data============auto_repair')
                            data["op_type_id"] = self.pos.config.repair_order_op_type[0];
                            self._rpc({
                                model: 'repair.order',
                                method: 'auto_repair_order_transfer',
                                args: [data],
                            })
                            .then(function(data_e){
                                console.log('==========auto_repair_order_transfer==data====', data_e);
                            })
                            .catch(function(error_e){
                                console.log('==========auto_repair_order_transfer==error====', error_e);
                            }); 
                        }
                        self.finalize_validation();
                    }
                })
                .catch(function(data){
                    console.log(data, 'catch========data====stock_picking_check')
                })
                // console.log(this.pos.config.auto_repair_order_transfer, '=============')
                // console.log(this.pos.config.repair_order_op_type, '=============')
            }
            else{
                self.finalize_validation();
            }
        },
        back_from_adv_pymt: function(){
            var self = this;
            self.gui.show_screen('order_screen', {});
        },
        show: function(){
            var self = this;
            this._super();
            if(this.pos.get_order().get_screen_data('previous-screen') == 'order_screen'){
                self.$('.back').hide();
                self.$('.next').hide();
                self.$('.adv_pymt_validate').show();
                self.$('.adv_pymt_back').show();
            }
            else{
                self.$('.adv_pymt_validate').hide();
                self.$('.adv_pymt_back').hide();
                self.$('.back').show();
                self.$('.next').show();
            }
            console.log(this.pos.get_order(), '======this.pos.get_order()')
            if(this.pos.get_order().repair_name && this.pos.get_order().repair_state){
                self.$('#repair_name_info').text(this.pos.get_order().repair_name + ',' + this.pos.get_order().repair_state);
            }
        }
    });

    var StockPickingStatusInPosPopupWidget = popup_widget.extend({
        template: 'StockPickingStatusInPosPopupWidget',
        events: {
            'click .button.cancel': 'click_cancel',
            'click .button.force_validate': 'force_validate_all_picking'
        },
        show: function (options) {
            var self = this;
            self._super(options);
            this.options = options;
        },
        force_validate_all_picking: function(){
            var self = this;
            console.log(self.pos.get_order().repair_id, '=============order===repair_id==')
            var repair_id = this.pos.get_order().repair_id;
            var data = {
                'repair_id': repair_id
            }
            self._rpc({
                model: 'repair.order',
                method: 'confirm_stock_picking_forcefully',
                args: [data],
            })
            .then(function(data){
                console.log(data, 'then=============data==============')
                self.pos.gui.close_popup();
            })
            .catch(function(data){
                console.log(data, 'catch=============data==============')
            })
        },
    });
    gui.define_popup({
        name: 'stock_picking_status_in_pos',
        widget: StockPickingStatusInPosPopupWidget
    });

    var NewOrdersScreenWidget = screens.ScreenWidget.extend({
        template: 'NewOrdersScreenWidget',

        events: {
            'click #create_vehcile_rec': 'create_new_vehicle',
            'click #wk_save_quotation': 'click_wk_save_quotation',
            'click #wk_save_print_quotation': 'click_wk_save_print_quotation',
            'click #wk_save_adv_quotation': 'click_wk_save_adv_quotation',
            'click .set-customer': 'show_customer_screen',
            'change .vehicle_num_dd': 'add_vehicle_info',
        },

        init: function (parent, options) {
            this._super(parent, options);
        },
        show_customer_screen: function(){
            var self = this;
            self.gui.show_screen('clientlist');
        },
        render_list: function (orders, stockable_order, serviceable_order) {
            var self = this;
            var loaded_order = self.pos.get_order();
            console.log(loaded_order, '++++++++loaded_order+++')
            if(loaded_order.repair_name){
                var date = new Date(loaded_order.delivery_date);
                console.log(date, '+++++++++date')
                this.$el.html(QWeb.render('NewOrdersScreenWidget', {
                    widget: this,
                    date: orders['date'],
                    partner_id: orders['partner_id'],
                    partner_phone: orders['partner_phone'],
                    name: orders['name'],
                    service: serviceable_order.length,
                    stock: stockable_order.length,
                    total_with_tax: orders['total_with_tax'],
                    total_tax: orders['total_tax'],
                    total_without_tax: orders['total_without_tax'],
                    order_types: loaded_order.repair_type,
                    client_vehicle: loaded_order.vehicle_id,
                    repair_name: loaded_order.repair_name,
                    odoo_meters: loaded_order.odometer_reading ? loaded_order.odometer_reading : undefined,
                    notes: loaded_order.note ? loaded_order.note : undefined,
                    operation_type: loaded_order.operation_type,
                    delivery_date: moment(date).format("YYYY/MM/DD hh:mm")
                }));
            }
            else{
                this.$el.html(QWeb.render('NewOrdersScreenWidget', {
                    widget: this,
                    date: orders['date'],
                    partner_id: orders['partner_id'],
                    partner_phone: orders['partner_phone'],
                    name: orders['name'],
                    service: serviceable_order.length,
                    stock: stockable_order.length,
                    total_with_tax: orders['total_with_tax'],
                    total_tax: orders['total_tax'],
                    total_without_tax: orders['total_without_tax'],
                    delivery_date: moment().format("YYYY/MM/DD hh:mm")
                }));
            }
            if (stockable_order.length > 0) {
                var contents = this.$el[0].querySelector('.wk-order-stock-list-contents');
                contents.innerHTML = "";
                for (var i = 0, len = stockable_order.length; i < len; i++) {
                    var orderline_html = QWeb.render('WkOrderLineStock', {
                        widget: this,
                        orderlines: stockable_order[i],
                    });
                    var orderline = document.createElement('tbody');
                    orderline.innerHTML = orderline_html;
                    orderline = orderline.childNodes[1];
                    contents.appendChild(orderline);
                }
            }
            if (serviceable_order.length > 0) {
                var contentsss = this.$el[0].querySelector('.wk-order-service-list-contents');
                contentsss.innerHTML = "";
                for (var ii = 0, lens = serviceable_order.length; ii < lens; ii++) {
                    var orderline_htmls = QWeb.render('WkOrderLineService', {
                        widget: this,
                        orderlines: serviceable_order[ii],
                    });
                    var orderlines = document.createElement('tbody');
                    orderlines.innerHTML = orderline_htmls;
                    orderlines = orderlines.childNodes[1];
                    contentsss.appendChild(orderlines);
                }
            }
        },
        add_vehicle_info: function(){
            var self = this;
            var dictionary = self.pos.vehicles;
            var vehicle;
            for(var i in dictionary){
                if(dictionary[i].id == parseInt(self.$("#client-vehicle").val())){
                    vehicle = dictionary[i];
                    break; 
                }
            }
            if(vehicle){
                var data = {
                    'v_brand' : vehicle.brand_id[1],
                    'v_model' : vehicle.model_id[1],
                    'v_fuel_type' : vehicle.fuel_type_id[1],
                    'v_l_num' : vehicle.license_number,
                    'v_model_year': vehicle.year
                }
                var vehicles_html = QWeb.render('VehicleInformationWidget', {
                    widget: self,
                    data: data,
                });
                self.$('.vehcile_info_tab').empty();
                self.$('.vehcile_info_tab').append(vehicles_html);
            }
        },
        show: function (options) {
            var self = this;
            self.options = options;
            self._super(options);
            var current_order = self.pos.get_order();
            var d = current_order.creation_date
            var curr_date = d.getDate();
            var curr_month = d.getMonth() + 1;
            var curr_year = d.getFullYear();
            var curr_hour = d.getHours();
            var curr_min = d.getMinutes();
            var curr_sec = d.getSeconds();
            var final_date = curr_date + "-" + curr_month + "-" + curr_year + " " + curr_hour + ":" + curr_min + ":" + curr_sec
            var orders = {
                'date': final_date,
                'partner_id': (current_order.get_client()) ? current_order.get_client().name : '-',
                'partner_phone': (current_order.get_client()) ? current_order.get_client().phone : '-',
                'name': 'Name',
                'total_with_tax': current_order.get_total_with_tax().toFixed(2),
                'total_tax': current_order.get_total_tax().toFixed(2),
                'total_without_tax': current_order.get_total_without_tax().toFixed(2)
            };
            var stockable_order = [];
            var serviceable_order = [];
            var lines = current_order.orderlines.models;
            for (var line = 0; line < lines.length; line++) {
                if (lines[line].product.type !== 'service') {
                    var stock_tax_ids = self.getTax(lines[line])
                    stockable_order.push({
                        'id': lines[line].product.id,
                        'taxes': stock_tax_ids,
                        'display_name': lines[line].product.display_name,
                        'quantity': parseFloat(lines[line].quantity),
                        'unit_price': parseFloat((lines[line].price).toFixed(2)),
                        'discount': lines[line].discount,
                        'price': parseFloat((lines[line].price * lines[line].quantity).toFixed(2))
                    })
                }
                else {
                    var service_tax_ids = self.getTax(lines[line]);
                    serviceable_order.push({
                        'id': lines[line].product.id,
                        'taxes': service_tax_ids,
                        'display_name': lines[line].product.display_name,
                        'quantity': parseFloat(lines[line].quantity),
                        'unit_price': parseFloat((lines[line].price).toFixed(2)),
                        'discount': lines[line].discount,
                        'price': parseFloat((lines[line].price * lines[line].quantity).toFixed(2))
                    })
                }
            }
            stockable_order = self.groupBy(stockable_order)
            serviceable_order = self.groupBy(serviceable_order)
            this.render_list(orders, stockable_order, serviceable_order);
            this.$('.back').on('click', function () {
                self.gui.show_screen('products');
            });

        },
        getTax: function (orderline) {
            var res_taxes = ['-'];
            orderline.get_taxes().forEach(function (tax_id) {
                res_taxes.push(tax_id.name);
            });
            if (res_taxes.length > 1) {
                res_taxes.shift();
            }
            return res_taxes;
        },
        groupBy: function (xs) {
            var result = xs.reduce((result, item) => {
                if (result.map.has(item.id)) {
                    result.map.get(item.id).quantity += parseFloat(item.quantity);
                    result.map.get(item.id).price += parseFloat(item.price);
                } else {
                    result.array.push(item);
                    result.map.set(item.id, item);
                }
                return result;
            }, { map: new Map(), array: [] }).array
            return result;
        },
        close: function () {
            this._super();
            this.$('.wk-order-list-contents').undelegate();
        },
        click_cancel: function () {
            this.pos.gui.close_popup();
        },
        create_new_vehicle: function () {
            var self = this;
            self.pos.gui.show_popup('create_vehicle');
        },
        click_wk_save_quotation: function (print_quotation) {
            var self = this;
            return new Promise(function (resolve, reject) {
                var order_type = self.$("input[name='order_types']:checked").val();
                // if(order_type !== 'quote'){
                //     self.gui.show_popup('pr_error_notify', {
                //         title: _t('Please go with Advance Payment.'),
                //         body: _t('Save option is for Quotation.'),
                //     });
                // }
                // else{
                    if(self.pos.get_order().repair_name){
                        var order = self.pos.get_order();
                        var json = order.export_as_JSON();
                        console.log(json, '+++++++json++++++')
                        var order_vals = {
                            'repair_type': self.$("input[name='order_types']:checked").val(),
                            'note': self.$("#note").val(),
                            'operation_type': self.$("input[name='operation_type']:checked").val(),
                            'odometer_reading': parseFloat(self.$("#odoo_meter").val()),
                            'delivery_date': self.$("#delivery_date").val(),
                            'vehicle_id': self.$("#client-vehicle").val(),
                            'partner_id': (order.get_client() != null) ? (order.get_client().id) : undefined
                        }
                        rpc.query({
                            model: 'repair.order',
                            method: 'update_repair_order',
                            args: [{"json": json, "order_vals": order_vals}]
                        })
                        .then(function(data){
                            console.log(data, '=============data==============')
                            console.log(print_quotation, '=======print_quotation=========')
                            self.pos.gui.show_popup('repair_order_saved', {
                                title: _t("Repair Order: "),
                                body: 'Repair Order updated successfully.',
                                repair_name: order.repair_name,
                            });
                            if(print_quotation === 'adv_pymt'){
                                self.gui.show_screen('receipt');
                            }
                        })
                        .catch(function(error){
                            self.gui.show_popup('pr_error_notify', {
                                title: _t('Failed To update Quotation Details.'),
                                body: _t('Please make sure you are connected to the network.'),
                            });
                        });
                        
                    }
                    else{
                        var order_type = self.$("input[name='order_types']:checked").val();
                        if(!order_type){
                            self.gui.show_popup('pr_error_notify', {
                                title: _t('Save'),
                                body: _t('Please select Type to save repair order.'),
                            });
                        }
                        else{
                            var current_order = self.pos.get_order();
                            var order_vals = {};
                            var o_count = 0;
                            order_vals.product_id = self.pos.config.product_id[0];
                            order_vals.product_uom = self.pos.config.pr_uom_id[0];
                            order_vals.date_order = current_order.creation_date;
                            order_vals.user_id = self.pos.user.id;
                            order_vals.session_id = self.pos.pos_session.id;
                            order_vals.employee_id = self.pos.get_cashier().id;
                            order_vals.pricelist_id = current_order.pricelist.id;
                            order_vals.repair_type = self.$("input[name='order_types']:checked").val();
                            order_vals.vehicle_id = self.$("#client-vehicle").val();
                            order_vals.odoometer_reading = parseFloat(self.$("#odoo_meter").val());
                            order_vals.warehouse_id = self.pos.config.warehouse_id[0];
                            order_vals.internal_notes = self.$("#note").val();
                            order_vals.operation_type = self.$("input[name='operation_type']:checked").val();
                            if(self.$("#delivery_date").val())
                                order_vals.expected_delivery_date = self.$("#delivery_date").val();
                            if (current_order.fiscal_position)
                                order_vals.fiscal_position_id = current_order.fiscal_position.id
                            // var sent_email = self.pos.config.send_email_on_save_quotation;
                            if (self.pos.get_order().get_client() != null)
                                order_vals.partner_id = self.pos.get_order().get_client().id;
                            rpc.query({
                                model: 'repair.order',
                                method: 'create',
                                args: [order_vals],
                            })
                                .then(function (new_quotation_id) {
                                    current_order.repair_id = new_quotation_id;
                                    rpc.query({
                                        model: 'repair.order',
                                        method: 'get_quotation_name',
                                        args: [new_quotation_id],
                                    })
                                    .then(function (quote) {
                                        var current_order = self.pos.get_order();
                                        console.log(quote, '==============quote22222')
                                        current_order.repair_name = quote;
                                        self.pos.db.all_repair_ids.unshift(quote);                                        
                                        if (print_quotation)
                                            self.created_quotation_id = new_quotation_id;
                                        var orderlines = self.pos.get_order().get_orderlines();
                                        var line_length = orderlines.length;
                                        orderlines.forEach(function (orderline) {
                                            var order_line_vals = {};
                                            order_line_vals.repair_id = new_quotation_id;
                                            order_line_vals.product_id = orderline.product.id;
                                            if(orderline.stock_location_id){
                                                order_line_vals.stock_loc_id = orderline.stock_location_id;
                                            }
                                            order_line_vals.price_unit = orderline.get_unit_display_price();
                                            order_line_vals.product_uom_qty = orderline.quantity;
                                            order_line_vals.product_uom = orderline.product.uom_id[0];                                            
                                            var tax_ids = [];
                                            orderline.product.taxes_id.forEach(function (tax_id) {
                                                tax_ids.push(tax_id);
                                                order_line_vals.tax_id = [[6, false, tax_ids]];
                                            });
                                            if (orderline.product.type !== 'service') {
                                                // order_line_vals.location_id = self.pos.config.location_id[0];
                                                // order_line_vals.location_dest_id = self.pos.config.location_dest_id[0];
                                                order_line_vals.discount = orderline.discount;
                                                order_line_vals.type = 'add';
                                                order_line_vals.created_from = 'pos';
                                                rpc.query({
                                                    model: 'repair.line',
                                                    method: 'create',
                                                    args: [order_line_vals],
                                                })
                                                    .then(function (quotation_line_id) {
                                                        o_count+=1;
                                                        if(o_count === line_length){
                                                            self.confirm_order(current_order.repair_id);
                                                            resolve();
                                                        }
                                                    })
                                                    .catch(function (error)  {
                                                        self.gui.show_popup('pr_error_notify', {
                                                            title: _t('Failed To Save Quotation Details.'),
                                                            body: _t('Please make sure you are connected to the network.'),
                                                        });
                                                        reject();
                                                    })
                                                    
                                            }
                                            else {
                                                order_line_vals.name = orderline.product.display_name;
                                                order_line_vals.created_from = 'pos';
                                                rpc.query({
                                                    model: 'repair.fee',
                                                    method: 'create',
                                                    args: [order_line_vals],
                                                })
                                                    .then(function (quotation_line_id) {
                                                        o_count+=1;
                                                        if(o_count === line_length){
                                                            self.confirm_order(current_order.repair_id);
                                                            resolve();
                                                        }
                                                    })
                                                    .catch(function (error)  {
                                                        self.gui.show_popup('pr_error_notify', {
                                                            title: _t('Failed To Save Quotation Details.'),
                                                            body: _t('Please make sure you are connected to the network.'),
                                                        });
                                                        reject();
                                                    })
                                            }

                                        });
                                        if(print_quotation!=='adv_pymt'){
                                            self.pos.gui.show_popup('repair_order_saved', {
                                                title: _t("Repair Order: "),
                                                body: 'Repair Order created successfully.',
                                                repair_name: current_order.repair_name,
                                            });
                                        }
                                    })
                                    .catch( function(){
                                        self.gui.show_popup('pr_error_notify', {
                                            title: _t('Failed To Create Quotation.'),
                                            body: _t('Please make sure you are connected to the network.'),
                                        });
                                        reject();
                                    })
                                })
                                .catch(function (error)  {
                                    self.gui.show_popup('pr_error_notify', {
                                        title: _t('Failed To Create Quotation.'),
                                        body: _t('Please make sure you are connected to the network.'),
                                    });
                                    reject();
                                });
                        }
                    // }
                }
            });
        },
        confirm_order: function(new_quotation_id){
            rpc.query({
                model: 'repair.order',
                method: 'confirm_repair_order',
                args: [new_quotation_id],
            })
            .then(function(){
                console.log('done');
            })
            .catch(function(error){
                console.log('error', error);
            })
        },
        click_wk_save_adv_quotation: function(){
            var self = this;
            var order = self.pos.get_order();
            var order_type = self.$("input[name='order_types']:checked").val();
            if(order.adv_pymt_done){
                self.gui.show_popup('pr_error_notify', {
                    title: _t('Error'),
                    body: _t('Advance payment done, Please go with Save and Save&Print'),
                });
            }
            else if(order_type!=='service'){
                self.gui.show_popup('pr_error_notify', {
                    title: _t('Please go with Save and Save&Print.'),
                    body: _t('Advance payment is only for service type order.'),
                });
            }
            else{
                var data = {
                    repair_type : self.$("input[name='order_types']:checked").val(),
                    vehicle_id : self.$("#client-vehicle").val(),
                    odoometer_reading : parseFloat(self.$("#odoo_meter").val())
                }
                self.gui.show_screen('payment', {adv_pymt_data: data});
            }
            // else{
            //     if(order_type === 'service' && self.pos.get_order().adv_pymt_done){
            //         self.gui.show_popup('pr_error_notify', {
            //             title: _t('Please go with Save and Save&Print.'),
            //             body: _t('Advance payment done, Please go with Save and Save&Print'),
            //         });
            //     }
            //     else if(order_type !== 'service' && !self.pos.get_order().adv_pymt_done){
            //         self.gui.show_popup('pr_error_notify', {
            //             title: _t('Please go with Save and Save&Print.'),
            //             body: _t('Advance payment is only for service type order'),
            //         });
            //     }
            // }

        },
        click_wk_save_print_quotation: function(){
            var self = this;
            // var order_type = self.$("input[name='order_types']:checked").val();
            // if(order_type !== 'quote'){
            //     self.gui.show_popup('pr_error_notify', {
            //         title: _t('Please go with Advance Payment.'),
            //         body: _t('Save&Print option is for Quotation.'),
            //     });
            // }
            // else{
            self.click_wk_save_quotation('adv_pymt').then(function(){
                if(self.pos.config.quotation_print_type == 'pdf'){
                    self.pos.gui.show_popup('repair_order_saved', {
                        title: _t("Repair Order: "),
                        body: _t("Repair Order created successfully."),
                        repair_name: self.pos.get_order().repair_name,
                    });
                    console.log(self.pos.get_order(),'++++++++++++POS')
                    if(self.pos.get_order().repair_name){
                        console.log('+++++++++++++HEREPDTED')
                        setTimeout(function(){
                            self.chrome.do_action('pos_repair_order.report_quotation',{additional_context:{
                                active_ids:[self.pos.get_order().repair_id],
                            }});
                        },1000);
                    }
                    else{
                        console.log('===========updated')
                        setTimeout(function(){
                            self.chrome.do_action('pos_repair_order.report_quotation',{additional_context:{
                                active_ids:[self.created_quotation_id],
                            }});
                        },1000);
                    }
                }
                else{
                    self.gui.show_screen('receipt');
                }
            })
                
            // }
        },
    });
    gui.define_screen({ name: 'order_screen', widget: NewOrdersScreenWidget });

    screens.ProductScreenWidget.include({
        show: function () {
            var self = this;
            self._super();
            this.product_categories_widget.reset_category();
            this.numpad.state.reset();
            $('#load_quotation').on('click', function () {
                self.gui.show_popup('load_repair_order');
                $('#load_repair_id').focus();
                $('#load_quotation').bind('click');      
            });
            $('#save_order').on('click', function () {
                var current_order = self.pos.get_order();
                if (current_order.orderlines.length === 0) {
                    self.gui.show_popup('pr_error_notify', {
                        title: _t('ORDER'),
                        body: _t('You cannot process an empty order!!!')
                    });
                }
                else if(current_order.adv_pymt_data){
                    self.gui.show_popup('pr_error_notify', {
                        title: _t('ORDER'),
                        body: _t('Proceed with the Payment Option.')
                    });
                }
                else{
                    self.gui.show_screen('order_screen', {});
                }
            });
        },
    });

    var NotAvailableInPosPopupWidget = popup_widget.extend({
        template: 'NotAvailableInPosPopupWidget',
        events: {
            'click .button.cancel': 'click_cancel'
        },
        show: function (options) {
            var self = this;
            self._super(options);
            console.log(options, '==========options=====')
            this.options = options;
        }
    });
    gui.define_popup({
        name: 'not_available_in_pos',
        widget: NotAvailableInPosPopupWidget
    });

    var LoadRepairOrderPopupWidget = popup_widget.extend({
		template: 'LoadRepairOrderPopupWidget',
		events: {
			'click .button.cancel': 'click_cancel',
			'click .button.confirm': 'click_confirm',
			'click .selection-item': 'click_item',
			'click .input-button': 'click_numpad',
			'click .mode-button': 'click_numpad',
			'click #load_repair_order': 'click_wk_load_quotation',
			'keyup #load_repair_id': 'key_press_input',
			'focusout .input-button':'focusout_quote_input',
		},
		show:function(){
			var self = this;
			self._super();
			self.index = -1;
			self.previous_quote = '';
			self.parent = self.$('.suggest-holder');
		},
		key_press_input: function(e) {
            console.log(e.which, '+++++++=e.which++++++++')
			var self = this;
			var updown_press;
            var all_repair_ids = self.pos.db.all_repair_ids;
			self.$('.repair_details').hide();
			$('.suggest-holder ul').empty();
            var search = self.$('#load_repair_id').val();
            self.$('.suggest-holder').show();
            search = new RegExp(search.replace(/[^0-9a-z_]/i), 'i');
            for(var i in all_repair_ids){
                if(all_repair_ids[i].match(search)){
                $('.suggest-holder ul').append($("<li><span class='suggest-name'>" + all_repair_ids[i] + "</span></li>"));
                }
            }
            $('.suggest-holder ul').show();
			self.$('.suggest-holder li').on('click', function(){
				var repair_id = $(this).text();
				self.$("#load_repair_id").val(repair_id);
				self.focusout_quote_input();
			});
			if(e.which == 38){
				// Up arrow
				self.index--;
				var len = $('.suggest-holder li').length;
				if(self.index < 0)
					self.index = len-1;
				self.parent.scrollTop(36*self.index);
				updown_press = true;
			}else if(e.which == 40){
				// Down arrow
				self.index++;
				if(self.index > $('.suggest-holder li').length - 1)
					self.index = 0;
				self.parent.scrollTop(36*self.index);
			   	updown_press = true;
            }
            else if(e.which == 13 && self.$('#load_repair_id').val() != ''){  
                // When quotation box has input and Enter key preseed.
                self.click_wk_load_quotation()
            }
			if(updown_press){
				$('.suggest-holder li.active').removeClass('active');
				$('.suggest-holder li').eq(self.index).addClass('active');
				$('.suggest-holder li.active').select();
			}

			if(e.which == 27){
				// Esc key
				$('.suggest-holder ul').hide();
			}else if(e.which == 13 && self.index >=0 && $('.suggest-holder li').eq(self.index)[0]){
				var selcted_li_quote_id = $('.suggest-holder li').eq(self.index)[0].innerText;
				self.$("#load_repair_id").val(selcted_li_quote_id);
				self.$('.suggest-holder').hide();
				self.index = -1;
				self.focusout_quote_input();
			}

		},

		focusout_quote_input: function(){
			var self = this;
			$('.suggest-holder').hide();
			var quotation = self.$('#load_repair_id').val();
			if(quotation && self.pos.db.repair_by_id[quotation]){
				quotation = self.pos.db.repair_by_id[quotation]
				self.$('.repair_details').show();
				if(quotation.partner_id)
					self.$('.repair_customer_name').text(quotation.partner_id[1]);
				else
                    self.$('.repair_customer_name').text("-");
                if(quotation.date_order){
                    self.$('.repair_order_date').text(quotation.date_order.slice(0,11));
                }
				self.$('.repair_amount_total').text(self.format_currency(quotation.amount_total));
				self.$('.repair_repair_status').text(quotation.state.charAt(0).toUpperCase() + quotation.state.slice(1));

			}
		},

		click_wk_load_quotation: function() {
			var self = this;
            if (self.$('#load_repair_id').val() == '') {
				self.$('#repair_id_error').text("Invalid Quotation Id");
				self.$('#repair_id_error').css("padding-left", "31%");
				self.$('#repair_id_error').css("width", "69%");
				self.$('#repair_id_error').show();
			} else {
                var repair_id = $('#load_repair_id').val();
				rpc.query({
						model: 'repair.order',
						method: 'get_repair_details',
						args: [{"repair_id": repair_id}],
					})
					.then(function(repair_details) {
                        console.log(repair_details, '=======repair_details========')
                        var repair_dict = repair_details;
						if (repair_dict.status) {
							self.$('#repair_id_error').hide();
							self.chrome.widget.order_selector.neworder_click_handler();
                            var new_order = self.pos.get_order();
                            new_order.adv_pymt_done = repair_dict.adv_pymt_done
                            if(repair_dict.repair_state)
                                new_order.repair_state = repair_dict.repair_state
                            if(repair_dict.vehicle_id)
                                new_order.vehicle_id = repair_dict.vehicle_id
                            if(repair_dict.l_num)
                                new_order.v_l_num = repair_dict.l_num
                            if(repair_dict.brand)
                                new_order.v_brand = repair_dict.brand
                            if(repair_dict.year)
                                new_order.year = repair_dict.year
                            if(repair_dict.model)
                                new_order.v_model = repair_dict.model
                            if(repair_dict.fuel_type)
                                new_order.fuel_type = repair_dict.fuel_type
                            if(repair_dict.odometer_reading)
                                new_order.odometer_reading = repair_dict.odometer_reading
                            if(repair_dict.repair_type)
                                new_order.repair_type = repair_dict.repair_type
                            if(repair_dict.operation_type)
                                new_order.operation_type = repair_dict.operation_type
                            if(repair_dict.note)
                                new_order.note = repair_dict.note
                            if(repair_dict.delivery_date)
                                new_order.delivery_date = repair_dict.delivery_date
                            if(repair_dict.partner_id)
                                new_order.set_client(self.pos.db.get_partner_by_id(repair_dict.partner_id))
                            if(repair_dict.adv_pymt_data)
                                new_order.adv_pymt_data = repair_dict.adv_pymt_data
							var quote_pricelist = _.find(self.pos.pricelists,function(fp) {
								return fp.id == repair_dict.pricelist_id
                            });
							if (quote_pricelist)
								new_order.set_pricelist(quote_pricelist);
							repair_dict.line.forEach(function(line) {
								var orderline = new models.Orderline({}, {
									pos: self.pos,
									order: new_order,
									product: self.pos.db.get_product_by_id(line.product_id),
								});
								orderline.set_unit_price(line.price_unit);
								orderline.set_discount(line.discount);
								orderline.set_quantity(line.qty, true);
								new_order.add_orderline(orderline);
                            });
                            new_order.repair_id = repair_dict.repair_obj_id;
                            new_order.repair_name = repair_dict.repair_id;
                            self.pos.gui.show_popup('quotation_saved',{
                                'quotation_status':'Quotation Loaded'
                            });                            

						} else if(! repair_details.identifier){
							self.$('#repair_id_error').text(repair_dict.message);
							self.$('#repair_id_error').show();
                        }
                        else{
                            self.pos.gui.show_popup('not_available_in_pos',{
                                'repair_name': repair_details.repair_name,
                                'product_info': repair_details.message
                            });
                        }
                    });
			}
		},
	});
	gui.define_popup({
		name: 'load_repair_order',
		widget: LoadRepairOrderPopupWidget
    });

    var QuotationListScreenWidget = screens.ScreenWidget.extend({
		template: 'QuotationListScreenWidget',

		events:{
			'click .button.back':'wk_click_back',
            'click .button.wk_load_quotation.wk_highlight_line':'wk_click_customer_quotation',
            'click .cancel_repair_order': 'cancel_repair_order',
            'click .refund_repair_order': 'refund_repair_order',
        },
        wk_exchange_order: function(order){
			var self = this;
			var all_pos_orders = self.pos.get('orders').models || [];
			var return_order_exist = _.find(all_pos_orders, function(pos_order){
				if(pos_order.return_order_id && pos_order.return_order_id == order_id)
					return pos_order;
					
			});
			if(return_order_exist){
				self.gui.show_popup('my_message',{
					'title': _t('Exchange/Return Already In Progress'),
					'body': _t("Exchange/Return order is already in progress. Please proceed with Order Reference " + return_order_exist.sequence_number),
				});
			}
			else if(order){
				var order_list = self.pos.db.pos_all_orders;
				var order_line_data = self.pos.db.pos_all_order_lines;
				var message = '';
				var non_returnable_products = false;
				var original_orderlines = [];
				var allow_return = true;
				if(order.return_status == 'Fully-Returned'){
					message = 'No items are left to return for this order!!'
					allow_return = false;
				}
				if (allow_return) {
					order.lines.forEach(function(line_id){
						var line = self.pos.db.line_by_id[line_id];
						var product = self.pos.db.get_product_by_id(line.product_id[0]);
						if(product == null){
							non_returnable_products = true;
							message = 'Some product(s) of this order are unavailable in Point Of Sale, do you wish to exchange other products?'
						}
						else if (product.not_returnable) {
							non_returnable_products = true;
							message = 'This order contains some Non-Returnable products, do you wish to exchange other products?'
						}
						else if(line.qty - line.line_qty_returned > 0)
							original_orderlines.push(line);
					});
					if(original_orderlines.length == 0){
						self.gui.show_popup('my_message',{
							'title': _t('Cannot exchange This Order!!!'),
							'body': _t("There are no exchangable products left for this order. Maybe the products are Non-Returnable or unavailable in Point Of Sale!!"),
						});
					}
					else if(non_returnable_products){
						self.gui.show_popup('confirm',{
							'title': _t('Warning !!!'),
							'body': _t(message),
							confirm: function(){
								self.gui.show_popup('exchange_products_popup',{
									'orderlines': original_orderlines,
									'order':order,
									'is_partial_return':true,
								});
							},
						});
					}
					else{
						self.gui.show_popup('exchange_products_popup',{
							'orderlines': original_orderlines,
							'order':order,
							'is_partial_return':false,
						});
					}
				}
				else
				{
					self.gui.show_popup('my_message',{
						'title': _t('Warning!!!'),
						'body': _t(message),
					});
				}
			}
		},
		wk_click_customer_quotation: function(event) {
			var self = this;
            var repair_id = $('.quotation-line.wk_highlight_line').data('id');
			if (repair_id) {
				rpc.query({
					model: 'repair.order',
					method: 'get_repair_details',
                    args: [{"repair_id": repair_id}],
				})
				.catch(function(unused, event) {
					self.gui.show_popup('pr_error_notify', {
						title: _t('Failed To Fetch Quotation Details.'),
						body: _t('Please make sure you are connected to the network.'),
					});
				})
				.then(function(quotation_details) {
					var quotation_dict = quotation_details;
					if (quotation_dict.status) {
						self.$('#quotation_id_error').hide();
						self.chrome.widget.order_selector.neworder_click_handler();
                        var new_order = self.pos.get_order();
                        new_order.adv_pymt_done = quotation_dict.adv_pymt_done
                        if(quotation_dict.repair_state)
                            new_order.repair_state = quotation_dict.repair_state
                        if(quotation_dict.vehicle_id)
                            new_order.vehicle_id = quotation_dict.vehicle_id
                        if(quotation_dict.l_num)
                            new_order.v_l_num = quotation_dict.l_num
                        if(quotation_dict.brand)
                            new_order.v_brand = quotation_dict.brand
                        if(quotation_dict.year)
                            new_order.year = quotation_dict.year
                        if(quotation_dict.model)
                            new_order.v_model = quotation_dict.model
                        if(quotation_dict.fuel_type)
                            new_order.fuel_type = quotation_dict.fuel_type
                        if(quotation_dict.odometer_reading)
                            new_order.odometer_reading = quotation_dict.odometer_reading
                        if(quotation_dict.repair_type)
                            new_order.repair_type = quotation_dict.repair_type
                        if(quotation_dict.operation_type)
                            new_order.operation_type = quotation_dict.operation_type
                        if(quotation_dict.note)
                            new_order.note = quotation_dict.note
                        if(quotation_dict.delivery_date)
                            new_order.delivery_date = quotation_dict.delivery_date
                        if(quotation_dict.pos_order_id)
                            new_order.pos_order_id = quotation_dict.pos_order_id
                        if(quotation_dict.adv_pymt_data)
                            new_order.adv_pymt_data = quotation_dict.adv_pymt_data
						self.pos.gui.show_popup('quotation_saved',{
							'quotation_status':'Quotation Loaded'
                        });
                        if(quotation_dict.partner_id)
                            new_order.set_client(self.pos.db.get_partner_by_id(quotation_dict.partner_id));
						quotation_dict.line.forEach(function(line) {
							var orderline = new models.Orderline({}, {
								pos: self.pos,
								order: new_order,
								product: self.pos.db.get_product_by_id(line.product_id),
							});
							orderline.set_unit_price(line.price_unit);
							orderline.set_discount(line.discount);
							orderline.set_quantity(line.qty, true);
							new_order.add_orderline(orderline);
						});
                        new_order.repair_id = quotation_dict.repair_obj_id;
                        new_order.repair_name = quotation_dict.repair_id;
                    }
                    else if(! quotation_dict.identifier){
                        self.$('#repair_id_error').text(quotation_dict.message);
                        self.$('#repair_id_error').show();
                    }
                    else{
                        self.pos.gui.show_popup('not_available_in_pos',{
                            'repair_name': quotation_dict.repair_name,
                            'product_info': quotation_dict.message
                        });
                    }
				});
			}
		},
		wk_click_back: function(){
			var self = this;
			self.gui.show_screen(self.pos.get_order().clientlist_previous_screen);
		},
		get_quotations: function(){
			var self = this;
			if(self.gui)
				return self.gui.get_current_screen_param('quotations_for_customer');
			else
				return undefined;
        },
        cancel_repair_order: function(event){
            var repair_name = event.target.id;
            self.pos.gui.show_popup('pr_cancel_confirm',{
                'repair_name' : repair_name,
                'screen_name': 'wk_quotations'
            });
        },
        refund_repair_order: function(event){
            var self = this;
            var pos_id = event.target.id;
            var order = self.pos.db.order_by_id[pos_id];
            console.log(order, '+++++++++++++++++++order')
            self.display_pos_order_details(order);
        },
        display_pos_order_details: function(order) {
            console.log(order, '=============order')
            var self = this;
            var contents = this.$('.quotation-details-content');
            var orderlines = [];
            var statements = [];
            var payment_methods_used = [];
                order.lines.forEach(function(line_id) {
                    orderlines.push(self.pos.db.line_by_id[line_id]);
                });
                if(order && order.payment_ids)
                    order.payment_ids.forEach(function(payment_id) {
                        var payment = self.pos.db.payment_by_id[payment_id];
                        statements.push(payment);
                        payment_methods_used.push(payment.journal_id[0]);
                    });
                contents.empty();
                contents.append($(QWeb.render('OrderDetails', { widget: this, order: order, orderlines: orderlines, statements: statements })));

                this.details_visible = true;
                self.$("#close_order_details").on("click", function() {
                    self.selected_tr_element.removeClass('highlight');
                    self.selected_tr_element.addClass('lowlight');
                    self.details_visible = false;
                    contents.empty();
                });
                self.$("#wk_refund").on("click", function() {
                    var order_list = self.pos.db.pos_all_orders;
                    var order_line_data = self.pos.db.pos_all_order_lines;
                    var order_id = this.id;
                    var message = '';
                    var non_returnable_products = false;
                    var original_orderlines = [];
                    var allow_return = true;
                    if (order.return_status == 'Fully-Returned') {
                        message = 'No items are left to return for this order!!'
                        allow_return = false;
                    }
                    var all_pos_orders = self.pos.get('orders').models || [];
                    var return_order_exist = _.find(all_pos_orders, function(pos_order) {
                        if (pos_order.return_order_id && pos_order.return_order_id == order.id)
                            return pos_order;

                    });
                    if (return_order_exist) {
                        self.gui.show_popup('my_message', {
                            'title': _t('Refund Already In Progress'),
                            'body': _t("Refund order is already in progress. Please proceed with Order Reference " + return_order_exist.sequence_number),
                        });
                    } else if (allow_return) {
                        order.lines.forEach(function(line_id) {
                            var line = self.pos.db.line_by_id[line_id];
                            var product = self.pos.db.get_product_by_id(line.product_id[0]);
                            if (product == null) {
                                non_returnable_products = true;
                                message = 'Some product(s) of this order are unavailable in Point Of Sale, do you wish to return other products?'
                            } else if (product.not_returnable) {
                                non_returnable_products = true;
                                message = 'This order contains some Non-Returnable products, do you wish to return other products?'
                            } else if (line.qty - line.line_qty_returned > 0)
                                original_orderlines.push(line);
                        });
                        if (original_orderlines.length == 0) {
                            self.gui.show_popup('my_message', {
                                'title': _t('Cannot Return This Order!!!'),
                                'body': _t("There are no returnable products left for this order. Maybe the products are Non-Returnable or unavailable in Point Of Sale!!"),
                            });
                        } else if (non_returnable_products) {
                            self.gui.show_popup('confirm', {
                                'title': _t('Warning !!!'),
                                'body': _t(message),
                                confirm: function() {
                                    self.gui.show_popup('return_products_popup', {
                                        'orderlines': original_orderlines,
                                        'order': order,
                                        'is_partial_return': true,
                                    });
                                },
                            });
                        } else {
                            self.gui.show_popup('return_products_popup', {
                                'orderlines': original_orderlines,
                                'order': order,
                                'is_partial_return': false,
                            });
                        }
                    } else {
                        self.gui.show_popup('my_message', {
                            'title': _t('Warning!!!'),
                            'body': _t(message),
                        });
                    }
                });
                self.$("#wk_exchange").on("click", function() {
                    self.wk_exchange_order(order);
                });
                
        },
		display_quotations: function(intput_txt) {
			var self = this;
            var all_quotations_for_customer = this.get_quotations();
			var quotations_to_render = all_quotations_for_customer;

			if (intput_txt != undefined && intput_txt != '') {
				var new_quotation_data = [];
				var search_text = intput_txt.toLowerCase()

				all_quotations_for_customer.forEach(function(quotation){
					if (((quotation.name.toLowerCase()).indexOf(search_text) != -1) || ((quotation.amount_total.toString().toLowerCase()).indexOf(search_text) != -1) ||((quotation.state.toLowerCase()).indexOf(search_text) != -1)) {
						new_quotation_data = new_quotation_data.concat(quotation);
					}
				});
				quotations_to_render = new_quotation_data
			}

			var contents = this.$el[0].querySelector('.quotation-list-contents');
			contents.innerHTML = "";
			quotations_to_render.forEach(function(quotation){
				quotation.partner_name = quotation.partner_id ?quotation.partner_id[1]:'-';
                quotation.state =  quotation.state.charAt(0).toUpperCase() + quotation.state.slice(1);
                if(quotation.repair_type === 'service')
                    quotation.repair_type = 'Service';
                else if(quotation.repair_type === 'quote')
                    quotation.repair_type = 'Quotation';
                console.log(quotation, '======')
				var quotationline_html = QWeb.render('WkQuotationLine', {
					widget: self,
					quotation: quotation
                });
				var quotationline = document.createElement('tbody');
				quotationline.innerHTML = quotationline_html;
                quotationline = quotationline.childNodes[1];
				contents.appendChild(quotationline);
			});
		},
		show: function() {
			var self = this;
			this._super();
			this.renderElement();
            this.details_visible = false;
            this.selected_tr_element = null;
			this.display_quotations(undefined);
			this.$('.quotation_search').keyup(function() {
				self.display_quotations(this.value);
			});
			this.$('.quotation-list-contents').delegate('.quotation-line', 'click', function(event) {
				self.line_select(event, $(this),$(this).data('id'));
			});
			var contents = this.$('.quotation-details-contents');
			contents.empty();
		},
		line_select: function(event, $line, id) {
			var self = this;
			if($line.hasClass('wk_highlight_line')) {
				self.$('.wk_quotation_table .wk_highlight_line').removeClass('wk_highlight_line');
				$('.button.wk_load_quotation').css("background-color","")
				$('.button.wk_load_quotation').removeClass('wk_highlight_line');
				$(".quotation-line").css("background-color","");
			}
			else{
				self.$('.wk_quotation_table .wk_highlight_line').removeClass('wk_highlight_line');
				$('.button.wk_load_quotation').css("background-color","rgb(110,200,155) !important");
				$('.button.wk_load_quotation').addClass('wk_highlight_line');
				$(".quotation-line").css("background-color","");
                $line.addClass('wk_highlight_line');
                self.selected_tr_element = $line;
				$line.css("background-color","rgb(110,200,155) !important");
			}
		},
	});
	gui.define_screen({name: 'wk_quotations',widget:QuotationListScreenWidget});


    screens.ClientListScreenWidget.include({
		events : _.extend({}, SuperClientListScreenWidget.prototype.events, {
			'click .view_quotations': 'click_customer_quotation',
		}),

		click_customer_quotation: function(event){
            var self = this;
            console.log(this.pos.get_order().get_screen_data('previous-screen'), '++++++++++++++++++++++')
			self.pos.get_order().clientlist_previous_screen = this.pos.get_order().get_screen_data('previous-screen');
            var partner_id = parseInt($(event.target).data('id'))
            var quotations_for_customer = self.filter_quotation_by_customer(partner_id);
			self.gui.show_screen('wk_quotations',{
				'partner_id': partner_id, 'quotations_for_customer': quotations_for_customer
			});
		},
		filter_quotation_by_customer: function(partner_id){
			var self = this;
            var quotations_for_customer = [];
			self.pos.db.r_orders.forEach(function(quotation){
				if(quotation.partner_id && quotation.partner_id[0] == partner_id){
					quotations_for_customer.push(quotation);
				}
			});
			return quotations_for_customer;
		}
    });

    var CancelConfirmationPopup = popup_widget.extend({
        template: 'CancelConfirmationPopup',
        events: {
            'click .button.cancel': 'click_cancel',
            'click .button.ok_cancel_order': 'cancel_order'
        },
        show: function (options) {
            var self = this;
            self._super(options);
            this.options = options;
        },
        cancel_order: function(){
            var self = this;
            var repair_name = self.$('.repair_name_popup').text();
            var screen_name = self.$('.screen_name_popup').text();
            rpc.query({
                model: 'repair.order',
                method: 'cancel_repair_order',
                args: [{"repair_id": repair_name}],
            })
            .catch(function(unused, event) {
                self.gui.show_popup('pr_error_notify', {
                    title: _t('Failed To Cancel Order.'),
                    body: _t('Please make sure you are connected to the network.'),
                });
            })
            .then(function(result){
                console.log(result, '=========result')
                // if("name" in result){
                //     console.log(self.pos.db.repair_by_id,'==========')
                //     console.log(result['name'], '========')
                //     var cancel_order = self.pos.db.repair_by_id[result['name']];
                //     console.log(cancel_order, '===========cancel_order')
                //     cancel_order.state = 'cancel';
                // }
                self.gui.show_screen('products');
                self.gui.show_screen(screen_name);
            });
        }
    });
    gui.define_popup({
        name: 'pr_cancel_confirm',
        widget: CancelConfirmationPopup
    });

    screens.ProductScreenWidget.include({
        show: function(){
            var self = this;
            this._super();
            this.product_categories_widget.reset_category();
            this.numpad.state.reset();
            $('#all_quotations').on('click',function(){
                self.pos.get_order().clientlist_previous_screen = 'products';
                console.log(self.pos.db.r_orders, '==========self.pos.db.r_orders');
                var data = self.pos.db.r_orders;
                data = data.sort(function(a,b){
                    return b.id - a.id;
                });
                self.gui.show_screen('wk_quotations',{
                    'quotations_for_customer': data
                });
            });
        },
    });

    return NewOrdersScreenWidget;
});