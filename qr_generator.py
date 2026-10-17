import qrcode

data="https://pornhub.com/"

qr=qrcode.make(data)
qr.save("qrcode.png")

print("QR code generated and saved as qrcode.png")
