from lxml import etree as ET
import os, stat
from calamari_ocr.utils.Abbyy.Data import Book
from shutil import copy


class XMLWriter:

    """

    """

    def __init__(self, savepath: str, imgpath: str, book: Book):

        """
        Initialize an XMLWriter class to write an AbbyyDocument

        :param imgpath: path of all the image (and xml) files
        :param book: the abbyy book class which should be written
        """

        self.directory = savepath + "\\save"
        self.book = book
        self.imgpath = imgpath
        self.savepath = savepath

    def write(self):

        """
        Writes Abbyy Files out of the parameters from __init__()
        and copy the image files into the path :param self.directory
        """

        root = ET.Element('document')
        tree = ET.ElementTree(root)

        self._addElement(root, "xmlns", self.book.schemaLocation.split(' ')[0])
        self._addElement(root, "version", self.book.version)
        self._addElement(root, "producer", self.book.producer)
        self._addElement(root, "languages", self.book.languages)
        NS_XSI: str = "{http://www.w3.org/2001/XMLSchema-instance}"
        root.set(NS_XSI + "schemaLocation",
                 "http://www.abbyy.com/FineReader_xml/FineReader10-schema-v1.xml http://www.abbyy.com/FineReader_xml/FineReader10-schema-v1.xml")
        oldxmlfile = None
        oldimgfile = None

        for page in self.book.pages:

            if oldxmlfile is not None and oldxmlfile != page.xmlFile:
                #print(page.xmlFile)
                try:
                    os.mkdir(self.directory)
                    os.chdir(self.directory)
                except FileExistsError:
                    os.chdir(self.directory)

                tree.write(open(oldxmlfile, 'wb'), encoding='utf-8', xml_declaration=True, pretty_print=True)
                try:
                    copy(self.imgpath + "\\" + oldimgfile, self.directory)
                except PermissionError:
                    pass

                root = ET.Element('document')
                tree = ET.ElementTree(root)

                self._addElement(root, "xmlns", self.book.schemaLocation.split(' ')[0])
                self._addElement(root, "version", self.book.version)
                self._addElement(root, "producer", self.book.producer)
                self._addElement(root, "languages", self.book.languages)
                NS_XSI: str = "{http://www.w3.org/2001/XMLSchema-instance}"
                root.set(NS_XSI + "schemaLocation",
                         "http://www.abbyy.com/FineReader_xml/FineReader10-schema-v1.xml http://www.abbyy.com/FineReader_xml/FineReader10-schema-v1.xml")

            pageNode = ET.SubElement(root, "page")
            self._addElement(pageNode, "width", page.width)
            self._addElement(pageNode, "height", page.height)
            self._addElement(pageNode, "resolution", page.resolution)
            self._addElement(pageNode, "originalCoords", page.resolution)

            for block in page.blocks:

                blockNode = ET.SubElement(pageNode, "block")
                self._addElement(blockNode, "blockType", block.blockType)
                self._addElement(blockNode, "blockName", block.blockName)
                self._addElement(blockNode, "l", block.rect.left.__str__())
                self._addElement(blockNode, "t", block.rect.top.__str__())
                self._addElement(blockNode, "r", block.rect.right.__str__())
                self._addElement(blockNode, "b", block.rect.bottom.__str__())

                textNode = ET.SubElement(blockNode, "text")

                for par in block.pars:

                    parNode = ET.SubElement(textNode, "par")
                    self._addElement(parNode, "align", par.align)
                    self._addElement(parNode, "startIndent", par.startIndent)
                    self._addElement(parNode, "lineSpacing", par.lineSpacing)

                    for line in par.lines:

                        lineNode = ET.SubElement(parNode, "line")
                        self._addElement(lineNode, "baseline", line.baseline)
                        self._addElement(lineNode, "l", line.rect.left.__str__())
                        self._addElement(lineNode, "t", line.rect.top.__str__())
                        self._addElement(lineNode, "r", line.rect.right.__str__())
                        self._addElement(lineNode, "b", line.rect.bottom.__str__())

                        for fo in line.formats:

                            foNode = ET.SubElement(lineNode, "formatting")
                            self._addElement(foNode, "lang", fo.lang)
                            foNode.text = fo.text

            oldxmlfile = page.xmlFile
            oldimgfile = page.imgFile

        try:
            os.mkdir(self.directory)
            os.chdir(self.directory)
        except FileExistsError:
            os.chdir(self.directory)

        tree.write(open(oldxmlfile, 'wb'), encoding='utf-8', xml_declaration=True, pretty_print=True)
        try:
            copy(self.imgpath + "\\" + oldimgfile, self.directory)
        except PermissionError:
            pass

    def _addElement(self, element, key, value):

        """
        Only add attributes to an tag if the key is not None

        :param element: the tag element of the xml tree
        :param key: the key of the attribute
        :param value: the value of the attribute
        :return:
        """

        if value is not None:
            element.set(key, value)

