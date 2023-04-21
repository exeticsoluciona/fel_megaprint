# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round

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


class AccountInvoice(models.Model):
    _inherit = "account.move"

    def button_draft(self):

        # result = super(AccountInvoice, self)

        for factura in self:
            if factura.estado_doc_fel == 'Activo':
                raise UserError("No se puede cancelar o cambia a borrador una factura activa en FEL.")

        return super(AccountInvoice, self).button_draft()

    def invoice_fel(self):

        for factura in self:

            if factura.uuid_contigencia:
                raise UserError(
                    "El documento fue creado en contingencia, no puede certificarse de forma normal, debe esperar que el Sistema procese automaticamente.")
            if factura.firma_fel:
                raise UserError("El documento fue validado, por lo que no puede ser validado nuevamente.")

            if factura.journal_id.direccion_fel.username_fel and not factura.firma_fel and factura.amount_total != 0:

                xmls = factura.dteDocumento()

                if xmls:

                    headers = {"Content-Type": "application/xml"}
                    data = '<?xml version="1.0" encoding="UTF-8"?><SolicitaTokenRequest><usuario>{}</usuario><apikey>{}</apikey></SolicitaTokenRequest>'.format(
                        factura.journal_id.direccion_fel.username_fel, factura.journal_id.direccion_fel.password_fel)

                    # Url Documento
                    urlApi = factura.company_id.url_api_fel
                    if urlApi == False:
                        urlApi = factura.company_id.dev_url_api_fel

                    # Url Firma
                    urlApiFirma = factura.company_id.url_api_firma_fel
                    if urlApiFirma == False:
                        urlApiFirma = factura.company_id.dev_url_api_firma_fel

                    # Url Solicita Token
                    urlApiToken = factura.company_id.url_api_token_fel
                    if urlApiToken == False:
                        urlApiToken = factura.company_id.dev_url_api_token_fel

                    # Url PDF
                    urlApiPdf = factura.company_id.url_api_pdf_fel
                    if urlApiPdf == False:
                        urlApiPdf = factura.company_id.dev_url_api_pdf_fel

                    r = {}
                    try:
                        r = requests.post(urlApiToken, data=data.encode('utf-8'), headers=headers)
                    except:
                        raise UserError("No hay conexión al servicio web de Mega Print, Emita factura en contingencia.")

                    logging.warn(r.text)
                    resultadoXML = etree.XML(bytes(r.text, encoding='utf-8'))

                    if len(resultadoXML.xpath("//token")) > 0:
                        token = resultadoXML.xpath("//token")[0].text
                        uuid_factura = str(uuid.uuid5(uuid.NAMESPACE_OID, str(factura.id))).upper()

                        headers = {"Content-Type": "application/xml", "authorization": "Bearer " + token}
                        logging.warn(headers)
                        data = '<?xml version="1.0" encoding="UTF-8"?><FirmaDocumentoRequest id="{}"><xml_dte><![CDATA[{}]]></xml_dte></FirmaDocumentoRequest>'.format(
                            uuid_factura, xmls)
                        logging.warn(data)
                        r = requests.post(urlApiFirma, data=data.encode('utf-8'), headers=headers)
                        logging.warn(r.text)
                        resultadoXML = etree.XML(bytes(r.text, encoding='utf-8'))

                        if len(resultadoXML.xpath("//xml_dte")) > 0:
                            xml_con_firma = resultadoXML.xpath("//xml_dte")[0].text

                            headers = {"Content-Type": "application/xml", "authorization": "Bearer " + token}
                            data = '<?xml version="1.0" encoding="UTF-8"?><RegistraDocumentoXMLRequest id="{}"><xml_dte><![CDATA[{}]]></xml_dte></RegistraDocumentoXMLRequest>'.format(
                                uuid_factura, xml_con_firma)
                            logging.warn(data)
                            r = requests.post(urlApi, data=data.encode('utf-8'), headers=headers)
                            resultadoXML = etree.XML(bytes(r.text, encoding='utf-8'))

                            if len(resultadoXML.xpath("//listado_errores")) == 0:
                                xml_certificado = resultadoXML.xpath("//xml_dte")[0].text
                                xml_certificado_root = etree.XML(bytes(xml_certificado, encoding='utf-8'))
                                numero_autorizacion = xml_certificado_root.find(
                                    ".//{http://www.sat.gob.gt/dte/fel/0.2.0}NumeroAutorizacion")
                                factura.tipo_doc_fel = factura.journal_id.tipo_documento_fel
                                factura.firma_fel = numero_autorizacion.text
                                factura.ref = numero_autorizacion.get("Serie") + "-" + numero_autorizacion.get(
                                    "Numero")
                                factura.serie_fel = numero_autorizacion.get("Serie")
                                factura.numero_fel = numero_autorizacion.get("Numero")
                                factura.estado_doc_fel = 'Activo'

                                headers = {"Content-Type": "application/xml", "authorization": "Bearer " + token}
                                data = '<?xml version="1.0" encoding="UTF-8"?><RetornaPDFRequest><uuid>{}</uuid></RetornaPDFRequest>'.format(
                                    factura.firma_fel)
                                r = requests.post(urlApiPdf, data=data, headers=headers)
                                resultadoXML = etree.XML(bytes(r.text, encoding='utf-8'))
                                if len(resultadoXML.xpath("//listado_errores")) == 0:
                                    pdf = resultadoXML.xpath("//pdf")[0].text
                                    factura.pdf_fel = pdf
                                    pdfname = '{}.pdf'.format(factura.ref)
                                    factura.name_pdf_fel = pdfname
                            else:
                                raise UserError(r.text)
                        else:
                            raise UserError(r.text)
                    else:
                        raise UserError(r.text)

                    logging.warn(xmls)

        return super(AccountInvoice, self)

    def invoice_contigencia(self):

        for factura in self:
            if factura.contingencia_fel and factura.firma_fel == False:
                raise UserError("El documento cuenta con No. de acceso.")

            if factura.firma_fel:
                raise UserError("El documento fue certificado anteriormente, por lo que no se genera No. de acceso.")

            uuid_factura = random.randint(100000000, 999999999)
            factura.contingencia_fel = '1'
            factura.uuid_contigencia = uuid_factura

        return super(AccountInvoice, self)

    def invoiceDue_fel(self):
        result = super(AccountInvoice, self)
        if result:

            for factura in self:

                if factura.estado_doc_fel == 'Anulado':
                    raise UserError(
                        "El documento fue Anulado anteriormente, por lo que no puede ser Anulado nuevamnte.")

                if factura.journal_id.direccion_fel.username_fel and factura.firma_fel:

                    xmls = factura.dteAnulaDocumento()

                    if xmls:

                        # Url Anula
                        urlApi = factura.company_id.url_api_anula_fel
                        if urlApi == False:
                            urlApi = factura.company_id.dev_url_api_anula_fel

                        # Url Firma
                        urlApiFirma = factura.company_id.url_api_firma_fel
                        if urlApiFirma == False:
                            urlApiFirma = factura.company_id.dev_url_api_firma_fel

                        # Url Solicita Token
                        urlApiToken = factura.company_id.url_api_token_fel
                        if urlApiToken == False:
                            urlApiToken = factura.company_id.dev_url_api_token_fel

                        # Url PDF
                        urlApiPdf = factura.company_id.url_api_pdf_fel
                        if urlApiPdf == False:
                            urlApiPdf = factura.company_id.dev_url_api_pdf_fel

                        logging.warn(xmls)

                        headers = {"Content-Type": "application/xml"}
                        data = '<?xml version="1.0" encoding="UTF-8"?><SolicitaTokenRequest><usuario>{}</usuario><apikey>{}</apikey></SolicitaTokenRequest>'.format(
                            factura.journal_id.direccion_fel.username_fel,
                            factura.journal_id.direccion_fel.password_fel)
                        r = {}
                        try:
                            r = requests.post(urlApiToken, data=data.encode('utf-8'), headers=headers)
                        except:
                            raise UserError("No hay conexión al servicio web de Mega Print.")

                        resultadoXML = etree.XML(bytes(r.text, encoding='utf-8'))

                        if len(resultadoXML.xpath("//token")) > 0:
                            token = resultadoXML.xpath("//token")[0].text
                            uuid_factura = str(uuid.uuid5(uuid.NAMESPACE_OID, str(factura.id))).upper()

                            headers = {"Content-Type": "application/xml", "authorization": "Bearer " + token}
                            data = '<?xml version="1.0" encoding="UTF-8"?><FirmaDocumentoRequest id="{}"><xml_dte><![CDATA[{}]]></xml_dte></FirmaDocumentoRequest>'.format(
                                uuid_factura, xmls)
                            logging.warn(data)
                            r = requests.post(urlApiFirma, data=data.encode('utf-8'), headers=headers)
                            logging.warn(r.text)
                            resultadoXML = etree.XML(bytes(r.text, encoding='utf-8'))
                            if len(resultadoXML.xpath("//xml_dte")) > 0:
                                xml_con_firma = html.unescape(resultadoXML.xpath("//xml_dte")[0].text)

                                headers = {"Content-Type": "application/xml", "authorization": "Bearer " + token}
                                data = '<?xml version="1.0" encoding="UTF-8"?><AnulaDocumentoXMLRequest id="{}"><xml_dte><![CDATA[{}]]></xml_dte></AnulaDocumentoXMLRequest>'.format(
                                    uuid_factura, xml_con_firma)
                                logging.warn(data)
                                r = requests.post(urlApi, data=data.encode('utf-8'), headers=headers)
                                resultadoXML = etree.XML(bytes(r.text, encoding='utf-8'))

                                if len(resultadoXML.xpath("//listado_errores")) > 0:
                                    raise UserError(r.text)
                                else:
                                    factura.estado_doc_fel = 'Anulado'
                                    headers = {"Content-Type": "application/xml", "authorization": "Bearer " + token}
                                    data = '<?xml version="1.0" encoding="UTF-8"?><RetornaPDFRequest><uuid>{}</uuid></RetornaPDFRequest>'.format(
                                        factura.firma_fel)
                                    r = requests.post(urlApiPdf, data=data, headers=headers)
                                    resultadoXML = etree.XML(bytes(r.text, encoding='utf-8'))
                                    if len(resultadoXML.xpath("//listado_errores")) == 0:
                                        pdf = resultadoXML.xpath("//pdf")[0].text
                                        factura.pdf_fel = pdf
                                        pdfname = '{}.pdf'.format(factura.ref)
                                        factura.name_pdf_fel = pdfname
                            else:
                                raise UserError(r.text)
                        else:
                            raise UserError(r.text)

        return result
