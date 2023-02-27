import PyPDF2
import datetime


def load_txt(file):
    fp = open(file, "r")
    draws = []
    for line in fp.readlines():
        draws.append(line.split())
        print(line.split())

    return draws


load_txt("roomdraw-2017.txt")
"""
fp = open('roomdraw-2017.txt', 'r')
draws = []
for line in fp.readlines():
    draws.append(line.split())
print(draws)

# creating a pdf file object  
pdfFileObj = open('AvailableRoomsList19-20.pdf', 'rb')  
    
# creating a pdf reader object  
pdfReader = PyPDF2.PdfFileReader(pdfFileObj) 
    
# creating a page object  
pageObj = pdfReader.getPage(0)  
    
# extracting text from page  
text = pageObj.extractText()
print(text)
    
# closing the pdf file object  
pdfFileObj.close()  
"""
