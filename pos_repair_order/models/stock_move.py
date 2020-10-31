# -*- coding: utf-8 -*-

try:
   import newrelic
   import newrelic.agent
except:
   newrelic = None
   
# import time
# import json
from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import UserError

class StockMove(models.Model):
    _inherit = 'stock.move'

    def reverse_stock_move(self, repair_obj):
        """
        This function reverse stock move of repiar.line of particular repair.order.
        """
        newrelic.agent.set_transaction_name("reverse_stock_move_pro", "/StockMove", priority=None)
        for item in repair_obj.operations:
            stock_move = item.move_id
            reverse_data = {
                'name' : "Reversed "+stock_move.name,
                'location_id' : stock_move.location_dest_id.id,
                'location_dest_id' : stock_move.location_id.id,
                'date': datetime.now()
            }
            stock_move_reversed = stock_move.copy(reverse_data)
            stock_move_reversed._action_assign()
            stock_move_reversed._action_done()
            item.rev_move_id = stock_move_reversed
        return {
                'obj_n':'stock.move',
            }
        