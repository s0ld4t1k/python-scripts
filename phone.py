import phonenumbers
from phonenumbers import timezone,geocoder,carrier

def analyze(number):
    x=phonenumbers.parse(number)
    timeZone=timezone.time_zones_for_number(x)
    Carrier=carrier.name_for_number(x,'ru')
    Region=geocoder.description_for_number(x,'ru')
    valid=phonenumbers.is_valid_number(x)
    possible=phonenumbers.is_possible_number(x)
    print(x,timeZone,Carrier,Region,f'Valid: {valid}',f'Possible: {possible}',sep='\n')

text='This numbers for contact +99361400905 and +99361400904'
numbers=phonenumbers.PhoneNumberMatcher(text,"TM")

for number in numbers:
    print(number.raw_string)
    analyze(number.raw_string)
    print('-'*50)
