# -*- coding: utf-8 -*-.
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from odoo.tools.safe_eval import safe_eval
import ast

logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.multi    
    def chunks(self, shop_dt):
        n = 5
        """Yield successive n-sized chunks from shop_dt."""
        for i in range(0, len(shop_dt), n):
            logger.info(shop_dt[i:i + n])
            self.env['res.partner'].create_odoo_shop_in_LN(shop_dt[i:i + n])
        return True
  
    @api.multi
    def syncOdooShopinLoginext(self):
        ''' Sync Odoo Shop in Loginext which does not exist in Loginext'''
        shops = self.env['res.partner'].sudo().search([('ln_customer_reference_id','=',False),('type','=','shop')])
        self.chunks(shops)
        data = tuple(shops.ids)   
        if not data:
            raise ValidationError("All shops have loginext customer and reference Id's")
        else:
            query = "SELECT id,ln_customer_reference_id,ln_address_reference_id from res_partner where id in %s;"%(str(data).replace(',)',')'))
            self._cr.execute(query)
            res = self._cr.fetchall()
            error_dt = [ii[0] for ii in res if not ii[1] or not ii[2]]
            if error_dt:
                self.env['koko.loginext.conf'].sendApiErrorMail(error_dt)