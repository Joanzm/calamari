from lxml import etree as ET
import os
from calamari_ocr.utils.Abbyy import Data, Exceptions
from calamari_ocr.utils.Abbyy.Data import Book


class XMLReader:

    """
    This class can read Abbyy documents out of a directory
    """

    def __init__(self, directory: str):

        """
        Constructs an XMLReader class with the :param directory

        :param directory: Absolute or relative path of the directory there the abbyy documents are located
        """
        self.directory = directory
        self.pagecount = 0
        self.blockcount = 0
        self.linecount = 0

    def read(self)-> Data.Book:

        """
        Starst trying to read the data from the directory :var self.directory

        :return: a Data.Book class with all the readed data from :var self.directory
        :exception WrongFileStructureException: Is raised then files are missing in the directory
                    (e.g.: no image file for an xml file which is named equally)
        :exception XMLParseError: Is raised then there are errors in a xml file
        """

        os.chdir(self.directory)
        FileList = sorted(os.listdir(self.directory))

        # Ignores all irrelevant data but unnecessary xml files can cause errors
        # jpg and xml files which belongs to another have to be named equally
        deleteList = []
        for file in FileList:
            if not file.endswith('.jpg') and not file.endswith('.xml'):
                deleteList.append(file)

        for file in deleteList:
            FileList.remove(file)

        FileList.sort()

        book: Book = None

        for i in range(0, len(FileList), 2):

            # This try-block checks if the data structure fulfill the necessary requirements:
            # jpg and xml files which belongs to another have to be named equally
            try:
                FileList[i+1]
            except IndexError:
                raise Exceptions.WrongFileStructureException('The file \'' + FileList[i] + '\' has no suitable'
                                                             ' image or xml file.')
            xmlFile = FileList[i]
            if FileList[i].endswith('.xml'):
                xmlFile = FileList[i]
                if FileList[i+1].endswith('.jpg'):
                    imgFile = FileList[i+1]
                    splitXML = xmlFile.split('.')
                    splitImg = imgFile.split('.')
                    if splitImg[0] != splitXML[0]:
                        raise Exceptions.WrongFileStructureException('The image file \'' + imgFile +'\' and xml file'
                                                                     ' \'' + xmlFile +'\' have no equal name.')
                else:
                    raise Exceptions.WrongFileStructureException('The xml file \'' + xmlFile +'\' has no suitable'
                                                                 ' image file.')
            elif FileList[i+1].endswith('.xml'):
                xmlFile = FileList[i+1]
                if FileList[i].endswith('.jpg'):
                    imgFile = FileList[i]
                    splitXML = xmlFile.split('.')
                    splitImg = imgFile.split('.')
                    if splitImg[0] != splitXML[0]:
                        raise Exceptions.WrongFileStructureException('The image file \'' + imgFile + '\' and xml file'
                                                                     ' \'' + xmlFile + '\' have no equal name.')
                else:
                    raise Exceptions.WrongFileStructureException('The xml file \'' + xmlFile + '\' has no suitable'
                                                                                               ' image file.')
            else:
                raise Exceptions.WrongFileStructureException('The image file \'' + xmlFile + '\' has no suitable'
                                                                                             ' xml file.')

            # Reads the xml file with the xml.etree.ElementTree package
            try:
                tree = ET.parse(xmlFile)
            except ET.ParseError as e:
                raise Exceptions.XMLParseError('The xml file \''+xmlFile+'\' couldn\'t be read because of a '
                                               'syntax error in the xml file. '+e.msg)

            root = tree.getroot()

            if root is None:
                raise Exceptions.XMLParseError('The xml file \'' + xmlFile + '\' is empty.')

            schemaLocation = root.get('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation')
            version = root.get('version')
            producer = root.get('producer')
            languages = root.get('languages')

            # initialize a book class if its not None
            if book is None:
                book: Book = Data.Book(self.directory, schemaLocation, version, producer, languages)

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
                                                   + xmlFile + '\' the \'width\' attribute is missing in the page tag.')
                if height is None:
                    raise Exceptions.XMLParseError('On the page ' + self.pagecount.__str__() + ' in the document \''
                                                   + xmlFile + '\' the \'height\' attribute is missing in the page tag.')
                if res is None:
                    raise Exceptions.XMLParseError('On the page ' + self.pagecount.__str__() + ' in the document \''
                                                   + xmlFile + '\' the \'resolution\' attribute '
                                                               'is missing in the page tag.')
                if oC is None:
                    raise Exceptions.XMLParseError('On the page ' + self.pagecount.__str__() + ' in the document \''
                                                   + xmlFile + '\' the \'original coords\' attribute'
                                                               ' is missing in the page tag.')

                page: Data.Page = Data.Page(width, height, res, oC, imgFile, xmlFile)

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
                                'On the page number '+self.pagecount.__str__()+' in the block number '+self.blockcount+
                                ' in the document \''+xmlFile+'\' the rectangle attribute \'l\' is missing.')
                        if t is None:
                            raise Exceptions.XMLParseError(
                                'On the page number ' + self.pagecount.__str__() + ' in the block number ' + self.blockcount +
                                ' in the document \'' + xmlFile + '\' the rectangle attribute \'t\' is missing.')
                        if r is None:
                            raise Exceptions.XMLParseError(
                                'On the page number ' + self.pagecount.__str__() + ' in the block number ' + self.blockcount +
                                ' in the document \'' + xmlFile + '\' the rectangle attribute \'r\' is missing.')
                        if b is None:
                            raise Exceptions.XMLParseError(
                                'On the page number ' + self.pagecount.__str__() + ' in the block number ' + self.blockcount +
                                ' in the document \'' + xmlFile + '\' the rectangle attribute \'b\' is missing.')

                        try:
                            rect: Data.Rect = Data.Rect(int(l), int(t), int(r), int(b))
                        except ValueError:
                            raise Exceptions.XMLParseError(
                                'On the page number ' + self.pagecount.__str__() + ' in the block number ' + self.blockcount +
                                ' in the document \'' + xmlFile + '\' one of the rectangle attributes is not a number')

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
                                                + self.blockcount.__str__() +' in the line number '+self.linecount.__str__()+
                                                ' in the document \'' + xmlFile +
                                                '\' the rectangle attribute \'l\' is missing.')
                                        if t is None:
                                            raise Exceptions.XMLParseError(
                                                'On the page number ' + self.pagecount.__str__() + ' in the block number'
                                                + self.blockcount.__str__() + ' in the line number ' + self.linecount.__str__() +
                                                ' in the document \'' + xmlFile +
                                                '\' the rectangle attribute \'t\' is missing.')
                                        if r is None:
                                            raise Exceptions.XMLParseError(
                                                'On the page number ' + self.pagecount.__str__() + ' in the block number'
                                                + self.blockcount.__str__() + ' in the line number ' + self.linecount.__str__() +
                                                ' in the document \'' + xmlFile +
                                                '\' the rectangle attribute \'r\' is missing.')
                                        if b is None:
                                            raise Exceptions.XMLParseError(
                                                'On the page number ' + self.pagecount.__str__() + ' in the block number'
                                                + self.blockcount.__str__() + ' in the line number ' + self.linecount.__str__() +
                                                ' in the document \'' + xmlFile +
                                                '\' the rectangle attribute \'b\' is missing.')

                                        try:
                                            rect: Data.Rect = Data.Rect(int(l), int(t), int(r), int(b))
                                        except ValueError:
                                            raise Exceptions.XMLParseError(
                                                'On the page number ' + self.pagecount.__str__() + ' in the block number'
                                                + self.blockcount.__str__() + ' in the line number ' + self.linecount.__str__() +
                                                ' in the document \'' + xmlFile +
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
            if (((i//2)+1)%10) == 0:
                print('Documents readed: ' + ((i//2)+1).__str__() + ' of ' + (len(FileList)//2).__str__())

        print(' ')
        print('Book was read!')

        if not book.pages:
            raise Exceptions.XMLParseError('In this selected directory there is no suitable data!')

        return book

