from lxml import etree as ET
import os
from calamari_ocr.utils.Abbyy import Data, Exceptions
from calamari_ocr.utils.Abbyy.Data import Book
from tqdm import tqdm


class XMLReader:
    """
    This class can read Abbyy documents out of a directory
    """

    def __init__(self, imgfiles: [], skip_invalid: bool, remove_invalid: bool):

        """
        Constructs an XMLReader class with the :param directory

        :param directory: Absolute or relative path of the directory there the abbyy documents are located
        """
        self.imgfiles = sorted(imgfiles)
        self.skip_invalid = skip_invalid
        self.remove_invalid = remove_invalid
        self.pagecount = 0
        self.blockcount = 0
        self.linecount = 0

    def read(self) -> Data.Book:

        """
        Starst trying to read the data from the directory :var self.directory

        :return: a Data.Book class with all the readed data from :var self.directory
        :exception WrongFileStructureException: Is raised then files are missing in the directory
                    (e.g.: no image file for an xml file which is named equally)
        :exception XMLParseError: Is raised then there are errors in a xml file
        """

        xmlfiles = []
        book: Book = None

        # Searching for the xml abbyy files and handling Errors in the data structure
        for imgfile in self.imgfiles:
            split = imgfile.split('.')
            split[len(split) - 1] = 'xml'
            xmlfile = split[0]
            for i in range(1, len(split)):
                xmlfile = xmlfile + '.' + split[i]
            if not os.path.exists(xmlfile):
                if not self.skip_invalid:
                    raise Exceptions.WrongFileStructureException('The image file' + imgfile + 'has no suitable abbyy '
                                                                 'xml file. The Files which belongs together have to '
                                                                 'be named equally.')
                else:
                    self.imgfiles.remove(imgfile)
                if self.remove_invalid:
                    os.remove(imgfile)
                    os.remove(xmlfile)
            else:
                xmlfiles.append(xmlfile)

        # Starts reading the xml files
        for imgfile, xmlfile in tqdm(zip(self.imgfiles, xmlfiles), desc='Reading', total=len(xmlfiles)):

            # Reads the xml file with the xml.etree.ElementTree package
            try:
                tree = ET.parse(xmlfile)
            except ET.ParseError as e:
                raise Exceptions.XMLParseError('The xml file \'' + xmlfile + '\' couldn\'t be read because of a '
                                                                             'syntax error in the xml file. ' + e.msg)

            root = tree.getroot()

            if root is None:
                raise Exceptions.XMLParseError('The xml file \'' + xmlfile + '\' is empty.')

            schemaLocation = root.get('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation')
            version = root.get('version')
            producer = root.get('producer')
            languages = root.get('languages')

            # initialize a book class if its not None
            if book is None:
                book: Book = Data.Book(os.path.dirname(xmlfile), schemaLocation, version, producer, languages)

            for pageNode in root:

                self.pagecount = self.pagecount + 1

                # Constructs a page class out of the xml data
                width = pageNode.get('width')
                height = pageNode.get('height')
                res = pageNode.get('resolution')
                oC = pageNode.get('originalCoords')

                # Controls the existence of the variable
                if width is None:
                    raise Exceptions.XMLParseError('On the page ' + self.pagecount.__str__() + ' in the document \''
                                                   + xmlfile + '\' the \'width\' attribute is missing in the page tag.')
                if height is None:
                    raise Exceptions.XMLParseError('On the page ' + self.pagecount.__str__() + ' in the document \''
                                                   + xmlfile + '\' the \'height\' attribute is missing in the page tag.')
                if res is None:
                    raise Exceptions.XMLParseError('On the page ' + self.pagecount.__str__() + ' in the document \''
                                                   + xmlfile + '\' the \'resolution\' attribute '
                                                               'is missing in the page tag.')
                if oC is None:
                    raise Exceptions.XMLParseError('On the page ' + self.pagecount.__str__() + ' in the document \''
                                                   + xmlfile + '\' the \'original coords\' attribute'
                                                               ' is missing in the page tag.')

                page: Data.Page = Data.Page(width, height, res, oC, imgfile, xmlfile)

                for blockNode in pageNode:

                    self.blockcount = self.blockcount + 1

                    # Checks if the blockType is text, ignoring all other types
                    type = blockNode.get('blockType')
                    if type is not None and type == 'Text':

                        # Reads rectangle data and controls if they are empty
                        name = blockNode.get('blockName')

                        l = blockNode.get('l')
                        t = blockNode.get('t')
                        r = blockNode.get('r')
                        b = blockNode.get('b')

                        if l is None:
                            raise Exceptions.XMLParseError(
                                'On the page number ' + self.pagecount.__str__() + ' in the block number ' + self.blockcount +
                                ' in the document \'' + xmlfile + '\' the rectangle attribute \'l\' is missing.')
                        if t is None:
                            raise Exceptions.XMLParseError(
                                'On the page number ' + self.pagecount.__str__() + ' in the block number ' + self.blockcount +
                                ' in the document \'' + xmlfile + '\' the rectangle attribute \'t\' is missing.')
                        if r is None:
                            raise Exceptions.XMLParseError(
                                'On the page number ' + self.pagecount.__str__() + ' in the block number ' + self.blockcount +
                                ' in the document \'' + xmlfile + '\' the rectangle attribute \'r\' is missing.')
                        if b is None:
                            raise Exceptions.XMLParseError(
                                'On the page number ' + self.pagecount.__str__() + ' in the block number ' + self.blockcount +
                                ' in the document \'' + xmlfile + '\' the rectangle attribute \'b\' is missing.')

                        try:
                            rect: Data.Rect = Data.Rect(int(l), int(t), int(r), int(b))
                        except ValueError:
                            raise Exceptions.XMLParseError(
                                    'On the page number ' + self.pagecount.__str__() + ' in the block number ' + self.blockcount +
                                    ' in the document \'' + xmlfile + '\' one of the rectangle attributes is not a number')

                        block: Data.Block = Data.Block(type, name, rect)

                        for textNode in blockNode:

                            # Again only text nodes will be considered

                            if textNode.tag == '{http://www.abbyy.com/FineReader_xml/FineReader10-schema-v1.xml}text':
                                for parNode in textNode:

                                    align = parNode.get('align')
                                    startIndent = parNode.get('startIndent')
                                    lineSpacing = parNode.get('lineSpacing')

                                    par: Data.Par = Data.Par(align, startIndent, lineSpacing)

                                    for lineNode in parNode:

                                        self.linecount = self.linecount + 1

                                        baseline = lineNode.get('baseline')

                                        l = lineNode.get('l')
                                        t = lineNode.get('t')
                                        r = lineNode.get('r')
                                        b = lineNode.get('b')

                                        if l is None:
                                            raise Exceptions.XMLParseError(
                                                'On the page number ' + self.pagecount.__str__() + ' in the block number'
                                                + self.blockcount.__str__() + ' in the line number ' + self.linecount.__str__() +
                                                ' in the document \'' + xmlfile +
                                                '\' the rectangle attribute \'l\' is missing.')
                                        if t is None:
                                            raise Exceptions.XMLParseError(
                                                'On the page number ' + self.pagecount.__str__() + ' in the block number'
                                                + self.blockcount.__str__() + ' in the line number ' + self.linecount.__str__() +
                                                ' in the document \'' + xmlfile +
                                                '\' the rectangle attribute \'t\' is missing.')
                                        if r is None:
                                            raise Exceptions.XMLParseError(
                                                'On the page number ' + self.pagecount.__str__() + ' in the block number'
                                                + self.blockcount.__str__() + ' in the line number ' + self.linecount.__str__() +
                                                ' in the document \'' + xmlfile +
                                                '\' the rectangle attribute \'r\' is missing.')
                                        if b is None:
                                            raise Exceptions.XMLParseError(
                                                'On the page number ' + self.pagecount.__str__() + ' in the block number'
                                                + self.blockcount.__str__() + ' in the line number ' + self.linecount.__str__() +
                                                ' in the document \'' + xmlfile +
                                                '\' the rectangle attribute \'b\' is missing.')

                                        try:
                                            rect: Data.Rect = Data.Rect(int(l), int(t), int(r), int(b))
                                        except ValueError:
                                            raise Exceptions.XMLParseError(
                                                'On the page number ' + self.pagecount.__str__() + ' in the block number'
                                                + self.blockcount.__str__() + ' in the line number ' + self.linecount.__str__() +
                                                ' in the document \'' + xmlfile +
                                                '\' one of the rectangle attributes is not a number.')

                                        line: Data.Line = Data.Line(baseline, rect)

                                        lang = None
                                        text = ""
                                        maxCount = 0
                                        for formNode in lineNode:
                                            countChars = 0
                                            if formNode.text is None or formNode.text == "\n" or formNode.text == "":
                                                for charNode in formNode:
                                                    text += charNode.text.__str__()
                                                    countChars = countChars + 1
                                                if countChars > maxCount:
                                                    maxCount = countChars
                                                    lang = formNode.get('lang')


                                            else:
                                                lang = formNode.get('lang')
                                                text = formNode.text.__str__()

                                        format: Data.Format = Data.Format(lang, text)
                                        line.formats.append(format)
                                        par.lines.append(line)

                                    self.linecount = 0
                                    block.pars.append(par)

                        page.blocks.append(block)

                self.blockcount = 0
                book.pages.append(page)

            self.pagecount = 0

        if not book.pages:
            raise Exceptions.XMLParseError('In this selected directory there is no suitable data!')

        return book
