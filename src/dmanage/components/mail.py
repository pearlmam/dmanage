# -*- coding: utf-8 -*-
import smtplib 
import ssl
import socket
import os

class Mail():
    def __init__(self,senderMail,password):
        self.smtpServer = 'smtp.gmail.com'
        self.port = 465
        self.senderMail = senderMail
        self.password = password
        self.hostname = socket.gethostname()
        
    def send(self,email,subject,content):
        sslContext = ssl.create_default_context()
        server = smtplib.SMTP_SSL(self.smtpServer, self.port, context=sslContext)
        server.login(self.senderMail, self.password)
        result = server.sendmail(self.senderMail, email, f"Subject: {subject}\n{content}")
        server.quit()
        return result
    
    def send_done(self, sendtoMail, subject='', content='', outputFile=None):
        if subject == '':
            subject = '%s: Simulation Complete'%self.hostname

        if type(outputFile) != type(None):
            #outputFile = os.path.join(os.getcwd(),'') + outputFile
            
            if os.path.exists(outputFile):
                breakText = '--------------------------------------------------------------'
                file = open(outputFile, "r")
                content = content + "\n%s\nContents Of file: '%s'\n%s\n%s"%(breakText,outputFile,breakText,file.read())
                file.close()
        result = self.send(sendtoMail,subject,content)
        return result