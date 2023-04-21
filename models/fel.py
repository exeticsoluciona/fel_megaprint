# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round
from odoo.tools import float_is_zero, float_compare

from datetime import datetime
import base64
from lxml import etree
import requests
import re
import operator
import json
import logging
import html
import uuid
import random
from odoo.addons.l10n_gt_extra.a_letras import num_a_letras


class FelMegaprint(models.Model):
    _inherit = "account.move"

    factura_org_id = fields.Many2one('account.move', string="Factura original FEL")
    firma_fel = fields.Char('Firma Fel', copy=False,
                            readonly=True, states={'draft': [('readonly', False)]})
    serie_fel = fields.Char('Serie Fel', copy=False,
                            readonly=True, states={'draft': [('readonly', False)]})
    numero_fel = fields.Char('Numero Fel', copy=False,
                             readonly=True, states={'draft': [('readonly', False)]})
    pdf_fel = fields.Binary('PDF Fel', copy=False,
                            help="Haciendo click en este enlace podra descargar el documento FEL generado",
                            readonly=True, states={'draft': [('readonly', False)]})
    name_pdf_fel = fields.Char('Nombre del Archivo PDF', default='fel.pdf', size=32)
    pdf_uri = fields.Char('PDF Fels', copy=False,
                          help="Valida PDF.",
                          readonly=True, states={'draft': [('readonly', True)]})
    uuid_contigencia = fields.Char('Numero de acceso', copy=False,
                                   help="Numero de acceso para facturar en contingencia.",
                                   readonly=True, states={'draft': [('readonly', True)]})
    motivo_nota = fields.Char('Motivo de Nota (Crédito o Débito)',
                              help="Si emite una nota de credito, nota de débito o nota de abono es de caracter obligatorio que escriba el motivo para la creación de este documento",
                              readonly=False, states={'draft': [('readonly', False)]})
    motivo_anula_fel = fields.Char('Motivo de anulación',
                                   default="",
                                   help="Si desea anular un documento FEL previamente validado, deberá cambiar la factura a estado borrador, luego deberá escribir en este campo el motivo de la anulación del documento para por último hacer clic en el botón cancelar .",
                                   readonly=False, states={'draft': [('readonly', False)]})
    tipo_doc_fel = fields.Char('Tipo documento', copy=False,
                               help="Este campo indica el tipo de documento generado.",
                               readonly=True, states={'draft': [('readonly', False)]})
    estado_doc_fel = fields.Char('Estado del documento', copy=False,
                                 help="Este campo indicara el estado del documento electronico, Activa significa que el documento esta activo, Inactiva significa que el documento ha sido anulado.",
                                 readonly=True, states={'draft': [('readonly', False)]})
    contingencia_fel = fields.Char('Emision en contigencia.', copy=False)
    consignatario_fel = fields.Many2one('res.partner', string="Consignatario o Destinatario FEL")
    comprador_fel = fields.Many2one('res.partner', string="Comprador FEL")
    exportador_fel = fields.Many2one('res.partner', string="Exportador FEL")
    incoterm_fel = fields.Char(string="Incoterm FEL")
    codigo_escenario = fields.Char(
        string='Codigo de escenario FEL',
        help="Si desea agregar una frase el documento agregara este valor para enviarlo al certificador.",
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    # tipo_frase = fields.Char(
    #     string='Tipo de frase FEL',
    #     help="Si desea agregar una frase el documento agregara este valor para enviarlo al certificador.",
    #     readonly=True,
    #     states={'draft': [('readonly', False)]},
    #     attrs={'required': [('codigo_escenario', '!=', False)]}
    # )
    tipo_frase = fields.Char(
        string='Tipo de frase FEL',
        help="Si desea agregar una frase el documento agregara este valor para enviarlo al certificador.",
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    def amount_to_text1(self):

        self.ensure_one()
        factura = self

        numLetras = num_a_letras(factura.amount_total)
        return numLetras

    def dteAnulaDocumento(self):

        self.ensure_one()
        factura = self

        NSMAP = {
            "ds": "http://www.w3.org/2000/09/xmldsig#",
            "dte": "http://www.sat.gob.gt/dte/fel/0.1.0",
        }

        DTE_NS = "{http://www.sat.gob.gt/dte/fel/0.1.0}"
        DS_NS = "{http://www.w3.org/2000/09/xmldsig#}"

        tipo_documento_fel = factura.journal_id.tipo_documento_fel
        if tipo_documento_fel in ['FACT', 'FACM'] and factura.move_type == 'out_refund':
            tipo_documento_fel = 'NCRE'

        nit_receptor = ''
        if factura.partner_id.vat:
            nit_receptor = factura.partner_id.vat.replace('-', '')
        if tipo_documento_fel == "FESP" and factura.partner_id.cui:
            nit_receptor = factura.partner_id.cui
        if factura.partner_id.cui_por_nit and factura.partner_id.cui:
            nit_receptor = factura.partner_id.cui

        motivo_anulacion = 'Error'
        if factura.motivo_anula_fel:
            motivo_anulacion = factura.motivo_anula_fel

        fecha = fields.Date.from_string(factura.invoice_date).strftime('%Y-%m-%d')
        # hora = fields.Datetime.context_timestamp(factura, timestamp=datetime.now()).strftime('%H:%M:%S')
        hora = "00:00:00-06:00"
        fecha_hora = fecha + 'T' + hora

        # fecha_hoy = fields.Date.context_today(factura, timestamp=datetime.now())
        fecha_hora_hoy = fields.Datetime.context_timestamp(factura, timestamp=datetime.now()).strftime(
            '%Y-%m-%dT%H:%M:%S-06:00')

        GTAnulacionDocumento = etree.Element(DTE_NS + "GTAnulacionDocumento", {}, Version="0.1", nsmap=NSMAP)
        SAT = etree.SubElement(GTAnulacionDocumento, DTE_NS + "SAT")
        AnulacionDTE = etree.SubElement(SAT, DTE_NS + "AnulacionDTE", ID="DatosCertificados")
        DatosGenerales = etree.SubElement(AnulacionDTE, DTE_NS + "DatosGenerales", ID="DatosAnulacion",
                                          NumeroDocumentoAAnular=factura.firma_fel,
                                          NITEmisor=factura.journal_id.direccion_fel.vat.replace("-", ""),
                                          IDReceptor=nit_receptor, FechaEmisionDocumentoAnular=fecha_hora,
                                          FechaHoraAnulacion=fecha_hora_hoy, MotivoAnulacion=motivo_anulacion)

        xmls = etree.tostring(GTAnulacionDocumento, encoding="UTF-8").decode("utf-8")

        return xmls

    def dteDocumento(self):

        detalles = []
        subtotal = 0

        self.ensure_one()
        factura = self

        attr_qname = etree.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation")

        NSMAP = {
            "ds": "http://www.w3.org/2000/09/xmldsig#",
            "dte": "http://www.sat.gob.gt/dte/fel/0.2.0",
        }

        NSMAP_REF = {
            "cno": "http://www.sat.gob.gt/face2/ComplementoReferenciaNota/0.1.0",
        }

        NSMAP_ABONO = {
            "cfc": "http://www.sat.gob.gt/dte/fel/CompCambiaria/0.1.0",
        }

        NSMAP_EXP = {
            "cex": "http://www.sat.gob.gt/face2/ComplementoExportaciones/0.1.0",
        }

        NSMAP_FE = {
            "cfe": "http://www.sat.gob.gt/face2/ComplementoFacturaEspecial/0.1.0",
        }

        DTE_NS = "{http://www.sat.gob.gt/dte/fel/0.2.0}"
        DS_NS = "{http://www.w3.org/2000/09/xmldsig#}"
        CNO_NS = "{http://www.sat.gob.gt/face2/ComplementoReferenciaNota/0.1.0}"
        CFE_NS = "{http://www.sat.gob.gt/face2/ComplementoFacturaEspecial/0.1.0}"
        CEX_NS = "{http://www.sat.gob.gt/face2/ComplementoExportaciones/0.1.0}"
        CFC_NS = "{http://www.sat.gob.gt/dte/fel/CompCambiaria/0.1.0}"

        GTDocumento = etree.Element(DTE_NS + "GTDocumento", {}, Version="0.1", nsmap=NSMAP)
        SAT = etree.SubElement(GTDocumento, DTE_NS + "SAT", ClaseDocumento="dte")
        DTE = etree.SubElement(SAT, DTE_NS + "DTE", ID="DatosCertificados")
        DatosEmision = etree.SubElement(DTE, DTE_NS + "DatosEmision", ID="DatosEmision")

        tipo_documento_fel = factura.journal_id.tipo_documento_fel
        print("tipo_documento_fel>>>>>>>>>>>>>>>>",tipo_documento_fel)
        if tipo_documento_fel in ['FACT', 'FACM'] and factura.move_type == 'out_refund':
            tipo_documento_fel = 'NCRE'

        moneda = "GTQ"
        if factura.currency_id.id != factura.company_id.currency_id.id:
            moneda = "USD"

        fecha = fields.Date.to_date(factura.invoice_date)
        hora = '00:00:00'
        fecha_hora = str(fecha) + 'T' + hora + '-06:00'
        DatosGenerales = etree.SubElement(DatosEmision, DTE_NS + "DatosGenerales", CodigoMoneda=moneda,
                                          FechaHoraEmision=fecha_hora, Tipo=tipo_documento_fel)

        if factura.tipo_gasto == 'importacion':
            DatosGenerales.attrib['Exp'] = "SI"

        print("DatosEmision--------",DatosEmision)
        print("DTE_NS--------",DTE_NS)
        print("factura.journal_id.direccion_fel.codigo_establecimiento--------",factura.journal_id.direccion_fel.codigo_establecimiento)
        print("factura.journal_id.direccion_fel.email--------",factura.journal_id.direccion_fel.email)
        print("factura.journal_id.direccion_fel.vat--------",factura.journal_id.direccion_fel.vat)
        print("factura.journal_id.direccion_fel.name--------",factura.journal_id.direccion_fel.name)
        print("factura.journal_id.direccion_fel.name--------",factura.journal_id.direccion_fel.name)
        Emisor = etree.SubElement(DatosEmision, DTE_NS + "Emisor", AfiliacionIVA="GEN",
                                  CodigoEstablecimiento=factura.journal_id.direccion_fel.codigo_establecimiento,
                                  CorreoEmisor=factura.journal_id.direccion_fel.email or '',
                                  NITEmisor=factura.journal_id.direccion_fel.vat.replace('-', ''),
                                  NombreComercial=factura.journal_id.direccion_fel.name,
                                  NombreEmisor=factura.journal_id.direccion_fel.name)
        DireccionEmisor = etree.SubElement(Emisor, DTE_NS + "DireccionEmisor")
        Direccion = etree.SubElement(DireccionEmisor, DTE_NS + "Direccion")
        Direccion.text = factura.journal_id.direccion_fel.street or 'Ciudad'
        CodigoPostal = etree.SubElement(DireccionEmisor, DTE_NS + "CodigoPostal")
        CodigoPostal.text = factura.journal_id.direccion_fel.zip or '01001'
        Municipio = etree.SubElement(DireccionEmisor, DTE_NS + "Municipio")
        Municipio.text = factura.journal_id.direccion_fel.city or 'Guatemala'
        Departamento = etree.SubElement(DireccionEmisor, DTE_NS + "Departamento")
        Departamento.text = factura.journal_id.direccion_fel.state_id.name if factura.journal_id.direccion_fel.state_id else 'Guatemala'
        Pais = etree.SubElement(DireccionEmisor, DTE_NS + "Pais")
        Pais.text = factura.journal_id.direccion_fel.country_id.code or 'GT'

        nit_receptor = ''
        if factura.partner_id.vat:
            nit_receptor = factura.partner_id.vat.replace('-', '')
        if tipo_documento_fel == "FESP" and factura.partner_id.cui:
            nit_receptor = factura.partner_id.cui
        if factura.partner_id.cui_por_nit  and factura.partner_id.cui:
            nit_receptor = factura.partner_id.cui

        Receptor = etree.SubElement(DatosEmision, DTE_NS+"Receptor", IDReceptor=nit_receptor, NombreReceptor=factura.partner_id.name)

        if factura.partner_id.nombre_facturacion_fel:
            Receptor.attrib['NombreReceptor'] = factura.partner_id.nombre_facturacion_fel
        if factura.partner_id.email:
            Receptor.attrib['CorreoReceptor'] = factura.partner_id.email

        if tipo_documento_fel == "FESP" and factura.partner_id.cui:
            Receptor.attrib['TipoEspecial'] = "CUI"
        if factura.partner_id.cui_por_nit and factura.partner_id.cui:
            Receptor.attrib['TipoEspecial'] = "CUI"
        if factura.partner_id.country_id and factura.partner_id.country_id.code != 'GT':
            Receptor.attrib['TipoEspecial'] = "EXT"

        DireccionReceptor = etree.SubElement(Receptor, DTE_NS + "DireccionReceptor")
        Direccion = etree.SubElement(DireccionReceptor, DTE_NS + "Direccion")
        Direccion.text = (factura.partner_id.street or 'Ciudad') + ' ' + (factura.partner_id.street2 or ' ')
        CodigoPostal = etree.SubElement(DireccionReceptor, DTE_NS + "CodigoPostal")
        CodigoPostal.text = factura.partner_id.zip or '01001'
        Municipio = etree.SubElement(DireccionReceptor, DTE_NS + "Municipio")
        Municipio.text = factura.partner_id.city or 'Ciudad'
        Departamento = etree.SubElement(DireccionReceptor, DTE_NS + "Departamento")
        Departamento.text = factura.partner_id.state_id.name if factura.partner_id.state_id else 'Guatemala'
        Pais = etree.SubElement(DireccionReceptor, DTE_NS + "Pais")
        Pais.text = factura.partner_id.country_id.code or 'GT'

        if datetime.now().isoformat() < '2022-11-01':
            if tipo_documento_fel not in ['NABN', 'FESP', 'NDEB', 'NCRE'] or (
                    factura.tipo_frase and factura.codigo_escenario) or factura.tipo_gasto == 'importacion':
                ElementoFrases = etree.Element(DTE_NS + "Frases")
                if factura.journal_id.direccion_fel.frases_fel and tipo_documento_fel not in ['NDEB', 'NCRE']:
                    frasesList = str(factura.journal_id.direccion_fel.frases_fel).splitlines()
                    for fraseItem in frasesList:
                        item = str(fraseItem).split(",")
                        ElementoFrase = etree.SubElement(ElementoFrases, DTE_NS + "Frase", TipoFrase=item[0],
                                                         CodigoEscenario=item[1])
                if factura.tipo_frase and factura.codigo_escenario:
                    Frase1 = etree.SubElement(ElementoFrases, DTE_NS + "Frase",
                                              CodigoEscenario=factura.codigo_escenario, TipoFrase=factura.tipo_frase)
                if factura.tipo_gasto == 'importacion':
                    Frase2 = etree.SubElement(ElementoFrases, DTE_NS + "Frase", CodigoEscenario="1", TipoFrase="4")
                DatosEmision.append(ElementoFrases)

        if datetime.now().isoformat() >= '2022-11-01':
            if tipo_documento_fel not in ['NABN', 'FESP'] or (
                    factura.tipo_frase and factura.codigo_escenario) or factura.tipo_gasto == 'importacion':
                ElementoFrases = etree.Element(DTE_NS + "Frases")
                if factura.journal_id.direccion_fel.frases_fel:
                    frasesList = str(factura.journal_id.direccion_fel.frases_fel).splitlines()
                    for fraseItem in frasesList:
                        item = str(fraseItem).split(",")
                        ElementoFrase = etree.SubElement(ElementoFrases, DTE_NS + "Frase", TipoFrase=item[0],
                                                         CodigoEscenario=item[1])
                if factura.tipo_frase and factura.codigo_escenario:
                    Frase1 = etree.SubElement(ElementoFrases, DTE_NS + "Frase",
                                              CodigoEscenario=factura.codigo_escenario, TipoFrase=factura.tipo_frase)
                if factura.tipo_gasto == 'importacion':
                    Frase2 = etree.SubElement(ElementoFrases, DTE_NS + "Frase", CodigoEscenario="1", TipoFrase="4")
                DatosEmision.append(ElementoFrases)

        Items = etree.SubElement(DatosEmision, DTE_NS + "Items")

        linea_num = 0
        gran_subtotal = 0
        gran_total = 0
        gran_total_impuestos = 0
        cantidad_impuestos = 0
        for linea in factura.invoice_line_ids:

            if linea.quantity * linea.price_unit == 0:
                continue

            linea_num += 1

            tipo_producto = "B"

            if linea.product_id.type == 'service':
                tipo_producto = "S"

            precio_unitario = linea.price_unit * (100 - linea.discount) / 100
            precio_sin_descuento = linea.price_unit
            descuento = precio_sin_descuento * linea.quantity - precio_unitario * linea.quantity
            precio_unitario_base = linea.price_subtotal / linea.quantity
            total_linea = precio_unitario * linea.quantity
            total_linea_base = precio_unitario_base * linea.quantity
            total_impuestos = total_linea - total_linea_base
            cantidad_impuestos += len(linea.tax_ids)

            Item = etree.SubElement(Items, DTE_NS + "Item", BienOServicio=tipo_producto, NumeroLinea=str(linea_num))
            Cantidad = etree.SubElement(Item, DTE_NS + "Cantidad")
            Cantidad.text = str(linea.quantity)
            UnidadMedida = etree.SubElement(Item, DTE_NS + "UnidadMedida")
            UnidadMedida.text = "UNI"
            Descripcion = etree.SubElement(Item, DTE_NS + "Descripcion")
            Descripcion.text = linea.name
            PrecioUnitario = etree.SubElement(Item, DTE_NS + "PrecioUnitario")
            PrecioUnitario.text = '{:.6f}'.format(precio_sin_descuento)
            Precio = etree.SubElement(Item, DTE_NS + "Precio")
            Precio.text = '{:.6f}'.format(precio_sin_descuento * linea.quantity)
            Descuento = etree.SubElement(Item, DTE_NS + "Descuento")
            Descuento.text = '{:.6f}'.format(descuento)

            # if len(linea.tax_ids) > 0:
            if tipo_documento_fel not in ['NABN']:
                Impuestos = etree.SubElement(Item, DTE_NS + "Impuestos")
                Impuesto = etree.SubElement(Impuestos, DTE_NS + "Impuesto")
                NombreCorto = etree.SubElement(Impuesto, DTE_NS + "NombreCorto")
                NombreCorto.text = "IVA"
                CodigoUnidadGravable = etree.SubElement(Impuesto, DTE_NS + "CodigoUnidadGravable")
                CodigoUnidadGravable.text = "1"

                # if factura.tipo_gasto == 'importacion':
                if float_is_zero(total_impuestos, precision_rounding=factura.currency_id.rounding):
                    CodigoUnidadGravable.text = "2"

                MontoGravable = etree.SubElement(Impuesto, DTE_NS + "MontoGravable")
                MontoGravable.text = '{:.2f}'.format(factura.currency_id.round(total_linea_base))
                MontoImpuesto = etree.SubElement(Impuesto, DTE_NS + "MontoImpuesto")
                MontoImpuesto.text = '{:.2f}'.format(factura.currency_id.round(total_impuestos))
            # / len(linea.tax_ids) > 0:

            Total = etree.SubElement(Item, DTE_NS + "Total")
            Total.text = '{:.2f}'.format(factura.currency_id.round(total_linea))

            gran_total += factura.currency_id.round(total_linea)
            gran_subtotal += factura.currency_id.round(total_linea_base)
            gran_total_impuestos += factura.currency_id.round(total_impuestos)

        Totales = etree.SubElement(DatosEmision, DTE_NS + "Totales")

        # if cantidad_impuestos > 0:
        if tipo_documento_fel not in ['NABN']:
            TotalImpuestos = etree.SubElement(Totales, DTE_NS + "TotalImpuestos")
            TotalImpuesto = etree.SubElement(TotalImpuestos, DTE_NS + "TotalImpuesto", NombreCorto="IVA",
                                             TotalMontoImpuesto='{:.2f}'.format(
                                                 factura.currency_id.round(gran_total_impuestos)))
        # /cantidad_impuestos > 0

        GranTotal = etree.SubElement(Totales, DTE_NS + "GranTotal")
        GranTotal.text = '{:.2f}'.format(factura.currency_id.round(gran_total))

        # En todos estos casos, es necesario enviar complementos
        if tipo_documento_fel in ['NDEB', 'NCRE'] or tipo_documento_fel in ['FCAM'] or (tipo_documento_fel in ['FACT',
                                                                                                               'FCAM'] and factura.tipo_gasto == 'importacion') or tipo_documento_fel in [
            'FESP']:
            Complementos = etree.SubElement(DatosEmision, DTE_NS + "Complementos")

            if tipo_documento_fel in ['NDEB', 'NCRE']:
                Complemento = etree.SubElement(Complementos, DTE_NS + "Complemento", IDComplemento="ReferenciasNota",
                                               NombreComplemento="Nota de Credito" if tipo_documento_fel == 'NCRE' else "Nota de Debito",
                                               URIComplemento="text")
                if factura.factura_org_id.numero_fel:
                    ReferenciasNota = etree.SubElement(Complemento, CNO_NS + "ReferenciasNota",
                                                       FechaEmisionDocumentoOrigen=str(
                                                           factura.factura_org_id.invoice_date), MotivoAjuste="-",
                                                       NumeroAutorizacionDocumentoOrigen=factura.factura_org_id.firma_fel,
                                                       NumeroDocumentoOrigen=factura.factura_org_id.numero_fel,
                                                       SerieDocumentoOrigen=factura.factura_org_id.serie_fel,
                                                       Version="0.0", nsmap=NSMAP_REF)
                else:
                    ReferenciasNota = etree.SubElement(Complemento, CNO_NS + "ReferenciasNota",
                                                       RegimenAntiguo="Antiguo", FechaEmisionDocumentoOrigen=str(
                            factura.factura_org_id.invoice_date), MotivoAjuste="-",
                                                       NumeroAutorizacionDocumentoOrigen=factura.factura_org_id.firma_fel,
                                                       NumeroDocumentoOrigen=factura.factura_org_id.name.split("-")[1],
                                                       SerieDocumentoOrigen=factura.factura_org_id.name.split("-")[0],
                                                       Version="0.0", nsmap=NSMAP_REF)

            if tipo_documento_fel in ['FCAM']:
                Complemento = etree.SubElement(Complementos, DTE_NS + "Complemento", IDComplemento="FCAM",
                                               NombreComplemento="AbonosFacturaCambiaria",
                                               URIComplemento="#AbonosFacturaCambiaria")
                AbonosFacturaCambiaria = etree.SubElement(Complemento, CFC_NS + "AbonosFacturaCambiaria", Version="1",
                                                          nsmap=NSMAP_ABONO)
                Abono = etree.SubElement(AbonosFacturaCambiaria, CFC_NS + "Abono")
                NumeroAbono = etree.SubElement(Abono, CFC_NS + "NumeroAbono")
                NumeroAbono.text = "1"
                FechaVencimiento = etree.SubElement(Abono, CFC_NS + "FechaVencimiento")
                FechaVencimiento.text = str(factura.invoice_date_due)
                MontoAbono = etree.SubElement(Abono, CFC_NS + "MontoAbono")
                MontoAbono.text = '{:.2f}'.format(factura.currency_id.round(gran_total))

            if tipo_documento_fel in ['FACT', 'FCAM'] and factura.tipo_gasto == 'importacion':
                Complemento = etree.SubElement(Complementos, DTE_NS + "Complemento", IDComplemento="text",
                                               NombreComplemento="text", URIComplemento="text")
                Exportacion = etree.SubElement(Complemento, CEX_NS + "Exportacion", Version="1", nsmap=NSMAP_EXP)
                NombreConsignatarioODestinatario = etree.SubElement(Exportacion,
                                                                    CEX_NS + "NombreConsignatarioODestinatario")
                NombreConsignatarioODestinatario.text = factura.consignatario_fel.name if factura.consignatario_fel else "-"
                DireccionConsignatarioODestinatario = etree.SubElement(Exportacion,
                                                                       CEX_NS + "DireccionConsignatarioODestinatario")
                DireccionConsignatarioODestinatario.text = factura.consignatario_fel.street or "-" if factura.consignatario_fel else "-"
                NombreComprador = etree.SubElement(Exportacion, CEX_NS + "NombreComprador")
                NombreComprador.text = factura.comprador_fel.name if factura.comprador_fel else "-"
                DireccionComprador = etree.SubElement(Exportacion, CEX_NS + "DireccionComprador")
                DireccionComprador.text = factura.comprador_fel.street or "-" if factura.comprador_fel else "-"
                INCOTERM = etree.SubElement(Exportacion, CEX_NS + "INCOTERM")
                INCOTERM.text = factura.invoice_incoterm_id.code or "-"
                NombreExportador = etree.SubElement(Exportacion, CEX_NS + "NombreExportador")
                NombreExportador.text = factura.exportador_fel.name if factura.exportador_fel else "-"
                CodigoExportador = etree.SubElement(Exportacion, CEX_NS + "CodigoExportador")
                CodigoExportador.text = factura.exportador_fel.ref or "-" if factura.exportador_fel else "-"

            if tipo_documento_fel in ['NCRE'] and factura.factura_org_id.tipo_gasto == 'importacion':
                Complemento = etree.SubElement(Complementos, DTE_NS + "Complemento", IDComplemento="text",
                                               NombreComplemento="text", URIComplemento="text")
                Exportacion = etree.SubElement(Complemento, CEX_NS + "Exportacion", Version="1", nsmap=NSMAP_EXP)
                NombreConsignatarioODestinatario = etree.SubElement(Exportacion,
                                                                    CEX_NS + "NombreConsignatarioODestinatario")
                NombreConsignatarioODestinatario.text = factura.factura_org_id.consignatario_fel.name if factura.factura_org_id.consignatario_fel else "-"
                DireccionConsignatarioODestinatario = etree.SubElement(Exportacion,
                                                                       CEX_NS + "DireccionConsignatarioODestinatario")
                DireccionConsignatarioODestinatario.text = factura.factura_org_id.consignatario_fel.street or "-" if factura.factura_org_id.consignatario_fel else "-"
                NombreComprador = etree.SubElement(Exportacion, CEX_NS + "NombreComprador")
                NombreComprador.text = factura.comprador_fel.name if factura.comprador_fel else "-"
                DireccionComprador = etree.SubElement(Exportacion, CEX_NS + "DireccionComprador")
                DireccionComprador.text = factura.factura_org_id.comprador_fel.street or "-" if factura.factura_org_id.comprador_fel else "-"
                INCOTERM = etree.SubElement(Exportacion, CEX_NS + "INCOTERM")
                INCOTERM.text = factura.factura_org_id.invoice_incoterm_id.code or "-"
                NombreExportador = etree.SubElement(Exportacion, CEX_NS + "NombreExportador")
                NombreExportador.text = factura.factura_org_id.exportador_fel.name if factura.factura_org_id.exportador_fel else "-"
                CodigoExportador = etree.SubElement(Exportacion, CEX_NS + "CodigoExportador")
                CodigoExportador.text = factura.factura_org_id.exportador_fel.ref or "-" if factura.factura_org_id.exportador_fel else "-"

            if tipo_documento_fel in ['FESP']:
                total_isr = abs(factura.amount_tax)

                total_iva_retencion = 0

                for impuesto in factura.amount_by_group:
                    if impuesto[1] > 0:
                        total_iva_retencion += impuesto[1]

                Complemento = etree.SubElement(Complementos, DTE_NS + "Complemento", IDComplemento="text",
                                               NombreComplemento="text", URIComplemento="text")
                RetencionesFacturaEspecial = etree.SubElement(Complemento, CFE_NS + "RetencionesFacturaEspecial",
                                                              Version="1", nsmap=NSMAP_FE)
                RetencionISR = etree.SubElement(RetencionesFacturaEspecial, CFE_NS + "RetencionISR")
                RetencionISR.text = str(total_isr)
                RetencionIVA = etree.SubElement(RetencionesFacturaEspecial, CFE_NS + "RetencionIVA")
                RetencionIVA.text = str(total_iva_retencion)
                TotalMenosRetenciones = etree.SubElement(RetencionesFacturaEspecial, CFE_NS + "TotalMenosRetenciones")
                TotalMenosRetenciones.text = str(factura.amount_total)

        xmls = etree.tostring(GTDocumento, encoding="UTF-8").decode("utf-8")

        return xmls


class AccountJournal(models.Model):
    _inherit = "account.journal"

    tipo_documento_fel = fields.Selection(
        [('FACT', 'Factura'), ('FCAM', 'Factura Cambiaria'), ('FESP', 'Factura Especial'), ('NABN', 'Nota de Abono'),
         ('NDEB', 'Nota de Debito'), ('NCRE', 'Nota de Credito')], 'Tipo de Documento FEL', copy=False)
    direccion_fel = fields.Many2one('res.partner', string="Dirección Establecimiento Fel")


class ResCompany(models.Model):
    _inherit = "res.company"

    url_api_fel = fields.Char('URL del API Crea DTE',
                              help="URL del API que se consume para generar los documentos FEL.")
    url_api_token_fel = fields.Char('URL del API Solicita Token DTE',
                                    help="URL del API que se consume para solictar token.")
    url_api_firma_fel = fields.Char('URL del API Firma DTE',
                                    help="URL del API que se consume para generar firmar documento FEL.")
    url_api_anula_fel = fields.Char('URL del API anula DTE',
                                    help="URL del API que se consume para anular los documentos FEL.")
    url_api_pdf_fel = fields.Char('URL del API Genera PDF', help="URL del API que se consume para generar archivo PDF.")
    dev_url_api_fel = fields.Char('URL del API dev_ Crea DTE',
                                  help="URL del API que se consume para generar los documentos FEL.")
    dev_url_api_token_fel = fields.Char('URL del API dev_ Solicita Token DTE',
                                        help="URL del API que se consume para solictar token.")
    dev_url_api_firma_fel = fields.Char('URL del API dev_ Firma DTE',
                                        help="URL del API que se consume para generar firmar documento FEL.")
    dev_url_api_anula_fel = fields.Char('URL del API dev_ anula DTE',
                                        help="URL del API que se consume para anular los documentos FEL.")
    dev_url_api_pdf_fel = fields.Char('URL del API dev_ Genera PDF',
                                      help="URL del API que se consume para generar archivo PDF.")
