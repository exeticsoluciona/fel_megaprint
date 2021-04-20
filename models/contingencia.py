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

class Contingencia_Fel_Cron(models.Model):
    _inherit = "account.move"
    # fields
    def SendInvoiceCertificate(self): # method of this model
        
        logging.warn("Ejecutando Cron Job")
        
        obj = self.search([('contingencia_fel','=','1'),('firma_fel','=',False),('state','=','posted')])
        
        for factura in obj:
            logging.warn(factura.uuid_contigencia)
            
            if factura.firma_fel:
                logging.warn("La factura ya fue validada, por lo que no puede ser validada nuevamnte.")
                continue
            
            if factura.journal_id.direccion_fel.username_fel and not factura.firma_fel and factura.amount_total != 0:
                
                xmls = factura.dteDocumento()
                
                if xmls:  
                    
                    #Url Documento
                    urlApi = factura.company_id.url_api_fel
                    if urlApi == False:
                       urlApi = factura.company_id.dev_url_api_fel
                    
                    #Url Firma
                    urlApiFirma = factura.company_id.url_api_firma_fel
                    if urlApiFirma == False:
                       urlApiFirma = factura.company_id.dev_url_api_firma_fel

                    #Url Solicita Token   
                    urlApiToken = factura.company_id.url_api_token_fel
                    if urlApiToken == False:
                       urlApiToken = factura.company_id.dev_url_api_token_fel
                    
                    #Url PDF 
                    urlApiPdf = factura.company_id.url_api_pdf_fel
                    if urlApiPdf == False:
                       urlApiPdf = factura.company_id.dev_url_api_pdf_fel
                              
                    headers = { "Content-Type": "application/xml" }
                    data = '<?xml version="1.0" encoding="UTF-8"?><SolicitaTokenRequest><usuario>{}</usuario><apikey>{}</apikey></SolicitaTokenRequest>'.format(factura.journal_id.direccion_fel.username_fel, factura.journal_id.direccion_fel.password_fel)
                    r = requests.post(urlApiToken, data=data.encode('utf-8'), headers=headers)
                    logging.warn(r.text)
                    resultadoXML = etree.XML(bytes(r.text, encoding='utf-8'))
    
                    if len(resultadoXML.xpath("//token")) > 0:
                        token = resultadoXML.xpath("//token")[0].text
                        uuid_factura = str(uuid.uuid5(uuid.NAMESPACE_OID, str(factura.id))).upper()
    
                        headers = { "Content-Type": "application/xml", "authorization": "Bearer "+token }
                        logging.warn(headers)
                        data = '<?xml version="1.0" encoding="UTF-8"?><FirmaDocumentoRequest id="{}"><xml_dte><![CDATA[{}]]></xml_dte></FirmaDocumentoRequest>'.format(uuid_factura, xmls)
                        logging.warn(data)
                        r = requests.post(urlApiFirma, data=data.encode('utf-8'), headers=headers)
                        logging.warn(r.text)
                        resultadoXML = etree.XML(bytes(r.text, encoding='utf-8'))
                        if len(resultadoXML.xpath("//xml_dte")) > 0:
                            xml_con_firma = resultadoXML.xpath("//xml_dte")[0].text
    
                            headers = { "Content-Type": "application/xml", "authorization": "Bearer "+token }
                            data = '<?xml version="1.0" encoding="UTF-8"?><RegistraDocumentoXMLRequest id="{}"><xml_dte><![CDATA[{}]]></xml_dte></RegistraDocumentoXMLRequest>'.format(uuid_factura, xml_con_firma)
                            logging.warn(data)
                            r = requests.post(urlApi, data=data.encode('utf-8'), headers=headers)
                            resultadoXML = etree.XML(bytes(r.text, encoding='utf-8'))
    
                            if len(resultadoXML.xpath("//listado_errores")) == 0:
                                xml_certificado = resultadoXML.xpath("//xml_dte")[0].text
                                xml_certificado_root = etree.XML(bytes(xml_certificado, encoding='utf-8'))
                                numero_autorizacion = xml_certificado_root.find(".//{http://www.sat.gob.gt/dte/fel/0.2.0}NumeroAutorizacion")
                                factura.tipo_doc_fel = factura.journal_id.tipo_documento_fel
                                factura.firma_fel = numero_autorizacion.text
                                factura.name = numero_autorizacion.get("Serie")+"-"+numero_autorizacion.get("Numero")
                                factura.serie_fel = numero_autorizacion.get("Serie")
                                factura.numero_fel = numero_autorizacion.get("Numero")
                                factura.estado_doc_fel = 'Activo'
    
                                headers = { "Content-Type": "application/xml", "authorization": "Bearer "+token }
                                data = '<?xml version="1.0" encoding="UTF-8"?><RetornaPDFRequest><uuid>{}</uuid></RetornaPDFRequest>'.format(factura.firma_fel)
                                r = requests.post(urlApiPdf, data=data, headers=headers)
                                resultadoXML = etree.XML(bytes(r.text, encoding='utf-8'))
                                if len(resultadoXML.xpath("//listado_errores")) == 0:
                                    pdf = resultadoXML.xpath("//pdf")[0].text
                                    factura.pdf_fel = pdf
                                    pdfname = '{}.pdf'.format(factura.name)
                                    factura.name_pdf_fel = pdfname
                            else:
                                logging.warn(r.text)
                        else:
                            logging.warn(r.text)
                    else:
                        logging.warn(r.text)            
        
        logging.warn("Finaliza Cron Job")