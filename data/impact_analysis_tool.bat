@echo off
echo Set objOutlook = CreateObject("Outlook.Application") > email.vbs
echo Set objMail = objOutlook.CreateItem(0) >> email.vbs
echo objMail.To = "BOT-Engineering.ENG-Navigator@bcn.bosch.com" >> email.vbs
echo objMail.Subject = "Navigator-ImpactAnalysis" >> email.vbs
echo objMail.Body = "Dear Navigator team," ^& vbCrLf ^& vbCrLf ^& "New Issue-FD :" ^& vbCrLf ^& "Analyzed Issue-FD :" ^& vbCrLf ^& vbCrLf ^& "Regard," >> email.vbs
echo objMail.Display >> email.vbs
start /wait email.vbs
del email.vbs

