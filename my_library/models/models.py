# -*- coding: utf-8 -*-

from odoo import models, fields, api


class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Ma librarie de livre à lire'

    name = fields.Char('Titre', required=True)
    date_release = fields.Date('Date de Publication')
    author_ids = fields.Many2many('res.partner', string='Auteurs')
    description = fields.Text()