# -*- coding: utf-8 -*-
# The MIT License (MIT)
# 
# Copyright (c) 2015 Dmitry Vasilev <dima@hlabs.org>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

# Usage example:
# 
#   >>> from pricepi import PricepiAPI
#   >>> pricepi = PricepiAPI("UniqueID", "AuthKey")
#   >>> # Product name, Currency, Merchant name, Limit
#   >>> pricepi.query(u"ProductName", "USD", u"MerchantName", 10)
#

import time
import re
import datetime
from decimal import Decimal
from xml.sax.saxutils import unescape
from xml.dom.minidom import parse
from urllib import urlencode, quote_plus
from hashlib import sha256
from urllib2 import urlopen


class PricepiAPIError(Exception):
  pass

class PricepiAPI(object):

  url = "https://api.pricepi.com/pricepiapi.pi"

  SORT_RELEVANCE = "relevance"
  SORT_PRICE = "price"

  prepare_query = re.compile(r"\s+")
  prepare_hash = re.compile(r"[+\s]+")

  def __init__(self, unique_id, account_key):
    self.unique_id = unique_id
    self.account_key = account_key

  def query(self, query, currency, seller, limit, offset=0, unknown=False,
            sortby=SORT_RELEVANCE):
    unknown = "on" if unknown else "off"
    # Offset/Limit pair should be urlencoded before hashing
    ol = "%d %d" % (offset, limit)
    ts = int(time.time())
    query = self.prepare_query.sub("", query.encode("utf-8"))
    seller = seller.encode("utf-8")
    to_hash = "".join((query, currency, seller, sortby, quote_plus(ol), str(ts),
                       self.unique_id))
    to_hash = self.prepare_hash.sub("", to_hash) + self.account_key
    h = sha256()
    h.update(to_hash)
    args = [
      ("query", query),
      ("currency", currency),
      ("seller", seller),
      ("sortby", sortby),
      ("limit", ol),
      ("timestamp", ts),
      ("uniqid", self.unique_id),
      ("authcode", h.hexdigest()),
    ]
    f = urlopen(self.url + "?" + urlencode(args))
    return self._parseXMLResponse(f)

  def _parseXMLResponse(self, f):
    # TODO: Probably better to use SAX parser
    dom = parse(f)
    error_text = self._getText(dom, "Pricepi_response")
    if error_text:
      raise PricepiAPIError(error_text)
    info = []
    for p in dom.getElementsByTagName("result"):
      id = self._getText(p, "id")
      name = self._getText(p, "name")
      seller = self._getText(p, "seller")
      url = self._getText(p, "location")
      image_url = self._getText(p, "image")
      date = self._getText(p, "date")
      price = self._getText(p, "price")
      currency = self._getText(p, "currency")
      product = Product(id, name, seller, url, image_url, date, price, currency)
      info.append(product)
    return info

  def _getText(self, parent, name):
    children = parent.getElementsByTagName(name)[0].childNodes
    return unescape("".join(node.data for node in children
                            if node.nodeType in (node.TEXT_NODE,
                                node.CDATA_SECTION_NODE)).strip())

class Product(object):

  date_format = "%Y_%m_%d"

  def __init__(self, id, name, seller, url, image_url, date, price, currency):
    self.id = id
    self.name = name
    self.seller = seller
    self.url = url
    self.image_url = image_url
    self.date = datetime.datetime.strptime(date, self.date_format)
    self.price = Decimal(price)
    self.currency = currency

  def __repr__(self):
    return "Product(%r, %r, %r, %r, %r, %r, %r, %r)" % (self.id, self.name,
           self.seller, self.url, self.image_url, self.date, self.price,
           self.currency)
