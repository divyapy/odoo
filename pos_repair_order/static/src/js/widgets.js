odoo.define('pos_repair_order.widgets', function (require) {
    "use strict"
    var rpc = require('web.rpc');
    var models = require("point_of_sale.models");

    var _super_posmodel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({

        delete_current_order: function () {
            var self = this;
            var order = this.get_order();
            var repair_name = order.repair_name;
            _super_posmodel.delete_current_order.apply(this, arguments);
            // self.delete_repair_order(repair_name);
        },

        // delete_repair_order: function(repair_name){
        //     rpc.query({
        //         model: 'repair.order',
        //         method: 'unlink_order',
        //         args: [{"repair_name": repair_name}],
        //     })
        //     .then(function(repair_details) {
        //         console.log("Associated Repair Order deleted successfully.");
        //         self.pos.db.all_repair_ids.shift(repair_name);
        //     })
        //     .catch(function(error){
        //         console.log("Their is an error while deleting assciated Repair Order.")
        //     })
        // }
    });

});