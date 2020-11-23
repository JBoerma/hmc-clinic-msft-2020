from datetime import datetime

def getTime():
    return datetime.now().strftime("%Y/%m/%d %H:%M:%S")