# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
import logging

class Partner(models.Model):
    _inherit = "res.partner"

    username_fel = fields.Char('Usuario del API de Mega Print', copy=False)
    password_fel = fields.Char('Contraseña del API de Mega Print', copy=False)
    codigo_establecimiento = fields.Char('Código Establecimiento FEL', copy=False, help = "Código que identifica al establecimiento.")
    frases_fel = fields.Text('Frases', copy=False, help="Las frases dependen del RTU de la empresa, para agregarlas debe separar por una coma (TipoFrase,CodigoEscenario) en caso de tener más de una frase precione Eneter e ingrese la nueva frase.")
